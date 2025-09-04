from fastapi import HTTPException
from typing import List
from pymongo import ReturnDocument
from bson import ObjectId
from ..models.schedule import Schedule, UpdateScheduleBreaks
from app.database import get_database
import pytz
from datetime import datetime

ist = pytz.timezone("Asia/Kolkata")


def serialize_doc(doc: dict) -> dict:
    """Convert MongoDB ObjectIds to strings in a single document."""
    if not doc:
        return doc
    doc = doc.copy()
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    if "patient_id" in doc and isinstance(doc["patient_id"], ObjectId):
        doc["patient_id"] = str(doc["patient_id"])
    return doc


class ScheduleService:
    @staticmethod
    async def add_schedule(schedule: Schedule):
        db = get_database()
        schedules_collection = db.schedules
        doctors_collection = db.doctors

        # ✅ doctor_id is "DOC001" (string), not ObjectId
        doctor_exists = await doctors_collection.find_one({"ID": schedule.doctor_id})
        if doctor_exists:
            raise HTTPException(status_code=404, detail="Doctor not found.")

        schedule_data = schedule.model_dump(by_alias=True)
        schedule_data.pop("_id", None)

        result = await schedules_collection.insert_one(schedule_data)
        created_schedule = await schedules_collection.find_one({"_id": result.inserted_id})

        if created_schedule:
            return Schedule(**serialize_doc(created_schedule))

        raise HTTPException(status_code=500, detail="Failed to create schedule.")

    @staticmethod
    async def get_schedules_for_doctor(doctor_id: str) -> List[Schedule]:
        db = get_database()
        schedules_collection = db.schedules

        # ✅ no ObjectId check
        cursor = await schedules_collection.find({"doctor_id": doctor_id}).to_list(length=None)
        schedules = []
        for doc in cursor:
            schedules.append(Schedule(**serialize_doc(doc)))
        return schedules
    
    @staticmethod
    async def get_schedules_for_doctor_all() -> List[Schedule]:
        db = get_database()
        schedules_collection = db.schedules

        # ✅ no ObjectId check
        cursor = await schedules_collection.find({}).to_list(length=None)
        schedules = []
        for doc in cursor:
            schedules.append(Schedule(**serialize_doc(doc)))
        return schedules

