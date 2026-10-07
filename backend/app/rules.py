"""Step 2: decide a claim.

There is no LLM in this file. The same documents and the same policy always
give the same decision, and every rupee that is cut comes with a reason.
"""

from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.claims import Claim, Decision, ItemDecision, Policy
from app.schemas import Bill
from app.text import normalize

ZERO = Decimal("0.00")


def money(value) -> Decimal:
    """Rupees with exactly two decimals. Going through str keeps 33.6 as 33.60 instead of 33.6000000000000014."""
    return Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def parse_date(text: str | None) -> date | None:
    try:
        return date.fromisoformat(text)
    except (TypeError, ValueError):
        return None


def label(doc: Bill) -> str:
    return doc.bill_number or doc.provider_name or doc.document_type


def document_problems(claim: Claim, bills: list[Bill]) -> list[str]:
    """Reasons the documents cannot be trusted enough to decide without a person looking."""
    problems = []
    for doc in claim.documents:
        if normalize(doc.patient_name) != normalize(claim.member.name):
            problems.append(f"{label(doc)}: patient {doc.patient_name!r} is not the member {claim.member.name!r}.")
        if parse_date(doc.bill_date) is None:
            problems.append(f"{label(doc)}: the date is missing or unreadable.")
    for bill in bills:
        gross = sum((money(item.amount) for item in bill.line_items), ZERO)
        if bill.total_amount is None or gross <= 0:
            problems.append(f"{label(bill)}: the total or the items are missing.")
            continue
        after_discount = gross - money(bill.discount or 0)
        if abs(after_discount - money(bill.total_amount)) > 1:
            problems.append(
                f"{label(bill)}: the items come to ₹{after_discount:,.2f} but the bill total says ₹{money(bill.total_amount):,.2f}."
            )
    return problems


def assess_bill(bill: Bill, claim: Claim, policy: Policy, prescriptions: list[Bill]) -> list[ItemDecision]:
    """Decide each line of one bill, before limits and co-pay."""
    bill_date = date.fromisoformat(bill.bill_date)
    days_since_bill = (claim.submitted_on - bill_date).days

    # Reasons that knock out the whole bill.
    if not policy.start_date <= bill_date <= policy.end_date:
        bill_reason = f"The bill is dated {bill_date}, outside the policy period."
    elif days_since_bill < 0:
        bill_reason = f"The bill is dated {bill_date}, after the claim was submitted."
    elif days_since_bill > policy.claim_window_days:
        bill_reason = f"Submitted {days_since_bill} days after the bill date; the limit is {policy.claim_window_days} days."
    else:
        bill_reason = None

    # A bill that includes the doctor's consultation needs no separate prescription.
    # A stand-alone pharmacy or lab bill does: same patient, dated on or before the bill.
    has_consultation = any(item.category == "consultation" for item in bill.line_items)
    has_prescription = any(
        normalize(p.patient_name) == normalize(bill.patient_name) and date.fromisoformat(p.bill_date) <= bill_date
        for p in prescriptions
    )

    # A discount on the whole bill is shared across its items in proportion,
    # so each item is claimed at what the member actually paid for it.
    gross = sum((money(item.amount) for item in bill.line_items), ZERO)
    share_paid = money(bill.total_amount) / gross

    decisions = []
    for item in bill.line_items:
        claimed = money(money(item.amount) * share_paid)
        if bill_reason:
            payable, reason = ZERO, bill_reason
        elif item.category not in policy.category_limits:
            payable, reason = ZERO, f"{item.category.capitalize()} items are not covered."
        elif item.category in policy.prescription_required and not (has_consultation or has_prescription):
            payable, reason = ZERO, "No prescription for this patient dated on or before the bill."
        else:
            payable, reason = claimed, "Covered."
        decisions.append(
            ItemDecision(description=item.description, category=item.category, claimed=claimed, payable=payable, reason=reason)
        )
    return decisions


def apply_category_limits(items: list[ItemDecision], policy: Policy) -> None:
    """Cap what is payable in each category across the whole claim."""
    paid_so_far: dict[str, Decimal] = {}
    for item in items:
        if item.payable == 0:
            continue
        limit = policy.category_limits[item.category]
        room = max(limit - paid_so_far.get(item.category, ZERO), ZERO)
        if item.payable > room:
            item.payable = money(room)
            item.reason = f"Capped by the {item.category} limit of ₹{limit:,.2f} per claim."
        paid_so_far[item.category] = paid_so_far.get(item.category, ZERO) + item.payable


def decide(claim: Claim, policy: Policy) -> Decision:
    bills = [doc for doc in claim.documents if doc.document_type == "bill"]
    prescriptions = [doc for doc in claim.documents if doc.document_type == "prescription"]
    claimed = sum((money(bill.total_amount or 0) for bill in bills), ZERO)

    if not bills:
        return Decision(status="REJECTED", claimed=claimed, approved=ZERO, steps=["No bill was submitted."], items=[])

    problems = document_problems(claim, bills)
    if problems:
        return Decision(status="MANUAL_REVIEW", claimed=claimed, approved=ZERO, steps=problems, items=[])

    items = [decision for bill in bills for decision in assess_bill(bill, claim, policy, prescriptions)]
    apply_category_limits(items, policy)

    payable = sum((item.payable for item in items), ZERO)
    copay = money(payable * policy.copay_percent / 100)
    after_copay = payable - copay
    limit_left = max(policy.annual_limit - claim.member.used_this_year, ZERO)
    approved = money(min(after_copay, limit_left))

    steps = [
        f"Documents checked: {len(bills)} bill(s), {len(prescriptions)} prescription(s).",
        f"Payable under the policy: ₹{payable:,.2f} of ₹{claimed:,.2f} claimed.",
        f"Co-pay of {policy.copay_percent}%: minus ₹{copay:,.2f}.",
    ]
    if approved < after_copay:
        steps.append(f"Only ₹{limit_left:,.2f} of the annual limit of ₹{policy.annual_limit:,.2f} is left.")

    if approved == 0:
        status = "REJECTED"
    elif approved < after_copay or any(item.payable < item.claimed for item in items):
        status = "PARTIAL"
    else:
        status = "APPROVED"

    return Decision(status=status, claimed=claimed, approved=approved, steps=steps, items=items)
