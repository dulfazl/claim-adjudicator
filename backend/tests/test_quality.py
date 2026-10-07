"""The sharpness check must let scans and ordinary photos through and stop the rough ones."""

from pathlib import Path

import pytest

from app.adjudicate import adjudicate
from app.quality import is_readable, sharpness

SAMPLES = Path(__file__).parent.parent / "samples"
NAMES = sorted(p.stem for p in SAMPLES.glob("*.html"))


@pytest.mark.parametrize("name", NAMES)
def test_scans_and_ordinary_photos_pass(name):
    assert is_readable((SAMPLES / f"{name}.png").read_bytes())
    assert is_readable((SAMPLES / f"{name}.photo.jpg").read_bytes())


@pytest.mark.parametrize("name", NAMES)
def test_rough_photos_are_stopped(name):
    assert not is_readable((SAMPLES / f"{name}.rough.jpg").read_bytes())


def test_the_same_page_scores_lower_the_worse_the_photo():
    scan, photo, rough = (sharpness((SAMPLES / f"001_clinic_bill{suffix}").read_bytes()) for suffix in (".png", ".photo.jpg", ".rough.jpg"))
    assert scan > photo > rough


def test_a_blurred_photo_is_turned_away_without_calling_the_model(monkeypatch):
    def model_must_not_be_called(*args):
        raise AssertionError("the model was called on a blurred photo")

    monkeypatch.setattr("app.adjudicate.extract_bill", model_must_not_be_called)
    rough = (SAMPLES / "001_clinic_bill.rough.jpg").read_bytes()
    decision, documents = adjudicate({"name": "Ananya Rao"}, "2026-09-20", [(rough, "image/jpeg")])
    assert decision.status == "RETAKE_PHOTO"
    assert "clearer photo" in decision.steps[0]
