from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.orm import Session
from jose import jwt, JWTError
from app.config import settings
from app.database import get_db
from app.models.user_model import User
from app.models.product_model import Product
from app.models.demand_model import Demand, Offer
from app.models.order_model import Order
from app.schemas.user_schema import UserResponse, UserUpdate
from app.utils import get_current_user
from app.routers.notification_router import send_in_app_notification

router = APIRouter(prefix="/users", tags=["User Profile & Dashboard (প্রোফাইল ও ড্যাশবোর্ড)"])


def compute_user_stats(user: User, db: Session) -> dict:
    role = (user.role or "farmer").strip().lower()
    if role == "farmer":
        products_count = db.query(Product).filter(Product.farmer_id == user.id).count()
        active_products_count = db.query(Product).filter(
            Product.farmer_id == user.id,
            Product.status == "active"
        ).count()
        offers_count = db.query(Offer).filter(Offer.farmer_id == user.id).count()
        farmer_orders = db.query(Order).filter(Order.farmer_id == user.id).all()
        active_orders = sum(1 for o in farmer_orders if o.order_status not in ["completed", "cancelled"])
        completed_orders = sum(1 for o in farmer_orders if o.order_status == "completed")
        order_earnings = sum(o.total_amount for o in farmer_orders if (o.is_deposit_paid or o.order_status == "completed"))
        total_earnings = max(order_earnings, getattr(user, "total_earnings", 0.0) or 0.0)

        rating = float(user.rating or 0.0)
        reviews_count = int(user.reviews_count or 0)

        return {
            "products_count": products_count,
            "active_products_count": active_products_count,
            "offers_count": offers_count,
            "active_orders_count": active_orders,
            "completed_orders": max(completed_orders, user.completed_orders or 0),
            "total_earnings": float(total_earnings),
            "total_spent": 0.0,
            "rating": float(rating),
            "reviews_count": int(reviews_count),
        }
    else:  # buyer
        demands_count = db.query(Demand).filter(Demand.buyer_id == user.id).count()
        active_demands = db.query(Demand).filter(
            Demand.buyer_id == user.id,
            Demand.status == "active"
        ).count()
        buyer_demand_ids = [d[0] for d in db.query(Demand.id).filter(Demand.buyer_id == user.id).all()]
        offers_count = db.query(Offer).filter(Offer.demand_id.in_(buyer_demand_ids)).count() if buyer_demand_ids else 0
        buyer_orders = db.query(Order).filter(Order.buyer_id == user.id).all()
        active_orders = sum(1 for o in buyer_orders if o.order_status not in ["completed", "cancelled"])
        completed_orders = sum(1 for o in buyer_orders if o.order_status == "completed")
        order_spent = sum(o.total_amount for o in buyer_orders if (o.is_deposit_paid or o.order_status == "completed"))
        total_spent = max(order_spent, getattr(user, "total_earnings", 0.0) or 0.0)

        rating = float(user.rating or 0.0)
        reviews_count = int(user.reviews_count or 0)


        return {
            "products_count": demands_count,
            "active_products_count": active_demands,
            "offers_count": offers_count,
            "active_orders_count": active_orders,
            "completed_orders": max(completed_orders, user.completed_orders or 0),
            "total_earnings": 0.0,
            "total_spent": float(total_spent),
            "rating": float(rating),
            "reviews_count": int(reviews_count),
        }


def serialize_user_with_stats(user: User, db: Session) -> UserResponse:
    stats = compute_user_stats(user, db)
    return UserResponse(
        id=user.id,
        role=user.role,
        name=user.name,
        phone=user.phone,
        email=user.email or "",
        photo_url=user.photo_url or "",
        district=user.district or "",
        address=user.address or "",
        nid_or_doc=user.nid_or_doc or "",
        nid_front_url=user.nid_front_url or "",
        nid_back_url=user.nid_back_url or "",
        farmer_type=user.farmer_type or "",
        upazila=user.upazila or "",
        union=user.union or "",
        krishi_card_doc_url=user.krishi_card_doc_url or "",
        business_name=user.business_name or "",
        business_type=user.business_type or "",
        arot_location=user.arot_location or "",
        trade_info=user.trade_info or "",
        trade_license_url=user.trade_license_url or "",
        verification_status=user.verification_status or "pending",
        admin_note=user.admin_note or "",
        nid_status=user.nid_status or "pending",
        nid_rejection_note=user.nid_rejection_note or "",
        completed_orders=stats["completed_orders"],
        rating=stats["rating"],
        reviews_count=stats["reviews_count"],
        payment_reliability=user.payment_reliability or 98,
        products_count=stats["products_count"],
        active_products_count=stats["active_products_count"],
        offers_count=stats["offers_count"],
        active_orders_count=stats["active_orders_count"],
        total_earnings=stats["total_earnings"],
        total_spent=stats["total_spent"],
    )


@router.get("/", response_model=List[UserResponse])
def get_all_users(
    role: Optional[str] = None,
    verification_status: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    Get all registered users with all their details and live activity stats
    (products, offers, earnings, rating, reviews) for Admin Dashboard.
    """
    query = db.query(User)

    if role and role.strip():
        query = query.filter(User.role == role.strip().lower())

    if verification_status and verification_status.strip():
        query = query.filter(User.verification_status == verification_status.strip().lower())

    if search and search.strip():
        term = f"%{search.strip()}%"
        query = query.filter(
            (User.name.ilike(term)) |
            (User.phone.ilike(term)) |
            (User.email.ilike(term)) |
            (User.district.ilike(term)) |
            (User.business_name.ilike(term))
        )

    users = query.order_by(User.id.desc()).all()
    return [serialize_user_with_stats(u, db) for u in users]



@router.patch("/{user_id}/status", response_model=UserResponse)
def update_user_verification_status(
    user_id: str,
    status_update: dict,
    db: Session = Depends(get_db)
):
    """
    Update verification status of a user (verified, rejected, pending, in_progress, suspended)
    and NID status (verified, rejected, pending) from Admin Dashboard.
    Generates notifications for the user automatically.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ব্যবহারকারী পাওয়া যায়নি।"
        )
    
    old_v_status = (user.verification_status or "pending").strip().lower()
    old_admin_note = (user.admin_note or "").strip()
    old_nid_status = (user.nid_status or "pending").strip().lower()
    old_nid_note = (user.nid_rejection_note or "").strip()

    status_changed = False
    new_status = status_update.get("verification_status") or status_update.get("status")
    if new_status:
        st = new_status.strip().lower()
        if st in ["inprogress", "in_progress"]:
            st = "in_progress"
        if st != old_v_status:
            user.verification_status = st
            status_changed = True
        
    admin_note_changed = False
    if "admin_note" in status_update:
        new_note = (status_update.get("admin_note") or "").strip()
        if new_note != old_admin_note:
            user.admin_note = new_note
            admin_note_changed = True
        
    nid_status_changed = False
    if "nid_status" in status_update:
        new_nid_st = (status_update.get("nid_status") or "").strip().lower()
        if new_nid_st != old_nid_status:
            user.nid_status = new_nid_st
            nid_status_changed = True
        
    nid_note_changed = False
    if "nid_rejection_note" in status_update:
        new_nid_note = (status_update.get("nid_rejection_note") or "").strip()
        if new_nid_note != old_nid_note:
            user.nid_rejection_note = new_nid_note
            nid_note_changed = True

    db.add(user)
    db.commit()
    db.refresh(user)

    # 1. Trigger in-app notification on verification status change
    cur_v_status = (user.verification_status or "pending").strip().lower()
    if status_changed or (admin_note_changed and cur_v_status in ["rejected", "suspended", "in_progress"]):
        if cur_v_status == "verified":
            send_in_app_notification(
                db=db,
                user_id=user.id,
                title="অভিনন্দন! আপনার অ্যাকাউন্ট ভেরিফাইড হয়েছে ✅",
                message="আপনার অ্যাকাউন্ট সফলভাবে যাচাই করা হয়েছে। এখন আপনি প্ল্যাটফর্মের সব ফিচার ও সরাসরি কেনাবেচা সম্পন্ন করতে পারবেন।",
                notification_type="verification",
                related_id=user.id
            )
        elif cur_v_status == "rejected":
            note_txt = f" কারণ: {user.admin_note}" if user.admin_note else " অনুগ্রহ করে সঠিক তথ্য প্রদান করে পুনরায় আবেদন করুন।"
            send_in_app_notification(
                db=db,
                user_id=user.id,
                title="অ্যাকাউন্ট আবেদন বাতিল করা হয়েছে ❌",
                message=f"আপনার অ্যাকাউন্ট ভেরিফিকেশন আবেদন বাতিল করা হয়েছে।{note_txt}",
                notification_type="verification",
                related_id=user.id
            )
        elif cur_v_status == "suspended":
            note_txt = f" কারণ: {user.admin_note}" if user.admin_note else " বিস্তারিত জানতে সাপোর্ট টিমের সাথে যোগাযোগ করুন।"
            send_in_app_notification(
                db=db,
                user_id=user.id,
                title="অ্যাকাউন্ট সাময়িক স্থগিত 🚫",
                message=f"আপনার অ্যাকাউন্ট সাময়িক স্থগিত করা হয়েছে।{note_txt}",
                notification_type="verification",
                related_id=user.id
            )
        elif cur_v_status == "in_progress":
            note_txt = f" নোট: {user.admin_note}" if user.admin_note else " পর্যালোচনার পর অতি দ্রুত ফলাফল জানানো হবে।"
            send_in_app_notification(
                db=db,
                user_id=user.id,
                title="কাগজপত্র যাচাই চলছে 🔄",
                message=f"আপনার অ্যাকাউন্ট ভেরিফিকেশনের তথ্য ও কাগজপত্র পর্যালোচনা করা হচ্ছে।{note_txt}",
                notification_type="verification",
                related_id=user.id
            )

    # 2. Trigger in-app notification on NID status change
    cur_nid_status = (user.nid_status or "pending").strip().lower()
    if nid_status_changed or (nid_note_changed and cur_nid_status == "rejected"):
        if cur_nid_status == "rejected":
            note_txt = f" কারণ: {user.nid_rejection_note}।" if user.nid_rejection_note else ""
            send_in_app_notification(
                db=db,
                user_id=user.id,
                title="জাতীয় পরিচয়পত্র (NID) সংক্রান্ত সতর্কতা ⚠️",
                message=f"আপনার NID কার্ড যাচাই বাতিল করা হয়েছে।{note_txt} অনুগ্রহ করে প্রোফাইল থেকে স্পষ্ট ছবি পুনরায় আপলোড করুন।",
                notification_type="nid",
                related_id=user.id
            )
        elif cur_nid_status == "verified":
            send_in_app_notification(
                db=db,
                user_id=user.id,
                title="জাতীয় পরিচয়পত্র (NID) সফলভাবে যাচাইকৃত ✅",
                message="আপনার জাতীয় পরিচয়পত্রের নথি সফলভাবে যাচাই ও অনুমোদিত হয়েছে।",
                notification_type="nid",
                related_id=user.id
            )

    return serialize_user_with_stats(user, db)


@router.post("/reupload-nid", response_model=UserResponse)
def reupload_nid_documents(
    payload: dict,
    user_id: Optional[str] = Query(None),
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Allow user to re-upload their NID front and back images when rejected by admin.
    Supports Bearer token in header or user_id query/payload.
    """
    user = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
        try:
            p = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            uid = p.get("sub")
            if uid:
                user = db.query(User).filter(User.id == uid).first()
        except JWTError:
            pass

    if not user:
        req_uid = user_id or payload.get("user_id")
        if req_uid:
            user = db.query(User).filter(User.id == str(req_uid).strip()).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="ব্যবহারকারী শনাক্ত করা যায়নি। অনুগ্রহ করে লগইন করুন।"
        )

    nid_front = payload.get("nid_front_url")
    nid_back = payload.get("nid_back_url")
    nid_number = payload.get("nid_or_doc")
    
    if nid_front:
        user.nid_front_url = nid_front
    if nid_back:
        user.nid_back_url = nid_back
    if nid_number:
        user.nid_or_doc = nid_number
        
    user.nid_status = "pending"
    user.nid_rejection_note = ""
    user.verification_status = "pending"
    user.admin_note = "ইউজার নতুন এনআইডি জমা দিয়েছেন (যাচাই প্রয়োজন)"
    
    db.add(user)
    db.commit()
    db.refresh(user)

    # Send confirmation notification to the user
    send_in_app_notification(
        db=db,
        user_id=user.id,
        title="সংশোধিত NID জমা সম্পন্ন হয়েছে 📄",
        message="আপনার সংশোধিত জাতীয় পরিচয়পত্র সফলভাবে গৃহীত হয়েছে। অ্যাডমিন টিম দ্রুত এটি যাচাই করবে।",
        notification_type="nid",
        related_id=user.id
    )

    return serialize_user_with_stats(user, db)




@router.get("/profile", response_model=UserResponse)
def get_user_profile(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get full profile data for current authenticated user (Farmer / Buyer).
    """
    return serialize_user_with_stats(current_user, db)


@router.get("/me", response_model=UserResponse)
def get_user_me(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Get profile data with live stats for /users/me endpoint.
    """
    return serialize_user_with_stats(current_user, db)


@router.get("/profile/{user_id}", response_model=UserResponse)
def get_user_by_id(user_id: str, db: Session = Depends(get_db)):
    """
    Get public/full profile by user ID.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ব্যবহারকারী পাওয়া যায়নি।"
        )
    return serialize_user_with_stats(user, db)


@router.get("/by-identifier", response_model=UserResponse)
def get_user_by_identifier(
    phone: str = "",
    email: str = "",
    db: Session = Depends(get_db)
):
    """
    Get user profile by phone or email.
    """
    clean_phone = phone.strip()
    clean_email = email.strip().lower()
    user = None
    if clean_phone:
        user = db.query(User).filter(User.phone == clean_phone).first()
    if not user and clean_email:
        user = db.query(User).filter(User.email == clean_email).first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ব্যবহারকারী পাওয়া যায়নি।"
        )
    return serialize_user_with_stats(user, db)


@router.patch("/profile", response_model=UserResponse)
def update_user_profile(
    user_update: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    PATCH API to update user profile information.
    """
    update_data = user_update.model_dump(exclude_unset=True)

    for field, value in update_data.items():
        if value is not None:
            setattr(current_user, field, value)

    db.add(current_user)
    db.commit()
    db.refresh(current_user)
    return serialize_user_with_stats(current_user, db)


@router.patch("/profile/{user_id}", response_model=UserResponse)
def update_user_profile_by_id(
    user_id: str,
    user_update: UserUpdate,
    db: Session = Depends(get_db)
):
    """
    Update profile directly by user_id.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="ব্যবহারকারী পাওয়া যায়নি।"
        )
    update_data = user_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(user, field, value)

    db.add(user)
    db.commit()
    db.refresh(user)
    return serialize_user_with_stats(user, db)



@router.get("/dashboard-stats")
def get_dashboard_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns summarized key statistics tailored for Farmer or Buyer dashboards.
    """
    if current_user.role == "farmer":
        total_products = db.query(Product).filter(Product.farmer_id == current_user.id).count()
        active_products = db.query(Product).filter(
            Product.farmer_id == current_user.id,
            Product.status == "active"
        ).count()
        total_offers = db.query(Offer).filter(Offer.farmer_id == current_user.id).count()
        
        farmer_orders = db.query(Order).filter(Order.farmer_id == current_user.id).all()
        total_orders = len(farmer_orders)
        completed_orders = sum(1 for o in farmer_orders if o.order_status == "completed")
        active_orders = sum(1 for o in farmer_orders if o.order_status not in ["completed", "cancelled"])
        total_earnings = sum(o.total_amount for o in farmer_orders if o.is_deposit_paid)

        return {
            "role": "farmer",
            "user_name": current_user.name,
            "verification_status": current_user.verification_status,
            "total_products": total_products,
            "active_products": active_products,
            "submitted_offers": total_offers,
            "total_orders": total_orders,
            "active_orders": active_orders,
            "completed_orders": completed_orders,
            "total_earnings": total_earnings,
            "rating": current_user.rating,
            "reviews_count": current_user.reviews_count,
            "payment_reliability": current_user.payment_reliability
        }
    else:  # buyer
        total_demands = db.query(Demand).filter(Demand.buyer_id == current_user.id).count()
        active_demands = db.query(Demand).filter(
            Demand.buyer_id == current_user.id,
            Demand.status == "active"
        ).count()
        
        buyer_orders = db.query(Order).filter(Order.buyer_id == current_user.id).all()
        total_orders = len(buyer_orders)
        completed_orders = sum(1 for o in buyer_orders if o.order_status == "completed")
        active_orders = sum(1 for o in buyer_orders if o.order_status not in ["completed", "cancelled"])
        total_spent = sum(o.total_amount for o in buyer_orders if o.is_deposit_paid)

        return {
            "role": "buyer",
            "business_name": current_user.business_name or current_user.name,
            "verification_status": current_user.verification_status,
            "total_demands": total_demands,
            "active_demands": active_demands,
            "total_orders": total_orders,
            "active_orders": active_orders,
            "completed_orders": completed_orders,
            "total_spent": total_spent,
            "rating": current_user.rating,
            "reviews_count": current_user.reviews_count,
            "payment_reliability": current_user.payment_reliability
        }
