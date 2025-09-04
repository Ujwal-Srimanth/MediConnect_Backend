from fastapi import APIRouter, status, Response , Depends , HTTPException
from typing import List
from ..utils.doctor_service import DoctorService
from ..models.doctors import Doctor, UpdateDoctor , Doctor1 , Receptionist
from ..utils.slot_service import SlotService
from ..utils.auth_utils import get_current_user
from app.database import get_database
from bson import ObjectId
router = APIRouter()

def serialize_doc(doc):
    """Convert ObjectId to str recursively"""
    if not doc:
        return doc
    serialized = {}
    for k, v in doc.items():
        if isinstance(v, ObjectId):
            serialized[k] = str(v)
        else:
            serialized[k] = v
    return serialized


@router.get("/receptionist/{email}/appointments")
async def get_hospital_schedules(email: str,current_user: dict = Depends(get_current_user)):
    db = get_database()
    users_collection = db.users
    receptionist_collection = db.receptionist
    doctors_collection = db.doctors
    appointments_collection = db.appointments

    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="Receptionist not found")

    receptionist = await receptionist_collection.find_one({"_id": user["ID"]})
    if not receptionist:
        raise HTTPException(status_code=404, detail="Receptionist not found")
    
    hospital_id = receptionist.get("hospital_id")
    if not hospital_id:
        raise HTTPException(status_code=400, detail="Receptionist missing hospital_id")

    # Get doctors for this hospital
    doctors_cursor = doctors_collection.find({"hospital_id": hospital_id})
    doctors = await doctors_cursor.to_list(length=None)
    if not doctors:
        return {"hospital_id": hospital_id, "appointments": []}

    doctor_ids = [doc["_id"] for doc in doctors]

    # Get appointments
    appointments_cursor = appointments_collection.find({"doctor_id": {"$in": doctor_ids}})
    appointments = await appointments_cursor.to_list(length=None)

    # Add doctor name and serialize ObjectId
    doctor_map = {str(doc["_id"]): doc.get("name") for doc in doctors}
    serialized_appointments = []
    for appt in appointments:
        appt_data = serialize_doc(appt)
        appt_data["doctor_name"] = doctor_map.get(str(appt_data["doctor_id"]), None)
        serialized_appointments.append(appt_data)

    print("bYE")

    return {"hospital_id": hospital_id, "appointments": serialized_appointments}

@router.post("/", response_model=Doctor, status_code=status.HTTP_201_CREATED)
async def create_doctor(doctor: Doctor,current_user: dict = Depends(get_current_user)):
    return await DoctorService.create_doctor(doctor)


@router.get("/", response_model=List[Doctor1])
async def list_doctors(current_user: dict = Depends(get_current_user)):
    return await DoctorService.list_doctors()


@router.get("/{id}", response_model=Doctor)
async def get_doctor(id: str):
    return await DoctorService.get_doctor(id)


@router.get("/receptionist/{id}", response_model=Receptionist)
async def get_receptionist(id: str):
    return await DoctorService.get_receptionist(id)


@router.get("/hospital/{hospital_id}", response_model=List[Doctor1])
async def get_doctors_by_hospital(hospital_id: str,current_user: dict = Depends(get_current_user)):
    return await DoctorService.get_doctors_by_hospital(hospital_id)


@router.put("/{id}", response_model=Doctor)
async def update_doctor(id: str, doctor: UpdateDoctor):
    return await DoctorService.update_doctor(id, doctor)


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_doctor(id: str):
    DoctorService.delete_doctor(id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/{doctor_id}/{date}/slots")
async def get_doctor_slots(doctor_id: str, date: str,current_user: dict = Depends(get_current_user)):
    """
    Return all 15-min slots (9 to 5) for a given date,
    marking them filled if any booking overlaps.
    """
    print("hi")
    slots = await SlotService.get_slots(doctor_id, date)
    return {"slots": slots}
