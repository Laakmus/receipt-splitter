"""Test integracyjny: prawdziwy PDF przechodzi przez tesseract i parser.

Wymaga zainstalowanego tesseracta z pakietem 'pol'. Uruchamiany osobno
(pytest -m slow) oraz w CI, gdzie tesseract instalowany jest jako krok pipeline'u.
"""
from decimal import Decimal
from pathlib import Path

import pytest

from receipts.ocr import extract_receipt_text, rasterize_pdf, run_ocr
from receipts.parsing import clean_lines, find_items_section, fit_price_to_item, merge_deposits

SAMPLE_PDF = Path(__file__).parent / "fixtures" / "sample_receipt.pdf"

pytestmark = pytest.mark.slow


def test_rasterize_pdf_returns_one_image_per_page():
    images = rasterize_pdf(SAMPLE_PDF)

    assert len(images) == 2
    # 300 DPI na stronie paragonu daje obraz o szerokosci ponad 600 px
    assert images[0].width > 600


def test_run_ocr_reads_polish_characters():
    image = rasterize_pdf(SAMPLE_PDF)[0]

    text = run_ocr(image)

    # polskie znaki diakrytyczne - dowod ze pakiet jezykowy 'pol' jest uzywany
    assert "KRAŚNICKA" in text
    assert "Żniwna" in text
    assert "Rabat" in text


def test_whole_pipeline_from_pdf_matches_printed_total():
    """Od pliku PDF do gotowych pozycji — bez zapisanego wyniku OCR."""
    text = extract_receipt_text(SAMPLE_PDF)

    items = merge_deposits(fit_price_to_item(clean_lines(find_items_section(text))))

    assert len(items) == 24
    assert sum(item.total for item in items) == Decimal("156.75")


def test_deposit_is_merged_into_the_drink():
    text = extract_receipt_text(SAMPLE_PDF)

    items = merge_deposits(fit_price_to_item(clean_lines(find_items_section(text))))

    cola = next(item for item in items if item.name.startswith("NapCola"))
    assert cola.had_deposit is True
    assert cola.deposit_amount == Decimal("6.00")
    assert cola.had_discount is True
    assert cola.pre_discount_total == Decimal("29.88")
