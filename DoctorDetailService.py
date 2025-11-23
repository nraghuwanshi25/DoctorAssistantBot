# DoctorDetailService.py
from sqlalchemy import and_, asc
from sqlalchemy.future import select
from sqlalchemy.ext.asyncio import AsyncSession
from datetime import time, datetime, date as dt_date
from typing import List, Any, Optional, Dict

from EntityClasses import (
    Doctor,
    Speciality,
    TimeSlots,
    Patient,
    DoctorAvailability
)


class DoctorDetailService:
    def __init__(self, db: AsyncSession):
        self.db = db
        print("[INIT] DoctorDetailService initialized with AsyncSession")

    # =========================================================
    # 1. Get all doctors
    # =========================================================
    async def get_doctors(self):
        print("[GET_DOCTORS] Querying all doctors")
        query = select(Doctor).join(Speciality)
        result = await self.db.execute(query)
        doctors = result.scalars().all()
        print(f"[GET_DOCTORS] Found {len(doctors)} doctors")

        return {
            "status": "success",
            "type": "doctor_list",
            "total": len(doctors),
            "doctors": [
                {
                    "doctorId": d.doctor_id,
                    "doctorName": d.name,
                    "email": d.email,
                    "address": d.address,
                    "speciality": {
                        "id": d.speciality.speciality_id,
                        "name": d.speciality.name
                    }
                }
                for d in doctors
            ]
        }

    # =========================================================
    # 2. Filter doctors by speciality
    # =========================================================
    async def filter_doctors(self, speciality_name: str):
        """
        Filter doctors by speciality. Uses a case-insensitive substring match first.
        If no results are found, fall back to a fuzzy match against known speciality
        names (handles cases like 'Orthopedist' vs 'Orthopedic / Chiropractic').
        """
        print(f"[FILTER_DOCTORS] Filtering doctors by speciality '{speciality_name}'")

        # 1) Primary: case-insensitive substring match
        query = (
            select(Doctor)
            .join(Speciality)
            .where(Speciality.name.ilike(f"%{speciality_name}%"))
        )
        result = await self.db.execute(query)
        doctors = result.scalars().all()
        print(f"[FILTER_DOCTORS] Found {len(doctors)} doctors matching speciality (direct ilike)")

        # 2) Fallback: fuzzy match against known specialities (use difflib)
        if not doctors:
            print("[FILTER_DOCTORS] No direct matches found; attempting fuzzy match against known specialities")
            try:
                import difflib

                # Load all known specialities
                sp_res = await self.db.execute(select(Speciality))
                all_specialities = sp_res.scalars().all()

                # Build list of names
                names = [s.name for s in all_specialities if s.name]
                # Use difflib to find best match
                matches = difflib.get_close_matches(speciality_name, names, n=1, cutoff=0.5)
                if matches:
                    best = matches[0]
                    print(f"[FILTER_DOCTORS] Fuzzy matched '{speciality_name}' -> '{best}'")
                    # Query doctors for the best matched speciality
                    query2 = (
                        select(Doctor)
                        .join(Speciality)
                        .where(Speciality.name == best)
                    )
                    res2 = await self.db.execute(query2)
                    doctors = res2.scalars().all()
                else:
                    print(f"[FILTER_DOCTORS] No fuzzy match found for '{speciality_name}'")
            except Exception as exc:
                print(f"[FILTER_DOCTORS] Fuzzy matching failed: {exc}")

        if not doctors:
            return {
                "status": "not_found",
                "message": f"No doctors found for speciality '{speciality_name}'.",
                "doctors": []
            }

        return {
            "status": "success",
            "type": "filtered_doctors",
            "speciality": speciality_name,
            "total": len(doctors),
            "doctors": [
                {
                    "doctorId": d.doctor_id,
                    "doctorName": d.name,
                    "email": d.email,
                    "address": d.address,
                    "speciality": d.speciality.name
                }
                for d in doctors
            ]
        }

    # =========================================================
    # 3. Get doctor availability with slots
    # =========================================================
    async def get_doctor_availability(self, doctor_name: str, date: Optional[str] = None, include_booked: bool = False):
        """
        Return slot timings for the given doctor.
        If `date` is provided (YYYY-MM-DD) return slots only for that date.
        If `date` is omitted or None, return all available slots across all dates for the doctor.
        """
        print(f"[GET_DOCTOR_AVAILABILITY] Loading availability for {doctor_name} on {date if date else 'ALL_DATES'}")

        target_date: Optional[dt_date] = None
        if date:
            try:
                # parse strict YYYY-MM-DD to a date object
                target_date = datetime.strptime(date, "%Y-%m-%d").date()
            except Exception:
                return {
                    "status": "error",
                    "message": "Invalid date format. Please use YYYY-MM-DD.",
                    "availability": []
                }

        doctor_result = await self.db.execute(select(Doctor).where(Doctor.name == doctor_name))
        doctor = doctor_result.scalar_one_or_none()
        if doctor is None:
            print("[GET_DOCTOR_AVAILABILITY] Doctor not found")
            return {
                "status": "not_found",
                "message": f"No doctor found with name '{doctor_name}'.",
                "availability": []
            }

        # If a specific date was requested, filter by it. Otherwise return all availabilities for the doctor.
        if target_date:
            avail_query = select(DoctorAvailability).where(
                and_(
                    DoctorAvailability.doctor_id == doctor.doctor_id,
                    DoctorAvailability.available_date == target_date,
                )
            )
        else:
            avail_query = (
                select(DoctorAvailability)
                .where(DoctorAvailability.doctor_id == doctor.doctor_id)
                .order_by(asc(DoctorAvailability.available_date))
            )

        avail_result = await self.db.execute(avail_query)
        availabilities = avail_result.scalars().all()
        if not availabilities:
            print("[GET_DOCTOR_AVAILABILITY] Doctor has no configured availability for the requested scope")
            return {
                "status": "not_found",
                "message": (
                    f"No availability configured for doctor '{doctor_name}' on {date}." if target_date
                    else f"No availability configured for doctor '{doctor_name}'."
                ),
                "doctor": {
                    "doctorId": doctor.doctor_id,
                    "doctorName": doctor.name,
                    "speciality": doctor.speciality.name
                },
                "availability": []
            }

        availability_payload = []
        for availability in availabilities:
            slots_payload = []
            for slot in availability.slots:
                if not include_booked and slot.is_booked:
                    continue
                slots_payload.append(
                    {
                        "slotId": slot.slot_id,
                        "start": slot.start_time.strftime("%H:%M:%S"),
                        "end": slot.end_time.strftime("%H:%M:%S"),
                        "isBooked": slot.is_booked,
                    }
                )

            if slots_payload:
                availability_payload.append(
                    {
                        "availabilityId": availability.availability_id,
                        "date": str(availability.available_date),
                        "slots": slots_payload,
                    }
                )

        status = "success" if availability_payload else "not_found"
        message = None
        if not availability_payload:
            if target_date:
                message = f"No {'available ' if not include_booked else ''}slots found for doctor '{doctor_name}' on {date}."
            else:
                message = f"No {'available ' if not include_booked else ''}slots found for doctor '{doctor_name}'."

        response: Dict[str, Any] = {
            "status": status,
            "type": "doctor_availability",
            "doctor": {
                "doctorId": doctor.doctor_id,
                "doctorName": doctor.name,
                "email": doctor.email,
                "address": doctor.address,
                "speciality": doctor.speciality.name,
            },
            "availability": availability_payload,
        }
        if message:
            response["message"] = message

        return response

    # =========================================================
    # 4. Book Appointment
    # =========================================================
    async def book_appointment(
            self,
            user_id: str,
            doctor_name: str,
            date: str,
            time_range: str,
            patient_name: str,
            email: str,
            phone: str
    ):
        print(f"[BOOK_APPOINTMENT] Booking for {doctor_name} on {date} at {time_range}")
        start_str, end_str = time_range.split("-")
        start_time = time.fromisoformat(start_str)
        end_time = time.fromisoformat(end_str)

        # 1) Find matching slot
        slot = await self.get_slot_id(
            doctor_name=doctor_name,
            date=date,
            start_time=start_time,
            end_time=end_time
        )

        if slot is None:
            print("[BOOK_APPOINTMENT] Slot not available")
            alternatives = await self.recommend_alternatives(
                doctor_name, date, start_time, end_time
            )
            print(f"[BOOK_APPOINTMENT] Alternatives found: {alternatives}")
            return {
                "status": "error",
                "message": "Slot not available or already booked",
                "alternatives": alternatives
            }

        print(f"[BOOK_APPOINTMENT] Found slot {slot.slot_id}, marking as booked")
        slot.is_booked = True

        # 2) Doctor reference
        doctor = slot.availability.doctor

        # 3) Insert patient booking
        patient_entry = Patient(
            user_id=user_id,
            name=patient_name,
            email=email,
            phone=phone,
            slot_id=slot.slot_id
        )
        self.db.add(patient_entry)

        # 4) Commit + refresh
        await self.db.commit()
        await self.db.refresh(patient_entry)
        await self.db.refresh(slot)
        print(f"[BOOK_APPOINTMENT] Booking completed for {patient_name}")

        # 5) Return structured JSON
        return {
            "status": "success",
            "type": "booking_confirmation",
            "message": f"Appointment booked successfully with {doctor.name}",
            "doctor": {
                "doctorId": doctor.doctor_id,
                "doctorName": doctor.name,
                "speciality": doctor.speciality.name
            },
            "appointment": {
                "date": date,
                "slotId": slot.slot_id,
                "time": {
                    "start": slot.start_time.strftime("%H:%M:%S"),
                    "end": slot.end_time.strftime("%H:%M:%S")
                }
            },
            "patient": {
                "name": patient_name,
                "email": email,
                "phone": phone
            }
        }

    # =========================================================
    # 5. Get Slot Under Availability
    # =========================================================
    async def get_slot_id(
            self,
            doctor_name: str,
            date: str,
            start_time: time,
            end_time: time
    ) -> Optional[TimeSlots]:
        print(f"[GET_SLOT] Searching slot for {doctor_name} on {date} from {start_time} to {end_time}")
        res_doc = await self.db.execute(select(Doctor).where(Doctor.name == doctor_name))
        doctor = res_doc.scalar_one_or_none()
        if doctor is None:
            print("[GET_SLOT] Doctor not found")
            return None

        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
        except Exception:
            print("[GET_SLOT] Invalid date format provided to get_slot_id")
            return None

        res_avail = await self.db.execute(
            select(DoctorAvailability).where(
                and_(
                    DoctorAvailability.doctor_id == doctor.doctor_id,
                    DoctorAvailability.available_date == parsed_date
                )
            )
        )
        availability = res_avail.scalar_one_or_none()
        if availability is None:
            print("[GET_SLOT] No availability for this date")
            return None

        res_slot = await self.db.execute(
            select(TimeSlots).where(
                and_(
                    TimeSlots.availability_id == availability.availability_id,
                    TimeSlots.start_time == start_time,
                    TimeSlots.end_time == end_time,
                    TimeSlots.is_booked == False
                )
            )
        )
        slot = res_slot.scalar_one_or_none()
        if slot:
            print(f"[GET_SLOT] Slot found: {slot.slot_id}")
        else:
            print("[GET_SLOT] Slot not found or already booked")
        return slot

    # =========================================================
    # 6. Recommend Alternatives
    # =========================================================
    async def recommend_alternatives(
            self,
            doctor_name: str,
            date: str,
            start_time: time,
            end_time: time
    ) -> List[Dict[str, Any]]:
        print(f"[RECOMMEND_ALTERNATIVES] Looking alternatives for {doctor_name} on {date}")
        requested_start = start_time

        res_doc = await self.db.execute(select(Doctor).where(Doctor.name == doctor_name))
        doctor = res_doc.scalar_one_or_none()
        if not doctor:
            print("[RECOMMEND_ALTERNATIVES] Doctor not found")
            return []

        speciality_id = doctor.speciality_id

        # Same doctor -> same date
        # parse requested date for accurate comparisons
        try:
            parsed_date = datetime.strptime(date, "%Y-%m-%d").date()
        except Exception:
            parsed_date = None

        if parsed_date:
            res_avail = await self.db.execute(
                select(DoctorAvailability).where(
                    and_(
                        DoctorAvailability.doctor_id == doctor.doctor_id,
                        DoctorAvailability.available_date == parsed_date
                    )
                )
            )
            same_doc_avail = res_avail.scalar_one_or_none()
        else:
            same_doc_avail = None

        if same_doc_avail:
            res_slots = await self.db.execute(
                select(TimeSlots).where(
                    and_(
                        TimeSlots.availability_id == same_doc_avail.availability_id,
                        TimeSlots.is_booked == False
                    )
                ).order_by(asc(TimeSlots.start_time))
            )
            slots = res_slots.scalars().all()
            if slots:
                slots = sorted(
                    slots,
                    key=lambda s: abs(
                        datetime.combine(datetime.today(), s.start_time)
                        - datetime.combine(datetime.today(), requested_start)
                    )
                )
                print(f"[RECOMMEND_ALTERNATIVES] Found {len(slots[:3])} slots for same doctor same date")
                return [
                    {
                        "doctor": doctor.name,
                        "speciality": doctor.speciality.name,
                        "date": date,
                        "slotId": s.slot_id,
                        "start": s.start_time.strftime("%H:%M:%S"),
                        "end": s.end_time.strftime("%H:%M:%S")
                    }
                    for s in slots[:3]
                ]

        print("[RECOMMEND_ALTERNATIVES] No slots for same doctor same date, checking same speciality")
        # Same speciality -> same date
        res_docs = await self.db.execute(select(Doctor).where(Doctor.speciality_id == speciality_id))
        specialty_doctor_ids = [d.doctor_id for d in res_docs.scalars().all()]

        if specialty_doctor_ids:
            if parsed_date:
                res_same_date_avail = await self.db.execute(
                    select(DoctorAvailability).where(
                        and_(
                            DoctorAvailability.available_date == parsed_date,
                            DoctorAvailability.doctor_id.in_(specialty_doctor_ids)
                        )
                    )
                )
                same_date_avails = res_same_date_avail.scalars().all()
            else:
                same_date_avails = []

            specialty_same_date_slots = []
            for a in same_date_avails:
                res_slots = await self.db.execute(
                    select(TimeSlots).where(
                        and_(
                            TimeSlots.availability_id == a.availability_id,
                            TimeSlots.is_booked == False
                        )
                    )
                )
                specialty_same_date_slots.extend(res_slots.scalars().all())

            if specialty_same_date_slots:
                specialty_same_date_slots = sorted(
                    specialty_same_date_slots,
                    key=lambda s: abs(
                        datetime.combine(datetime.today(), s.start_time)
                        - datetime.combine(datetime.today(), requested_start)
                    )
                )
                print(f"[RECOMMEND_ALTERNATIVES] Found {len(specialty_same_date_slots[:3])} slots for same speciality same date")
                return [
                    {
                        "doctor": s.availability.doctor.name,
                        "speciality": s.availability.doctor.speciality.name,
                        "date": str(s.availability.available_date),
                        "slotId": s.slot_id,
                        "start": s.start_time.strftime("%H:%M:%S"),
                        "end": s.end_time.strftime("%H:%M:%S")
                    }
                    for s in specialty_same_date_slots[:3]
                ]

        print("[RECOMMEND_ALTERNATIVES] No slots same date, checking future dates")
        # Same speciality -> next dates
        res_next_avail = await self.db.execute(
            select(DoctorAvailability)
            .where(DoctorAvailability.doctor_id.in_(specialty_doctor_ids))
            .order_by(asc(DoctorAvailability.available_date))
        )
        future_avails = res_next_avail.scalars().all()

        future_slots = []
        for a in future_avails:
            if parsed_date and a.available_date == parsed_date:
                continue
            res_slots = await self.db.execute(
                select(TimeSlots).where(
                    and_(
                        TimeSlots.availability_id == a.availability_id,
                        TimeSlots.is_booked == False
                    )
                )
            )
            future_slots.extend(res_slots.scalars().all())

        future_slots = sorted(
            future_slots,
            key=lambda s: (s.availability.available_date, s.start_time)
        )
        print(f"[RECOMMEND_ALTERNATIVES] Found {len(future_slots[:3])} slots for future dates")
        return [
            {
                "doctor": s.availability.doctor.name,
                "speciality": s.availability.doctor.speciality.name,
                "date": str(s.availability.available_date),
                "slotId": s.slot_id,
                "start": s.start_time.strftime("%H:%M:%S"),
                "end": s.end_time.strftime("%H:%M:%S")
            }
            for s in future_slots[:3]
        ]
