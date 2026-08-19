from decimal import Decimal

import pytest

from receipts.models import LineItem, Person, Receipt


@pytest.mark.django_db
def test_create_receipt():
    receipt = Receipt(uploaded_file="receipt_1.pdf")
    receipt.save()

    assert receipt.status == Receipt.Status.UPLOADED
    assert receipt.store == "Biedronka"
    assert Receipt.objects.count() == 1


@pytest.mark.django_db
def test_relation_btw_receipt_and_line_item():
    receipt = Receipt(uploaded_file="receipt_1.pdf")
    item_line = LineItem(receipt=receipt, position=1, name="Mleko", final_total=100)
    receipt.save()
    item_line.save()

    assert item_line.receipt == receipt
    assert item_line in receipt.line_items.all()


@pytest.mark.django_db
def test_relation_btw_item_and_person():
    receipt = Receipt(uploaded_file="receipt_1.pdf")
    receipt.save()
    person1 = Person(name="Agata", receipt=receipt)
    person2 = Person(name="Lucyna", receipt=receipt)
    item = LineItem(receipt=receipt, position=1, name="Mleko", final_total=100)
    receipt.save()
    item.save()
    person1.save()
    person2.save()

    item.shared_by.add(person1, person2)

    assert item.shared_by.count() == 2
    assert person1 in item.shared_by.all()
    assert person2 in item.shared_by.all()
    assert person1.line_items.count() == 1


@pytest.mark.django_db
def test_delete_receipt_cascade():
    receipt = Receipt(uploaded_file="receipt_1.pdf")
    receipt.save()
    item = LineItem(receipt=receipt, position=1, name="Mleko", final_total=100)
    person1 = Person(name="Agata", receipt=receipt)
    person2 = Person(name="Lucyna", receipt=receipt)
    item.save()
    person1.save()
    person2.save()
    item.shared_by.add(person1, person2)

    assert item.shared_by.count() == 2
    assert person1 in item.shared_by.all()
    assert person2 in item.shared_by.all()
    assert receipt.persons.count() == 2

    receipt.delete()
    assert LineItem.objects.count() == 0
    assert Person.objects.count() == 0







@pytest.mark.django_db
def test_str_shows_readable_names():
    receipt = Receipt.objects.create(uploaded_file="receipt_1.pdf")
    person = Person.objects.create(name="Agata", receipt=receipt)
    item = LineItem.objects.create(receipt=receipt, position=1, name="Mleko", final_total=100)

    assert str(receipt) == "Biedronka"
    assert str(person) == "Agata"
    assert str(item) == "Mleko"


@pytest.mark.django_db
def test_discount_amount_is_none_without_discount():
    receipt = Receipt.objects.create(uploaded_file="receipt_1.pdf")
    item = LineItem.objects.create(receipt=receipt, position=1, name="Mleko",
                                   final_total=Decimal("3.49"))

    assert item.discount_amount is None


@pytest.mark.django_db
def test_discount_amount_ignores_deposit():
    receipt = Receipt.objects.create(uploaded_file="receipt_1.pdf")
    # cena 29,88 -> rabat 7,50 -> 22,38, do tego 6,00 kaucji = 28,38 w final_total
    item = LineItem.objects.create(receipt=receipt, position=1, name="Cola",
                                   pre_discount_total=Decimal("29.88"),
                                   deposit_amount=Decimal("6.00"),
                                   final_total=Decimal("28.38"))

    assert item.discount_amount == Decimal("7.50")
