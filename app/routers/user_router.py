from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user_model import User
from app.models.product_model import Product
from app.models.demand_model import Demand, Offer
from app.models.order_model import Order
from app.schemas.user_schema import UserResponse, UserUpdate
from app.utils import get_current_user

router = APIRouter(prefix="/users", tags=["User Profile & Dashboard (প্রোফাইল ও ড্যাশবোর্ড)"])


@router.get("/profile", response_model=UserResponse)
def get_user_profile(current_user: User = Depends(get_current_user)):
    """
    Get full profile data for current authenticated user (Farmer / Buyer).
    """
    return current_user


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
    return user


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
    return user


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
    return current_user


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
