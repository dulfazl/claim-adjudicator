"""The generated test set: repeatable, in step with the files on disk, and varied enough to be worth scoring."""

import json
from collections import Counter
from pathlib import Path

from app.adjudicate import POLICY
from app.claims import Claim
from app.rules import decide
from app.schemas import Bill
from scripts.generate_dataset import INJECTION, build

DATASET = Path(__file__).parent.parent / "dataset"


def test_the_same_seed_gives_the_same_documents():
    first_documents, first_cases = build(seed=11)
    second_documents, second_cases = build(seed=11)
    assert first_cases == second_cases
    assert {name: html for name, (_, html) in first_documents.items()} == {name: html for name, (_, html) in second_documents.items()}


def test_files_on_disk_match_the_generator():
    documents, cases = build()
    assert json.loads((DATASET / "cases.json").read_text()) == cases
    for name, (bill, html) in documents.items():
        assert Bill.model_validate_json((DATASET / f"{name}.expected.json").read_text()) == bill
        assert (DATASET / f"{name}.html").read_text() == html


def test_every_claim_can_be_decided_and_all_four_outcomes_appear():
    documents, cases = build()
    statuses = Counter(
        decide(Claim(member=case["member"], submitted_on=case["submitted_on"], documents=[documents[n][0] for n in case["documents"]]), POLICY).status
        for case in cases
    )
    assert set(statuses) == {"APPROVED", "PARTIAL", "REJECTED", "MANUAL_REVIEW"}


def test_the_set_contains_the_hard_cases_on_purpose():
    documents, _ = build()
    pages = [html for _, html in documents.values()]
    assert any(INJECTION in html for html in pages)  # text that tries to give the model orders
    assert any('class="stamp"' in html for html in pages)  # a stamp over part of the page
    wrong_totals = [
        bill for bill, _ in documents.values()
        if bill.total_amount is not None and abs(sum(i.amount for i in bill.line_items) - (bill.discount or 0) - bill.total_amount) > 1
    ]
    assert wrong_totals  # bills whose printed total does not add up
