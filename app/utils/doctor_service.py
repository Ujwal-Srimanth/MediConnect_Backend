from fastapi import HTTPException, status, Response
from bson import ObjectId
from typing import List

from httpx import get
from ..models.doctors import Doctor, UpdateDoctor ,Doctor1 , Receptionist
from app.database import get_database


def serialize_doc(doc: dict) -> dict:
    if not doc:
        return doc
    doc["_id"] = str(doc["_id"])
    return doc


class DoctorService:
    @staticmethod
    async def create_doctor(doctor: Doctor):
        doctors_collection = get_database().doctors
        doctor_data = doctor.model_dump(by_alias=True)
        doctor_data.pop("_id", None)
        result = doctors_collection.insert_one(doctor_data)
        created_doctor = doctors_collection.find_one({"_id": result.inserted_id})
        if created_doctor:
            created_doctor["_id"] = str(created_doctor["_id"])
            return Doctor(**created_doctor)
        raise HTTPException(status_code=500, detail="Failed to create doctor.")

    @staticmethod
    async def list_doctors() -> List[Doctor1]:
        db = get_database()
        print("hi")
        doctors_collection = db.doctors
        schedules_collection = db.schedules
        docs = await doctors_collection.find().to_list(length=None)

        # 2️⃣ Fetch all doctor_ids present in schedules
        schedules = await schedules_collection.find({}, {"doctor_id": 1}).to_list(length=None)
        print(schedules)
        registered_ids = {sched["doctor_id"] for sched in schedules}  

        # 3️⃣ Add registered field
        doctor_list = []
        for doc in docs:
            doc_data = serialize_doc(doc)
            doc_data["registered"] = doc_data["_id"] in registered_ids
            doctor_list.append(Doctor1(**doc_data))


        return doctor_list
    
    @staticmethod
    @staticmethod
    async def get_doctors_by_hospital(hospital_id: str) -> List[Doctor1]:
        db = get_database()
        doctors_collection = db.doctors
        schedules_collection = db.schedules

        # 1️⃣ Get doctors for the hospital
        doctors = await doctors_collection.find({"hospital_id": hospital_id}).to_list(length=None)

        if not doctors:
            raise HTTPException(
                status_code=404,
                detail=f"No doctors found for hospital ID '{hospital_id}'.",
            )

        # 2️⃣ Fetch doctor_ids from schedules
        schedules = await schedules_collection.find({}, {"doctor_id": 1}).to_list(length=None)
        registered_ids = {sched["doctor_id"] for sched in schedules}
        print(registered_ids)

        # 3️⃣ Add registered field
        doctor_list = []
        for doc in doctors:
            doc_data = serialize_doc(doc)
            doc_data["registered"] = doc_data["_id"] in registered_ids
            doctor_list.append(Doctor1(**doc_data))
        print(doctor_list)

        return doctor_list

    

    @staticmethod
    async def get_receptionist(id: str) -> Receptionist:
        receptionists_collection = get_database().receptionist

        # Validate format (starts with "REC")
        if not id.startswith("REC"):
            raise HTTPException(status_code=400, detail="Invalid Receptionist ID format.")

        # Query by _id (which is a string)
        receptionist = await receptionists_collection.find_one({"_id": id})
        if receptionist:
            return Receptionist(**serialize_doc(receptionist))
        
        raise HTTPException(
            status_code=404,
            detail="Receptionist not found. Please enter a different ID or contact the hospital administration."
        )

    @staticmethod
    async def get_doctor(id: str) -> Doctor:
        doctors_collection = get_database().doctors

        # Validate format (starts with "DOC")
        if not id.startswith("DOC"):
            raise HTTPException(status_code=400, detail="Invalid Doctor ID format.")

        # Query by _id (which is a string)
        doctor = await doctors_collection.find_one({"_id": id})
        if doctor:
            return Doctor(**serialize_doc(doctor))
        raise HTTPException(status_code=404, detail="Doctor not found. Please Enter a Different ID or Contact the Hospital Administration")

    @staticmethod
    async def update_doctor(id: str, doctor: UpdateDoctor) -> Doctor:
        doctors_collection = get_database().doctors

        if not id.startswith("DOC"):
            raise HTTPException(status_code=400, detail="Invalid Doctor ID format.")

        update_data = doctor.model_dump(by_alias=True, exclude_unset=True)
        if not update_data:
            raise HTTPException(status_code=400, detail="No fields to update.")

        updated_doctor = await doctors_collection.find_one_and_update(
            {"_id": id}, {"$set": update_data}, return_document=True
        )

        if not updated_doctor:
            raise HTTPException(status_code=404, detail="Doctor not found.")

        return Doctor(**serialize_doc(updated_doctor))

    @staticmethod
    async def delete_doctor(id: str):
        doctors_collection = get_database().doctors

        if not id.startswith("DOC"):
            raise HTTPException(status_code=400, detail="Invalid Doctor ID format.")

        delete_result = await doctors_collection.delete_one({"_id": id})
        if delete_result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Doctor not found.")

