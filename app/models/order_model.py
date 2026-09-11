from sqlalchemy import Column, String, Float, Boolean, Text
from app.database import Base

class Order(Base):
    __tablename__ = "orders"

    id = Column(String, primary_key=True, index=True)
    order_number = Column(String, unique=True, index=True, nullable=False)
    demand_id = Column(String, nullable=True)
    offer_id = Column(String, nullable=True)
    
    buyer_id = Column(String, index=True, nullable=False)
    buyer_name = Column(String, nullable=False)
    buyer_business_name = Column(String, nullable=False)
    buyer_phone = Column(String, nullable=False)
    
    farmer_id = Column(String, index=True, nullable=False)
    farmer_name = Column(String, nullable=False)
    farmer_phone = Column(String, nullable=False)
    farmer_location = Column(String, nullable=False)
    
    product_title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False, default="কেজি (kg)")
    price_per_unit = Column(Float, nullable=False)
    total_amount = Column(Float, nullable=False)
    deposit_required = Column(Float, nullable=False)
    is_deposit_paid = Column(Boolean, default=False)
    order_status = Column(String, default="pending")
    delivery_location = Column(String, nullable=False)
    expected_delivery_date = Column(String, nullable=False)
    
    # Payment verification
    payment_status = Column(String, default="unpaid")  # unpaid, pending_verification, confirmed, refund_pending, refunded
    payment_verification_notes = Column(String, default="")

    # Transport Info
    transport_agency = Column(String, default="")
    pickup_location = Column(String, default="")
    collection_center = Column(String, default="")
    driver_name = Column(String, default="মোঃ রফিকুল ইসলাম")
    driver_phone = Column(String, default="01712-345678")
    vehicle_number = Column(String, default="ঢাকা মেট্রো-ট ১১-৪৫২৩")
    transport_status = Column(String, default="waiting")
    
    # Quality Verification Info
    inspector_name = Column(String, default="")
    inspector_designation = Column(String, default="")
    actual_weight = Column(Float, nullable=True)
    quality_grade = Column(String, nullable=True)
    verified_by = Column(String, nullable=True)
    verification_notes = Column(Text, nullable=True)
    is_quality_verified = Column(Boolean, default=False)
    is_quality_passed = Column(Boolean, nullable=True)
    rejection_reason = Column(Text, default="")

    # Refund Info
    refund_status = Column(String, default="none")  # none, pending, completed
    refund_amount = Column(Float, default=0.0)
    refund_notes = Column(Text, default="")

    has_dispute = Column(Boolean, default=False)
    is_rated = Column(Boolean, default=False)
    created_at = Column(String, nullable=False)

