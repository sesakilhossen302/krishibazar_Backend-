from sqlalchemy import Column, String, Boolean, Float, Integer
from app.database import Base
import enum

class UserRole(str, enum.Enum):
    FARMER = "farmer"
    BUYER = "buyer"
    ADMIN = "admin"

class VerificationStatus(str, enum.Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REJECTED = "rejected"

class User(Base):
    __tablename__ = "users"

    id = Column(String, primary_key=True, index=True)
    phone = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, nullable=True, default="")
    hashed_password = Column(String, nullable=False)
    name = Column(String, nullable=False)
    role = Column(String, default=UserRole.FARMER)
    photo_url = Column(String, nullable=True, default="")
    
    # Common Address & NID Docs
    district = Column(String, nullable=False, default="")
    address = Column(String, nullable=False, default="")
    nid_or_doc = Column(String, nullable=True, default="")
    nid_front_url = Column(String, nullable=True, default="")
    nid_back_url = Column(String, nullable=True, default="")

    # Farmer Specific Fields
    farmer_type = Column(String, nullable=True, default="")
    upazila = Column(String, nullable=True, default="")
    union = Column(String, nullable=True, default="")
    krishi_card_doc_url = Column(String, nullable=True, default="")

    # Buyer Specific Fields (Shop, Arot, Trade License)
    business_name = Column(String, nullable=True, default="")
    business_type = Column(String, nullable=True, default="")
    arot_location = Column(String, nullable=True, default="")
    trade_info = Column(String, nullable=True, default="")
    trade_license_url = Column(String, nullable=True, default="")

    # Verification & Rating Stats
    verification_status = Column(String, default=VerificationStatus.VERIFIED)
    completed_orders = Column(Integer, default=0)
    rating = Column(Float, default=0.0)
    reviews_count = Column(Integer, default=0)
    payment_reliability = Column(Integer, default=98)
    is_active = Column(Boolean, default=True)
