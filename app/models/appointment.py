from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from enum import Enum


class AppointmentStatus(str, Enum):
    AVAILABLE = "available"
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class SlotBookingRequest(BaseModel):
    patient_id: str = Field(..., description="Patient ID")
    start_datetime: datetime = Field(..., description="Start datetime of slot")
    end_datetime: datetime = Field(..., description="End datetime of slot")
    purpose: str | None = Field(None, description="Purpose of appointment")


class Appointment(BaseModel):
    doctor_id: str = Field(..., description="Doctor identifier")
    patient_id: Optional[str] = Field(None, description="Patient ID if booked")
    date: str = Field(..., description="Date in YYYY-MM-DD format")
    day: str = Field(..., description="Day of the week")
    start_datetime: datetime = Field(..., description="Start datetime of the slot")
    end_datetime: datetime = Field(..., description="End datetime of the slot")
    is_booked: bool = Field(default=False, description="Whether the slot is booked")
    purpose: Optional[str] = Field(None, description="Purpose of the appointment")
    status: AppointmentStatus = Field(
        default=AppointmentStatus.AVAILABLE, description="Appointment status"
    )


class AppointmentBooking(BaseModel):
    slot_id: str = Field(..., description="Slot ID to book")
    patient_id: str = Field(..., description="Patient ID")
    purpose: str = Field(..., description="Purpose of the appointment")


class AppointmentAction(BaseModel):
    action: str = Field(..., description="Action to take: 'approve' or 'reject'")
    reason: Optional[str] = Field(None, description="Reason for rejection")
