# EntityClasses.py
from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    Time,
    Date,
    ForeignKey
)
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()


class Speciality(Base):
    __tablename__ = "Speciality"

    speciality_id = Column(Integer, primary_key=True)
    name = Column(String(50), unique=True, nullable=False)
    description = Column(String(100))

    doctors = relationship("Doctor", back_populates="speciality", lazy="selectin")


class Doctor(Base):
    __tablename__ = "Doctor"

    doctor_id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    email = Column(String(100), unique=True, nullable=False)
    address = Column(String(200))
    speciality_id = Column(Integer, ForeignKey("Speciality.speciality_id"))

    speciality = relationship("Speciality", back_populates="doctors", lazy="selectin")
    availabilities = relationship("DoctorAvailability", back_populates="doctor", lazy="selectin")


class DoctorAvailability(Base):
    __tablename__ = "Doctor_Availability"

    availability_id = Column(Integer, primary_key=True)
    doctor_id = Column(Integer, ForeignKey("Doctor.doctor_id"))
    available_date = Column(Date, nullable=False)

    doctor = relationship("Doctor", back_populates="availabilities", lazy="selectin")
    slots = relationship("TimeSlots", back_populates="availability", lazy="selectin")


class TimeSlots(Base):
    __tablename__ = "Time_Slots"

    slot_id = Column(Integer, primary_key=True)
    availability_id = Column(Integer, ForeignKey("Doctor_Availability.availability_id"))
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    is_booked = Column(Boolean, default=False)

    availability = relationship("DoctorAvailability", back_populates="slots", lazy="selectin")
    patients = relationship("Patient", back_populates="slot", lazy="selectin")


class Patient(Base):
    __tablename__ = "Patient"

    booking_id = Column(Integer, primary_key=True)
    user_id = Column(String(50), nullable=False)
    slot_id = Column(Integer, ForeignKey("Time_Slots.slot_id"), nullable=False)

    name = Column(String(100), nullable=False)
    email = Column(String(100), nullable=False)
    phone = Column(String(20), nullable=False)

    slot = relationship("TimeSlots", back_populates="patients", lazy="selectin")
