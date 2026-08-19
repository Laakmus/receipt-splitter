from django.shortcuts import render, redirect, get_object_or_404
from .models import LineItem, Receipt
from .forms import ReceiptForm
from .ocr import extract_receipt_text
from .parsing import find_items_section, clean_lines, fit_price_to_item, merge_deposits


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
    positions = receipt.line_items.all()
    return render(request, 'receipts/receipt_preview.html', {"positions": positions, "receipt": receipt})



