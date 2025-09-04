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
            await send_email(patient["email"], subject, body_text)
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

        try:
            await send_email(patient["email"], subject, body_text)
        except Exception as e:
            import logging
            logging.error(f"Failed to send confirmation email: {e}")

    return {"slot": slot}


@router.get("/{doctor_id}")
async def get_next_24h_appointments(doctor_id: str):
    """
    Get all appointments for the given doctor in the next 24 hours (IST).
    """
    return await SlotService.get_upcoming_appointments(doctor_id)


# Receptionist use-case
@router.post("/{appointment_id}/status")
async def update_appointment_status(appointment_id: str, action: str = Body(..., embed=True),current_user: dict = Depends(get_current_user)):
    """
    Approve or reject an appointment.
    - If action=approve → updates status
    - If action=reject → deletes the appointment
    """
    return await SlotService.update_appointment_status(appointment_id, action)
