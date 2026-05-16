import json
import types
import pytest
import importlib


def test_load_notes_file_exists(mocker):
    fake_data = [{"title": "Note 1"}]
    json_content = json.dumps(fake_data)
    mock_bot = mocker.Mock()
    mocker.patch("telebot.TeleBot", return_value=mock_bot)

    mocker.patch("telegram_bot.os.path.exists", return_value=True)
    mock_open = mocker.mock_open(read_data=json_content)
    mocker.patch("telegram_bot.open", mock_open)

    from telegram_bot import load_notes, NOTES_FILE

    result = load_notes()

    assert result == fake_data
    mock_open.assert_called_once_with(NOTES_FILE, "r", encoding="utf-8")


def test_load_notes_file_does_not_exist(mocker):
    mocker.patch("telegram_bot.os.path.exists", return_value=False)

    import telegram_bot

    result = telegram_bot.load_notes()

    assert result == []


def test_save_notes_writes_correct_json(mocker):
    notes = [{"title": "Test", "content": "Something"}, {"title": "Another", "content": "Else"}]
    expected_output = json.dumps(notes, ensure_ascii=False, indent=2)

    mock_file = mocker.mock_open()
    mocker.patch("telegram_bot.open", mock_file)

    from telegram_bot import save_notes, NOTES_FILE

    save_notes(notes)

    mock_file.assert_called_once_with(NOTES_FILE, "w", encoding="utf-8")
    written = "".join(call.args[0] for call in mock_file().write.call_args_list)
    assert written == expected_output


def test_save_empty_list(mocker):
    notes = []
    expected_output = json.dumps(notes, ensure_ascii=False, indent=2)

    mock_file = mocker.mock_open()
    mocker.patch("telegram_bot.open", mock_file)

    from telegram_bot import save_notes

    save_notes(notes)

    written = "".join(call.args[0] for call in mock_file().write.call_args_list)
    assert written == expected_output


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


def test_save_new_note_variants(mocker):
    import telegram_bot

    reply_to = mocker.patch.object(telegram_bot.bot, "reply_to")

    empty_message = mocker.Mock()
    empty_message.text = "   "
    telegram_bot.save_new_note(empty_message)

    reply_to.assert_called_once_with(
        empty_message, "⚠️ Notatka nie może być pusta. Spróbuj ponownie."
    )

    reply_to.reset_mock()

    message = mocker.Mock()
    message.text = "To jest ważna notatka"
    message.from_user = mocker.Mock()
    mocker.patch("telegram_bot.build_user_display", return_value="TestUser")
    mock_notes = []
    mocker.patch("telegram_bot.load_notes", return_value=mock_notes)
    save_notes_mock = mocker.patch("telegram_bot.save_notes")

    telegram_bot.save_new_note(message)

    assert len(mock_notes) == 1
    assert mock_notes[0]["user"] == "TestUser"
    assert mock_notes[0]["note"] == "To jest ważna notatka"
    assert "ts" in mock_notes[0]
    save_notes_mock.assert_called_once_with(mock_notes)
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