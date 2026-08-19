from django.db import models

class Receipt(models.Model):
    class Status(models.TextChoices):
        UPLOADED = 'uploaded', 'przesłano'
        OCR_FAILED = 'ocr_failed', 'błąd ocr'
        PARSED = 'parsed', 'przetworzono'
        PARSE_FAILED = 'parse_failed', 'błąd przetwarzania'
        REVIEWED = 'reviewed', 'zweryfikowano'


    uploaded_file = models.FileField(upload_to='receipts/')
    store = models.CharField(max_length=100, default='Biedronka')
    status = models.CharField(choices=Status, default=Status.UPLOADED, max_length=30)
    raw_ocr_text = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.store


class Person(models.Model):
    name = models.CharField(max_length=100)
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='persons')

    def __str__(self):
        return self.name


class LineItem(models.Model):
    receipt = models.ForeignKey(Receipt, on_delete=models.CASCADE, related_name='line_items')
    position = models.IntegerField()
    raw_text = models.TextField(blank=True)
    name = models.CharField(max_length=100)
    quantity = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    unit_price = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    pre_discount_total = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    final_total = models.DecimalField(decimal_places=2, max_digits=10)
    deposit_amount = models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True)
    had_discount = models.BooleanField(default=False)
    had_deposit = models.BooleanField(default=False)
    parse_warning = models.TextField(blank=True)
    shared_by = models.ManyToManyField(Person, related_name='line_items', blank=True)

    @property
    def discount_amount(self):
        """Kwota rabatu — różnica między ceną przed obniżką a finalną."""
        if self.pre_discount_total is None:
            return None
        # final_total zawiera juz doliczona kaucje - odejmujemy ja, zeby zostala sama cena towaru
        cena_towaru = self.final_total - (self.deposit_amount or 0)
        return self.pre_discount_total - cena_towaru

    def __str__(self):
        return self.name