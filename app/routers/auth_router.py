import random
import uuid
from datetime import datetime, timedelta
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user_model import User
from app.models.otp_model import OTP
from app.schemas.user_schema import (
    UserSignup,
    UserLogin,
    TokenResponse,
    UserResponse,
    SendOtpRequest,
    VerifyOtpRequest,
    OtpLoginRequest,
    ForgotPasswordRequest,
    ResetPasswordRequest,
    ChangePasswordRequest,
    OtpResponse
)
from app.utils import hash_password, verify_password, create_access_token, get_current_user
from app.services.email_service import send_otp_via_gmail

router = APIRouter(prefix="/auth", tags=["Authentication & OTP"])


# ----------------- OTP Endpoints -----------------

@router.post("/send-otp", response_model=OtpResponse)
def send_otp(req: SendOtpRequest, db: Session = Depends(get_db)):
    """
    Generate and send a 6-digit OTP code to the user's Gmail address.
    The email is sent from the owner's Gmail SMTP configuration.
    """
    clean_email = req.email.strip().lower()
    if not clean_email or "@" not in clean_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="সঠিক ইমেইল বা জিমেইল ঠিকানা দিন।"
        )

    # 1. Generate 6-digit random code
    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    # 2. Invalidate previous active OTPs for same email & purpose
    db.query(OTP).filter(
        OTP.email == clean_email,
        OTP.purpose == req.purpose,
        OTP.is_used == False
    ).update({"is_used": True})

    # 3. Create new OTP record
    new_otp = OTP(
        id=f"otp_{uuid.uuid4().hex[:10]}",
        email=clean_email,
        phone=req.phone.strip() if req.phone else "",
        otp_code=otp_code,
        purpose=req.purpose,
        is_used=False,
        attempts=0,
        expires_at=expires_at,
        created_at=datetime.utcnow()
    )
    db.add(new_otp)
    db.commit()

    # 4. Dispatch Email via Gmail SMTP
    email_result = send_otp_via_gmail(
        to_email=clean_email,
        otp_code=otp_code,
        user_name=req.name or "সম্মানিত ব্যবহারকারী",
        purpose=req.purpose
    )

    print("=" * 70)
    print(f"[API HIT /auth/send-otp] Email: {clean_email}, Name: {req.name}")
    print(f"[GENERATED OTP CODE]: >>> {otp_code} <<<")
    print(f"[SMTP RESULT]: {email_result}")
    print("=" * 70)

    if email_result.get("success") == False:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="জিমেইলে ওটিপি পাঠানো সম্ভব হয়নি। দয়া করে সঠিক ও সক্রিয় জিমেইল ঠিকানা দিন।"
        )

    return OtpResponse(
        success=True,
        message=f"আপনার জিমেইল ({clean_email}) এ ৬ ডিজিটের ওটিপি কোড পাঠানো হয়েছে।",
        email=clean_email,
        purpose=req.purpose,
        expires_in_seconds=300,
        otp_code=otp_code
    )


@router.post("/verify-otp")
def verify_otp(req: VerifyOtpRequest, db: Session = Depends(get_db)):
    """
    Verify the 6-digit OTP received in Gmail.
    """
    clean_email = req.email.strip().lower()
    clean_code = req.otp_code.strip()

    otp_record = db.query(OTP).filter(
        OTP.email == clean_email,
        OTP.purpose == req.purpose,
        OTP.is_used == False
    ).order_by(OTP.created_at.desc()).first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="কোন সক্রিয় ওটিপি পাওয়া যায়নি। নতুন ওটিপি অনুরোধ করুন।"
        )

    if otp_record.expires_at < datetime.utcnow():
        otp_record.is_used = True
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ওটিপি কোডের মেয়াদ শেষ হয়ে গেছে। অনুগ্রহ করে পুনরায় ওটিপি পাঠান।"
        )

    if otp_record.otp_code != clean_code:
        otp_record.attempts += 1
        db.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ভুল ওটিপি কোড। সঠিক কোড দিয়ে আবার চেষ্টা করুন।"
        )

    # Mark as verified / used
    otp_record.is_used = True
    db.commit()

    return {
        "success": True,
        "message": "ওটিপি ভেরিফিকেশন সফল হয়েছে!",
        "email": clean_email
    }


# ----------------- Signup & Login Endpoints -----------------

@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(user_data: UserSignup, db: Session = Depends(get_db)):
    """
    Register a new Farmer (কৃষক) or Buyer (পাইকার/আড়তদার).
    Immediately generates JWT access token and logs the user in!
    """
    clean_phone = user_data.phone.strip()
    clean_email = user_data.email.strip().lower() if user_data.email else ""

    # 1. Check if phone number already registered
    existing_phone = db.query(User).filter(User.phone == clean_phone).first()
    if existing_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="এই ফোন নম্বরটি দিয়ে ইতিমধ্যে একটি অ্যাকাউন্ট তৈরি করা আছে।"
        )

    # 2. Check if email already registered
    if clean_email:
        existing_email = db.query(User).filter(User.email == clean_email).first()
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="এই জিমেইল/ইমেইল দিয়ে ইতিমধ্যে একটি অ্যাকাউন্ট রয়েছে।"
            )

    # 3. OTP Code Verification (If OTP code is provided in signup payload)
    if user_data.otp_code and user_data.otp_code.strip():
        clean_otp = user_data.otp_code.strip()
        otp_record = db.query(OTP).filter(
            OTP.email == clean_email,
            OTP.purpose == "signup",
            OTP.is_used == False
        ).order_by(OTP.created_at.desc()).first()

        if not otp_record:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ইনপুট দেওয়া ওটিপি (OTP) কোডটি পাওয়া যায়নি।"
            )

        if otp_record.otp_code != clean_otp:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ইনপুট দেওয়া ওটিপি (OTP) কোডটি ভুল। সঠিক ওটিপি দিন।"
            )

        if otp_record.expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="ওটিপি (OTP) কোডটির মেয়াদ শেষ হয়ে গেছে। নতুন ওটিপি পাঠান।"
            )

        # Mark OTP as used upon successful validation
        otp_record.is_used = True

    # 4. Buyer validations
    if user_data.role == "buyer" and not user_data.business_name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="পাইকার বা আড়তদার সাইনআপের জন্য ব্যবসা বা আড়তের নাম আবশ্যক।"
        )

    new_id = f"usr_{uuid.uuid4().hex[:8]}"

    db_user = User(
        id=new_id,
        role=user_data.role,
        name=user_data.name.strip(),
        phone=clean_phone,
        email=clean_email,
        hashed_password=hash_password(user_data.password),
        district=user_data.district,
        address=user_data.address,
        nid_or_doc=user_data.nid_or_doc or "",
        nid_front_url=user_data.nid_front_url or "",
        nid_back_url=user_data.nid_back_url or "",

        # Farmer specific
        farmer_type=user_data.farmer_type or "",
        upazila=user_data.upazila or "",
        union=user_data.union or "",
        krishi_card_doc_url=user_data.krishi_card_doc_url or "",

        # Buyer specific
        business_name=user_data.business_name or "",
        business_type=user_data.business_type or "",
        arot_location=user_data.arot_location or "",
        trade_info=user_data.trade_info or "",
        trade_license_url=user_data.trade_license_url or "",

        verification_status="verified",
        completed_orders=0,
        rating=5.0,
        reviews_count=0,
        payment_reliability=100
    )

    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Generate JWT Token for immediate login
    access_token = create_access_token(data={"sub": db_user.id, "role": db_user.role})

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=db_user.id,
        role=db_user.role,
        name=db_user.name,
        phone=db_user.phone,
        email=db_user.email or "",
        district=db_user.district or "",
        verification_status=db_user.verification_status or "verified"
    )


@router.post("/login", response_model=TokenResponse)
def login(user_data: UserLogin, db: Session = Depends(get_db)):
    """
    Standard Login with Phone or Email and Password.
    """
    identifier = (user_data.identifier or user_data.phone or "").strip()
    if not identifier:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ফোন নম্বর অথবা জিমেইল প্রদান করুন।"
        )

    # Find user by phone OR email
    user = db.query(User).filter(
        (User.phone == identifier) | (User.email == identifier.lower())
    ).first()

    if not user or not verify_password(user_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ভুল ফোন নম্বর/ইমেইল অথবা পাসওয়ার্ড।"
        )

    access_token = create_access_token(data={"sub": user.id, "role": user.role})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role,
        name=user.name,
        phone=user.phone,
        email=user.email or "",
        district=user.district or "",
        verification_status=user.verification_status or "verified"
    )


@router.post("/login-otp", response_model=TokenResponse)
def login_via_otp(req: OtpLoginRequest, db: Session = Depends(get_db)):
    """
    Passwordless OTP login via Gmail OTP.
    Farmers or Buyers can simply receive an OTP in their Gmail and log in!
    """
    clean_email = (req.email or "").strip().lower()
    clean_phone = (req.phone or "").strip()
    clean_code = req.otp_code.strip()

    if not clean_email and not clean_phone:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="জিমেইল অথবা ফোন নম্বর দিন।"
        )

    # Verify OTP
    otp_query = db.query(OTP).filter(
        OTP.purpose == "login",
        OTP.is_used == False
    )
    if clean_email:
        otp_query = otp_query.filter(OTP.email == clean_email)
    elif clean_phone:
        otp_query = otp_query.filter(OTP.phone == clean_phone)

    otp_record = otp_query.order_by(OTP.created_at.desc()).first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="অবৈধ বা মেয়াদোত্তীর্ণ ওটিপি কোড।"
        )

    if otp_record.expires_at < datetime.utcnow() or otp_record.otp_code != clean_code:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="অবৈধ বা মেয়াদোত্তীর্ণ ওটিপি কোড।"
        )

    # Find User
    user = None
    if clean_email:
        user = db.query(User).filter(User.email == clean_email).first()
    if not user and clean_phone:
        user = db.query(User).filter(User.phone == clean_phone).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="এই অ্যাকাউন্টের কোনো ইউজার পাওয়া যায়নি। দয়া করে আগে সাইনআপ করুন।"
        )

    otp_record.is_used = True
    db.commit()

    access_token = create_access_token(data={"sub": user.id, "role": user.role})
    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user_id=user.id,
        role=user.role,
        name=user.name,
        phone=user.phone,
        email=user.email or "",
        district=user.district or "",
        verification_status=user.verification_status or "verified"
    )


# ----------------- Password Reset & Change -----------------

@router.post("/forgot-password", response_model=OtpResponse)
def forgot_password(req: ForgotPasswordRequest, db: Session = Depends(get_db)):
    """
    Initiates password reset by sending a 6-digit OTP code to the user's Gmail.
    """
    clean_email = req.email.strip().lower()
    user = db.query(User).filter(User.email == clean_email).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="এই জিমেইল দিয়ে কোনো অ্যাকাউন্ট পাওয়া যায়নি।"
        )

    otp_code = str(random.randint(100000, 999999))
    expires_at = datetime.utcnow() + timedelta(minutes=5)

    db.query(OTP).filter(
        OTP.email == clean_email,
        OTP.purpose == "reset_password",
        OTP.is_used == False
    ).update({"is_used": True})

    new_otp = OTP(
        id=f"otp_{uuid.uuid4().hex[:10]}",
        email=clean_email,
        phone=user.phone,
        otp_code=otp_code,
        purpose="reset_password",
        is_used=False,
        expires_at=expires_at,
        created_at=datetime.utcnow()
    )
    db.add(new_otp)
    db.commit()

    send_otp_via_gmail(
        to_email=clean_email,
        otp_code=otp_code,
        user_name=user.name,
        purpose="reset_password"
    )

    return OtpResponse(
        success=True,
        message="পাসওয়ার্ড রিসেট ওটিপি আপনার জিমেইলে পাঠানো হয়েছে।",
        email=clean_email,
        purpose="reset_password",
        expires_in_seconds=300,
        otp_code=otp_code
    )


@router.post("/reset-password")
def reset_password(req: ResetPasswordRequest, db: Session = Depends(get_db)):
    """
    Verify reset OTP and set new password.
    """
    clean_email = req.email.strip().lower()
    otp_record = db.query(OTP).filter(
        OTP.email == clean_email,
        OTP.purpose == "reset_password",
        OTP.is_used == False
    ).order_by(OTP.created_at.desc()).first()

    if not otp_record:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="অবৈধ বা মেয়াদোত্তীর্ণ ওটিপি কোড।"
        )

    if otp_record.expires_at < datetime.utcnow() or otp_record.otp_code != req.otp_code.strip():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="অবৈধ বা মেয়াদোত্তীর্ণ ওটিপি কোড।"
        )

    user = db.query(User).filter(User.email == clean_email).first()
    if not user:
        raise HTTPException(status_code=404, detail="ব্যবহারকারী পাওয়া যায়নি।")

    user.hashed_password = hash_password(req.new_password)
    otp_record.is_used = True
    db.commit()

    return {
        "success": True,
        "message": "পাসওয়ার্ড সফলভাবে পরিবর্তন করা হয়েছে। নতুন পাসওয়ার্ড দিয়ে লগইন করুন।"
    }


@router.post("/change-password")
def change_password(
    req: ChangePasswordRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Change password for currently authenticated user.
    """
    if not verify_password(req.old_password, current_user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="বর্তমান পাসওয়ার্ডটি সঠিক নয়।"
        )

    current_user.hashed_password = hash_password(req.new_password)
    db.commit()

    return {
        "success": True,
        "message": "পাসওয়ার্ড সফলভাবে আপডেট করা হয়েছে।"
    }


# ----------------- User Profile / Session -----------------

@router.get("/me", response_model=UserResponse)
def get_me(current_user: User = Depends(get_current_user)):
    """
    Get profile data of the currently logged in user.
    """
    return current_user
