from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from .forms import ReceiptForm
from .models import LineItem, Person, Receipt
from .ocr import extract_receipt_text
from .parsing import clean_lines, find_items_section, fit_price_to_item, merge_deposits
from .services import compute_split, unassigned_items


def receipt_upload(request):
    if request.method == "POST":
        form = ReceiptForm(request.POST, request.FILES)
        if form.is_valid():
            receipt = form.save()
            receipt_path = receipt.uploaded_file.path
            receipt.raw_ocr_text = extract_receipt_text(receipt_path)
            receipt.save()
            list_of_aim_data = find_items_section(receipt.raw_ocr_text)
            products_list = clean_lines(list_of_aim_data)
            list_fit_price = fit_price_to_item(products_list)
            result = merge_deposits(list_fit_price)
            for position, item in enumerate(result, start=1):
                LineItem.objects.create(name=item.name, quantity=item.quantity, unit_price=item.unit_price,
                                        final_total=item.total, pre_discount_total=item.pre_discount_total,
                                        deposit_amount=item.deposit_amount, had_discount=item.had_discount,
                                        had_deposit=item.had_deposit, receipt=receipt, position=position)

            return redirect('receipt-preview', pk=receipt.pk)
    else:
        form = ReceiptForm()
    return render(request, 'receipts/receipt_upload.html', {'form': form})


def receipt_preview(request, pk):
    receipt = get_object_or_404(Receipt, pk=pk)

    if request.method == "POST":
        action = request.POST.get("action")

        if action == "add_person":
            name = request.POST.get("person_name", "").strip()
            if name:
                Person.objects.create(receipt=receipt, name=name)

        elif action == "delete_person":
            Person.objects.filter(pk=request.POST.get("person_id"), receipt=receipt).delete()

        elif action == "compute":
            # zaznaczenia sa nadpisywane w calosci - odznaczone osoby znikaja z pozycji
            for item in receipt.line_items.all():
                item.shared_by.set(request.POST.getlist(f"item_{item.pk}"))
            url = reverse('receipt-preview', kwargs={'pk': receipt.pk})
            return redirect(f"{url}?policz=1")

        return redirect('receipt-preview', pk=receipt.pk)

    people = list(receipt.persons.all())
    positions = receipt.line_items.prefetch_related('shared_by').all()

    # szablon nie potrafi sprawdzic przynaleznosci do relacji, wiec ptaszki liczymy tutaj
    rows = []
    for item in positions:
        checked = {person.pk for person in item.shared_by.all()}
        rows.append({'item': item, 'checks': [(person, person.pk in checked) for person in people]})

    receipt_total = sum(item.final_total for item in positions)
    missing = unassigned_items(receipt)
    totals = None
    if request.GET.get("policz") and people and not missing:
        amounts = compute_split(receipt)
        totals = [(person, amounts[person.id]) for person in people]

    return render(request, 'receipts/receipt_preview.html', {
        'receipt': receipt,
        'rows': rows,
        'receipt_total': receipt_total,
        'people': people,
        'missing': missing,
        'totals': totals,
        'asked_to_compute': bool(request.GET.get("policz")),
    })


def receipt_list(request):
    receipts = Receipt.objects.order_by('-created_at')
    return render(request, 'receipts/receipt_list.html', {'receipts': receipts})


def receipt_delete(request, pk):
    receipt = get_object_or_404(Receipt, pk=pk)
    if request.method == "POST":
        receipt.delete()
        return redirect('receipt-list')
    return render(request, 'receipts/receipt_confirm_delete.html', {'receipt': receipt})
