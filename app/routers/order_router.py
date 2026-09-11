from fastapi import APIRouter, Depends, HTTPException, status, Header, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
from jose import jwt, JWTError

from app.config import settings
from app.database import get_db
from app.models.order_model import Order
from app.models.user_model import User
from app.schemas.order_schema import (
    OrderCreate,
    OrderResponse,
    OrderStatusUpdate,
    TransportUpdate,
    QualityVerificationUpdate,
    OrderDisputeCreate
)
from app.utils import get_current_user
from app.routers.notification_router import send_in_app_notification

router = APIRouter(prefix="/orders", tags=["Orders & Transport (অর্ডার ও পরিবহন)"])


@router.get("/", response_model=List[OrderResponse])
def get_orders(
    buyer_id: Optional[str] = None,
    farmer_id: Optional[str] = None,
    user_id: Optional[str] = None,
    status: Optional[str] = None,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    List orders with optional filtering by buyer_id, farmer_id, user_id (matches either), or status.
    """
    query = db.query(Order)
    if user_id:
        uid = str(user_id).strip()
        query = query.filter((Order.buyer_id == uid) | (Order.farmer_id == uid))
    if buyer_id:
        query = query.filter(Order.buyer_id == str(buyer_id).strip())
    if farmer_id:
        query = query.filter(Order.farmer_id == str(farmer_id).strip())
    if status:
        query = query.filter(Order.order_status == status)
    return query.order_by(Order.created_at.desc()).all()


@router.get("/my-orders", response_model=List[OrderResponse])
def get_my_orders(
    authorization: Optional[str] = Header(None),
    user_id: Optional[str] = Query(None),
    farmer_id: Optional[str] = Query(None),
    buyer_id: Optional[str] = Query(None),
    status: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get all orders associated with the user (as Buyer or as Farmer).
    Accepts Bearer token, user_id, farmer_id, or buyer_id.
    """
    uid = user_id or farmer_id or buyer_id
    if not uid and authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            uid = payload.get("sub")
        except JWTError:
            pass

    query = db.query(Order)
    if uid:
        target_uid = str(uid).strip()
        query = query.filter((Order.buyer_id == target_uid) | (Order.farmer_id == target_uid))
    if status:
        query = query.filter(Order.order_status == status)
    return query.order_by(Order.created_at.desc()).all()


@router.get("/{order_id}", response_model=OrderResponse)
def get_order_by_id(order_id: str, db: Session = Depends(get_db)):
    """
    Get order details by order ID.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="অর্ডারটি পাওয়া যায়নি।")
    return order


@router.post("/", response_model=OrderResponse, status_code=status.HTTP_201_CREATED)
def create_order(
    order_in: OrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Directly create a new produce order.
    """
    farmer = db.query(User).filter(User.id == order_in.farmer_id).first()
    if not farmer:
        raise HTTPException(status_code=404, detail="কৃষক পাওয়া যায়নি।")

    new_id = f"ord_{uuid.uuid4().hex[:8]}"
    order_num = f"KB-{uuid.uuid4().hex[:6].upper()}"
    total = order_in.quantity * order_in.price_per_unit
    deposit = total * 0.20  # 20% deposit

    db_order = Order(
        id=new_id,
        order_number=order_num,
        buyer_id=current_user.id,
        buyer_name=current_user.name,
        buyer_business_name=current_user.business_name or "পাইকারি আড়ত",
        buyer_phone=current_user.phone,
        farmer_id=farmer.id,
        farmer_name=farmer.name,
        farmer_phone=farmer.phone,
        farmer_location=farmer.district,
        product_title=order_in.product_title,
        category=order_in.category,
        quantity=order_in.quantity,
        unit=order_in.unit,
        price_per_unit=order_in.price_per_unit,
        total_amount=total,
        deposit_required=deposit,
        is_deposit_paid=False,
        order_status="pending",
        delivery_location=order_in.delivery_location,
        expected_delivery_date=order_in.expected_delivery_date,
        pickup_location=farmer.address or farmer.district,
        collection_center=f"{farmer.district} কালেকশন হাব",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    db.add(db_order)
    db.commit()
    db.refresh(db_order)

    # Notify farmer
    send_in_app_notification(
        db=db,
        user_id=farmer.id,
        title="নতুন অর্ডার এসেছে!",
        message=f"{current_user.name} আপনার {order_in.quantity} {order_in.unit} {order_in.product_title} এর নতুন অর্ডার দিয়েছেন। অর্ডার নং: {order_num}",
        notification_type="order",
        related_id=db_order.id
    )

    return db_order


@router.post("/{order_id}/pay-deposit", response_model=OrderResponse)
def pay_deposit(
    order_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Pay 20% security deposit to KrishiBazar Escrow.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="অর্ডারটি পাওয়া যায়নি।")

    order.is_deposit_paid = True
    order.order_status = "paymentConfirmed"
    db.commit()
    db.refresh(order)

    # Notify farmer and buyer
    send_in_app_notification(
        db=db,
        user_id=order.farmer_id,
        title="💰 অর্ডারের ডিপোজিট পরিশোধিত!",
        message=f"অর্ডার নং {order.order_number} এর ২০% জামানত (৳{order.deposit_required:,.2f}) কৃষিবাজার এসক্রোতে জমা হয়েছে। পণ্য প্রস্তুত করুন।",
        notification_type="order",
        related_id=order.id
    )

    return order


@router.patch("/{order_id}/verify-quality", response_model=OrderResponse)
def verify_order_quality(
    order_id: str,
    verification_in: QualityVerificationUpdate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Quality and weight inspection at collection hub (performed via Admin Dashboard).
    Marks the order as collectionVerified and updates verification data.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="অর্ডারটি পাওয়া যায়নি।")

    order.actual_weight = verification_in.actual_weight
    order.quality_grade = verification_in.quality_grade
    if verification_in.verified_by:
        order.verified_by = verification_in.verified_by
    if verification_in.verification_notes:
        order.verification_notes = verification_in.verification_notes
    order.is_quality_verified = True
    order.order_status = "collectionVerified"

    db.commit()
    db.refresh(order)

    # Notify buyer & farmer
    send_in_app_notification(
        db=db,
        user_id=order.buyer_id,
        title="✅ পণ্যের মান ও ওজন যাচাই সম্পন্ন!",
        message=f"অর্ডার নং {order.order_number} এর গুণমান যাচাই সম্পন্ন হয়েছে (গ্রেড: {order.quality_grade}, প্রকৃত ওজন: {order.actual_weight} {order.unit})। পণ্য এখন পরিবহনের জন্য প্রস্তুত।",
        notification_type="order",
        related_id=order.id
    )
    send_in_app_notification(
        db=db,
        user_id=order.farmer_id,
        title="✅ পণ্যের হাব যাচাই সম্পন্ন!",
        message=f"অর্ডার নং {order.order_number} কালেকশন হাবে ইন্সপেকশন সম্পন্ন হয়েছে।",
        notification_type="order",
        related_id=order.id
    )

    return order


@router.patch("/{order_id}/status", response_model=OrderResponse)
def update_order_status(
    order_id: str,
    status_update: OrderStatusUpdate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Update order lifecycle status (e.g. pending, paymentConfirmed, collectionVerified, inTransit, delivered, completed, cancelled).
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="অর্ডারটি পাওয়া যায়নি।")

    order.order_status = status_update.order_status

    if status_update.order_status == "completed":
        # Increment completed orders stats for farmer and buyer
        farmer = db.query(User).filter(User.id == order.farmer_id).first()
        buyer = db.query(User).filter(User.id == order.buyer_id).first()
        if farmer:
            farmer.completed_orders += 1
        if buyer:
            buyer.completed_orders += 1

    db.commit()
    db.refresh(order)

    # Resolve sender/current user if token provided
    current_uid = None
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            current_uid = payload.get("sub")
        except JWTError:
            pass

    # Notify counter-party
    target_user_id = order.buyer_id if current_uid == order.farmer_id else order.farmer_id
    send_in_app_notification(
        db=db,
        user_id=target_user_id,
        title=f"অর্ডার স্ট্যাটাস আপডেট: {status_update.order_status}",
        message=f"অর্ডার নং {order.order_number} এর স্ট্যাটাস পরিবর্তিত হয়ে '{status_update.order_status}' হয়েছে।",
        notification_type="order",
        related_id=order.id
    )

    return order


@router.patch("/{order_id}/transport", response_model=OrderResponse)
def update_transport_details(
    order_id: str,
    transport_in: TransportUpdate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Update transport & vehicle tracking information for the order (driver, vehicle, status).
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="অর্ডারটি পাওয়া যায়নি।")

    update_data = transport_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(order, field, value)

    # Automatically synchronize order_status with transport progression if applicable
    if transport_in.transport_status in ["in_transit", "onTheWay"]:
        order.order_status = "inTransit"
    elif transport_in.transport_status in ["delivered", "reached"]:
        order.order_status = "delivered"

    db.commit()
    db.refresh(order)

    # Notify buyer & farmer
    send_in_app_notification(
        db=db,
        user_id=order.buyer_id,
        title=f"🚚 পরিবহন আপডেট: {order.transport_status}",
        message=f"অর্ডার নং {order.order_number} পরিবহন আপডেট: {order.transport_status} (ড্রাইভার: {order.driver_name}, গাড়ি: {order.vehicle_number})",
        notification_type="order",
        related_id=order.id
    )

    return order



@router.post("/{order_id}/dispute", response_model=OrderResponse)
def raise_order_dispute(
    order_id: str,
    dispute_in: OrderDisputeCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Raise a dispute for safety and mediation.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="অর্ডারটি পাওয়া যায়নি।")

    order.has_dispute = True
    order.order_status = "disputed"
    db.commit()
    db.refresh(order)

    send_in_app_notification(
        db=db,
        user_id=order.farmer_id if current_user.id == order.buyer_id else order.buyer_id,
        title="⚠️ অর্ডার নিয়ে অভিযোগ/ডিসপিউট দাখিল হয়েছে",
        message=f"অর্ডার নং {order.order_number} এ অভিযোগ এসেছে: {dispute_in.reason}। কৃষিবাজার সাপোর্ট টিম পর্যালোচনা করছে।",
        notification_type="order",
        related_id=order.id
    )

    return order
