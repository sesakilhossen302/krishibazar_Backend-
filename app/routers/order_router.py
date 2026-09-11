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
    PaymentConfirmRequest,
    InspectorAssignRequest,
    QualityRejectRequest,
    RefundProcessRequest,
    FarmerPayoutRequest,
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
    deposit = round(total * 0.20, 2)  # 20% deposit
    buyer_fee = round(total * 0.05, 2)  # 5% extra platform service fee for buyer
    buyer_total = round(total + buyer_fee, 2)
    farmer_fee = round(total * 0.05, 2)  # 5% platform fee deducted from farmer
    farmer_payout = round(total - farmer_fee, 2)

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
        product_amount=total,
        buyer_service_fee=buyer_fee,
        buyer_total_amount=buyer_total,
        farmer_service_fee=farmer_fee,
        farmer_payout_amount=farmer_payout,
        farmer_payout_status="unpaid",
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
    Buyer submits 20% security deposit. Status becomes pending_verification for admin inspection.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="অর্ডারটি পাওয়া যায়নি।")

    order.is_deposit_paid = True
    order.payment_status = "pending_verification"
    order.order_status = "paymentPending"
    db.commit()
    db.refresh(order)

    # Notify farmer and buyer
    send_in_app_notification(
        db=db,
        user_id=order.farmer_id,
        title="💰 ক্রেতা ডিপোজিট জমা দিয়েছেন!",
        message=f"অর্ডার নং {order.order_number} এর ২০% জামানত (৳{order.deposit_required:,.2f}) জমা হয়েছে। এডমিন পেমেন্ট ভেরিফাই করছেন।",
        notification_type="order",
        related_id=order.id
    )
    send_in_app_notification(
        db=db,
        user_id=order.buyer_id,
        title="⏳ পেমেন্ট ভেরিফিকেশন পেন্ডিং",
        message=f"আপনার ২০% জামানত (৳{order.deposit_required:,.2f}) গ্রহণের অনুরোধ জমা হয়েছে। এডমিন টাকা প্রাপ্তি নিশ্চিত করছেন।",
        notification_type="order",
        related_id=order.id
    )

    return order


@router.post("/{order_id}/confirm-payment", response_model=OrderResponse)
def confirm_order_payment(
    order_id: str,
    payment_confirm_in: PaymentConfirmRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Admin confirms receipt of 20% deposit from buyer and assigns inspection agent.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="অর্ডারটি পাওয়া যায়নি।")

    order.is_deposit_paid = True
    order.payment_status = "confirmed"
    order.order_status = "paymentConfirmed"
    if payment_confirm_in.inspector_name:
        order.inspector_name = payment_confirm_in.inspector_name
        order.verified_by = payment_confirm_in.inspector_name
    if payment_confirm_in.inspector_designation:
        order.inspector_designation = payment_confirm_in.inspector_designation
    if payment_confirm_in.notes:
        order.payment_verification_notes = payment_confirm_in.notes

    db.commit()
    db.refresh(order)

    # Notify buyer & farmer
    inspector_label = f"{order.inspector_name} ({order.inspector_designation})" if order.inspector_name else "ইন্সপেকশন টিম"
    send_in_app_notification(
        db=db,
        user_id=order.buyer_id,
        title="💰 টাকা পাওয়া গেছে - কনফার্মড!",
        message=f"অর্ডার নং {order.order_number} এর ২০% জামানতের টাকা কৃষিবাজার অ্যাকাউন্টে জমা হয়েছে। কালেকশন হাবে পণ্য পরীক্ষার জন্য {inspector_label} নিযুক্ত করা হয়েছে।",
        notification_type="order",
        related_id=order.id
    )
    send_in_app_notification(
        db=db,
        user_id=order.farmer_id,
        title="💰 ক্রেতার ডিপোজিট কনফার্মড!",
        message=f"অর্ডার নং {order.order_number} এর ২০% জামানতের টাকা নিশ্চিত হয়েছে। কালেকশন হাবে পণ্য যাচাইয়ের জন্য পাঠানো শুরু করুন।",
        notification_type="order",
        related_id=order.id
    )

    return order


@router.post("/{order_id}/assign-inspector", response_model=OrderResponse)
def assign_order_inspector(
    order_id: str,
    inspector_in: InspectorAssignRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Admin assigns an inspector agent to examine produce at the collection hub.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="অর্ডারটি পাওয়া যায়নি।")

    order.inspector_name = inspector_in.inspector_name
    order.inspector_designation = inspector_in.inspector_designation or "কোয়ালিটি কন্ট্রোল অফিসার"
    order.verified_by = inspector_in.inspector_name
    db.commit()
    db.refresh(order)

    # Notify buyer & farmer
    send_in_app_notification(
        db=db,
        user_id=order.buyer_id,
        title="🔍 পণ্য পরীক্ষক নিয়োজিত হয়েছেন",
        message=f"অর্ডার নং {order.order_number} এর জন্য পণ্য পরীক্ষক হিসেবে {order.inspector_name} ({order.inspector_designation}) নিয়োজিত হয়েছেন। তিনি কালেকশন হাবে পণ্য পরীক্ষা করবেন।",
        notification_type="order",
        related_id=order.id
    )
    send_in_app_notification(
        db=db,
        user_id=order.farmer_id,
        title="🔍 পণ্য পরীক্ষক নিয়োজিত হয়েছেন",
        message=f"অর্ডার নং {order.order_number} এর জন্য পরীক্ষক হিসেবে {order.inspector_name} নিয়োজিত হয়েছেন। তিনি পণ্যের মান পরীক্ষা করবেন।",
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
    Marks product as passed and updates verification data.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="অর্ডারটি পাওয়া যায়নি।")

    order.actual_weight = verification_in.actual_weight
    order.quality_grade = verification_in.quality_grade
    if verification_in.verified_by:
        order.verified_by = verification_in.verified_by
    if verification_in.inspector_name:
        order.inspector_name = verification_in.inspector_name
    if verification_in.inspector_designation:
        order.inspector_designation = verification_in.inspector_designation
    if verification_in.verification_notes:
        order.verification_notes = verification_in.verification_notes
    order.is_quality_verified = True
    order.is_quality_passed = True
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
        message=f"অর্ডার নং {order.order_number} কালেকশন হাবে ইন্সপেকশন সফল হয়েছে।",
        notification_type="order",
        related_id=order.id
    )

    return order


@router.post("/{order_id}/reject-quality", response_model=OrderResponse)
def reject_order_quality(
    order_id: str,
    reject_in: QualityRejectRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Admin rejects order quality at collection hub. Prompts buyer to look for alternatives and queues 20% deposit refund.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="অর্ডারটি পাওয়া যায়নি।")

    order.is_quality_verified = True
    order.is_quality_passed = False
    order.rejection_reason = reject_in.rejection_reason
    if reject_in.inspector_name:
        order.inspector_name = reject_in.inspector_name
        order.verified_by = reject_in.inspector_name
    if reject_in.inspector_designation:
        order.inspector_designation = reject_in.inspector_designation

    order.order_status = "qualityRejected"
    order.payment_status = "refund_pending"
    order.refund_status = "pending"
    order.refund_amount = order.deposit_required

    db.commit()
    db.refresh(order)

    # Notify buyer & farmer
    send_in_app_notification(
        db=db,
        user_id=order.buyer_id,
        title="⚠️ পণ্যের মান সন্তোষজনক পাওয়া যায়নি",
        message=f"অর্ডার নং {order.order_number} হাবে পরীক্ষার পর মানসম্মত না হওয়ায় বাতিল করা হয়েছে। আপনার ২০% জামানতের টাকা রিফান্ড পেন্ডিং রয়েছে। অনুগ্রহ করে অন্য পণ্য অনুসন্ধান করুন।",
        notification_type="order",
        related_id=order.id
    )
    send_in_app_notification(
        db=db,
        user_id=order.farmer_id,
        title="⚠️ সরবরাহকৃত পণ্যের মান কালেকশন হাবে উত্তীর্ণ হয়নি",
        message=f"অর্ডার নং {order.order_number} এর পণ্য কোয়ালিটি টেস্টে উত্তীর্ণ হয়নি। কারণ: {order.rejection_reason}। ভবিষ্যতে উন্নত পণ্য সরবরাহ করুন।",
        notification_type="order",
        related_id=order.id
    )

    return order


@router.post("/{order_id}/process-refund", response_model=OrderResponse)
def process_order_refund(
    order_id: str,
    refund_in: RefundProcessRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Admin completes refunding the 20% deposit back to the buyer.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="অর্ডারটি পাওয়া যায়নি।")

    order.payment_status = "refunded"
    order.refund_status = "completed"
    order.order_status = "refunded"
    if refund_in.refund_notes:
        order.refund_notes = refund_in.refund_notes

    db.commit()
    db.refresh(order)

    send_in_app_notification(
        db=db,
        user_id=order.buyer_id,
        title="✅ ২০% টাকা সফলভাবে ফেরত দেওয়া হয়েছে",
        message=f"অর্ডার নং {order.order_number} এর ২০% জামানতের টাকা (৳{order.deposit_required:,.2f}) আপনার অ্যাকাউন্টে রিফান্ড সম্পন্ন হয়েছে। কারণ: পণ্যের মান সন্তোষজনক ছিল না।",
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

    if status_update.order_status in ["delivered", "completed"]:
        if order.farmer_payout_status != "completed":
            order.farmer_payout_status = "pending"

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
        if order.farmer_payout_status != "completed":
            order.farmer_payout_status = "pending"

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


@router.post("/{order_id}/farmer-payout", response_model=OrderResponse)
def disburse_farmer_payout(
    order_id: str,
    payout_in: FarmerPayoutRequest,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Admin confirms payment/payout of net product value to the farmer after delivery cash is collected.
    """
    order = db.query(Order).filter(Order.id == order_id).first()
    if not order:
        raise HTTPException(status_code=404, detail="অর্ডারটি পাওয়া যায়নি।")

    # If financial fields are empty on older records, compute them dynamically
    if not order.farmer_payout_amount:
        farmer_fee = round(order.total_amount * 0.05, 2)
        order.farmer_service_fee = farmer_fee
        order.farmer_payout_amount = round(order.total_amount - farmer_fee, 2)
    if not order.buyer_service_fee:
        order.buyer_service_fee = round(order.total_amount * 0.05, 2)
        order.buyer_total_amount = round(order.total_amount + order.buyer_service_fee, 2)

    order.farmer_payout_status = "completed"
    notes_text = payout_in.notes or "কৃষকের বিকাশ/ব্যাংক অ্যাকাউন্টে টাকা পরিশোধ করা হয়েছে"
    if payout_in.transaction_id:
        notes_text += f" (TrxID: {payout_in.transaction_id})"
    order.farmer_payout_notes = notes_text
    order.farmer_payout_date = datetime.now().strftime("%Y-%m-%d %H:%M")

    # If delivered, we can also mark order status as completed
    if order.order_status == "delivered":
        order.order_status = "completed"

    db.commit()
    db.refresh(order)

    payout_val = order.farmer_payout_amount or (order.total_amount * 0.95)

    # Send high-priority notification to farmer
    send_in_app_notification(
        db=db,
        user_id=order.farmer_id,
        title="💰 আপনার টাকা অ্যাকাউন্টে পাঠানো হয়েছে!",
        message=f"অর্ডার নং {order.order_number} এর নিট পাওনা ৳{payout_val:,.2f} টাকা (৫% প্ল্যাটফর্ম ফি কর্তন পরবর্তী) আপনার অ্যাকাউন্টে সফলভাবে পরিশোধ করা হয়েছে। নোট: {notes_text}",
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
