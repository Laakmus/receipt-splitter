#!/bin/bash
# Uruchamia i zatrzymuje Receipt Splitter jednym kliknieciem.
# Pierwsze uruchomienie doinstalowuje brakujace narzedzia - moze potrwac kilkanascie minut.

cd "$(dirname "$0")" || exit 1

PID_FILE=".server.pid"
PORT=8000
URL="http://127.0.0.1:$PORT/"

# --- 1. Czy aplikacja juz dziala? Wtedy klikniecie ja zatrzymuje ---------

if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if kill -0 "$PID" 2>/dev/null; then
        echo "Zatrzymuję aplikację..."
        # runserver uruchamia proces potomny - zabijamy cala grupe
        pkill -P "$PID" 2>/dev/null
        kill "$PID" 2>/dev/null
        rm -f "$PID_FILE"
        echo "Zatrzymane. Kliknij ikonkę ponownie, żeby uruchomić."
        sleep 2
        exit 0
    fi
    # nieaktualny plik po nieczystym zamknieciu
    rm -f "$PID_FILE"
fi

echo "======================================"
echo "  Receipt Splitter — uruchamianie"
echo "======================================"
echo

# --- 2. Brakujace narzedzia ---------------------------------------------

if ! command -v brew > /dev/null 2>&1; then
    echo "Brakuje menedżera Homebrew — instaluję go teraz."
    echo "UWAGA: za chwilę system poprosi o hasło do Twojego Maca."
    echo "Hasło nie wyświetla się podczas wpisywania — to normalne."
    echo
    /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || {
        echo "Nie udało się zainstalować Homebrew. Sprawdź połączenie z internetem."
        read -r -p "Naciśnij Enter, żeby zamknąć."
        exit 1
    }
    # swiezy Homebrew nie jest jeszcze w PATH tej sesji
    eval "$(/opt/homebrew/bin/brew shellenv 2>/dev/null || /usr/local/bin/brew shellenv)"
fi

PYTHON_BIN=$(command -v python3.13 || command -v python3.14 || true)
if [ -z "$PYTHON_BIN" ]; then
    echo "Instaluję Pythona — potrwa kilka minut..."
    brew install python@3.13 || exit 1
    PYTHON_BIN=$(command -v python3.13)
fi

if ! command -v tesseract > /dev/null 2>&1; then
    echo "Instaluję tesseract (rozpoznawanie tekstu) — potrwa kilka minut..."
    brew install tesseract tesseract-lang || exit 1
elif ! tesseract --list-langs 2>/dev/null | grep -q "^pol$"; then
    echo "Instaluję polski pakiet językowy dla tesseract..."
    brew install tesseract-lang || exit 1
fi

# --- 3. Srodowisko Pythona ----------------------------------------------

if [ ! -d ".venv" ]; then
    echo "Przygotowuję środowisko Pythona..."
    "$PYTHON_BIN" -m venv .venv || exit 1
fi

if [ ! -f ".venv/.installed" ]; then
    echo "Instaluję biblioteki — to jednorazowe, potrwa kilka minut..."
    .venv/bin/pip install --quiet --upgrade pip
    .venv/bin/pip install --quiet -r requirements.txt || {
        echo "Nie udało się zainstalować bibliotek."
        read -r -p "Naciśnij Enter, żeby zamknąć."
        exit 1
    }
    touch .venv/.installed
fi

# --- 4. Baza danych -----------------------------------------------------

export DB_ENGINE=sqlite

echo "Przygotowuję bazę danych..."
.venv/bin/python manage.py migrate --no-input > /dev/null || {
    echo "Nie udało się przygotować bazy danych."
    read -r -p "Naciśnij Enter, żeby zamknąć."
    exit 1
}

# --- 5. Serwer ----------------------------------------------------------

echo "Uruchamiam aplikację..."
.venv/bin/python manage.py runserver "127.0.0.1:$PORT" --noreload > /tmp/receipt-splitter.log 2>&1 &
echo $! > "$PID_FILE"

# czekamy az serwer zacznie odpowiadac - do 30 sekund
for _ in $(seq 1 60); do
    if curl -s -o /dev/null "$URL"; then
        break
    fi
    sleep 0.5
done

if ! curl -s -o /dev/null "$URL"; then
    echo "Aplikacja nie odpowiada. Szczegóły błędu:"
    tail -20 /tmp/receipt-splitter.log
    rm -f "$PID_FILE"
    read -r -p "Naciśnij Enter, żeby zamknąć."
    exit 1
fi

open "$URL"

echo
echo "======================================"
echo "  Gotowe — aplikacja działa"
echo "======================================"
echo
echo "Przeglądarka powinna otworzyć się sama."
echo "Gdyby nie: wejdź na $URL"
echo
echo "Żeby ZATRZYMAĆ aplikację — kliknij tę samą ikonkę jeszcze raz."
echo "To okno możesz zamknąć, aplikacja będzie działać dalej."
echo
sleep 3
