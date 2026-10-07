"""Measure the system on a folder of labelled documents.

    python -m app.evaluate            # the generated test set in dataset/
    python -m app.evaluate samples    # the five hand-made documents
    python -m app.evaluate --fresh    # ignore saved model answers and ask the model again

Two things are measured for each image version (clean, photo, rough):
  1. Extraction: how many fields and line items the model read correctly.
  2. Decisions: whether the claim decision made from the model's reading matches
     the decision made from the true documents, and if not, in which direction it went wrong.
     This is shown twice: for the model on its own, and for the whole system, where the
     sharpness check turns blurred photos away before the model reads them.

The model's answer for every image is saved under results/, so scoring again costs no API calls.
"""

import json
import sys
import time
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from app.adjudicate import POLICY
from app.claims import Claim, Decision
from app.extract import MODEL, extract_bill
from app.quality import is_readable
from app.rules import decide
from app.schemas import Bill
from app.text import normalize

ROOT = Path(__file__).parent.parent
VERSIONS = {"clean": ".png", "photo": ".photo.jpg", "rough": ".rough.jpg"}
SECONDS_BETWEEN_CALLS = 5  # stays under the free tier's requests-per-minute limit

EXACT_FIELDS = ["document_type", "bill_date"]
TEXT_FIELDS = ["provider_name", "patient_name", "doctor_name", "bill_number", "diagnosis"]
NUMBER_FIELDS = ["discount", "total_amount"]
ALL_FIELDS = EXACT_FIELDS + TEXT_FIELDS + NUMBER_FIELDS

last_call = 0.0


@dataclass
class Score:
    fields_right: int = 0
    fields_total: int = len(ALL_FIELDS)
    items_right: int = 0
    items_total: int = 0
    wrong_fields: list[str] = field(default_factory=list)
    mistakes: list[str] = field(default_factory=list)


def same_number(a: float | None, b: float | None) -> bool:
    if a is None or b is None:
        return a is b
    return abs(a - b) < 0.01


def score(got: Bill, expected: Bill) -> Score:
    result = Score()

    for name in ALL_FIELDS:
        g, e = getattr(got, name), getattr(expected, name)
        if name in TEXT_FIELDS:
            right = normalize(g) == normalize(e)
        elif name == "discount":  # a printed "Discount 0.00" and no discount line mean the same thing
            right = same_number(g or 0, e or 0)
        elif name in NUMBER_FIELDS:
            right = same_number(g, e)
        else:
            right = g == e
        if right:
            result.fields_right += 1
        else:
            result.wrong_fields.append(name)
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


def decision_outcome(got: Decision, expected: Decision) -> str:
    """Compare the decision made from the model's reading with the decision made from the true documents."""
    if got.status == expected.status and got.approved == expected.approved:
        return "correct"
    if got.status == "MANUAL_REVIEW":
        return "sent to review"  # safe: a person will look at it
    if expected.status == "MANUAL_REVIEW":
        return "missed review"  # unsafe: decided automatically when a person should have looked
    if got.approved > expected.approved:
        return "overpaid"  # unsafe: money paid that was not due
    if got.approved < expected.approved:
        return "underpaid"
    return "wrong status"


def read_document(image: Path, saved: Path, fresh: bool) -> Bill | None:
    """The model's answer for one image, from disk if we already have it. None if the call fails."""
    global last_call
    if saved.exists() and not fresh:
        return Bill.model_validate_json(saved.read_text())

    time.sleep(max(0.0, SECONDS_BETWEEN_CALLS - (time.monotonic() - last_call)))
    last_call = time.monotonic()
    try:
        bill = extract_bill(image.read_bytes(), "image/png" if image.suffix == ".png" else "image/jpeg")
    except Exception as error:  # a failed call is reported and left unsaved, so the next run tries it again
        print(f"  could not read {image.name}: {str(error)[:150]}", flush=True)
        return None
    saved.parent.mkdir(parents=True, exist_ok=True)
    saved.write_text(bill.model_dump_json(indent=2) + "\n")
    return bill


def evaluate_version(folder: Path, suffix: str, saved_dir: Path, version: str, expected: dict[str, Bill], cases: list[dict], fresh: bool) -> dict:
    fields, items, documents, missed, blocked = Counter(), Counter(), Counter(), Counter(), Counter()
    model_alone, whole_system = Counter(), Counter()
    mistakes, read, unclear = [], {}, set()

    for name, truth in expected.items():
        image = folder / f"{name}{suffix}"
        if not image.exists():
            continue
        got = read_document(image, saved_dir / f"{name}.{version}.json", fresh)
        read[name] = got
        if got is None:
            result = Score(items_total=len(truth.line_items), wrong_fields=list(ALL_FIELDS), mistakes=["not read"])
        else:
            result = score(got, truth)

        if not is_readable(image.read_bytes()):
            unclear.add(name)
            blocked["bad readings" if result.mistakes else "good readings"] += 1

        fields.update(right=result.fields_right, total=result.fields_total)
        items.update(right=result.items_right, total=result.items_total)
        documents.update(right=not result.mistakes, total=1)
        missed.update(result.wrong_fields)
        if result.items_right < result.items_total:
            missed["line_items"] += 1
        mistakes += [f"{name}: {mistake}" for mistake in result.mistakes]

    for case in cases:
        documents_read = [read.get(name) for name in case["documents"]]
        truth = decide(Claim(member=case["member"], submitted_on=case["submitted_on"], documents=[expected[n] for n in case["documents"]]), POLICY)
        if any(doc is None for doc in documents_read):
            outcome = "not read"
        else:
            got = decide(Claim(member=case["member"], submitted_on=case["submitted_on"], documents=documents_read), POLICY)
            outcome = decision_outcome(got, truth)
            if outcome != "correct":
                mistakes.append(
                    f"claim {case['id']}: {outcome}: got {got.status} ₹{got.approved:,.2f}, should be {truth.status} ₹{truth.approved:,.2f}"
                )
        model_alone[outcome] += 1
        whole_system["retake requested" if unclear.intersection(case["documents"]) else outcome] += 1

    return {
        "fields": [fields["right"], fields["total"]],
        "items": [items["right"], items["total"]],
        "documents_all_right": [documents["right"], documents["total"]],
        "missed_by_field": dict(missed.most_common()),
        "documents_with_mistakes": documents["total"] - documents["right"],
        "blocked_by_sharpness_check": dict(blocked),
        "decisions_model_alone": dict(model_alone.most_common()),
        "decisions_whole_system": dict(whole_system.most_common()),
        "mistakes": mistakes,
    }


def percent(pair: list[int]) -> str:
    right, total = pair
    return f"{right}/{total} ({100 * right / total:.1f}%)" if total else "-"


def main() -> None:
    names = [arg for arg in sys.argv[1:] if not arg.startswith("--")]
    folder = ROOT / (names[0] if names else "dataset")
    saved_dir = ROOT / "results" / folder.name / MODEL

    expected = {p.name.removesuffix(".expected.json"): Bill.model_validate_json(p.read_text()) for p in sorted(folder.glob("*.expected.json"))}
    cases = json.loads((folder / "cases.json").read_text()) if (folder / "cases.json").exists() else []
    print(f"model: {MODEL}   folder: {folder.name}/   {len(expected)} documents, {len(cases)} claims\n", flush=True)

    results = {}
    for version, suffix in VERSIONS.items():
        print(f"reading the {version} images...", flush=True)
        results[version] = evaluate_version(folder, suffix, saved_dir, version, expected, cases, fresh="--fresh" in sys.argv)

    rows = [
        ("EXTRACTION", lambda r: ""),
        ("fields right", lambda r: percent(r["fields"])),
        ("line items right", lambda r: percent(r["items"])),
        ("documents fully right", lambda r: percent(r["documents_all_right"])),
    ]
    rows += [
        ("", lambda r: ""),
        ("SHARPNESS CHECK", lambda r: ""),
        ("bad readings blocked", lambda r: f"{r['blocked_by_sharpness_check'].get('bad readings', 0)} of {r['documents_with_mistakes']}"),
        ("good readings blocked", lambda r: str(r["blocked_by_sharpness_check"].get("good readings", 0))),
    ]
    if cases:
        outcomes = ["correct", "sent to review", "underpaid", "overpaid", "missed review"]
        for title, key in [("CLAIMS, MODEL ALONE", "decisions_model_alone"), ("CLAIMS, WHOLE SYSTEM", "decisions_whole_system")]:
            shown = outcomes + [o for o in ["retake requested", "wrong status", "not read"] if any(o in r[key] for r in results.values())]
            rows += [("", lambda r: ""), (title, lambda r: "")]
            rows += [(o, lambda r, o=o, key=key: str(r[key].get(o, 0))) for o in shown]

    print(f"\n{'':24}" + "".join(f"{version:>22}" for version in results))
    for label, cell in rows:
        print(f"{label:24}" + "".join(f"{cell(r):>22}" for r in results.values()))

    for version, r in results.items():
        if r["mistakes"]:
            print(f"\n{version}: most missed {r['missed_by_field']}")
            for mistake in r["mistakes"]:
                print(f"  {mistake}")

    summary = {"model": MODEL, "folder": folder.name, "documents": len(expected), "claims": len(cases), "versions": results}
    saved_dir.mkdir(parents=True, exist_ok=True)
    (saved_dir / "summary.json").write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n")
    print(f"\nsaved to {(saved_dir / 'summary.json').relative_to(ROOT)}")


if __name__ == "__main__":
    main()
