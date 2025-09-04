from pydantic import BaseModel, Field
from typing import Optional, List
from bson import ObjectId


class BreakTime(BaseModel):
    start_time: str = Field(
        ...,
        pattern=r"^(?:2[0-3]|[01]?[0-9]):[0-5]?[0-9]$",
        description="Break start time in HH:MM format (24-hour)",
    )
    end_time: str = Field(
        ...,
        pattern=r"^(?:2[0-3]|[01]?[0-9]):[0-5]?[0-9]$",
        description="Break end time in HH:MM format (24-hour)",
    )
    reason:str = Field(...,description="Reason for the break")
    class Config:
        json_schema_extra = {"example": {"start_time": "13:00", "end_time": "14:00"}}


class Schedule(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    doctor_id: str = Field(
        ..., description="The ID of the doctor this schedule belongs to"
    )
    day_off: str = Field(
        ...,
        pattern="^(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)$",
        description="Day of the week (e.g., Monday)",
    )
    start_time: str = Field(
        ...,
        pattern=r"^(?:2[0-3]|[01]?[0-9]):[0-5]?[0-9]$",
        description="Work start time in HH:MM format (24-hour)",
    )
    end_time: str = Field(
        ...,
        pattern=r"^(?:2[0-3]|[01]?[0-9]):[0-5]?[0-9]$",
        description="Work end time in HH:MM format (24-hour)",
    )
    breaks: List[BreakTime] = Field(
        default_factory=list, description="List of break time slots"
    )

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "doctor_id": "651a8c8e6d2b4a7e9f1a2b3c",
                "day_off": "Sunday",
                "start_time": "09:00",
                "end_time": "17:00",
                "breaks": [
                    {"start_time": "12:00", "end_time": "12:30"},
                    {"start_time": "15:00", "end_time": "15:15"},
                ],
            }
        }


class UpdateScheduleBreaks(BaseModel):
    breaks: List[BreakTime] = Field(
        ..., description="List of new break time slots to update"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "breaks": [
                    {"start_time": "13:30", "end_time": "14:30"},
                    {"start_time": "16:00", "end_time": "16:15"},
                ]
            }
        }
