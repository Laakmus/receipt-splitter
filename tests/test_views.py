from decimal import Decimal

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from receipts.models import LineItem, Person, Receipt

pytestmark = pytest.mark.django_db


@pytest.fixture
def media_root(settings, tmp_path):
    """Wgrywane pliki laduja w katalogu tymczasowym, nie w media/ projektu."""
    settings.MEDIA_ROOT = tmp_path
    return tmp_path


@pytest.fixture
def receipt(db):
    receipt = Receipt.objects.create(store="Biedronka")
    LineItem.objects.create(receipt=receipt, position=1, name="Cola",
                            final_total=Decimal("30.00"))
    LineItem.objects.create(receipt=receipt, position=2, name="Chleb",
                            final_total=Decimal("5.00"))
    return receipt


# --- upload: OCR podmieniony, tesseract nie jest uruchamiany ------------


def test_upload_runs_pipeline_and_saves_items(client, monkeypatch, media_root, raw_ocr_text):
    monkeypatch.setattr("receipts.views.extract_receipt_text", lambda path: raw_ocr_text)
    pdf = SimpleUploadedFile("paragon.pdf", b"%PDF-1.4 udawany", content_type="application/pdf")

    response = client.post(reverse("receipt-upload"), {"uploaded_file": pdf})

    receipt = Receipt.objects.get()
    assert response.status_code == 302
    assert response.url == reverse("receipt-preview", kwargs={"pk": receipt.pk})
    assert receipt.line_items.count() == 24
    assert sum(item.final_total for item in receipt.line_items.all()) == Decimal("156.75")


def test_upload_saves_discount_and_deposit_details(client, monkeypatch, media_root, raw_ocr_text):
    monkeypatch.setattr("receipts.views.extract_receipt_text", lambda path: raw_ocr_text)
    pdf = SimpleUploadedFile("paragon.pdf", b"%PDF-1.4 udawany", content_type="application/pdf")

    client.post(reverse("receipt-upload"), {"uploaded_file": pdf})

    cola = LineItem.objects.get(name__startswith="NapCola")
    assert cola.had_deposit is True
    assert cola.deposit_amount == Decimal("6.00")
    assert cola.had_discount is True
    assert cola.pre_discount_total == Decimal("29.88")
    assert cola.discount_amount == Decimal("7.50")


def test_upload_shows_form_on_get(client):
    response = client.get(reverse("receipt-upload"))

    assert response.status_code == 200
    assert "form" in response.context


# --- podglad: osoby, zaznaczenia, wynik ---------------------------------


def test_preview_lists_items(client, receipt):
    response = client.get(reverse("receipt-preview", kwargs={"pk": receipt.pk}))

    assert response.status_code == 200
    assert len(response.context["rows"]) == 2


def test_preview_returns_404_for_unknown_receipt(client):
    response = client.get(reverse("receipt-preview", kwargs={"pk": 9999}))

    assert response.status_code == 404


def test_add_person_creates_person(client, receipt):
    url = reverse("receipt-preview", kwargs={"pk": receipt.pk})

    client.post(url, {"action": "add_person", "person_name": "Anna"})

    assert [p.name for p in receipt.persons.all()] == ["Anna"]


def test_add_person_ignores_empty_name(client, receipt):
    url = reverse("receipt-preview", kwargs={"pk": receipt.pk})

    client.post(url, {"action": "add_person", "person_name": "   "})

    assert receipt.persons.count() == 0


def test_delete_person_removes_person(client, receipt):
    anna = Person.objects.create(receipt=receipt, name="Anna")
    url = reverse("receipt-preview", kwargs={"pk": receipt.pk})

    client.post(url, {"action": "delete_person", "person_id": anna.pk})

    assert receipt.persons.count() == 0


def test_compute_saves_checkboxes_and_redirects(client, receipt):
    anna = Person.objects.create(receipt=receipt, name="Anna")
    piotr = Person.objects.create(receipt=receipt, name="Piotr")
    cola, chleb = receipt.line_items.all()
    url = reverse("receipt-preview", kwargs={"pk": receipt.pk})

    response = client.post(url, {
        "action": "compute",
        f"item_{cola.pk}": [anna.pk, piotr.pk],
        f"item_{chleb.pk}": [anna.pk],
    })

    assert response.status_code == 302
    assert response.url.endswith("?policz=1")
    assert cola.shared_by.count() == 2
    assert chleb.shared_by.count() == 1


def test_compute_unchecking_removes_person_from_item(client, receipt):
    anna = Person.objects.create(receipt=receipt, name="Anna")
    cola, chleb = receipt.line_items.all()
    cola.shared_by.add(anna)
    url = reverse("receipt-preview", kwargs={"pk": receipt.pk})

    client.post(url, {"action": "compute", f"item_{chleb.pk}": [anna.pk]})

    assert cola.shared_by.count() == 0


def test_totals_shown_when_everything_assigned(client, receipt):
    anna = Person.objects.create(receipt=receipt, name="Anna")
    piotr = Person.objects.create(receipt=receipt, name="Piotr")
    cola, chleb = receipt.line_items.all()
    cola.shared_by.add(anna, piotr)
    chleb.shared_by.add(anna)
    url = reverse("receipt-preview", kwargs={"pk": receipt.pk})

    response = client.get(url, {"policz": "1"})

    assert dict(response.context["totals"]) == {anna: Decimal("20.00"), piotr: Decimal("15.00")}


def test_totals_blocked_when_item_has_nobody(client, receipt):
    anna = Person.objects.create(receipt=receipt, name="Anna")
    cola, _ = receipt.line_items.all()
    cola.shared_by.add(anna)
    url = reverse("receipt-preview", kwargs={"pk": receipt.pk})

    response = client.get(url, {"policz": "1"})

    assert response.context["totals"] is None
    assert len(response.context["missing"]) == 1


# --- lista i usuwanie ---------------------------------------------------


def test_receipt_list_shows_receipts(client, receipt):
    response = client.get(reverse("receipt-list"))

    assert response.status_code == 200
    assert list(response.context["receipts"]) == [receipt]


def test_delete_removes_receipt_with_items(client, receipt):
    url = reverse("receipt-delete", kwargs={"pk": receipt.pk})

    response = client.post(url)

    assert response.url == reverse("receipt-list")
    assert Receipt.objects.count() == 0
    assert LineItem.objects.count() == 0


def test_delete_get_only_asks_for_confirmation(client, receipt):
    url = reverse("receipt-delete", kwargs={"pk": receipt.pk})

    response = client.get(url)

    assert response.status_code == 200
    assert Receipt.objects.count() == 1
