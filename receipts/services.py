from decimal import ROUND_DOWN, Decimal

GROSZ = Decimal("0.01")


def split_amount(total: Decimal, people_count: int) -> list[Decimal]:
    """Split one amount into equal shares that still add up to the original.

    Leftover groszy go to the first people on the list, so no money is lost to rounding.
    """
    if people_count < 1:
        raise ValueError("Cannot split an amount between zero people")

    base = (total / people_count).quantize(GROSZ, rounding=ROUND_DOWN)
    shares = [base] * people_count

    leftover_groszy = int((total - base * people_count) / GROSZ)
    for i in range(leftover_groszy):
        shares[i] += GROSZ

    return shares


def unassigned_items(receipt) -> list:
    """Return the items nobody has been checked for.

    The summary stays blocked until this list is empty.
    """
    return [item for item in receipt.line_items.all() if not item.shared_by.exists()]


def compute_split(receipt) -> dict:
    """Work out how much each person owes for the whole receipt.

    Every item is divided equally between the people checked for it.
    """
    totals = {person.id: Decimal("0.00") for person in receipt.persons.all()}

    for item in receipt.line_items.all():
        people = list(item.shared_by.all())
        if not people:
            continue
        for person, share in zip(people, split_amount(item.final_total, len(people))):
            totals[person.id] += share

    return totals
