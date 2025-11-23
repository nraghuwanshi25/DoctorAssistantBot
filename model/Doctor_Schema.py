from pydantic import BaseModel

class BookingRequest(BaseModel):
    user_id: str
    doctor_name: str
    date: str
    time_range: str
    patient_name: str
    email: str
    phone: str

class BookingResponse(BaseModel):
    status: str
    type: str
    message: str
    doctor: dict
    appointment: dict
    patient: dict
