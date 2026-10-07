"""The web API, with the model replaced by the expected answers so no API calls are made."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import SAMPLE_CLAIMS, app
from app.schemas import Bill

SAMPLES = Path(__file__).parent.parent / "samples"
client = TestClient(app)


@pytest.fixture(autouse=True)
def model_returns_the_expected_answer(monkeypatch):
    """Recognise each sample image by its bytes and hand back its expected answer."""
    answers = {}
    for expected in SAMPLES.glob("*.expected.json"):
        name = expected.name.removesuffix(".expected.json")
        for suffix in (".png", ".photo.jpg"):
            answers[(SAMPLES / f"{name}{suffix}").read_bytes()] = Bill.model_validate_json(expected.read_text())
    monkeypatch.setattr("app.adjudicate.extract_bill", lambda data, mime_type: answers[data])


def upload(name: str, mime_type: str = "image/png"):
    return ("files", (name, (SAMPLES / name).read_bytes(), mime_type))


@pytest.mark.parametrize("claim_id", SAMPLE_CLAIMS)
def test_every_sample_claim_gets_its_expected_decision(claim_id):
    expected = SAMPLE_CLAIMS[claim_id]["expected"]
    decision = client.post(f"/api/samples/{claim_id}").json()["decision"]
    assert decision["status"] == expected["status"]
    assert float(decision["approved"]) == float(expected["approved"])


def test_a_rough_sample_asks_for_a_new_photo():
    result = client.post("/api/samples/claim_001_approved", params={"version": "rough"}).json()
    assert result["decision"]["status"] == "RETAKE_PHOTO"
    assert result["documents"] == []


def test_an_uploaded_claim_is_decided_and_the_reading_is_returned():
    form = {"member_name": "Karthik Subramanian", "submitted_on": "2026-09-10"}
    response = client.post("/api/claims", data=form, files=[upload("004_prescription.png"), upload("003_lab_bill.png")])
    result = response.json()
    assert response.status_code == 200
    assert result["decision"]["status"] == "PARTIAL"
    assert result["decision"]["approved"] == "1359.10"
    assert [doc["document_type"] for doc in result["documents"]] == ["prescription", "bill"]


def test_the_amount_already_used_this_year_is_respected():
    form = {"member_name": "Ananya Rao", "submitted_on": "2026-09-20", "used_this_year": "14000"}
    decision = client.post("/api/claims", data=form, files=[upload("001_clinic_bill.png")]).json()["decision"]
    assert decision["approved"] == "1000.00"


def test_bad_uploads_are_refused_with_a_reason():
    form = {"member_name": "Ananya Rao", "submitted_on": "2026-09-20"}
    not_an_image = client.post("/api/claims", data=form, files=[upload("001_clinic_bill.html", "text/html")])
    too_many = client.post("/api/claims", data=form, files=[upload("001_clinic_bill.png")] * 5)
    assert not_an_image.status_code == 400 and "only PNG" in not_an_image.json()["detail"]
    assert too_many.status_code == 400 and "at most 4" in too_many.json()["detail"]


def test_an_unknown_sample_is_not_found():
    assert client.post("/api/samples/nope").status_code == 404


def test_a_model_failure_becomes_a_clear_error(monkeypatch):
    def overloaded(data, mime_type):
        raise RuntimeError("503 high demand")

    monkeypatch.setattr("app.adjudicate.extract_bill", overloaded)
    response = client.post("/api/samples/claim_001_approved")
    assert response.status_code == 502
    assert "try again" in response.json()["detail"]


def test_sample_images_are_served():
    response = client.get("/api/sample-files/001_clinic_bill.png")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/png"
