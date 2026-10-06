"""The shape of the data we want out of a medical document.

The LLM is forced to answer in exactly this shape, and Pydantic rejects
anything that does not fit, so the rest of the code can trust the types.
"""

from typing import Literal, Optional

from pydantic import BaseModel, Field


class LineItem(BaseModel):
    description: str = Field(description="The item exactly as printed on the bill.")
    category: Literal["consultation", "diagnostic", "pharmacy", "procedure", "cosmetic", "other"] = Field(
        description=(
            "consultation = doctor's fee; diagnostic = lab tests, X-rays and scans; "
            "pharmacy = medicines and medical consumables; procedure = dressing, injection, surgery, dental treatment; "
            "cosmetic = cosmetic treatments, toiletries and personal-care products; "
            "other = anything else, such as collection or registration charges."
        )
    )
    quantity: Optional[float] = Field(description="Quantity if printed, otherwise null.")
    amount: float = Field(description="Total for this line in rupees, as a plain number.")


class Bill(BaseModel):
    document_type: Literal["bill", "prescription", "lab_report", "other"]
    provider_name: Optional[str] = Field(description="Clinic, hospital, lab or pharmacy name.")
    patient_name: Optional[str]
    doctor_name: Optional[str] = Field(description="Treating, prescribing or referring doctor.")
    bill_number: Optional[str] = Field(description="Bill, invoice or receipt number.")
    bill_date: Optional[str] = Field(description="Date of the document as YYYY-MM-DD.")
    diagnosis: Optional[str] = Field(description="Diagnosis if written on the document, otherwise null.")
    line_items: list[LineItem] = Field(description="Charged items only. Empty for a prescription.")
    discount: Optional[float] = Field(description="Discount on the whole bill in rupees, if printed.")
    total_amount: Optional[float] = Field(description="Final amount payable after discount, in rupees.")
