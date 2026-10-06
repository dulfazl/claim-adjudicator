"""The shapes used when deciding a claim: the policy, the claim itself, and the decision."""

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.schemas import Bill


class Policy(BaseModel):
    name: str
    start_date: date
    end_date: date
    annual_limit: Decimal
    copay_percent: Decimal = Field(description="Share of every payable amount that the member bears.")
    claim_window_days: int = Field(description="A bill must be submitted within this many days of its date.")
    category_limits: dict[str, Decimal] = Field(
        description="Covered categories and the most payable for each per claim. A category missing here is not covered."
    )
    prescription_required: list[str] = Field(description="Categories that need a prescription.")


class Member(BaseModel):
    name: str
    used_this_year: Decimal = Decimal("0")


class Claim(BaseModel):
    member: Member
    submitted_on: date
    documents: list[Bill]


class ItemDecision(BaseModel):
    description: str
    category: str
    claimed: Decimal
    payable: Decimal
    reason: str


class Decision(BaseModel):
    status: Literal["APPROVED", "PARTIAL", "REJECTED", "MANUAL_REVIEW"]
    claimed: Decimal
    approved: Decimal
    steps: list[str] = Field(description="What was checked and calculated, in order.")
    items: list[ItemDecision]
