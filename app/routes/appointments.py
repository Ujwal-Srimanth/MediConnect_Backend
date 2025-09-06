from fastapi import APIRouter, Body,Depends,HTTPException,status
from ..utils.slot_service import SlotService
from ..models.appointment import SlotBookingRequest
from ..utils.auth_utils import get_current_user
from app.database import get_database
from ..utils.email_service import send_email
from datetime import datetime
from bson import ObjectId


router = APIRouter()

db = get_database()
@router.get("/patients/{patient_id}")
async def get_upcoming_appointments(patient_id: str,current_user: dict = Depends(get_current_user)):
    try:
        appointments_collection = db.appointments
        doctors_collection = db.doctors
        now = datetime.utcnow()

        # Get upcoming appointments for patient
        appointments_cursor = await appointments_collection.find({
            "patient_id": ObjectId(patient_id),
            "start_datetime": {"$gte": now}
        }).to_list(length=None)

        print(appointments_cursor)

        appointments = []
        for appointment in appointments_cursor:
            # Get doctor info
            doctor = await doctors_collection.find_one({"_id": appointment["doctor_id"]})
            if not doctor:
                continue  

            appointments.append({
                "appointment_id": str(appointment["_id"]),
                "start_datetime": appointment["start_datetime"],
                "end_datetime": appointment["end_datetime"],
                "date":appointment["date"],
                "status": appointment["status"],
                "purpose": appointment["purpose"],
                "doctor": {
                    "doctor_id": str(doctor["_id"]),
                    "name": doctor["name"],
                    "specialization": doctor["specialization"],
                    "hospital": doctor["hospital"],
                }
            })

        return {"appointments": appointments}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    




@router.delete("/patients/cancel/{appointment_id}")
async def cancel_appointment(
    appointment_id: str,
    current_user: dict = Depends(get_current_user)
):
    try:
        db = get_database()
        users_collection = db.users

    # Fetch patient's email from DB using current_user["_id"]
        patient = await users_collection.find_one({"_id": ObjectId(current_user["_id"])}, {"email": 1})
        if not patient or "email" not in patient:
            raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient email not found",
            )
        print(patient)
        appointments_collection = db.appointments    
        # Ensure appointment_id is a valid ObjectId
        if not ObjectId.is_valid(appointment_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid appointment ID format"
            )
        
        appointment = await appointments_collection.find_one(
            {"_id": ObjectId(appointment_id)},
            {"doctor_id": 1, "start_datetime": 1, "end_datetime": 1, "purpose": 1}
        )

        # Try to delete appointment
        result = await appointments_collection.delete_one(
            {"_id": ObjectId(appointment_id)}
        )

        if result.deleted_count == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Appointment not found"
            )
        try:
            print(appointment,"Ujju")
            subject = "Appointment Cancellation Confirmation"
            body_text = (
            f"Hello ,\n\n"
            f"Your appointment with Doctor {appointment["doctor_id"]} has been Cancelled.\n"
            f"🗓 Date/Time: {appointment["start_datetime"]} - {appointment["end_datetime"]}\n"
            f"Purpose: {appointment["purpose"]}\n\n"
            "Please free feel to book another appointment if needed.\n\n"
            )

            body_html = f"""
                <html>
                <body style="font-family: Arial, sans-serif; line-height: 1.6;">
                    <p>Hello,</p>

                    <p>Your appointment with <b>Doctor {appointment["doctor_id"]}</b> has been <span style="color: red; font-weight: bold;">Cancelled</span>.</p>

                    <p>
                    🗓 <b>Date/Time:</b> {appointment["start_datetime"]} - {appointment["end_datetime"]}<br>
                    🎯 <b>Purpose:</b> {appointment["purpose"]}
                    </p>

                    <p>
                    Please feel free to book another appointment if needed.
                    </p>

                    <p style="margin-top:20px;">Thank you,<br><b>Mediconnect Team</b></p>
                </body>
                </html>
                """

            await send_email(patient["email"], subject, body_text,body_html)
        except Exception as e:
            import logging
            logging.error(f"Failed to send confirmation email: {e}")
        

        return {"message": "Appointment cancelled successfully"}

    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An error occurred while cancelling appointment: {str(e)}"
        )




@router.post("/{doctor_id}/book")
async def book_doctor_appointment(doctor_id: str, body: SlotBookingRequest,current_user: dict = Depends(get_current_user)):
    """
    Book a slot → saves it in DB as booked.
    """
    print(current_user)
    db = get_database()
    users_collection = db.users

    # Fetch patient's email from DB using current_user["_id"]
    patient = await users_collection.find_one({"_id": ObjectId(current_user["_id"])}, {"email": 1})
    if not patient or "email" not in patient:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Patient email not found",
        )
    print(patient)
    
    slot = await SlotService.book_slot(
        doctor_id=doctor_id,
        patient_id=body.patient_id,
        start_datetime=body.start_datetime,
        end_datetime=body.end_datetime,
        purpose=body.purpose,
    )
    if slot:  # success
        subject = "Appointment Confirmation"
        body_text = (
            f"Hello ,\n\n"
            f"Your appointment with Doctor {doctor_id} has been booked.\n"
            f"🗓 Date/Time: {slot['start_datetime']} - {slot['end_datetime']}\n"
            f"Purpose: {slot['purpose']}\n\n"
            "Thank you for choosing our service!"
        )

        body_html = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6;">
    <p>Hello,</p>

    <p>Your appointment with <b>Doctor {doctor_id}</b> has been 
    <span style="color: green; font-weight: bold;">Booked</span>.</p>

    <p>
      🗓 <b>Date/Time:</b> {slot['start_datetime']} - {slot['end_datetime']}<br>
      🎯 <b>Purpose:</b> {slot['purpose']}
    </p>

    <p>Thank you for choosing our service!</p>

    <p style="margin-top:20px;">Regards,<br><b>Mediconnect Team</b></p>
  </body>
</html>
"""


        try:
            await send_email(patient["email"], subject, body_text,body_html)
        except Exception as e:
            import logging
            logging.error(f"Failed to send confirmation email: {e}")

    return {"slot": slot}


@router.get("/{doctor_id}")
async def get_next_24h_appointments(doctor_id: str,current_user: dict = Depends(get_current_user)):
    """
    Get all appointments for the given doctor in the next 24 hours (IST).
    """
    return await SlotService.get_upcoming_appointments(doctor_id)





@router.get("/all/patients/{patient_id}")
async def get_all_appointments(patient_id: str, current_user: dict = Depends(get_current_user)):
    """
    Fetch all appointments (past, present, future) for a patient.
    """
    try:
        appointments_collection = db.appointments
        doctors_collection = db.doctors

        # ✅ Fetch ALL appointments for patient (no datetime filter)
        appointments_cursor = await appointments_collection.find({
            "patient_id": ObjectId(patient_id)
        }).to_list(length=None)

        appointments = []
        for appointment in appointments_cursor:
            # Get doctor info
            doctor = await doctors_collection.find_one({"_id": appointment["doctor_id"]})
            if not doctor:
                continue  

            appointments.append({
                "appointment_id": str(appointment["_id"]),
                "start_datetime": (
                    appointment["start_datetime"].isoformat()
                    if isinstance(appointment["start_datetime"], datetime)
                    else str(appointment["start_datetime"])
                ),
                "end_datetime": (
                    appointment["end_datetime"].isoformat()
                    if isinstance(appointment["end_datetime"], datetime)
                    else str(appointment["end_datetime"])
                ),
                "date": appointment.get("date"),
                "status": appointment.get("status"),
                "purpose": appointment.get("purpose"),
                "doctor": {
                    "doctor_id": str(doctor["_id"]),
                    "name": doctor.get("name"),
                    "specialization": doctor.get("specialization"),
                    "hospital": doctor.get("hospital"),
                }
            })

        # Sort by start_datetime (newest first)
        appointments.sort(key=lambda x: x["start_datetime"], reverse=True)

        return {"appointments": appointments}

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))



# Receptionist use-case
@router.post("/{appointment_id}/status")
async def update_appointment_status(appointment_id: str, action: str = Body(..., embed=True),current_user: dict = Depends(get_current_user)):
    """
    Approve or reject an appointment.
    - If action=approve → updates status
    - If action=reject → deletes the appointment
    """
    return await SlotService.update_appointment_status(appointment_id, action)
