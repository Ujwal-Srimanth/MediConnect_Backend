from fastapi import APIRouter, status, Response, Depends, HTTPException
from typing import List
from ..models.hospital import Hospital
from ..utils.auth_utils import get_current_user
from app.database import get_database

router = APIRouter()

# Get collection
def get_hospital_collection():
    db = get_database()
    return db.hosptials

@router.get("/", response_model=List[Hospital])
async def list_hospitals(current_user: dict = Depends(get_current_user)):
    hospitals_collection = get_hospital_collection()
    docs = await hospitals_collection.find().to_list(length=None)
    return [Hospital(**doc) for doc in docs]

@router.get("/{hospital_id}", response_model=Hospital)
async def get_hospital(hospital_id: str, current_user: dict = Depends(get_current_user)):
    hospitals_collection = get_hospital_collection()
    doc = await hospitals_collection.find_one({"_id": hospital_id})
    if not doc:
        raise HTTPException(status_code=404, detail="Hospital not found")
    return Hospital(**doc)

