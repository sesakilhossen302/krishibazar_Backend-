from sqlalchemy import Column, String, Float, Boolean, Text
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
    created_at = Column(String, nullable=False)
