from fastapi import APIRouter, HTTPException, Depends , Body
from pydantic import BaseModel
from ..models.user_model import UserCreate, UserLogin
from app.database import users_collection
from app.database import otps_collection
from ..utils.auth_utils import hash_password, check_password, create_token, get_current_user
from bson import ObjectId
import random
import string
import smtplib
from email.mime.text import MIMEText
from datetime import datetime, timedelta
from app.database import get_database

router = APIRouter()


otp_store = {}

def generate_otp():
    return ''.join(random.choices(string.digits, k=6))

def send_email(to_email: str, subject: str, body: str):
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "ujwalsrimanth@gmail.com"
    sender_password = "togdfcrvnauvojru"  

    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = sender_email
    msg["To"] = to_email

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(sender_email, sender_password)
        server.sendmail(sender_email, to_email, msg.as_string())

class VerifyIDRequest(BaseModel):
    ID: str

@router.post("/verify-id")
async def verify_id(request: VerifyIDRequest):
    db = get_database()
    users_collection = db.users
    user = await users_collection.find_one({"ID": request.ID})
    if user:
        return {"exists": True}
    else:
        return {"exists": False}

@router.post("/signup")
async def signup(user: UserCreate):
    existing_user = await users_collection.find_one({"email": user.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    user_dict = user.dict()
    user_dict["password"] = hash_password(user.password)
    user_dict["ID"] = None if user.role == "Patient" else user.ID
    user_dict["is_profile_filled"] = False
    await users_collection.insert_one(user_dict)
    return {"message": "Signup successful"}

@router.post("/login")
async def login(user: UserLogin):
    existing_user = await users_collection.find_one({"email": user.email})
    print(users_collection)
    if not existing_user or not check_password(user.password, existing_user["password"]):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_token(str(existing_user["_id"]), existing_user["role"])
    return {"token": token,"email":existing_user["email"],"role":existing_user["role"],"is_profile_filled":existing_user["is_profile_filled"],"id":str(existing_user["_id"])}

@router.post("/profile-complete")
async def complete_profile(current_user: dict = Depends(get_current_user)):
    await users_collection.update_one(
        {"_id": ObjectId(current_user["_id"])},
        {"$set": {"is_profile_filled": True}}
    )
    return {"message": "Profile marked as complete"}

@router.get("/get-id/{email}")
async def get_user_id(email: str,current_user: dict = Depends(get_current_user)):
    user = await users_collection.find_one({"email": email})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {"email": user["email"], "ID": user.get("ID")}


@router.get("/verify-user-email")
async def verify_user_email(email: str):
    existing_user = await users_collection.find_one({"email": email})
    if not existing_user:
        return {"exists": False}

    otp = generate_otp()
    expiry = datetime.utcnow() + timedelta(minutes=5)
    await otps_collection.update_one(
        {"email": email},
        {"$set": {
            "otp": otp,
            "expiry": expiry,
            "verified": False,
            "created_at": datetime.utcnow()
        }},
        upsert=True
    )
    send_email(email, "Your OTP Code", f"Your OTP is {otp}. It expires in 5 minutes.")

    return {"exists": True, "message": "OTP sent to email"}

@router.post("/verify-otp")
async def verify_otp(payload: dict = Body(...)):
    email = payload.get("email")
    otp = payload.get("otp")
    record = await otps_collection.find_one({"email": email})
    if not record:
        return {"valid": False, "message": "No OTP found"}

    if datetime.utcnow() > record["expiry"]:
        return {"valid": False, "message": "OTP expired"}

    if otp != record["otp"]:
        return {"valid": False, "message": "Invalid OTP"}

    await otps_collection.update_one(
        {"email": email},
        {"$set": {"verified": True}}
    )
    return {"valid": True, "message": "OTP verified"}




@router.post("/forgot-password")
async def forgot_password(payload: dict = Body(...)):
    email = payload.get("email")
    new_password = payload.get("new_password")

    if not email or not new_password:
        raise HTTPException(status_code=400, detail="Email and new password are required")

    otp_record = await otps_collection.find_one({"email": email})
    if not otp_record or not otp_record.get("verified", False):
        raise HTTPException(status_code=400, detail="Email not verified. Please complete OTP verification first.")

    existing_user = await users_collection.find_one({"email": email})
    if not existing_user:
        raise HTTPException(status_code=404, detail="User not found")

    hashed_pw = hash_password(new_password)
    await users_collection.update_one(
        {"email": email},
        {"$set": {"password": hashed_pw}}
    )

    await otps_collection.update_one(
        {"email": email},
        {"$set": {"verified": False}}
    )

    return {"status":True,"message": "Password reset successful"}
