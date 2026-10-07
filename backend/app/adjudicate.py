"""Decide a claim end to end: check each photo, read it, then apply the policy rules.

    python -m app.adjudicate claims/claim_001_approved.json            # reads the clean images with the LLM
    python -m app.adjudicate claims/claim_001_approved.json --rough    # the rough photos: stopped by the sharpness check
    python -m app.adjudicate claims/claim_001_approved.json --offline  # uses the expected answers, no API calls
"""

import json
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from app.claims import Claim, Decision, Policy
from app.extract import extract_bill
from app.quality import is_readable
from app.rules import decide
from app.schemas import Bill

ROOT = Path(__file__).parent.parent
SAMPLES = ROOT / "samples"
POLICY = Policy.model_validate_json((ROOT / "policies" / "standard_opd.json").read_text())
VERSIONS = {"clean": (".png", "image/png"), "photo": (".photo.jpg", "image/jpeg"), "rough": (".rough.jpg", "image/jpeg")}


def adjudicate(member: dict, submitted_on: str, images: list[tuple[bytes, str]], policy: Policy = POLICY) -> tuple[Decision, list[Bill]]:
    """The whole pipeline for one claim. Each image comes with its type, such as "image/png".

    Returns the decision and what the model read from each document.
    """
    # A blurred photo is turned away before the model sees it, because the model would guess instead of refusing.
    unclear = [number for number, (data, _) in enumerate(images, start=1) if not is_readable(data)]
    if unclear:
        steps = [f"Document {number} is too blurred to read reliably. Please take a clearer photo." for number in unclear]
        return Decision(status="RETAKE_PHOTO", claimed=0, approved=0, steps=steps, items=[]), []

    with ThreadPoolExecutor() as pool:  # the documents are read at the same time, not one after another
        documents = list(pool.map(lambda image: extract_bill(*image), images))
    return decide(Claim(member=member, submitted_on=submitted_on, documents=documents), policy), documents


def sample_images(names: list[str], version: str = "clean") -> list[tuple[bytes, str]]:
    suffix, mime_type = VERSIONS[version]
    return [((SAMPLES / f"{name}{suffix}").read_bytes(), mime_type) for name in names]


def load_claim(path: Path, offline: bool) -> Claim:
    data = json.loads(path.read_text())
    documents = []
    for name in data["documents"]:
        if offline:
            documents.append(Bill.model_validate_json((SAMPLES / f"{name}.expected.json").read_text()))
        else:
            documents.append(extract_bill((SAMPLES / f"{name}.png").read_bytes(), "image/png"))
    return Claim(member=data["member"], submitted_on=data["submitted_on"], documents=documents)


def report(member_name: str, submitted_on: str, decision: Decision) -> str:
    lines = [
        f"{member_name}, submitted {submitted_on}, {POLICY.name}",
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
    path = Path(sys.argv[1])
    data = json.loads(path.read_text())
    if "--offline" in sys.argv:
        decision = decide(load_claim(path, offline=True), POLICY)
    else:
        images = sample_images(data["documents"], "rough" if "--rough" in sys.argv else "clean")
        decision, _ = adjudicate(data["member"], data["submitted_on"], images)
    print(report(data["member"]["name"], data["submitted_on"], decision))
