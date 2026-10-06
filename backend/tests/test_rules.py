"""The policy rules, tested on the expected answers so no LLM is involved."""

import json
from decimal import Decimal
from pathlib import Path

import pytest

from app.adjudicate import POLICY, load_claim
from app.claims import Claim
from app.rules import decide, money
from app.schemas import Bill

ROOT = Path(__file__).parent.parent
CLAIM_FILES = sorted((ROOT / "claims").glob("*.json"))


def doc(name: str) -> Bill:
    return Bill.model_validate_json((ROOT / "samples" / f"{name}.expected.json").read_text())


def claim(member: str, submitted_on: str, *documents: Bill, used: int = 0) -> Claim:
    return Claim(member={"name": member, "used_this_year": used}, submitted_on=submitted_on, documents=list(documents))


def payable(decision, text: str) -> Decimal:
    return next(item.payable for item in decision.items if text in item.description)


@pytest.mark.parametrize("path", CLAIM_FILES, ids=lambda p: p.stem)
def test_sample_claims_get_their_expected_decision(path):
    expected = json.loads(path.read_text())["expected"]
    decision = decide(load_claim(path, offline=True), POLICY)
    assert decision.status == expected["status"]
    assert decision.approved == Decimal(expected["approved"])


def test_money_is_exact_to_the_paisa():
    assert money(33.6) + money(132.4) == Decimal("166.00")
    assert money(0.125) == Decimal("0.13")


def test_a_fully_covered_bill_is_approved_minus_copay():
    decision = decide(claim("Ananya Rao", "2026-09-20", doc("001_clinic_bill")), POLICY)
    assert decision.status == "APPROVED"
    assert decision.claimed == Decimal("1769.00")
    assert decision.approved == Decimal("1592.10")  # 1769 minus the 10% co-pay


def test_a_pharmacy_bill_alone_needs_a_prescription():
    decision = decide(claim("Ananya Rao", "2026-09-20", doc("002_pharmacy_bill")), POLICY)
    assert decision.status == "REJECTED"
    assert "No prescription" in decision.items[0].reason


def test_a_prescription_makes_the_lab_bill_payable():
    without = decide(claim("Karthik Subramanian", "2026-09-10", doc("003_lab_bill")), POLICY)
    with_it = decide(claim("Karthik Subramanian", "2026-09-10", doc("004_prescription"), doc("003_lab_bill")), POLICY)
    assert without.status == "REJECTED"
    assert with_it.status == "PARTIAL"
    assert with_it.approved == Decimal("1359.10")


def test_a_prescription_written_after_the_bill_does_not_count():
    late_prescription = doc("004_prescription")
    late_prescription.bill_date = "2026-09-05"  # the lab bill is dated 2026-09-03
    decision = decide(claim("Karthik Subramanian", "2026-09-10", late_prescription, doc("003_lab_bill")), POLICY)
    assert decision.status == "REJECTED"


def test_a_bill_discount_is_shared_across_the_items():
    decision = decide(claim("Karthik Subramanian", "2026-09-10", doc("004_prescription"), doc("003_lab_bill")), POLICY)
    assert sum(item.claimed for item in decision.items) == Decimal("1600.00")  # the net total, not the gross 1780
    assert payable(decision, "Lipid Profile") == Decimal("584.27")
    assert payable(decision, "Home Sample Collection") == 0  # "other" is not covered


def test_cosmetic_items_are_not_paid_and_procedures_are_capped():
    decision = decide(claim("Fatima Sheikh", "2026-09-25", doc("005_dental_bill")), POLICY)
    assert payable(decision, "Teeth Whitening") == 0
    assert payable(decision, "Root Canal") == Decimal("5000.00")  # billed 6500, limit 5000
    assert decision.approved == Decimal("5220.00")


def test_a_late_claim_is_rejected_with_the_number_of_days():
    decision = decide(claim("Fatima Sheikh", "2026-12-30", doc("005_dental_bill")), POLICY)
    assert decision.status == "REJECTED"
    assert "100 days" in decision.items[0].reason


def test_a_bill_from_before_the_policy_started_is_rejected():
    old_bill = doc("001_clinic_bill")
    old_bill.bill_date = "2026-03-15"
    decision = decide(claim("Ananya Rao", "2026-03-20", old_bill), POLICY)
    assert decision.status == "REJECTED"
    assert "outside the policy period" in decision.items[0].reason


def test_someone_elses_bill_goes_to_manual_review():
    decision = decide(claim("Rahul Verma", "2026-09-20", doc("001_clinic_bill")), POLICY)
    assert decision.status == "MANUAL_REVIEW"
    assert decision.approved == 0


def test_a_total_that_does_not_add_up_goes_to_manual_review():
    bill = doc("001_clinic_bill")
    bill.total_amount = 2769.0  # the items still add up to 1769
    decision = decide(claim("Ananya Rao", "2026-09-20", bill), POLICY)
    assert decision.status == "MANUAL_REVIEW"
    assert "1,769.00" in decision.steps[0] and "2,769.00" in decision.steps[0]


def test_the_annual_limit_caps_the_payout():
    decision = decide(claim("Ananya Rao", "2026-09-20", doc("001_clinic_bill"), used=14000), POLICY)
    assert decision.status == "PARTIAL"
    assert decision.approved == Decimal("1000.00")  # 15000 limit minus 14000 already used


def test_a_claim_with_no_bill_is_rejected():
    decision = decide(claim("Karthik Subramanian", "2026-09-10", doc("004_prescription")), POLICY)
    assert decision.status == "REJECTED"
