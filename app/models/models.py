from pydantic import BaseModel, EmailStr
from typing import Optional, List

class EmergencyContact(BaseModel):
    contact_name: str
    relation: str
    phone: str

class InsuranceInfo(BaseModel):
    insurance_details: Optional[str] = None

class FileInfo(BaseModel):
    filename: str
    url: str

class PatientOut(BaseModel):
    id: str
    first_name: str
    last_name: str
    date_of_birth: str
    gender: str
    contact_number: str
    email_address: EmailStr
    address: str
    height_cm: Optional[float] = None
    weight_kg: Optional[float] = None
    any_disability: bool = False
    allergies: Optional[str] = None
    existing_conditions: Optional[str] = None
    current_medications: Optional[str] = None
    blood_group: Optional[str] = None
    emergency_contact: Optional[EmergencyContact] = None
    insurance: Optional[InsuranceInfo] = None
    medical_records: List[FileInfo] = []

class AnalyticsRequest(BaseModel):
    prompt: str
    
