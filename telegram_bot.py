import telebot
from telebot import types
import os
import json
import time
from typing import List
from datetime import datetime, timezone

API_KEY = os.environ.get("TELEGRAM_API_KEY", "")
bot = telebot.TeleBot(API_KEY, parse_mode="HTML")

NOTES_FILE = "notes.json"
MAX_LAST = 10

# ===== Funkcje pomocnicze ====================================================

def load_notes() -> List[dict]:
    """Load the list of notes from *NOTES_FILE* (may be empty)."""
    if os.path.exists(NOTES_FILE):
        with open(NOTES_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []


def save_notes(notes: List[dict]) -> None:
    """Save *notes* to *NOTES_FILE* in UTF-8 JSON format."""
    with open(NOTES_FILE, "w", encoding="utf-8") as f:
        json.dump(notes, f, ensure_ascii=False, indent=2)


def build_user_display(user: types.User) -> str:
    """Return a concise representation of a Telegram user."""
    name = user.first_name or ""
    username = f"@{user.username}" if user.username else ""
    return " ".join(part for part in (name, username) if part).strip()


def send_long_message(chat_id: int, lines: List[str]) -> None:
    """Send *lines* as one or more messages, each ≤ 4000 characters."""
    chunk: List[str] = []
    current_len = 0

    for line in lines:
        # +1 → account for the newline that will be inserted when joining
        if current_len + len(line) + 1 > 4000:
            bot.send_message(chat_id, "\n".join(chunk))
            chunk = [line]
            current_len = len(line) + 1
        else:
            chunk.append(line)
            current_len += len(line) + 1

    if chunk:
        bot.send_message(chat_id, "\n".join(chunk))

# ---------------------------------------------------------------------------
# Command handlers
# ---------------------------------------------------------------------------


@bot.message_handler(commands=["bot"])
def cmd_bot(message: types.Message) -> None:
    """Show help."""
    bot.send_message(
        message.chat.id,
        (
            "<b>Lista komend:</b>\n"
            "/notatki – pokaż wszystkie notatki\n"
            "/dodaj – dodaj nową notatkę\n"
            "/ostatnie – pokaż 10 ostatnich notatek (lub /ostatnie 5)\n"
            "/hello - przywitanie i krótki opis funkcjonalności bota"
        ),
    )


# ------------------------------ /notatki -----------------------------------


@bot.message_handler(commands=["notatki"])
def cmd_notatki(message: types.Message) -> None:
    """Display all saved notes."""
    notes = load_notes()
    if not notes:
        bot.reply_to(message, "Brak notatek.")
        return

    lines: List[str] = ["<b>Lista notatek:</b>"]
    for idx, entry in enumerate(reversed(notes), 1):
        note_text = entry["note"] if len(entry["note"]) <= 80 else entry["note"][:77] + "…"
        lines.append(f"{idx}. <i>{entry['user']}</i>: {note_text}")

    send_long_message(message.chat.id, lines)


# ------------------------------- /dodaj ------------------------------------


@bot.message_handler(commands=["dodaj"])
def cmd_dodaj(message: types.Message) -> None:
    """Prompt user to add a new note (next step handler)."""
    msg = bot.reply_to(message, "Podaj treść notatki, którą chcesz dodać:")
    bot.register_next_step_handler(msg, save_new_note)


def save_new_note(message: types.Message) -> None:
    """Callback that actually saves the new note."""
    text = (message.text or "").strip()
    if not text:
        bot.reply_to(message, "⚠️ Notatka nie może być pusta. Spróbuj ponownie.")
        return

    user_display = build_user_display(message.from_user)
    notes = load_notes()
    notes.append(
        {
            "user": user_display,
            "note": text,
            "ts": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
    save_notes(notes)

    bot.reply_to(message, f"✅ Dodano notatkę od <b>{user_display}</b>")


# ----------------------------- /ostatnie -----------------------------------


@bot.message_handler(commands=["ostatnie", "lista"])
def cmd_ostatnie(message: types.Message) -> None:
    """Return the last *N* notes (default ``MAX_LAST``)."""
    parts = message.text.split()
    try:
        n = int(parts[1]) if len(parts) > 1 else MAX_LAST
    except (ValueError, IndexError):
        n = MAX_LAST

    notes = load_notes()[-n:]  # last n entries
    if not notes:
        bot.reply_to(message, "Brak notatek.")
        return

    lines: List[str] = ["<b>Ostatnie notatki:</b>"]
    for idx, entry in enumerate(reversed(notes), 1):
        note_text = entry["note"] if len(entry["note"]) <= 80 else entry["note"][:77] + "…"
        lines.append(f"{idx}. <i>{entry['user']}</i>: {note_text}")

    bot.send_message(message.chat.id, "\n".join(lines))

@bot.message_handler(commands=["hello"])
def cmd_hello(message: types.Message) -> None:
    """Return a short description of the bot's functionality."""
    bot.send_message(
        message.chat.id,
        (
            "🤖 <b>Notatnik Telegramowy</b>\n"
            "Ten bot pozwala zapisywać i przeglądać krótkie notatki.\n"
            "Użyj /notatki, aby zobaczyć wszystkie notatki,\n"
            "/dodaj, aby dodać nową notatkę,\n"
            "lub /ostatnie, aby wyświetlić ostatnie wpisy."
        ),
    )


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

if __name__ == "__main__":  # pragma: no cover
    bot.infinity_polling()
