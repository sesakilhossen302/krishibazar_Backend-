from sqlalchemy import Column, String, Boolean, Integer, DateTime
from datetime import datetime
from app.database import Base

class OTP(Base):
    __tablename__ = "otps"

    id = Column(String, primary_key=True, index=True)
    email = Column(String, index=True, nullable=False)
    phone = Column(String, nullable=True, default="")
    otp_code = Column(String, nullable=False)
    purpose = Column(String, nullable=False, default="signup")  # signup, login, reset_password, verify_email
    is_used = Column(Boolean, default=False)
    attempts = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)
