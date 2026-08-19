from decimal import Decimal

import pytest

from receipts.parsing import (
    ParsedItem,
    clean_lines,
    find_items_section,
    fit_price_to_item,
    merge_deposits,
    parse_product_line,
    to_decimal,
)


def test_find_items_section_skips_header_and_summary(raw_ocr_text):
    result = find_items_section(raw_ocr_text)
    assert len(result) == 50


@pytest.mark.parametrize(
    "string, result",
    [
        ("23,5", Decimal("23.5")),
        ("345,23", Decimal("345.23")),
        ("2.4", Decimal("2.4")),
    ]
)
def test_to_decimal_converts_comma_to_dot(string, result):
    assert to_decimal(string) == result


def test_fit_price_to_item_uses_discounted_price(raw_ocr_text):
    lista = find_items_section(raw_ocr_text)
    result = fit_price_to_item(lista)
    assert len(result) == 26
    assert result[0].total == Decimal("22.38")


def test_parse_product_line_returns_item():
    linia = "Krok zmięs 400g c 1.000 x 7,29 7,29"
    result = parse_product_line(linia)
    assert result == ParsedItem(name="Krok zmięs 400g", quantity=Decimal("1.000"), unit_price=Decimal("7.29"),
                                total=Decimal("7.29"))

def test_clean_lines_drops_ocr_noise():
    lista = [
        "NapColaFizzUp0,5l A 12.000 x 2,49 29,88",   # produkt
        "Rabat -7,50",                                # rabat
        "22,38",                                      # cena po rabacie
        "4902/11/2116/23.06.2026 Strona 1z 2",        # stopka strony
        "",                                           # pusta linia
        "g",                                          # ucieta koncowka nazwy
    ]
    result = clean_lines(lista)
    assert result == lista[:3]



def test_full_pipeline_matches_receipt_total(raw_ocr_text):
    list_of_aim_data = find_items_section(raw_ocr_text)
    products_list = clean_lines(list_of_aim_data)
    list_fit_price = fit_price_to_item(products_list)
    result = merge_deposits(list_fit_price)

    assert len(result) == 24
    assert sum(x.total for x in result) == Decimal("156.75")

def test_merge_deposits_adds_deposit_to_drink():
    items = [
        ParsedItem(name="Cola", quantity=Decimal("1.000"), unit_price=Decimal("5.00"), total=Decimal("5.00")),
        ParsedItem(name="But Plastik kaucja", quantity=Decimal("1.000"), unit_price=Decimal("0.50"),
                   total=Decimal("0.50")),
    ]

    result = merge_deposits(items)
    assert result[0].total == Decimal("5.50")









def test_parse_product_line_accepts_space_instead_of_decimal_separator():
    """OCR na Linuksie odczytal '2,69' jako '2 69' - pozycja nie moze przez to zniknac."""
    line = "JOgPItI ruskrruv+UUgN e 1.000 x 2 69 2.69"

    item = parse_product_line(line)

    assert item is not None
    assert item.unit_price == Decimal("2.69")
    assert item.total == Decimal("2.69")


def test_to_decimal_handles_all_three_separators():
    assert to_decimal("2,69") == Decimal("2.69")
    assert to_decimal("2.69") == Decimal("2.69")
    assert to_decimal("2 69") == Decimal("2.69")
