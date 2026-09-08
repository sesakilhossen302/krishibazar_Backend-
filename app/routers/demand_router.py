from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from app.database import get_db
from app.models.demand_model import Demand, Offer
from app.models.order_model import Order
from app.models.user_model import User
from app.schemas.demand_schema import DemandCreate, DemandUpdate, DemandResponse, OfferCreate, OfferResponse
from app.schemas.order_schema import OrderResponse
from app.utils import get_current_user
from app.routers.notification_router import send_in_app_notification

router = APIRouter(prefix="/demands", tags=["Demands & Offers (চাহিদা ও দরপত্র)"])


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
    if buyer_id:
        query = query.filter(Demand.buyer_id == buyer_id)
    if category and category != "all":
        query = query.filter(Demand.category == category)
    if district:
        query = query.filter(Demand.required_location.contains(district))
    if search:
        query = query.filter(Demand.product_title.contains(search))
    return query.order_by(Demand.created_at.desc()).all()


@router.get("/my-demands", response_model=List[DemandResponse])
def get_my_demands(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    List demands created by currently logged-in buyer.
    """
    return db.query(Demand).filter(
        Demand.buyer_id == current_user.id
    ).order_by(Demand.created_at.desc()).all()


@router.get("/{demand_id}", response_model=DemandResponse)
def get_demand_by_id(demand_id: str, db: Session = Depends(get_db)):
    """
    Get a single demand by ID.
    """
    demand = db.query(Demand).filter(Demand.id == demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="চাহিদাপত্র পাওয়া যায়নি।")
    return demand


@router.post("/", response_model=DemandResponse, status_code=status.HTTP_201_CREATED)
def create_demand(
    demand_in: DemandCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Buyer creates a new demand for bulk produce.
    """
    new_id = f"dem_{uuid.uuid4().hex[:8]}"
    db_demand = Demand(
        id=new_id,
        buyer_id=current_user.id,
        buyer_name=current_user.name,
        buyer_business_name=current_user.business_name or "পাইকারি আড়ত",
        buyer_district=current_user.district,
        buyer_verified=(current_user.verification_status == "verified"),
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
    return db_demand


@router.patch("/{demand_id}", response_model=DemandResponse)
def update_demand(
    demand_id: str,
    demand_update: DemandUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update demand information or status.
    """
    demand = db.query(Demand).filter(Demand.id == demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="চাহিদা পাওয়া যায়নি।")
    if demand.buyer_id != current_user.id:
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
    """
    return db.query(Offer).filter(Offer.demand_id == demand_id).order_by(Offer.created_at.desc()).all()


@router.get("/offers/my-offers", response_model=List[OfferResponse])
def get_my_submitted_offers(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Farmer views all offers they have submitted.
    """
    return db.query(Offer).filter(
        Offer.farmer_id == current_user.id
    ).order_by(Offer.created_at.desc()).all()


@router.post("/offers", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
def create_offer(
    offer_in: OfferCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Farmer submits a price & quantity offer for a buyer's demand.
    """
    demand = db.query(Demand).filter(Demand.id == offer_in.demand_id).first()
    if not demand:
        raise HTTPException(status_code=404, detail="চাহিদাপত্রটি পাওয়া যায়নি।")

    new_id = f"off_{uuid.uuid4().hex[:8]}"
    db_offer = Offer(
        id=new_id,
        demand_id=offer_in.demand_id,
        farmer_id=current_user.id,
        farmer_name=current_user.name,
        farmer_phone=current_user.phone,
        farmer_location=current_user.district,
        farmer_verified=(current_user.verification_status == "verified"),
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
    demand.offers_count += 1
    db.commit()
    db.refresh(db_offer)

    # Notify the buyer
    send_in_app_notification(
        db=db,
        user_id=demand.buyer_id,
        title="নতুন দরপত্র (Offer) এসেছে!",
        message=f"{current_user.name} আপনার '{demand.product_title}' চাহিদায় ৳{offer_in.price_per_unit}/{offer_in.unit} দরে অফার পাঠিয়েছেন।",
        notification_type="offer",
        related_id=db_offer.id
    )

    return db_offer


@router.post("/offers/{offer_id}/accept", response_model=OrderResponse)
def accept_offer(
    offer_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Buyer accepts farmer's offer -> Automatically creates an Order with 20% deposit calculation!
    """
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="অফারটি পাওয়া যায়নি।")

    demand = db.query(Demand).filter(Demand.id == offer.demand_id).first()
    if not demand or demand.buyer_id != current_user.id:
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
    deposit = total * 0.20

    new_order = Order(
        id=new_order_id,
        order_number=order_num,
        demand_id=demand.id,
        offer_id=offer.id,
        buyer_id=current_user.id,
        buyer_name=current_user.name,
        buyer_business_name=current_user.business_name or "পাইকারি আড়ত",
        buyer_phone=current_user.phone,
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
    send_in_app_notification(
        db=db,
        user_id=offer.farmer_id,
        title="🎉 অভিনন্দন! আপনার অফার গৃহীত হয়েছে!",
        message=f"{current_user.name} আপনার {offer.offered_quantity} {offer.unit} {demand.product_title} এর অফার গ্রহণ করেছেন। অর্ডার নং: {order_num}",
        notification_type="order",
        related_id=new_order.id
    )

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
