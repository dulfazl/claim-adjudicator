"""Run the extractor on every sample image and score it against the expected answer.

    python -m app.evaluate
"""

from dataclasses import dataclass, field
from pathlib import Path

from app.extract import MODEL, extract_bill
from app.schemas import Bill
from app.text import normalize

SAMPLES = Path(__file__).parent.parent / "samples"
IMAGE_TYPES = {".png": "image/png", ".jpg": "image/jpeg"}

EXACT_FIELDS = ["document_type", "bill_date"]
TEXT_FIELDS = ["provider_name", "patient_name", "doctor_name", "bill_number", "diagnosis"]
NUMBER_FIELDS = ["discount", "total_amount"]


@dataclass
class Score:
    fields_right: int = 0
    fields_total: int = len(EXACT_FIELDS + TEXT_FIELDS + NUMBER_FIELDS)
    items_right: int = 0
    items_total: int = 0
    mistakes: list[str] = field(default_factory=list)


def same_number(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return a is b
    return abs(a - b) < 0.01


def score(got: Bill, expected: Bill) -> Score:
    result = Score()

    for name in EXACT_FIELDS + TEXT_FIELDS + NUMBER_FIELDS:
        g, e = getattr(got, name), getattr(expected, name)
        if name in TEXT_FIELDS:
            right = normalize(g) == normalize(e)
        elif name in NUMBER_FIELDS:
            right = same_number(g, e)
        else:
            right = g == e
        if right:
            result.fields_right += 1
        else:
            result.mistakes.append(f"{name}: got {g!r}, expected {e!r}")

    # A line item is right when an extracted item has the same category and amount.
    # Extra items the model invented count against it, so the total is the larger of the two lists.
    result.items_total = max(len(got.line_items), len(expected.line_items))
    unmatched = list(got.line_items)
    for item in expected.line_items:
        match = next((u for u in unmatched if u.category == item.category and same_number(u.amount, item.amount)), None)
        if match:
            unmatched.remove(match)
            result.items_right += 1
        else:
            result.mistakes.append(f"item missing or wrong: {item.description} ({item.category}, {item.amount})")
    for extra in unmatched[: result.items_total - result.items_right]:
        result.mistakes.append(f"item not expected: {extra.description} ({extra.category}, {extra.amount})")

    return result


def main() -> None:
    print(f"model: {MODEL}\n")
    totals = {"clean": Score(fields_total=0), "photo": Score(fields_total=0)}

    for image in sorted(p for p in SAMPLES.iterdir() if p.suffix in IMAGE_TYPES):
        kind = "photo" if ".photo" in image.name else "clean"
        expected_file = SAMPLES / f"{image.name.split('.')[0]}.expected.json"
        expected = Bill.model_validate_json(expected_file.read_text())

        try:
            result = score(extract_bill(image.read_bytes(), IMAGE_TYPES[image.suffix]), expected)
        except Exception as error:  # a failed call scores zero instead of stopping the whole run
            result = Score(items_total=len(expected.line_items), mistakes=[f"extraction failed: {error}"[:200]])

        print(f"{image.name:36} fields {result.fields_right}/{result.fields_total}   items {result.items_right}/{result.items_total}")
        for mistake in result.mistakes:
            print(f"    {mistake}")

        total = totals[kind]
        total.fields_right += result.fields_right
        total.fields_total += result.fields_total
        total.items_right += result.items_right
        total.items_total += result.items_total

    print()
    for kind, total in totals.items():
        if total.fields_total:
            print(
                f"{kind}: fields {total.fields_right}/{total.fields_total} "
                f"({100 * total.fields_right / total.fields_total:.1f}%)   "
                f"items {total.items_right}/{total.items_total} "
                f"({100 * total.items_right / max(total.items_total, 1):.1f}%)"
            )


if __name__ == "__main__":
    main()
