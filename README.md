# receipt-splitter

Aplikacja Django, która czyta paragon z Biedronki w formacie PDF, rozpoznaje pozycje przez OCR i dzieli koszty między kilka osób.

Powstała z konkretnej potrzeby: po wspólnych zakupach trzeba rozliczyć, kto ile jest komu winien. Ręczne przepisywanie 24 pozycji z paragonu i liczenie w kalkulatorze zajmuje kwadrans i łatwo się pomylić — zwłaszcza przy rabatach i kaucji za butelki.

## Jak to działa

```
PDF paragonu  →  rasteryzacja 300 DPI  →  tesseract (pol)  →  parser  →  baza  →  podział kosztów
```

1. **Wgrywasz PDF** — paragon z Biedronki nie ma warstwy tekstowej, to obrazek, więc konieczny jest OCR.
2. **Parser wyciąga pozycje** — nazwa, ilość, cena jednostkowa, wartość. Rozpoznaje też dwie rzeczy, które paragon zapisuje w osobnych liniach:
   - **rabat** — linia `Rabat -7,50` pod pozycją, a pod nią cena po obniżce
   - **kaucja** za butelki — osobna pozycja `But Plastik kaucja`, doliczana do napoju, którego dotyczy („kto pije, ten płaci")
3. **Dodajesz osoby** i zaznaczasz ptaszkami, kto co kupował.
4. **Klikasz „policz"** — koszt każdej pozycji dzieli się równo między zaznaczone osoby.

Grosze z zaokrąglenia trafiają do pierwszych osób na liście, więc **suma udziałów zawsze równa się kwocie z paragonu** — nic nie ginie i nic się nie dubluje.

## Stack

| | |
|---|---|
| backend | Python 3.13, Django 6.1 |
| baza | PostgreSQL 16 |
| OCR | pdfplumber (rasteryzacja) + pytesseract z pakietem `pol` |
| testy | pytest, pytest-django, pytest-cov |
| jakość | ruff |
| uruchomienie | Docker + docker-compose, gunicorn |
| CI | GitHub Actions |

## Uruchomienie

### Docker

```bash
cp .env.example .env      # uzupełnij wartości
docker-compose up --build
```

Aplikacja stoi na `http://localhost:8000/receipts/`. Tesseract wraz z polskim pakietem językowym jest instalowany w obrazie, więc OCR działa bez konfiguracji na hoście.

### Lokalnie

Wymaga zainstalowanego tesseracta z polskim pakietem:

```bash
brew install tesseract tesseract-lang     # macOS
```

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py runserver
```

## Testy

```bash
pytest
```

```bash
pytest --cov=receipts --cov-report=term-missing
```

44 testy, pokrycie 100%. CI wymaga minimum 85% i failuje poniżej tego progu.

Testy widoków podmieniają funkcję OCR, więc chodzą w ułamku sekundy i nie potrzebują tesseracta. Logika parsowania jest testowana na prawdziwym, zapisanym wyniku OCR z paragonu (`tests/fixtures/ocr_samples/`).

Osobno stoi test integracyjny, który przechodzi całą drogę od pliku PDF przez prawdziwego tesseracta aż po gotowe pozycje — dowód, że pipeline działa na czystej maszynie:

```bash
pytest -m slow
```

## Struktura

```
receipts/
├── models.py      Receipt, Person, LineItem (M2M shared_by)
├── ocr.py         rasteryzacja PDF + tesseract — jedyny moduł dotykający świata zewnętrznego
├── parsing.py     czyste funkcje: tekst OCR → lista pozycji (bez Django, bez I/O)
├── services.py    podział kosztów z obsługą zaokrągleń
├── views.py       upload → podgląd z podziałem → lista paragonów
└── templates/
tests/
├── test_parsing.py    parser na prawdziwym wyniku OCR
├── test_services.py   arytmetyka podziału
├── test_views.py      widoki z podmienionym OCR
├── test_models.py     relacje i pola wyliczane
└── test_ocr.py        integracyjny: prawdziwy PDF przez tesseract (-m slow)
```

Podział na moduły idzie po granicy wejścia-wyjścia: `parsing.py` i `services.py` to czyste funkcje, które testuje się bez bazy i bez plików. Cała nieprzewidywalność (OCR, dysk, HTTP) siedzi w `ocr.py` i `views.py`.

## Znane ograniczenia

- **Tylko paragony z Biedronki** — parser jest dopasowany do jej układu kolumn
- **Tylko PDF**, nie zdjęcie z telefonu — cyfrowy paragon daje czysty OCR bez potrzeby obróbki obrazu
- **Nazwy produktów bywają ucięte** (`SkyrBakom-WedWiś3(`) — tak są drukowane na paragonie, to nie błąd odczytu
- **Podział jest równy** między zaznaczone osoby — nie da się rozdzielić 12 sztuk coli w proporcji 5 do 7
- Brak logowania — narzędzie jednoosobowe, uruchamiane lokalnie
