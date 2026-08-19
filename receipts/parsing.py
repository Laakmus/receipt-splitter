import re
from dataclasses import dataclass
from decimal import Decimal


@dataclass
class ParsedItem:
    name: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    pre_discount_total: Decimal | None = None
    deposit_amount: Decimal | None = None
    had_discount: bool = False
    had_deposit: bool = False


# OCR czasem gubi separator dziesietny i zostawia spacje ("2 69" zamiast "2,69"),
# wiec kazda z tych trzech postaci jest dopuszczalna
NUMBER = r"\d+[.,\s]\d+"

PIECES_FORM = re.compile(
     r"^(.+?)" # name
     r"\s+" # space
     r"\S+" # PTU
     r"\s+"
     rf"({NUMBER})" # quantity
     r"\s+x\s+"
     rf"({NUMBER})" # unit price
     r"\s+"
     rf"({NUMBER})$" # total price
)

PRICE_FORM = re.compile(
    rf"^({NUMBER})$"
)


# --- helpers -------------------------------------------------------------


def to_decimal(s: str) -> Decimal:
    """Turn a price written with a comma or a stray space into a Decimal.

    Built from text, never from float, so no rounding error is carried over.
    """
    # spacja w srodku liczby to zgubiony przez OCR separator, nie odstep
    s = s.replace(" ", ".").replace(",", ".")
    return Decimal(s)


def parse_product_line(line: str) -> ParsedItem | None:
    """Read one product line into a ParsedItem.

    Returns None when the line is not a product, for example a discount or a footer.
    """
    new_line = PIECES_FORM.search(line)
    if new_line is None:
        return None
    return ParsedItem(name=new_line.group(1).strip(), quantity=to_decimal(new_line.group(2)),
                      unit_price=to_decimal(new_line.group(3).strip()), total=to_decimal(new_line.group(4).strip()))


# --- pipeline: text -> items ---------------------------------------------
# 1. find_items_section  2. clean_lines  3. fit_price_to_item  4. merge_deposits


def find_items_section(text: str) -> list[str]:
    """Step 1: cut out the lines between the table header and the tax summary.

    Both border lines are left out, so only the items part of the receipt stays.
    """
    new_list = []
    switcher = False
    for item_line in text.splitlines():
        if "Nazwa PTU Ilość Cena Wartość" in item_line:
            switcher = True
            continue
        if "Sprzedaż opodatkowana" in item_line:
            break
        elif switcher:
            new_list.append(item_line)
    return new_list


def clean_lines(data_text: list) -> list:
    """Step 2: keep only lines that are a product, a discount or a price.

    Removes OCR noise such as page footers, empty lines and cut-off name endings.
    """
    new_list = []
    for item in data_text:
        if PIECES_FORM.search(item) is not None or PRICE_FORM.search(item) is not None or "Rabat" in item:
            new_list.append(item)

    return new_list


def fit_price_to_item(data: list) -> list[ParsedItem]:
    """Step 3: turn lines into items and use the discounted price where a discount follows.

    A discount takes two extra lines: the discount amount and the final price.
    """
    new_list = []
    for i, item in enumerate(data):
        new_item = parse_product_line(item)
        if new_item is None:
            continue
        if i + 2 < len(data):
            if "Rabat" in data[i+1]:
                new_item.had_discount = True
                new_item.pre_discount_total = new_item.total
                new_item.total = to_decimal(data[i+2].strip())
        new_list.append(new_item)
    return new_list


def merge_deposits(data_list: list[ParsedItem]) -> list[ParsedItem]:
    """Step 4: add each bottle deposit to the drink it belongs to and drop it as a separate item.

    A deposit always follows its drink, so its price goes to the previous item.
    """
    new_data: list[ParsedItem] = []
    data = data_list[::-1]
    new_total = 0
    deposit = 0
    for i, item in enumerate(data):
        if "kaucja" in item.name.lower():
            deposit = item.total
            new_total= item.total + data[i+1].total
            continue
        if new_total != 0:
            item.had_deposit = True
            item.deposit_amount = deposit
            item.total = new_total
            new_total = 0
            deposit = 0
        new_data.append(item)

    return new_data[::-1]
