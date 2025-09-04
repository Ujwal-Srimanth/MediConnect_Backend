from fastapi import APIRouter, HTTPException, status,Depends
from typing import List
from ..utils.schedule_service import ScheduleService
from ..models.schedule import Schedule, UpdateScheduleBreaks
from app.database import get_database
from ..utils.auth_utils import get_current_user

router = APIRouter()

@router.get("/check-doctor/{doctor_id}")
async def check_doctor_exists(doctor_id: str,current_user: dict = Depends(get_current_user)):
    db = get_database()
    doctors_collection = db.schedules

    doctor = await doctors_collection.find_one({"doctor_id": doctor_id})
    
    if doctor:
        return {"exists": True}
    else:
        return {"exists": False}



@router.post("/", response_model=Schedule, status_code=status.HTTP_201_CREATED)
async def add_schedule(schedule: Schedule,current_user: dict = Depends(get_current_user)):
    return await ScheduleService.add_schedule(schedule)


@router.get("/{doctor_id}", response_model=List[Schedule],)
async def get_schedules_for_doctor(doctor_id: str,current_user: dict = Depends(get_current_user)):
    return await ScheduleService.get_schedules_for_doctor(doctor_id)

@router.get("/all", response_model=List[Schedule],)
async def get_schedules_for_doctor(doctor_id: str,current_user: dict = Depends(get_current_user)):
    return await ScheduleService.get_schedules_for_doctor_all()


@router.put("/{doctor_id}/breaks", response_model=Schedule)
async def update_schedule_breaks(doctor_id: str, updated_breaks: UpdateScheduleBreaks):
    return await ScheduleService.update_schedule_breaks(doctor_id, updated_breaks)
