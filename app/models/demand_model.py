from sqlalchemy import Column, String, Float, Boolean, Integer, Text
from app.database import Base

class Demand(Base):
    __tablename__ = "demands"

    id = Column(String, primary_key=True, index=True)
    buyer_id = Column(String, index=True, nullable=False)
    buyer_name = Column(String, nullable=False)
    buyer_business_name = Column(String, nullable=False)
    buyer_district = Column(String, nullable=False)
    buyer_verified = Column(Boolean, default=True)
    
    product_title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    required_quantity = Column(Float, nullable=False)
    fulfilled_quantity = Column(Float, default=0.0)
    unit = Column(String, nullable=False, default="কেজি (kg)")
    required_location = Column(String, nullable=False)
    required_date = Column(String, nullable=False)
    min_expected_price = Column(Float, nullable=False)
    max_expected_price = Column(Float, nullable=False)
    quality_grade = Column(String, nullable=False)
    additional_note = Column(Text, nullable=True, default="")
    status = Column(String, default="active")
    offers_count = Column(Integer, default=0)
    created_at = Column(String, nullable=False)


class Offer(Base):
    __tablename__ = "offers"

    id = Column(String, primary_key=True, index=True)
    demand_id = Column(String, index=True, nullable=False)
    farmer_id = Column(String, index=True, nullable=False)
    farmer_name = Column(String, nullable=False)
    farmer_phone = Column(String, nullable=False)
    farmer_location = Column(String, nullable=False)
    farmer_verified = Column(Boolean, default=True)
    
    offered_quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False, default="কেজি (kg)")
    price_per_unit = Column(Float, nullable=False)
    quality_grade = Column(String, nullable=False)
    available_date = Column(String, nullable=False)
    note = Column(Text, nullable=True, default="")
    status = Column(String, default="pending")
    created_at = Column(String, nullable=False)
