"""Checks that run without an API key."""

import json
from pathlib import Path

import pytest
from pydantic import ValidationError

from app.schemas import Bill

SAMPLES = Path(__file__).parent.parent / "samples"
EXPECTED_FILES = sorted(SAMPLES.glob("*.expected.json"))


@pytest.mark.parametrize("path", EXPECTED_FILES, ids=lambda p: p.name)
def test_expected_answer_fits_the_schema(path):
    Bill.model_validate_json(path.read_text())


@pytest.mark.parametrize("path", EXPECTED_FILES, ids=lambda p: p.name)
def test_line_items_minus_discount_equal_the_total(path):
    bill = Bill.model_validate_json(path.read_text())
    if bill.total_amount is None:  # prescriptions have no amounts
        assert bill.line_items == []
        return
    items = sum(item.amount for item in bill.line_items)
    assert items - (bill.discount or 0) == pytest.approx(bill.total_amount)


def test_unknown_category_is_rejected():
    data = json.loads((SAMPLES / "001_clinic_bill.expected.json").read_text())
    data["line_items"][0]["category"] = "spa"
    with pytest.raises(ValidationError):
        Bill.model_validate(data)
