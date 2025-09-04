from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId

class Receptionist(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str = Field(..., min_length=3, max_length=50)
    age: int = Field(..., gt=18, le=65)
    hospital_name: str = Field(..., min_length=3, max_length=100)
    hospital_id: str = Field(..., min_length=3, max_length=50)
    mobile: str = Field(..., min_length = 10 , max_length=13)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "name": "Anita Sharma",
                "age": 25,
                "hospital_name": "Apollo Hospitals",
                "hospital_id": "HSP001",
                "mobile": "9001000001"
            }
        }

class Doctor(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str = Field(..., min_length=3, max_length=50)
    age: int = Field(..., gt=0, le=120)
    fee: int = Field(...,gt = 0)
    gender: str = Field(..., pattern="^(Male|Female|Other)$")
    specialization: str = Field(..., min_length=3, max_length=100)
    hospital: str = Field(..., min_length=3, max_length=100)
    hospital_id: str = Field(..., min_length=3, max_length=50)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "name": "Dr. Sarah Lee",
                "age": 42,
                "fee" : 500,
                "gender": "Female",
                "specialization": "Pediatrics",
                "hospital": "Community Health Center",
                "hospital_id": "CHC002",
            }
        }

class Doctor1(BaseModel):
    id: Optional[str] = Field(None, alias="_id")
    name: str = Field(..., min_length=3, max_length=50)
    age: int = Field(..., gt=0, le=120)
    fee: int = Field(...,gt = 0)
    gender: str = Field(..., pattern="^(Male|Female|Other)$")
    specialization: str = Field(..., min_length=3, max_length=100)
    hospital: str = Field(..., min_length=3, max_length=100)
    hospital_id: str = Field(..., min_length=3, max_length=50)
    registered: bool = Field(...,description="whether doctor registered")

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}
        json_schema_extra = {
            "example": {
                "name": "Dr. Sarah Lee",
                "age": 42,
                "fee" : 500,
                "gender": "Female",
                "specialization": "Pediatrics",
                "hospital": "Community Health Center",
                "hospital_id": "CHC002",
                "registered":True
            }
        }


class UpdateDoctor(BaseModel):
    name: Optional[str] = Field(None, min_length=3, max_length=50)
    age: Optional[int] = Field(None, gt=0, le=120)
    gender: Optional[str] = Field(None, pattern="^(Male|Female|Other)$")
    specialization: Optional[str] = Field(None, min_length=3, max_length=100)
    hospital: Optional[str] = Field(None, min_length=3, max_length=100)
    hospital_id: Optional[str] = Field(None, min_length=3, max_length=50)

    class Config:
        json_schema_extra = {"example": {"specialization": "Pediatric Oncology"}}
