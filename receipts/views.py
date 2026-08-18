from django.shortcuts import render, redirect
from .models import LineItem
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
                LineItem.objects.create(name=item.name, quantity=item.quantity, unit_price=item.unit_price, final_total=item.total,
                                        receipt=receipt, position=position)

            return redirect('receipt-upload')
    else:
        form = ReceiptForm()
    return render(request, 'receipts/receipt_upload.html', {'form': form})

