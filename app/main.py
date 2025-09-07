from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.routes import patients
from app.routes import auth_routes
from app.routes import doctors
from app.routes import hospital
from app.routes import schedules
from app.routes import appointments
from app.routes import admin
from app.config import UPLOAD_DIR

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from fastapi import FastAPI
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
import pytz
from app.database import get_database
from app.utils.email_service import send_email
from datetime import datetime




app = FastAPI(title="Patient API")


async def send_daily_reminders():
    db = get_database()
    appointments = db.appointments
    doctors_collection = db.doctors
    users_collection = db.users

    print("🚀 send_daily_reminders triggered")

    today = datetime.now(pytz.timezone("Asia/Kolkata")).date()
    print(f"📅 Today's date: {today}")

    todays_appts = await appointments.find({
        "start_datetime": {
            "$gte": datetime.combine(today, datetime.min.time()),
            "$lt": datetime.combine(today, datetime.max.time())
        }
    }).to_list(length=None)

    print(f"📝 Found {len(todays_appts)} appointments for today")

    for appt in todays_appts:
        print(f"🔎 Appointment: {appt}")

        patient_id = appt.get("patient_id")
        doctor_id = appt.get("doctor_id")

        patient = await users_collection.find_one(
            {"_id": patient_id}, {"email": 1}
        )
        patient_email = patient.get("email") if patient else None

        print(f"📧 Patient ID: {patient_id}, Email: {patient_email}")
        doctor = await doctors_collection.find_one(
            {"_id": doctor_id}, {"name": 1, "hospital": 1}
        )
        doctor_name = doctor.get("name", "Doctor") if doctor else doctor_id
        doctor_hospital = doctor.get("hospital", "Unknown Hospital") if doctor else "Unknown Hospital"

        print(f"👨‍⚕️ Doctor info → Name: {doctor_name}, Hospital: {doctor_hospital}")

        if patient_email:
            subject = "Appointment Reminder"
            body_text = (
                f"Hello,\n\nThis is a reminder for your appointment.\n"
                f"👨‍⚕️ Doctor: {doctor_name} ({doctor_hospital})\n"
                f"🗓 Date/Time: {appt['start_datetime']} - {appt['end_datetime']}\n"
                f"Purpose: {appt['purpose']}\n\n"
                "Please be on time. Thank you!"
            )


            body_html = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333;">
                    <p>Hello,</p>
                    <p>This is a reminder for your appointment.</p>
                    <ul>
                    <li><b>👨‍⚕️ Doctor:</b> {doctor_name} ({doctor_hospital})</li>
                    <li><b>🗓 Date/Time:</b> {appt['start_datetime']} - {appt['end_datetime']}</li>
                    <li><b>Purpose:</b> {appt['purpose']}</li>
                    </ul>
                    <p>Please be on time. Thank you!</p>
                </body>
                </html>
            """

            try:
                await send_email(patient_email, subject, body_text,body_html)
                print(f"✅ Reminder email sent to {patient_email}")
            except Exception as e:
                print(f"❌ Failed to send reminder email to {patient_email}: {e}")
        else:
            print(f"⚠️ No email found for patient {patient_id}")

@app.on_event("startup")
async def startup_event():
    scheduler = AsyncIOScheduler()
    print(scheduler)
    scheduler.add_job(
        send_daily_reminders,
        CronTrigger(hour=7, minute=0, timezone="Asia/Kolkata")
    )
    print(scheduler.get_jobs())
    scheduler.start()

# ✅ Global validation error handler
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = []
    for err in exc.errors():
        loc = " -> ".join([str(l) for l in err["loc"]])
        msg = err["msg"]
        errors.append(f"{loc}: {msg}")

    return JSONResponse(
        status_code=422,
        content={"detail": errors},  # nice readable list
    )

origins = [
    "https://orange-hill-0603d7a00.1.azurestaticapps.net",  # frontend
    "http://localhost:3000",  # optional if you still want to test locally
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins, 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Serve uploaded files
app.mount("/files", StaticFiles(directory=UPLOAD_DIR), name="files")

# Register routers
app.include_router(patients.router, prefix="/patients", tags=["Patients"])
app.include_router(auth_routes.router, prefix="/api/auth")
app.include_router(doctors.router,prefix="/doctors",tags=["Doctors"])
app.include_router(hospital.router,prefix="/hospital",tags=["Hospital"])
app.include_router(schedules.router,prefix="/schedules",tags=["schedule"])
app.include_router(appointments.router,prefix="/appointments", tags=["Appointments"])
app.include_router(admin.router, prefix="/admin", tags=["Admin"])

