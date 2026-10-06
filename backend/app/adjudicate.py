"""Decide a claim end to end: read each document, then apply the policy rules.

    python -m app.adjudicate claims/claim_001_approved.json            # reads the images with the LLM
    python -m app.adjudicate claims/claim_001_approved.json --offline  # uses the expected answers, no API calls
"""

import json
import sys
from pathlib import Path

from app.claims import Claim, Decision, Policy
from app.extract import extract_bill
from app.rules import decide
from app.schemas import Bill

ROOT = Path(__file__).parent.parent
SAMPLES = ROOT / "samples"
POLICY = Policy.model_validate_json((ROOT / "policies" / "standard_opd.json").read_text())


def load_claim(path: Path, offline: bool) -> Claim:
    data = json.loads(path.read_text())
    documents = []
    for name in data["documents"]:
        if offline:
            documents.append(Bill.model_validate_json((SAMPLES / f"{name}.expected.json").read_text()))
        else:
            documents.append(extract_bill((SAMPLES / f"{name}.png").read_bytes(), "image/png"))
    return Claim(member=data["member"], submitted_on=data["submitted_on"], documents=documents)


def report(claim: Claim, decision: Decision) -> str:
    lines = [
        f"{claim.member.name}, submitted {claim.submitted_on}, {POLICY.name}",
        "",
        f"{decision.status}: ₹{decision.approved:,.2f} approved of ₹{decision.claimed:,.2f} claimed",
        "",
    ]
    for item in decision.items:
        lines.append(f"  ₹{item.payable:>9,.2f} of ₹{item.claimed:>9,.2f}  {item.description[:38]:38}  {item.reason}")
    lines.append("")
    lines += [f"  {number}. {step}" for number, step in enumerate(decision.steps, start=1)]
    return "\n".join(lines)


if __name__ == "__main__":
    claim = load_claim(Path(sys.argv[1]), offline="--offline" in sys.argv)
    print(report(claim, decide(claim, POLICY)))
