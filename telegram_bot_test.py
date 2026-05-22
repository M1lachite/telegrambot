import types
import pytest
import importlib
from datetime import datetime, timezone
import os

def make_db_mock(mocker, rows=None):
    """Return a mocked get_db_connection that yields given cursor rows."""
    mock_conn = mocker.Mock()
    mock_cur = mocker.Mock()
    mock_conn.cursor.return_value = mock_cur
    mock_cur.fetchall.return_value = rows or []
    mocker.patch("telegram_bot.get_db_connection", return_value=mock_conn)
    return mock_conn, mock_cur

def test_get_db_connection(mocker):
    import telegram_bot
    mock_connect = mocker.patch("psycopg2.connect")

    telegram_bot.get_db_connection()

    mock_connect.assert_called_once_with(
        host=os.environ["DB_HOST"],
        port=os.environ.get("DB_PORT", "5432"),
        dbname=os.environ["DB_NAME"],
        user=os.environ["DB_USER"],
        password=os.environ["DB_PASSWORD"]
    )


def test_load_notes_returns_rows(mocker):
    ts = datetime(2024, 1, 15, 12, 0, 0, tzinfo=timezone.utc)
    rows = [(1, "Anna", "Pierwsza notatka", ts)]

    make_db_mock(mocker, rows=rows)

    import telegram_bot
    result = telegram_bot.load_notes()

    assert len(result) == 1
    assert result[0]["id"] == 1
    assert result[0]["user"] == "Anna"
    assert result[0]["note"] == "Pierwsza notatka"
    assert result[0]["ts"] == ts.isoformat()


def test_load_notes_empty_table(mocker):
    make_db_mock(mocker, rows=[])

    import telegram_bot
    result = telegram_bot.load_notes()

    assert result == []


def test_load_notes_multiple_rows(mocker):
    ts1 = datetime(2024, 1, 1, tzinfo=timezone.utc)
    ts2 = datetime(2024, 1, 2, tzinfo=timezone.utc)
    rows = [
        (1, "Ala", "Notatka pierwsza", ts1),
        (2, "Jan", "Notatka druga", ts2),
    ]
    make_db_mock(mocker, rows=rows)

    import telegram_bot
    result = telegram_bot.load_notes()

    assert len(result) == 2
    assert result[0]["user"] == "Ala"
    assert result[1]["user"] == "Jan"


def test_load_notes_closes_connection(mocker):
    mock_conn, mock_cur = make_db_mock(mocker, rows=[])

    import telegram_bot
    telegram_bot.load_notes()

    mock_cur.close.assert_called_once()
    mock_conn.close.assert_called_once()


def test_save_notes_executes_insert(mocker):
    mock_conn, mock_cur = make_db_mock(mocker)

    import telegram_bot
    telegram_bot.save_notes("TestUser", "Treść notatki")

    mock_cur.execute.assert_called_once_with(
        "INSERT INTO notes (username, content) VALUES (%s, %s)",
        ("TestUser", "Treść notatki")
    )
    mock_conn.commit.assert_called_once()


def test_save_notes_closes_connection(mocker):
    mock_conn, mock_cur = make_db_mock(mocker)

    import telegram_bot
    telegram_bot.save_notes("User", "Note")

    mock_cur.close.assert_called_once()
    mock_conn.close.assert_called_once()


def test_save_notes_empty_string(mocker):
    """save_notes powinno zaakceptować pusty string — walidacja jest wyżej."""
    mock_conn, mock_cur = make_db_mock(mocker)

    import telegram_bot
    telegram_bot.save_notes("User", "")

    mock_cur.execute.assert_called_once()


@pytest.mark.parametrize(
    "first_name, username, expected",
    [
        ("Anna", "ann123", "Anna @ann123"),
        ("Bartek", None, "Bartek"),
        (None, "userX", "@userX"),
        (None, None, ""),
    ]
)
def test_build_user_display(first_name, username, expected):
    import telegram_bot
    user = types.SimpleNamespace(first_name=first_name, username=username)
    result = telegram_bot.build_user_display(user)
    assert result == expected


@pytest.mark.parametrize(
    "lines, expected_calls",
    [
        ([], 0),
        (["Line 1", "Line 2", "Line 3"], 1),
        (["x" * 3999], 1),
        (["x" * 3995, "123456"], 2),
        (["x" * 2000] * 3, 3),
    ],
)
def test_send_long_message_cases(mocker, lines, expected_calls):
    import telegram_bot
    mock_send = mocker.patch.object(telegram_bot.bot, "send_message")
    chat_id = 123

    telegram_bot.send_long_message(chat_id, lines)

    assert mock_send.call_count == expected_calls

    for call in mock_send.call_args_list:
        sent_text = call.args[1]
        assert len(sent_text) <= 4000


def fake_init(self, *args, **kwargs):
    self.message_handlers = []


def test_cmd_bot_sends_help_message(mocker):
    mocker.patch("telebot.TeleBot.__init__", fake_init)

    import telegram_bot
    importlib.reload(telegram_bot)

    mock_send = mocker.patch.object(telegram_bot.bot, "send_message")
    mock_message = types.SimpleNamespace(chat=types.SimpleNamespace(id=123456))
    telegram_bot.cmd_bot(mock_message)

    expected_text = (
        "<b>Lista komend:</b>\n"
        "/notatki – pokaż wszystkie notatki\n"
        "/dodaj – dodaj nową notatkę\n"
        "/ostatnie – pokaż 10 ostatnich notatek (lub /ostatnie 5)\n"
        "/hello - przywitanie i krótki opis funkcjonalności bota"
    )

    mock_send.assert_called_once_with(123456, expected_text)


def test_cmd_hello_sends_description(mocker):
    import telegram_bot
    mock_send = mocker.patch.object(telegram_bot.bot, "send_message")
    mock_message = types.SimpleNamespace(chat=types.SimpleNamespace(id=999))

    telegram_bot.cmd_hello(mock_message)

    mock_send.assert_called_once()
    sent_text = mock_send.call_args.args[1]
    assert "Notatnik Telegramowy" in sent_text
    assert "/notatki" in sent_text
    assert "/dodaj" in sent_text
    assert "/ostatnie" in sent_text


def test_cmd_notatki_variants(mocker):
    import telegram_bot

    mock_message = mocker.Mock()
    mock_message.chat.id = 123

    mocker.patch("telegram_bot.load_notes", return_value=[])
    reply_to = mocker.patch.object(telegram_bot.bot, "reply_to")
    send_long = mocker.patch("telegram_bot.send_long_message")

    telegram_bot.cmd_notatki(mock_message)

    reply_to.assert_called_once_with(mock_message, "Brak notatek.")
    send_long.assert_not_called()

    reply_to.reset_mock()
    send_long.reset_mock()
    mocker.patch("telegram_bot.load_notes", return_value=[
        {"user": "Ala", "note": "Krótka notatka"},
        {"user": "Jan", "note": "Długa notatka która przekracza 80 znaków. " + "x" * 40}
    ])

    telegram_bot.cmd_notatki(mock_message)

    skrot = ("Długa notatka która przekracza 80 znaków. " + "x" * 40)[:77] + "…"

    expected_lines = [
        "<b>Lista notatek:</b>",
        f"1. <i>Jan</i>: {skrot}",
        "2. <i>Ala</i>: Krótka notatka"
    ]

    send_long.assert_called_once_with(123, expected_lines)
    reply_to.assert_not_called()


def test_cmd_dodaj(mocker):
    import telegram_bot

    mock_message = mocker.Mock()
    mock_msg = mocker.Mock()
    mock_reply = mocker.patch.object(telegram_bot.bot, "reply_to", return_value=mock_msg)
    register_next = mocker.patch.object(telegram_bot.bot, "register_next_step_handler")

    telegram_bot.cmd_dodaj(mock_message)

    mock_reply.assert_called_once_with(mock_message, "Podaj treść notatki, którą chcesz dodać:")
    register_next.assert_called_once_with(mock_msg, telegram_bot.save_new_note)


def test_save_new_note_empty_text(mocker):
    import telegram_bot
    reply_to = mocker.patch.object(telegram_bot.bot, "reply_to")

    empty_message = mocker.Mock()
    empty_message.text = "   "

    telegram_bot.save_new_note(empty_message)

    reply_to.assert_called_once_with(
        empty_message, "⚠️ Notatka nie może być pusta. Spróbuj ponownie."
    )


def test_save_new_note_valid(mocker):
    import telegram_bot
    reply_to = mocker.patch.object(telegram_bot.bot, "reply_to")

    mocker.patch("telegram_bot.build_user_display", return_value="TestUser")
    save_notes_mock = mocker.patch("telegram_bot.save_notes")

    message = mocker.Mock()
    message.text = "To jest ważna notatka"

    telegram_bot.save_new_note(message)

    # save_notes powinno dostać (user, note) — nie listę jak wcześniej
    save_notes_mock.assert_called_once_with("TestUser", "To jest ważna notatka")
    reply_to.assert_called_once_with(
        message, "✅ Dodano notatkę od <b>TestUser</b>"
    )


def test_cmd_ostatnie_variants(mocker):
    import telegram_bot

    mock_message = mocker.Mock()
    mock_message.chat.id = 123
    send_message = mocker.patch.object(telegram_bot.bot, "send_message")
    reply_to = mocker.patch.object(telegram_bot.bot, "reply_to")
    mock_message.text = "/ostatnie"
    mocker.patch("telegram_bot.load_notes", return_value=[])

    telegram_bot.cmd_ostatnie(mock_message)

    reply_to.assert_called_once_with(mock_message, "Brak notatek.")
    send_message.assert_not_called()

    reply_to.reset_mock()
    send_message.reset_mock()
    mock_message.text = "/ostatnie 2"
    mocker.patch("telegram_bot.load_notes", return_value=[
        {"user": "U1", "note": "Note 1"},
        {"user": "U2", "note": "Note 2"},
        {"user": "U3", "note": "Note 3"},
    ])

    telegram_bot.cmd_ostatnie(mock_message)

    expected_text = "\n".join([
        "<b>Ostatnie notatki:</b>",
        "1. <i>U3</i>: Note 3",
        "2. <i>U2</i>: Note 2"
    ])
    send_message.assert_called_once_with(123, expected_text)

    reply_to.reset_mock()
    send_message.reset_mock()
    mock_message.text = "/ostatnie abc"
    mocker.patch("telegram_bot.load_notes", return_value=[
        {"user": f"U{i}", "note": f"Note {i}"} for i in range(1, telegram_bot.MAX_LAST + 1)
    ])

    telegram_bot.cmd_ostatnie(mock_message)

    assert send_message.call_count == 1
    assert "Ostatnie notatki" in send_message.call_args.args[1]

    reply_to.reset_mock()
    send_message.reset_mock()
    mock_message.text = "/ostatnie"
    mocker.patch("telegram_bot.load_notes", return_value=[
        {"user": "Test", "note": "A" * 90}
    ])

    telegram_bot.cmd_ostatnie(mock_message)

    expected_line = "1. <i>Test</i>: " + "A" * 77 + "…"
    send_message.assert_called_once_with(
        123,
        "<b>Ostatnie notatki:</b>\n" + expected_line
    )
