import types
import pytest
import importlib

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

def test_cmd_dodaj(mocker):
    import telegram_bot

    mock_message = mocker.Mock()
    mock_msg = mocker.Mock()
    mock_reply = mocker.patch.object(telegram_bot.bot, "reply_to", return_value=mock_msg)
    register_next = mocker.patch.object(telegram_bot.bot, "register_next_step_handler")

    telegram_bot.cmd_dodaj(mock_message)

    mock_reply.assert_called_once_with(mock_message, "Podaj treść notatki, którą chcesz dodać:")
    register_next.assert_called_once_with(mock_msg, telegram_bot.save_new_note)
