from fastapi import APIRouter, HTTPException , Depends
from pydantic import BaseModel, Field
from typing import Optional
from bson import ObjectId
from app.database import get_database
from ..utils.auth_utils import get_current_user, admin_required
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from fastapi import Request
from fastapi.encoders import jsonable_encoder

router = APIRouter()



# -----------------------------
# MODELS
# -----------------------------
class Doctor5(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    age: int = Field(..., gt=0, le=120)
    gender: str = Field(..., pattern="^(Male|Female|Other)$")
    specialization: str
    hospital_id: str
    fee: int = Field(..., gt=0)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class Receptionist5(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    age: int = Field(..., gt=18, le=70)
    mobile: str = Field(..., min_length=10, max_length=10)
    hospital_id: str

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}


class Hospital5(BaseModel):
    id: str = Field(..., alias="_id")
    name: str
    location: str
    mobile: str = Field(..., min_length=14, max_length=14)

    class Config:
        populate_by_name = True
        json_encoders = {ObjectId: str}

# -----------------------------
# ROUTES
# -----------------------------

# ✅ Create Doctor
@router.post("/doctors", response_model=Doctor5)
async def create_doctor(doctor: Doctor5, user=Depends(admin_required)):
    db = get_database()

    # check if doctor exists
    if await db.doctors.find_one({"_id": doctor.id}):
        raise HTTPException(status_code=400, detail="Doctor with this ID already exists")

    # check hospital exists
    hospital = await db.hosptials.find_one({"_id": doctor.hospital_id})
    if not hospital:
        raise HTTPException(status_code=400, detail="Hospital is Not Yet Registered")

    # enrich with hospital name
    doctor_data = doctor.dict(by_alias=True)
    doctor_data["hospital"] = hospital["name"]

    await db.doctors.insert_one(doctor_data)
    return doctor_data



# ✅ Create Receptionist
@router.post("/receptionists", response_model=Receptionist5)
async def create_receptionist(receptionist: Receptionist5, user=Depends(admin_required)):
    db = get_database()

    # check if receptionist exists
    if await db.receptionist.find_one({"_id": receptionist.id}):
        raise HTTPException(status_code=400, detail="Receptionist with this ID already exists")

    # check hospital exists
    hospital = await db.hosptials.find_one({"_id": receptionist.hospital_id})
    if not hospital:
        raise HTTPException(status_code=400, detail="Hospital is Not Yet Registered")

    # enrich with hospital name
    receptionist_data = receptionist.dict(by_alias=True)
    receptionist_data["hospital"] = hospital["name"]

    await db.receptionists.insert_one(receptionist_data)
    return receptionist_data



# ✅ Create Hospital
@router.post("/hospitals", response_model=Hospital5)
async def create_hospital(hospital: Hospital5,user=Depends(admin_required)):
    db = get_database()
    exists = await db.hosptials.find_one({"_id": hospital.id})
    if exists:
        raise HTTPException(status_code=400, detail="Hospital with this ID already exists")
    await db.hosptials.insert_one(hospital.dict(by_alias=True))
    return hospital
