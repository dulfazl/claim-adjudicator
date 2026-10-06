"""The scoring rules themselves need to be right, or the accuracy numbers mean nothing."""

from pathlib import Path

from app.evaluate import normalize, same_number, score
from app.schemas import Bill

SAMPLES = Path(__file__).parent.parent / "samples"


def load(name: str) -> Bill:
    return Bill.model_validate_json((SAMPLES / f"{name}.expected.json").read_text())


def test_case_punctuation_and_titles_are_ignored():
    assert normalize("Ms. ANANYA  Rao") == normalize("Ananya Rao")
    assert normalize("Dr. R. Menon") == normalize("R Menon")
    assert normalize("Ananya Rao") != normalize("Ananya Rai")


def test_a_missing_number_only_matches_a_missing_number():
    assert same_number(None, None)
    assert not same_number(None, 0.0)
    assert same_number(700.0, 700.004)
    assert not same_number(700.0, 70.0)


def test_a_perfect_extraction_gets_full_marks():
    expected = load("002_pharmacy_bill")
    result = score(expected, expected)
    assert result.fields_right == result.fields_total
    assert result.items_right == result.items_total == 5
    assert result.mistakes == []


def test_a_wrong_total_and_a_dropped_item_are_both_counted():
    expected = load("002_pharmacy_bill")
    got = expected.model_copy(deep=True)
    got.total_amount = 800.0
    got.line_items.pop()
    result = score(got, expected)
    assert result.fields_right == result.fields_total - 1
    assert result.items_right == 4 and result.items_total == 5


def test_an_invented_item_lowers_the_item_score():
    expected = load("004_prescription")
    got = expected.model_copy(deep=True)
    got.line_items = load("001_clinic_bill").line_items[:1]
    result = score(got, expected)
    assert result.items_right == 0 and result.items_total == 1
