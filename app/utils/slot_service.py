from datetime import datetime, timezone, date, time, timedelta
from typing import List, Dict, Any, Optional

from bson import ObjectId
from fastapi import HTTPException, status

from app.database import get_database
from ..models.appointment import AppointmentStatus
from ..models.schedule import Schedule
from ..utils.email_service import send_email
from ..utils.utils import normalize_files


def serialize_doc(doc: dict) -> dict:
    """
    Convert only actual ObjectId fields in a Mongo document to strings.
    Since doctor_id is a string (like 'DOC001'), we leave it as-is.
    """
    if not doc:
        return doc
    # Convert only if _id is an ObjectId
    if "_id" in doc and isinstance(doc["_id"], ObjectId):
        doc["_id"] = str(doc["_id"])
    return doc



class SlotService:
    """
    A service class for handling appointment slot logic, including generation,
    retrieval, and booking, while respecting doctor-specific schedules.
    """

    @staticmethod
    async def _get_doctor_schedule(doctor_oid: str,date_obj: datetime) -> List[Dict[str, time]]:
        """
        Generate slots for a doctor based on their schedule stored in MongoDB.

        Args:
            doctor_oid: The ObjectId of the doctor.
            slot_duration: Duration of each slot in minutes (default: 15).

        Returns:
            A list of available slot dicts like:
            [
                {"start_time": "09:00", "end_time": "09:15"},
                {"start_time": "09:15", "end_time": "09:30"},
                ...
            ]
            or [] if today is doctor's day_off
        """
        schedules_collection = get_database().schedules

        if not str(doctor_oid).startswith("DOC"):
            raise HTTPException(status_code=400, detail="Invalid Doctor ID format. Must start with 'DOC'.")

        schedule_doc = await schedules_collection.find_one({"doctor_id": str(doctor_oid)})
        if not schedule_doc:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Schedule not found for doctor",
            )
        # Parse into Schedule model
        print(schedule_doc,"Ujjwal1")
        schedule = Schedule(**serialize_doc(schedule_doc))
        print(schedule,"Ujjwal")

        # Respect day_off → if today matches, return no slots
        weekday_name = date_obj.strftime("%A")
        if schedule.day_off == weekday_name:
            return []
        

        # Convert workday start/end into datetime objects
        work_start = datetime.strptime(schedule.start_time, "%H:%M")
        work_end = datetime.strptime(schedule.end_time, "%H:%M")

        # Convert breaks into datetime intervals
        break_intervals = []
        for br in schedule.breaks:
            br_start = datetime.strptime(br.start_time, "%H:%M")
            br_end = datetime.strptime(br.end_time, "%H:%M")
            break_intervals.append((br_start, br_end))

        print(break_intervals,"Ujjwal")

        slots = []
        current = work_start
        delta = timedelta(minutes=15)

        while current + delta <= work_end:
            slot_start = current
            slot_end = current + delta

            # Check if this slot overlaps with any break
            overlaps_break = any(
                br_start < slot_end and br_end > slot_start
                for br_start, br_end in break_intervals
            )

            if not overlaps_break:
                slots.append(
                    {
                        "start_time": slot_start.time(),  # return as datetime.time
                        "end_time": slot_end.time(),
                    }
                )

            current = slot_end
        

        return slots

    @classmethod
    def _generate_slots_from_schedule(
        cls,
        date_obj: date,
        schedule_blocks: List[Dict[str, time]],
        slot_minutes: int = 15,
    ) -> List[tuple[datetime, datetime]]:
        """
        Generate time slots for a given date based on specific working blocks (schedule).
        This correctly handles breaks.
        """
        slots = []
        for block in schedule_blocks:
            start_dt = datetime.combine(date_obj, block["start_time"])
            end_dt = datetime.combine(date_obj, block["end_time"])

            current_dt = start_dt
            while current_dt < end_dt:
                next_dt = current_dt + timedelta(minutes=slot_minutes)
                if next_dt > end_dt:
                    break
                slots.append((current_dt, next_dt))
                current_dt = next_dt
        return slots

    @staticmethod
    def _overlaps(
        start1: datetime, end1: datetime, start2: datetime, end2: datetime
    ) -> bool:
        """Check if two time intervals overlap."""
        # Note: The intervals overlap if one starts before the other ends.
        return start1 < end2 and start2 < end1

    @classmethod
    async def get_slots(cls, doctor_id: str, date_str: str) -> List[Dict[str, Any]]:
        """
        Generate available slots for a doctor on a specific date, considering their
        actual schedule and existing appointments.
        """
        db = get_database()
        appointments_collection = db.appointments

        try:
            date_obj = datetime.strptime(date_str, "%Y-%m-%d").date()
        except ValueError:
            raise ValueError("Incorrect date format, should be YYYY-MM-DD")
        
       
        schedule_blocks = await cls._get_doctor_schedule(doctor_id,date_obj)

        generated_slots = cls._generate_slots_from_schedule(date_obj, schedule_blocks)

        now = datetime.now()
        if date_obj == now.date():
            generated_slots = [(start, end) for start, end in generated_slots if start > now]
        if not generated_slots:
            return []  

        day_start = datetime.combine(date_obj, time.min)
        day_end = datetime.combine(date_obj, time.max)

        query = {
            "doctor_id": doctor_id,  # doctor_id stored as str in DB
            "start_datetime": {"$lt": day_end},
            "end_datetime": {"$gt": day_start},
        }
        existing_appointments = await appointments_collection.find(query).to_list(length=None)


        # 4. Build list of booked intervals
        booked_intervals = [
            (appt["start_datetime"], appt["end_datetime"])
            for appt in existing_appointments
        ]

        # 5. Mark slots as booked or available
        response_slots = []
        print(generated_slots,"Ujjwal")
        for start, end in generated_slots:
            is_booked = any(
                cls._overlaps(start, end, b_start, b_end)
                for b_start, b_end in booked_intervals
            )
            response_slots.append(
                {
                    "doctor_id": doctor_id,
                    "date": date_str,
                    "start_datetime": start.isoformat(),
                    "end_datetime": end.isoformat(),
                    "status": "booked" if is_booked else "available",
                }
            )

        return response_slots

    @classmethod
    async def book_slot(
    cls,
    doctor_id: str,
    patient_id: str,
    start_datetime: datetime,
    end_datetime: datetime,
    purpose: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Books a slot for a patient with a doctor after verifying:
        1. doctor_id and patient_id are valid ObjectIds
        2. doctor and patient exist in DB
        3. slot does not overlap with existing appointments
        4. slot does not fall in doctor's breaks or outside working hours
        """
        db = get_database()
        appointments_collection = db.appointments
        doctors_collection = db.doctors
        patients_collection = db.users
        schedules_collection = db.schedules  # add this

        # 1. Validate ObjectId format
        if not str(doctor_id).startswith("DOC"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid doctor_id format",
            )
        if not ObjectId.is_valid(patient_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid patient_id format",
            )

        patient_oid = ObjectId(patient_id)

        # 2. Check if doctor and patient exist
        if not await doctors_collection.find_one({"_id": doctor_id}):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found",
            )

        if not await patients_collection.find_one({"_id": patient_oid, "role": "Patient"}):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient not found",
            )

        # 3A. Check doctor schedule
        schedule = await schedules_collection.find_one({"doctor_id": doctor_id})
        if not schedule:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor schedule not found",
            )

        # Convert working hours to datetime on the same day as start_datetime
        work_start = datetime.combine(start_datetime.date(), datetime.strptime(schedule["start_time"], "%H:%M").time())
        work_end = datetime.combine(start_datetime.date(), datetime.strptime(schedule["end_time"], "%H:%M").time())

        if start_datetime < work_start or end_datetime > work_end:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Requested time is outside doctor's working hours",
            )

        # 3B. Check against breaks
        def is_overlap(s1, e1, s2, e2):
            return max(s1, s2) < min(e1, e2)

        for br in schedule.get("breaks", []):
            br_start = datetime.combine(start_datetime.date(), datetime.strptime(br["start_time"], "%H:%M").time())
            br_end = datetime.combine(start_datetime.date(), datetime.strptime(br["end_time"], "%H:%M").time())

            if is_overlap(start_datetime, end_datetime, br_start, br_end):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Doctor not available during {br['reason']} break",
                )

        # 4. Check for overlapping appointments
        overlapping_query = {
            "doctor_id": doctor_id,
            "start_datetime": {"$lt": end_datetime},
            "end_datetime": {"$gt": start_datetime},
        }
        if await appointments_collection.find_one(overlapping_query):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="The requested time slot overlaps with an existing appointment.",
            )

        # 5. Insert appointment
        slot_doc = {
            "doctor_id": doctor_id,
            "patient_id": patient_oid,
            "date": start_datetime.strftime("%Y-%m-%d"),
            "day": start_datetime.strftime("%A"),
            "start_datetime": start_datetime,
            "end_datetime": end_datetime,
            "is_booked": True,
            "purpose": purpose,
            "status": AppointmentStatus.PENDING.value,
        }

        result = await appointments_collection.insert_one(slot_doc)

        # Prepare JSON response
        slot_doc["_id"] = str(result.inserted_id)
        slot_doc["doctor_id"] = str(slot_doc["doctor_id"])
        slot_doc["patient_id"] = str(slot_doc["patient_id"])
        slot_doc["start_datetime"] = slot_doc["start_datetime"].isoformat()
        slot_doc["end_datetime"] = slot_doc["end_datetime"].isoformat()

        return slot_doc


    @classmethod
    async def get_upcoming_appointments(cls, doctor_id: str) -> List[Dict[str, Any]]:
        """
        Fetch all booked appointments for a doctor starting from the current time
        up to 24 hours in the future (IST).
        """
        db = get_database()
        appointments_collection = db.appointments
        doctors_collection = db.doctors
        users_collection = db.users

        # ✅ Validate doctor_id before casting
        if not str(doctor_id).startswith("DOC"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid doctor_id: {doctor_id}",
            )

        doctor_oid = doctor_id

        if not await doctors_collection.find_one({"_id": doctor_oid}):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found",
            )

        # Current IST time and +24h
        now_ist = datetime.now(timezone.utc) + timedelta(hours=5, minutes=30)
        in_24_hours = now_ist + timedelta(hours=24)

        # Query MongoDB directly
        cursor = await appointments_collection.find(
            {
                "doctor_id": doctor_oid,
                "is_booked": True,
                "start_datetime": {"$gte": now_ist, "$lt": in_24_hours},
            },
            {
                "_id": 1,
                "doctor_id": 1,
                "patient_id": 1,
                "date": 1,
                "day": 1,
                "start_datetime": 1,
                "end_datetime": 1,
                "status": 1,
                "purpose": 1,
            },
        ).to_list(length=None)
        cursor.sort(key=lambda x: x.get("start_datetime", 0))

        # Convert ObjectId → str, datetime → isoformat
        appointments = []
        for doc in cursor:
            patient = await users_collection.find_one(
                {"_id": doc["patient_id"]}, {"email": 1}
            )
            patient_email = patient["email"] if patient else None
            appointments.append(
                {
                    "appointment_id": str(doc["_id"]),
                    "doctor_id": str(doc["doctor_id"]),
                    "patient_id": str(doc["patient_id"]),
                    "patient_email": patient_email,
                    "date": doc["date"],
                    "day": doc["day"],
                    "start_datetime": (
                        doc["start_datetime"].isoformat()
                        if isinstance(doc["start_datetime"], datetime)
                        else str(doc["start_datetime"])
                    ),
                    "end_datetime": (
                        doc["end_datetime"].isoformat()
                        if isinstance(doc["end_datetime"], datetime)
                        else str(doc["end_datetime"])
                    ),
                    "status": doc.get("status"),
                    "purpose": doc.get("purpose"),
                }
            )

        return appointments
    
    @classmethod
    async def get_all_appointments(cls, doctor_id: str) -> List[Dict[str, Any]]:
        """
        Fetch **all booked appointments** for a doctor (past + present + future).
        """
        db = get_database()
        appointments_collection = db.appointments
        doctors_collection = db.doctors
        users_collection = db.users

        # ✅ Validate doctor_id before casting
        if not str(doctor_id).startswith("DOC"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid doctor_id: {doctor_id}",
            )

        doctor_oid = doctor_id

        # Check doctor exists
        if not await doctors_collection.find_one({"_id": doctor_oid}):
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Doctor not found",
            )

        # ✅ Fetch ALL booked appointments (no 24h filter)
        cursor = await appointments_collection.find(
            {
                "doctor_id": doctor_oid,
                "is_booked": True,
            },
            {
                "_id": 1,
                "doctor_id": 1,
                "patient_id": 1,
                "date": 1,
                "day": 1,
                "start_datetime": 1,
                "end_datetime": 1,
                "status": 1,
                "purpose": 1,
                "medical_records": 1,
            },
        ).to_list(length=None)

        # Sort by start_datetime (oldest → newest)
        cursor.sort(key=lambda x: x.get("start_datetime", datetime.min))

        # Convert ObjectId → str, datetime → isoformat
        appointments = []
        for doc in cursor:
            patient = await users_collection.find_one(
                {"_id": doc["patient_id"]}, {"email": 1}
            )
            patient_email = patient["email"] if patient else None
            appointments.append(
                {
                    "appointment_id": str(doc["_id"]),
                    "doctor_id": str(doc["doctor_id"]),
                    "patient_id": str(doc["patient_id"]),
                    "patient_email": patient_email,
                    "date": doc["date"],
                    "day": doc["day"],
                    "start_datetime": (
                        doc["start_datetime"].isoformat()
                        if isinstance(doc["start_datetime"], datetime)
                        else str(doc["start_datetime"])
                    ),
                    "end_datetime": (
                        doc["end_datetime"].isoformat()
                        if isinstance(doc["end_datetime"], datetime)
                        else str(doc["end_datetime"])
                    ),
                    "status": doc.get("status"),
                    "purpose": doc.get("purpose"),
                    "medical_records": doc.get("medical_records", []), 
                }
            )

        return appointments


    @classmethod
    async def update_appointment_status(
        cls, appointment_id: str, action: str
    ) -> Dict[str, Any]:
        """
        Approve or reject an appointment.
        - If action == 'approve', set status = 'approved'
        - If action == 'reject', set status = 'rejected'
        """
        db = get_database()
        appointments_collection = db.appointments
        users_collection = db.users

        if not ObjectId.is_valid(appointment_id):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid appointment_id: {appointment_id}",
            )

        appointment_oid = ObjectId(appointment_id)

        # Fetch appointment details
        appointment = await appointments_collection.find_one({"_id": appointment_oid})
        if not appointment:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Appointment not found"
            )

        # Fetch patient email
        patient = await users_collection.find_one(
            {"_id": ObjectId(appointment["patient_id"])}, {"email": 1}
        )
        if not patient or "email" not in patient:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Patient email not found",
            )

        # Extract details for mail
        doctor_id = appointment.get("doctor_id")
        start_time = appointment.get("start_datetime")
        end_time = appointment.get("end_datetime")
        purpose = appointment.get("purpose")

        # Action handling
        if action == "approve":
            await appointments_collection.update_one(
                {"_id": appointment_oid}, {"$set": {"status": "approved"}}
            )

            # Send approval email
            try:
                subject = "Appointment Approved ✅"
                body_text = (
                    f"Hello,\n\n"
                    f"Your appointment with Doctor {doctor_id} has been APPROVED.\n"
                    f"🗓 Date/Time: {start_time} - {end_time}\n"
                    f"Purpose: {purpose}\n\n"
                    "We look forward to seeing you!"
                    "Please be present in the hospital 10 minutes before your scheduled time.\n\n"
                )

                body_html = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6;">
    <p>Hello,</p>

    <p>Your appointment with <b>Doctor {doctor_id}</b> has been 
    <span style="color: green; font-weight: bold;">APPROVED ✅</span>.</p>

    <p>
      🗓 <b>Date/Time:</b> {start_time} - {end_time}<br>
      🎯 <b>Purpose:</b> {purpose}
    </p>

    <p>We look forward to seeing you!</p>

    <p><b>Please be present in the hospital 10 minutes before your scheduled time.</b></p>

    <p style="margin-top:20px;">Regards,<br><b>Mediconnect Team</b></p>
  </body>
</html>
"""

                await send_email(patient["email"], subject, body_text,body_html)
            except Exception as e:
                import logging
                logging.error(f"Failed to send approval email: {e}")

            return {"appointment_id": appointment_id, "status": "approved"}

        elif action == "reject":
            await appointments_collection.update_one(
                {"_id": appointment_oid}, {"$set": {"status": "rejected"}}
            )

            # Send rejection email
            try:
                subject = "Appointment Rejected ❌"
                body_text = (
                    f"Hello,\n\n"
                    f"Unfortunately, your appointment with Doctor {doctor_id} Due to unexpected emergencies "
                    f"on {start_time} - {end_time} has been REJECTED.\n"
                    f"Purpose: {purpose}\n\n"
                    "Please try booking another slot."
                )

                body_html = f"""
<html>
  <body style="font-family: Arial, sans-serif; line-height: 1.6;">
    <p>Hello,</p>

    <p>Unfortunately, your appointment with <b>Doctor {doctor_id}</b> on 
    <b>{start_time} - {end_time}</b> has been 
    <span style="color: red; font-weight: bold;">REJECTED ❌</span> due to unexpected emergencies.</p>

    <p>
      🎯 <b>Purpose:</b> {purpose}
    </p>

    <p>Please try booking another slot at your convenience.</p>

    <p style="margin-top:20px;">Regards,<br><b>Mediconnect Team</b></p>
  </body>
</html>
"""

                await send_email(patient["email"], subject, body_text,body_html)
            except Exception as e:
                import logging
                logging.error(f"Failed to send rejection email: {e}")

            return {"appointment_id": appointment_id, "status": "rejected"}

        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid action. Must be 'approve' or 'reject'.",
            )
