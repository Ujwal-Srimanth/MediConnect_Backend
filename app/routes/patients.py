from fastapi import APIRouter, HTTPException, UploadFile, File, Form , Query , Depends
from typing import Optional, List, Any, Dict
import os, shutil, logging
from datetime import date
from bson import ObjectId

from app.database import patients_collection
from app.models.models import PatientOut
from app.utils.utils import to_iso_date, normalize_files
from app.config import UPLOAD_DIR
from ..utils.auth_utils import get_current_user
from app.database import get_database
from ..models.models import AnalyticsRequest
import httpx
from ..config import OPEN_AI_API_KEY


router = APIRouter()

db = get_database()

from fastapi.responses import StreamingResponse
from azure.storage.blob import BlobServiceClient
import os, io

# Use same connection string from app.config
from app.config import container_client

@router.get("/files/{filename}")
async def get_file(filename: str, current_user: dict = Depends(get_current_user)):
    try:
        blob_client = container_client.get_blob_client(filename)
        stream = io.BytesIO()
        blob_data = blob_client.download_blob().readall()
        stream.write(blob_data)
        stream.seek(0)

        # Optional: detect content type if you want proper headers
        return StreamingResponse(stream, media_type="application/octet-stream")
    except Exception as e:
        raise HTTPException(status_code=404, detail=f"File {filename} not found")


@router.get("/", response_model=List[PatientOut])
async def list_patients(email_address: str = Query(None),current_user: dict = Depends(get_current_user)):
    patients: List[PatientOut] = []

    query = {}
    if email_address:
        query = {"email_address": email_address}


    async for p in patients_collection.find(query):
        resp: Dict[str, Any] = {
            "id": str(p.get("_id", "")),
            "first_name": p.get("first_name", ""),
            "last_name": p.get("last_name", ""),
            "date_of_birth": to_iso_date(p.get("date_of_birth")),
            "gender": p.get("gender", ""),
            "contact_number": p.get("contact_number", ""),
            "email_address": p.get("email_address", ""),
            "height_cm": p.get("height_cm"),
            "weight_kg": p.get("weight_kg"),
            "any_disability": bool(p.get("any_disability", False)),
            "allergies": p.get("allergies"),
            "address": p.get("address",""),
            "existing_conditions": p.get("existing_conditions"),
            "current_medications": p.get("current_medications"),
            "blood_group": p.get("blood_group"),
            "emergency_contact": p.get("emergency_contact"),
            "insurance": p.get("insurance"),
            "medical_records": normalize_files(p.get("medical_records")),
        }
        patients.append(PatientOut(**resp))
    return patients


@router.post("/", response_model=PatientOut)
async def create_patient(
    first_name: str = Form(...),
    last_name: str = Form(...),
    date_of_birth: date = Form(...),
    gender: str = Form(...),
    contact_number: str = Form(...),
    email_address: str = Form(...),
    height_cm: Optional[float] = Form(None),
    weight_kg: Optional[float] = Form(None),
    any_disability: bool = Form(False),
    allergies: Optional[str] = Form(None),
    address: str = Form(...),
    existing_conditions: Optional[str] = Form(None),
    current_medications: Optional[str] = Form(None),
    blood_group: Optional[str] = Form(None),
    emergency_contact_name: Optional[str] = Form(None),
    emergency_relation: Optional[str] = Form(None),
    emergency_phone: Optional[str] = Form(None),
    insurance_details: Optional[str] = Form(None),
    medical_records: Optional[List[UploadFile]] = File(None),
    current_user: dict = Depends(get_current_user)
):
    try:
        dob_iso = date_of_birth.strftime("%Y-%m-%d")

        # Fetch existing patient first
        existing_patient = await patients_collection.find_one({"email_address": email_address})
        existing_medical_records = existing_patient.get("medical_records", []) if existing_patient else []

        doc = {
            "first_name": first_name,
            "last_name": last_name,
            "date_of_birth": dob_iso,
            "gender": gender,
            "contact_number": contact_number,
            "email_address": email_address,
            "height_cm": height_cm,
            "weight_kg": weight_kg,
            "any_disability": any_disability,
            "allergies": allergies,
            "address": address,
            "existing_conditions": existing_conditions,
            "current_medications": current_medications,
            "blood_group": blood_group,
            "emergency_contact": (
                {"contact_name": emergency_contact_name, "relation": emergency_relation, "phone": emergency_phone}
                if emergency_contact_name else None
            ),
            "insurance": ({"insurance_details": insurance_details} if insurance_details else None),
            "medical_records": existing_medical_records.copy(),  # start with existing files
        }

        # Save newly uploaded files and append to existing
        if medical_records:
            for f in medical_records:
                # save_path = os.path.join(UPLOAD_DIR, f.filename)
                # with open(save_path, "wb") as buf:
                #     shutil.copyfileobj(f.file, buf)
                # doc["medical_records"].append({"filename": f.filename, "filepath": save_path})
                from app.config import container_client
                import re
                def clean_filename(filename: str) -> str:
                    filename = filename.replace(" ", "_")
                    filename = re.sub(r"[()]", "", filename)
                    return filename
                safe_filename = clean_filename(f.filename)
                import uuid
                unique_name = f"{uuid.uuid4().hex}_{safe_filename}"
                blob_client = container_client.get_blob_client(unique_name)
                blob_client.upload_blob(f.file, overwrite=True)

                file_url = blob_client.url
                doc["medical_records"].append({"filename": safe_filename, "filepath": file_url, "blob_name": unique_name})

        # Update or insert patient
        result = await patients_collection.update_one(
            {"email_address": email_address},
            {"$set": doc},
            upsert=True
        )

        # Get updated/inserted document
        patient = await patients_collection.find_one({"email_address": email_address})
        resp = {
            "id": str(patient["_id"]),
            **patient,
            "medical_records": normalize_files(patient.get("medical_records", []))
        }

        await db["users"].update_one(
            {"email": email_address},           # Find user by email
                {"$set": {"is_profile_filled": True}}  # Set is_profile_filled to True
        )
        return PatientOut(**resp)

    except Exception as e:
        logging.exception("Failed to save patient")
        raise HTTPException(status_code=500, detail=f"Failed to save patient: {e}")
    

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import os
import httpx


@router.post("/api/patient-analytics")
async def patient_analytics(request: AnalyticsRequest):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent",
                headers={
                    "Content-Type": "application/json",
                    "X-goog-api-key": OPEN_AI_API_KEY  
                },
                json={
                    "contents": [
                        {
                            "parts": [
                                {"text": request.prompt}
                            ]
                        }
                    ]
                },
                timeout=30.0
            )
            print(response)

            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail=response.text)

            data = response.json()
            # Extract text from Gemini response
            ai_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
            return {"response": ai_text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

