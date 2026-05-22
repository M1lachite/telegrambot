#!/bin/bash
#
# pytest.sh
# Ogólny skrypt, który tworzy czyste wirtualne środowisko i uruchamia pytest.
# Przeznaczony do użycia w potoku Jenkins GitHub jako:
# sh("${JENKINS_HOME}/scripts/pytest.sh ${WORKSPACE}")
#
# Użycie: Wywołaj ten skrypt z katalogiem głównym projektu jako pierwszym argumentem.
# Przykład: /var/lib/jenkins/scripts/pytest.sh /var/lib/jenkins/workspace/twoja-aplikacja

set -e  # zakończ skrypt przy pierwszym błędzie

if [ -z "$1" ]; then
  echo "Użycie: ${0##*/} <katalog_projektu>"
  exit 1
fi

PROJECT_DIR="$1"
VIRTUAL_ENV_DIR="${PROJECT_DIR}/venv"

echo "--- Rozpoczęcie skryptu Pytest ---"
echo "Katalog projektu: ${PROJECT_DIR}"
echo "Katalog środowiska wirtualnego: ${VIRTUAL_ENV_DIR}"

# Przejdź do katalogu projektu
cd "$PROJECT_DIR" || { echo "BŁĄD: Nie udało się zmienić katalogu na ${PROJECT_DIR}. Zakończenie."; exit 1; }

# Usuń istniejące środowisko wirtualne
if [ -d "$VIRTUAL_ENV_DIR" ]; then
  echo "Usuwanie istniejącego środowiska wirtualnego: ${VIRTUAL_ENV_DIR}"
  rm -rf "$VIRTUAL_ENV_DIR"
fi

# Utwórz nowe środowisko wirtualne
echo "Tworzenie nowego środowiska wirtualnego w ${VIRTUAL_ENV_DIR}"
python3 -m venv "$VIRTUAL_ENV_DIR" || { echo "BŁĄD: Nie udało się utworzyć środowiska wirtualnego. Zakończenie."; exit 1; }

# Aktywuj środowisko wirtualne pod linux
source "${VIRTUAL_ENV_DIR}/bin/activate" || { echo "BŁĄD: Nie udało się aktywować środowiska wirtualnego. Zakończenie."; exit 1; }
# Aktywuj środowisko wirtualne pod windows
#source venv/Scripts/activate
echo "Środowisko wirtualne aktywowane."

# Ustaw zmienne środowiskowe potrzebne do importu modułu (bez prawdziwej bazy)
export TELEGRAM_API_KEY="${TELEGRAM_API_KEY:-123456:dummy}"
export DB_HOST="${DB_HOST:-localhost}"
export DB_PORT="${DB_PORT:-5432}"
export DB_NAME="${DB_NAME:-testdb}"
export DB_USER="${DB_USER:-testuser}"
export DB_PASSWORD="${DB_PASSWORD:-testpassword}"

# Zaktualizuj pip i zainstaluj zależności
echo "Instalowanie zależności projektu..."
pip install -e . || { echo "BŁĄD: Nie udało się zainstalować zależności. Zakończenie."; exit 1; }
echo "Zależności zainstalowane."

# Uruchom testy pytest
echo "Uruchamianie testów pytest..."
pytest --cov=telegram_bot || { echo "BŁĄD: Testy pytest nie powiodły się. Zakończenie."; exit 1; }
echo "Testy pytest zakończone pomyślnie."

# Dezaktywuj środowisko wirtualne
deactivate
echo "Środowisko wirtualne dezaktywowane."

echo "--- Skrypt Pytest Zakończony ---"
