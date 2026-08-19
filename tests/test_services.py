from decimal import Decimal

import pytest

from receipts.models import LineItem, Person, Receipt
from receipts.services import compute_split, split_amount, unassigned_items

# --- split_amount: czysta arytmetyka, bez bazy ---------------------------


def test_split_amount_divides_evenly():
    assert split_amount(Decimal("30.00"), 3) == [Decimal("10.00")] * 3


def test_split_amount_gives_leftover_groszy_to_first_people():
    shares = split_amount(Decimal("10.00"), 3)

    assert shares == [Decimal("3.34"), Decimal("3.33"), Decimal("3.33")]


def test_split_amount_never_loses_money():
    # najgorszy przypadek: kwota niepodzielna przez liczbe osob
    for people in range(1, 8):
        shares = split_amount(Decimal("100.03"), people)
        assert sum(shares) == Decimal("100.03")


def test_split_amount_rejects_zero_people():
    with pytest.raises(ValueError):
        split_amount(Decimal("10.00"), 0)


# --- compute_split i unassigned_items: wymagaja bazy --------------------


@pytest.fixture
def receipt_with_items(db):
    receipt = Receipt.objects.create(store="Biedronka")
    anna = Person.objects.create(receipt=receipt, name="Anna")
    piotr = Person.objects.create(receipt=receipt, name="Piotr")

    cola = LineItem.objects.create(receipt=receipt, position=1, name="Cola",
                                   final_total=Decimal("30.00"))
    chleb = LineItem.objects.create(receipt=receipt, position=2, name="Chleb",
                                    final_total=Decimal("5.00"))

    cola.shared_by.add(anna, piotr)
    chleb.shared_by.add(anna)

    return receipt, anna, piotr, cola, chleb


def test_compute_split_sums_shares_per_person(receipt_with_items):
    receipt, anna, piotr, _, _ = receipt_with_items

    totals = compute_split(receipt)

    assert totals[anna.id] == Decimal("20.00")   # polowa coli + caly chleb
    assert totals[piotr.id] == Decimal("15.00")  # sama polowa coli


def test_compute_split_total_equals_receipt_total(receipt_with_items):
    receipt, _, _, _, _ = receipt_with_items

    totals = compute_split(receipt)

    assert sum(totals.values()) == Decimal("35.00")


def test_compute_split_skips_items_without_people(receipt_with_items):
    receipt, _, _, _, _ = receipt_with_items
    LineItem.objects.create(receipt=receipt, position=3, name="Nieprzypisane",
                            final_total=Decimal("99.00"))

    totals = compute_split(receipt)

    assert sum(totals.values()) == Decimal("35.00")


def test_unassigned_items_lists_only_items_without_people(receipt_with_items):
    receipt, _, _, _, _ = receipt_with_items
    lonely = LineItem.objects.create(receipt=receipt, position=3, name="Nieprzypisane",
                                     final_total=Decimal("99.00"))

    missing = unassigned_items(receipt)

    assert [item.pk for item in missing] == [lonely.pk]


def test_unassigned_items_empty_when_everything_assigned(receipt_with_items):
    receipt, _, _, _, _ = receipt_with_items

    assert unassigned_items(receipt) == []
