from sqlalchemy import Column, String, Float, Boolean, Text, Integer
from app.database import Base

class Product(Base):
    __tablename__ = "products"

    id = Column(String, primary_key=True, index=True)
    farmer_id = Column(String, index=True, nullable=False)
    farmer_name = Column(String, nullable=False)
    farmer_district = Column(String, nullable=False)
    farmer_verified = Column(Boolean, default=True)
    
    title = Column(String, nullable=False)
    category = Column(String, nullable=False)
    quantity = Column(Float, nullable=False)
    remaining_quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False, default="কেজি (kg)")
    expected_price = Column(Float, nullable=False)
    min_price = Column(Float, nullable=False)
    location = Column(String, nullable=False)
    available_date = Column(String, nullable=False)
    harvest_date = Column(String, nullable=False)
    quality_grade = Column(String, nullable=False)
    description = Column(Text, nullable=True, default="")
    image_url = Column(Text, nullable=True, default="")
    video_url = Column(Text, nullable=True, default="")
    video_note = Column(String, nullable=True, default="")
    status = Column(String, default="active")
    offers_count = Column(Integer, default=0)
    created_at = Column(String, nullable=False)


class ProductOffer(Base):
    __tablename__ = "product_offers"

    id = Column(String, primary_key=True, index=True)
    product_id = Column(String, index=True, nullable=False)
    buyer_id = Column(String, index=True, nullable=False)
    buyer_name = Column(String, nullable=False)
    buyer_business_name = Column(String, nullable=False)
    buyer_phone = Column(String, nullable=False)
    buyer_district = Column(String, nullable=False)
    buyer_photo_url = Column(String, nullable=True, default="")
    buyer_verified = Column(Boolean, default=True)

    offered_quantity = Column(Float, nullable=False)
    unit = Column(String, nullable=False, default="কেজি (kg)")
    price_per_unit = Column(Float, nullable=False)
    delivery_location = Column(String, nullable=True, default="")
    expected_delivery_date = Column(String, nullable=True, default="")
    note = Column(Text, nullable=True, default="")
    status = Column(String, default="pending")  # pending, accepted, rejected
    created_at = Column(String, nullable=False)

