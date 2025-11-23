from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from Database import get_async_session
from DoctorDetailService import DoctorDetailService
from model.Doctor_Schema import BookingRequest, BookingResponse

app = FastAPI(title="SuperClinic API")

# -------------------------
# GET all doctors
# -------------------------
@app.get("/doctors")
async def get_doctors():
    async with get_async_session() as session:  # unwrap the async generator
        service = DoctorDetailService(session)
        return await service.get_doctors()

# -------------------------
# GET doctors by specialty
# -------------------------
@app.get("/doctors/filter")
async def filter_doctors(speciality: str):
    async with get_async_session() as session:  # unwrap the async generator
        service = DoctorDetailService(session)
        return await service.filter_doctors(speciality)

# -------------------------
# POST book appointment
# -------------------------
@app.post("/appointments", response_model=BookingResponse)
async def book_appointment(data: BookingRequest):
    async with get_async_session() as session:  # unwrap the async generator
        service = DoctorDetailService(session)
        result = await service.book_appointment(
            user_id=data.user_id,
            doctor_name=data.doctor_name,
            date=data.date,
            time_range=data.time_range,
            patient_name=data.patient_name,
            email=data.email,
            phone=data.phone
        )
        if result["status"] != "success":
            raise HTTPException(status_code=400, detail=result)
        return result
