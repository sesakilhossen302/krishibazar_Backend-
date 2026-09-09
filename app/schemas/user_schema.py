from pydantic import BaseModel, Field
from typing import Optional

# ----------------- OTP Schemas -----------------

class SendOtpRequest(BaseModel):
    email: str = Field(..., examples=["user@gmail.com"], description="User's Gmail address where OTP will be sent")
    purpose: str = Field(default="signup", examples=["signup"], description="signup, login, reset_password, verify_email")
    phone: Optional[str] = Field(default="", examples=["01712892102"])
    name: Optional[str] = Field(default="সম্মানিত ব্যবহারকারী", examples=["মো: আব্দুল রহিম"])

class VerifyOtpRequest(BaseModel):
    email: str = Field(..., examples=["user@gmail.com"])
    otp_code: str = Field(..., examples=["482910"], min_length=4, max_length=6)
    purpose: str = Field(default="signup", examples=["signup"])

class OtpLoginRequest(BaseModel):
    email: Optional[str] = Field(default="", examples=["user@gmail.com"])
    phone: Optional[str] = Field(default="", examples=["01712892102"])
    otp_code: str = Field(..., examples=["482910"])

class ForgotPasswordRequest(BaseModel):
    email: str = Field(..., examples=["user@gmail.com"])

class ResetPasswordRequest(BaseModel):
    email: str = Field(..., examples=["user@gmail.com"])
    otp_code: str = Field(..., examples=["482910"])
    new_password: str = Field(..., examples=["new_secret_123"], min_length=4)

class ChangePasswordRequest(BaseModel):
    old_password: str = Field(..., examples=["old_secret_123"])
    new_password: str = Field(..., examples=["new_secret_123"], min_length=4)

class OtpResponse(BaseModel):
    success: bool
    message: str
    email: str
    purpose: str
    expires_in_seconds: int = 300
    otp_code: Optional[str] = None  # Returned for convenience in dev/testing mode

# ----------------- Auth & Signup Schemas -----------------

class UserSignup(BaseModel):
    role: str = Field(..., examples=["farmer"], description="farmer or buyer")
    name: str = Field(..., examples=["মো: আব্দুল রহিম"])
    phone: str = Field(..., examples=["01712892102"])
    email: str = Field(..., examples=["rahim@gmail.com"], description="User Gmail address for OTP and alerts")
    password: str = Field(..., examples=["secret123"])
    otp_code: Optional[str] = Field(default="", examples=["123456"], description="Optional OTP code if pre-verified")
    
    # Address & NID Docs
    district: Optional[str] = Field(default="", examples=["ঢাকা"])
    address: Optional[str] = Field(default="", examples=["মহাখালী, ঢাকা"])
    nid_or_doc: Optional[str] = Field(default="", examples=["NID-7829102938"])
    nid_front_url: Optional[str] = Field(default="", examples=["https://example.com/nid_front.jpg"])
    nid_back_url: Optional[str] = Field(default="", examples=["https://example.com/nid_back.jpg"])

    # Farmer Specific Data
    farmer_type: Optional[str] = Field(default="", examples=["বাণিজ্যিক খামারি"])
    upazila: Optional[str] = Field(default="", examples=["গোদাগাড়ী"])
    union: Optional[str] = Field(default="", examples=["গোদাগাড়ী সদর"])
    krishi_card_doc_url: Optional[str] = Field(default="", examples=["https://example.com/krishi_doc.jpg"])

    # Buyer Specific Data (Shop, Arot, Trade License)
    business_name: Optional[str] = Field(default="", examples=["কাওরান বাজার পাইকারি আড়ত"])
    business_type: Optional[str] = Field(default="", examples=["পাইকারি আড়তদার ও সরবরাহকারী"])
    arot_location: Optional[str] = Field(default="", examples=["শেড নং ৪, কাওরান বাজার, ঢাকা"])
    trade_info: Optional[str] = Field(default="", examples=["TR-DH-892182"])
    trade_license_url: Optional[str] = Field(default="", examples=["https://example.com/trade_license.jpg"])


class UserLogin(BaseModel):
    identifier: Optional[str] = Field(default=None, examples=["01712892102"], description="Phone or Email")
    phone: Optional[str] = Field(default=None, examples=["01712892102"])
    password: str = Field(..., examples=["secret123"])


class UserUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    photo_url: Optional[str] = None
    district: Optional[str] = None
    address: Optional[str] = None
    nid_or_doc: Optional[str] = None
    nid_front_url: Optional[str] = None
    nid_back_url: Optional[str] = None
    
    # Farmer fields
    farmer_type: Optional[str] = None
    upazila: Optional[str] = None
    union: Optional[str] = None
    krishi_card_doc_url: Optional[str] = None

    # Buyer fields
    business_name: Optional[str] = None
    business_type: Optional[str] = None
    arot_location: Optional[str] = None
    trade_info: Optional[str] = None
    trade_license_url: Optional[str] = None

    # Verification and Notes
    verification_status: Optional[str] = None
    admin_note: Optional[str] = None
    nid_status: Optional[str] = None
    nid_rejection_note: Optional[str] = None


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str
    name: str
    phone: str
    email: str
    district: str
    verification_status: str
    admin_note: Optional[str] = ""
    nid_status: Optional[str] = "pending"
    nid_rejection_note: Optional[str] = ""


class UserResponse(BaseModel):
    id: str
    role: str
    name: str
    phone: str
    email: Optional[str] = ""
    photo_url: Optional[str] = ""
    district: str
    address: str
    nid_or_doc: Optional[str] = ""
    nid_front_url: Optional[str] = ""
    nid_back_url: Optional[str] = ""

    # Farmer fields
    farmer_type: Optional[str] = ""
    upazila: Optional[str] = ""
    union: Optional[str] = ""
    krishi_card_doc_url: Optional[str] = ""

    # Buyer fields
    business_name: Optional[str] = ""
    business_type: Optional[str] = ""
    arot_location: Optional[str] = ""
    trade_info: Optional[str] = ""
    trade_license_url: Optional[str] = ""

    # Verification & Stats
    verification_status: str
    admin_note: Optional[str] = ""
    nid_status: Optional[str] = "pending"
    nid_rejection_note: Optional[str] = ""
    completed_orders: int
    rating: float
    reviews_count: int
    payment_reliability: int

    class Config:
        from_attributes = True
