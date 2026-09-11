from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
from jose import JWTError, jwt
import uuid

from app.config import settings
from app.database import get_db
from app.models.demand_model import Demand, Offer
from app.models.order_model import Order
from app.models.user_model import User
from app.schemas.demand_schema import DemandCreate, DemandUpdate, DemandResponse, OfferCreate, OfferResponse
from app.schemas.order_schema import OrderResponse
from app.utils import get_current_user
from app.routers.notification_router import send_in_app_notification

router = APIRouter(prefix="/demands", tags=["Demands & Offers (চাহিদা ও দরপত্র)"])


def resolve_current_user(
    authorization: Optional[str] = Header(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
) -> Optional[User]:
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
        try:
            p = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            uid = p.get("sub")
            if uid:
                user = db.query(User).filter(User.id == str(uid).strip()).first()
                if user:
                    return user
        except Exception:
            pass
    if user_id and str(user_id).strip():
        user = db.query(User).filter(User.id == str(user_id).strip()).first()
        if user:
            return user
    return None


def serialize_demand(d: Demand, user: Optional[User] = None) -> DemandResponse:
    res = DemandResponse.model_validate(d)
    if user:
        if user.photo_url:
            res.buyer_photo_url = user.photo_url
        if user.phone:
            res.buyer_phone = user.phone
    return res


@router.get("/", response_model=List[DemandResponse])
def get_demands(
    buyer_id: Optional[str] = None,
    category: Optional[str] = None,
    district: Optional[str] = None,
    search: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """
    List all active demands from buyers.
    """
    query = db.query(Demand).filter(Demand.status == "active")
    if buyer_id and buyer_id.strip():
        query = query.filter(Demand.buyer_id == buyer_id.strip())
    if category and category != "all":
        query = query.filter(Demand.category == category)
    if district and district.strip():
        query = query.filter(Demand.required_location.contains(district.strip()))
    if search and search.strip():
        query = query.filter(Demand.product_title.contains(search.strip()))

    demands = query.order_by(Demand.created_at.desc()).all()
    buyer_ids = {d.buyer_id for d in demands if d.buyer_id}
    user_map = {u.id: u for u in db.query(User).filter(User.id.in_(buyer_ids)).all()} if buyer_ids else {}
    return [serialize_demand(d, user_map.get(d.buyer_id)) for d in demands]


@router.get("/my-demands", response_model=List[DemandResponse])
def get_my_demands(
    authorization: Optional[str] = Header(None),
    buyer_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    List demands created by currently logged-in buyer.
    Supports Bearer token or buyer_id / user_id query parameters.
    """
    user = resolve_current_user(authorization, buyer_id or user_id, db)
    target_id = user.id if user else (buyer_id or user_id)
    if not target_id or not str(target_id).strip():
        return []
    demands = db.query(Demand).filter(
        Demand.buyer_id == str(target_id).strip()
    ).order_by(Demand.created_at.desc()).all()
    return [serialize_demand(d, user) for d in demands]


@router.get("/{demand_id}", response_model=DemandResponse)
def get_demand_by_id(demand_id: str, db: Session = Depends(get_db)):
    """
    Get a single demand by ID.
    """
    demand = db.query(Demand).filter(Demand.id == demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="চাহিদাপত্র পাওয়া যায়নি।")
    u = db.query(User).filter(User.id == demand.buyer_id).first()
    return serialize_demand(demand, u)


@router.post("/", response_model=DemandResponse, status_code=status.HTTP_201_CREATED)
def create_demand(
    demand_in: DemandCreate,
    authorization: Optional[str] = Header(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Buyer creates a new demand for bulk produce.
    """
    user = resolve_current_user(authorization, user_id, db)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="চাহিদা পোস্ট করতে অনুগ্রহ করে লগইন করুন।"
        )

    new_id = f"dem_{uuid.uuid4().hex[:8]}"
    db_demand = Demand(
        id=new_id,
        buyer_id=user.id,
        buyer_name=user.name,
        buyer_business_name=user.business_name or "পাইকারি আড়ত",
        buyer_district=user.district or "ঢাকা",
        buyer_verified=(user.verification_status == "verified"),
        product_title=demand_in.product_title,
        category=demand_in.category,
        required_quantity=demand_in.required_quantity,
        fulfilled_quantity=0.0,
        unit=demand_in.unit,
        required_location=demand_in.required_location,
        required_date=demand_in.required_date,
        min_expected_price=demand_in.min_expected_price,
        max_expected_price=demand_in.max_expected_price,
        quality_grade=demand_in.quality_grade,
        additional_note=demand_in.additional_note or "",
        status="active",
        offers_count=0,
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    db.add(db_demand)
    db.commit()
    db.refresh(db_demand)

    # In-app notification to farmers about the new bulk demand
    try:
        farmers = db.query(User).filter(User.role == "farmer").limit(20).all()
        for f in farmers:
            send_in_app_notification(
                db=db,
                user_id=f.id,
                title="নতুন পাইকারি চাহিদা পোস্ট হয়েছে! 📢",
                message=f"{db_demand.buyer_business_name} {db_demand.required_quantity} {db_demand.unit} {db_demand.product_title} ক্রয় করতে চান। সরাসরি দরপত্র (Offer) জমা দিন!",
                notification_type="demand",
                related_id=db_demand.id
            )
    except Exception as e:
        print(f"Error sending demand alert notification: {e}")

    return serialize_demand(db_demand, user)


@router.delete("/{demand_id}")
def delete_demand(
    demand_id: str,
    authorization: Optional[str] = Header(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Delete / Cancel a demand by ID.
    """
    demand = db.query(Demand).filter(Demand.id == demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="চাহিদাপত্র পাওয়া যায়নি।")

    user = resolve_current_user(authorization, user_id, db)
    if user and user.role != "admin" and demand.buyer_id != user.id:
        raise HTTPException(status_code=403, detail="এই চাহিদা মুছে ফেলার অনুমতি নেই।")

    db.delete(demand)
    db.commit()
    return {"success": True, "message": "চাহিদা সফলভাবে মুছে ফেলা হয়েছে।"}


@router.patch("/{demand_id}", response_model=DemandResponse)
def update_demand(
    demand_id: str,
    demand_update: DemandUpdate,
    authorization: Optional[str] = Header(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Update demand information or status.
    """
    demand = db.query(Demand).filter(Demand.id == demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="চাহিদা পাওয়া যায়নি।")

    user = resolve_current_user(authorization, user_id, db)
    if user and user.role != "admin" and demand.buyer_id != user.id:
        raise HTTPException(status_code=403, detail="অনুমতি নেই।")

    update_data = demand_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(demand, field, value)

    db.commit()
    db.refresh(demand)
    return demand


# ----------------- Offers Subsystem -----------------

@router.get("/{demand_id}/offers", response_model=List[OfferResponse])
def get_offers_for_demand(demand_id: str, db: Session = Depends(get_db)):
    """
    Get all farmer offers for a specific demand.
    Enriches offers with farmer profile photo and contact info.
    """
    offers = db.query(Offer).filter(Offer.demand_id == demand_id).order_by(Offer.created_at.desc()).all()
    farmer_ids = {o.farmer_id for o in offers if o.farmer_id}
    farmer_map = {u.id: u for u in db.query(User).filter(User.id.in_(farmer_ids)).all()} if farmer_ids else {}

    results = []
    for o in offers:
        res = OfferResponse.model_validate(o)
        u = farmer_map.get(o.farmer_id)
        if u:
            if u.photo_url:
                res.farmer_photo_url = u.photo_url
            if u.phone:
                res.farmer_phone = u.phone
            if u.district:
                res.farmer_location = u.district
        results.append(res)
    return results


@router.get("/offers/my-offers", response_model=List[OfferResponse])
def get_my_submitted_offers(
    authorization: Optional[str] = Header(None),
    farmer_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Farmer views all offers they have submitted.
    Supports Bearer token, farmer_id or user_id query parameters.
    """
    user = resolve_current_user(authorization, farmer_id or user_id, db)
    target_id = user.id if user else (farmer_id or user_id)
    if not target_id or not str(target_id).strip():
        return []
    return db.query(Offer).filter(
        Offer.farmer_id == str(target_id).strip()
    ).order_by(Offer.created_at.desc()).all()


@router.post("/offers", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
def create_offer(
    offer_in: OfferCreate,
    authorization: Optional[str] = Header(None),
    farmer_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Farmer submits a price & quantity offer for a buyer's demand.
    Accepts Bearer auth, query parameters, or farmer fields inside body.
    """
    demand = db.query(Demand).filter(Demand.id == offer_in.demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="চাহিদাপত্রটি পাওয়া যায়নি।")

    user = resolve_current_user(authorization, offer_in.farmer_id or farmer_id or user_id, db)

    f_id = user.id if user else (offer_in.farmer_id or farmer_id or user_id or f"far_{uuid.uuid4().hex[:8]}")
    f_name = (user.name if user and user.name else None) or offer_in.farmer_name or "কৃষক"
    f_phone = (user.phone if user and user.phone else None) or offer_in.farmer_phone or ""
    f_loc = (user.district if user and user.district else None) or offer_in.farmer_location or "বাংলাদেশ"
    f_verified = (user.verification_status == "verified") if user else (offer_in.farmer_verified if offer_in.farmer_verified is not None else True)

    new_id = f"off_{uuid.uuid4().hex[:8]}"
    db_offer = Offer(
        id=new_id,
        demand_id=offer_in.demand_id,
        farmer_id=f_id,
        farmer_name=f_name,
        farmer_phone=f_phone,
        farmer_location=f_loc,
        farmer_verified=f_verified,
        offered_quantity=offer_in.offered_quantity,
        unit=offer_in.unit,
        price_per_unit=offer_in.price_per_unit,
        quality_grade=offer_in.quality_grade,
        available_date=offer_in.available_date,
        note=offer_in.note or "",
        status="pending",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    db.add(db_offer)
    demand.offers_count = (demand.offers_count or 0) + 1
    db.commit()
    db.refresh(db_offer)

    # Notify the buyer in-app
    try:
        send_in_app_notification(
            db=db,
            user_id=demand.buyer_id,
            title="নতুন দরপত্র (Offer) এসেছে! 🌾",
            message=f"{f_name} আপনার '{demand.product_title}' চাহিদায় ৳{offer_in.price_per_unit}/{offer_in.unit} দরে অফার পাঠিয়েছেন।",
            notification_type="offer",
            related_id=db_offer.id
        )
    except Exception as e:
        print(f"Error sending offer notification: {e}")

    return db_offer


@router.post("/offers/{offer_id}/accept", response_model=OrderResponse)
def accept_offer(
    offer_id: str,
    authorization: Optional[str] = Header(None),
    buyer_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Buyer accepts farmer's offer -> Automatically creates an Order with 20% deposit calculation!
    """
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="অফারটি পাওয়া যায়নি।")

    demand = db.query(Demand).filter(Demand.id == offer.demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="চাহিদাপত্র পাওয়া যায়নি।")

    user = resolve_current_user(authorization, buyer_id or user_id, db)
    if user and user.role != "admin" and demand.buyer_id != user.id:
        raise HTTPException(status_code=403, detail="শুধুমাত্র এই চাহিদার ক্রেতা অফার গ্রহণ করতে পারবেন।")

    # Mark offer as accepted
    offer.status = "accepted"
    demand.fulfilled_quantity += offer.offered_quantity
    if demand.fulfilled_quantity >= demand.required_quantity:
        demand.status = "fulfilled"

    # Create Order automatically
    new_order_id = f"ord_{uuid.uuid4().hex[:8]}"
    order_num = f"KB-{uuid.uuid4().hex[:6].upper()}"
    total = offer.offered_quantity * offer.price_per_unit
    deposit = round(total * 0.20, 2)
    buyer_fee = round(total * 0.05, 2)
    buyer_total = round(total + buyer_fee, 2)
    farmer_fee = round(total * 0.05, 2)
    farmer_payout = round(total - farmer_fee, 2)

    b_id = user.id if user else demand.buyer_id
    b_name = (user.name if user and user.name else None) or demand.buyer_name or "পাইকারি ক্রেতা"
    b_biz = (user.business_name if user and user.business_name else None) or demand.buyer_business_name or "আড়ত"
    b_phone = (user.phone if user and user.phone else None) or "০১৭০০০০০০০০"

    new_order = Order(
        id=new_order_id,
        order_number=order_num,
        demand_id=demand.id,
        offer_id=offer.id,
        buyer_id=b_id,
        buyer_name=b_name,
        buyer_business_name=b_biz,
        buyer_phone=b_phone,
        farmer_id=offer.farmer_id,
        farmer_name=offer.farmer_name,
        farmer_phone=offer.farmer_phone,
        farmer_location=offer.farmer_location,
        product_title=demand.product_title,
        category=demand.category,
        quantity=offer.offered_quantity,
        unit=offer.unit,
        price_per_unit=offer.price_per_unit,
        total_amount=total,
        product_amount=total,
        buyer_service_fee=buyer_fee,
        buyer_total_amount=buyer_total,
        farmer_service_fee=farmer_fee,
        farmer_payout_amount=farmer_payout,
        farmer_payout_status="unpaid",
        deposit_required=deposit,
        is_deposit_paid=False,
        order_status="pending",
        delivery_location=demand.required_location,
        expected_delivery_date=demand.required_date,
        pickup_location=offer.farmer_location,
        collection_center=f"{offer.farmer_location} কালেকশন হাব",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    # Send notifications to farmer
    try:
        send_in_app_notification(
            db=db,
            user_id=offer.farmer_id,
            title="🎉 অভিনন্দন! আপনার অফার গৃহীত হয়েছে!",
            message=f"{b_name} আপনার {offer.offered_quantity} {offer.unit} {demand.product_title} এর অফার গ্রহণ করেছেন। অর্ডার নং: {order_num}",
            notification_type="order",
            related_id=new_order.id
        )
    except Exception as e:
        print(f"Error sending order notification: {e}")

    return new_order


@router.post("/offers/{offer_id}/reject", response_model=OfferResponse)
def reject_offer(
    offer_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Buyer rejects farmer's offer.
    """
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="অফারটি পাওয়া যায়নি।")

    demand = db.query(Demand).filter(Demand.id == offer.demand_id).first()
    if not demand or demand.buyer_id != current_user.id:
        raise HTTPException(status_code=403, detail="অনুমতি নেই।")

    offer.status = "rejected"
    db.commit()
    db.refresh(offer)
    return offer
