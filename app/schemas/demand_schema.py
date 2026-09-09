from pydantic import BaseModel
from typing import Optional

class DemandCreate(BaseModel):
    product_title: str
    category: str
    required_quantity: float
    unit: str = "কেজি (kg)"
    required_location: str
    required_date: str
    min_expected_price: float
    max_expected_price: float
    quality_grade: str
    additional_note: Optional[str] = ""

class DemandUpdate(BaseModel):
    product_title: Optional[str] = None
    category: Optional[str] = None
    required_quantity: Optional[float] = None
    fulfilled_quantity: Optional[float] = None
    unit: Optional[str] = None
    required_location: Optional[str] = None
    required_date: Optional[str] = None
    min_expected_price: Optional[float] = None
    max_expected_price: Optional[float] = None
    quality_grade: Optional[str] = None
    additional_note: Optional[str] = None
    status: Optional[str] = None

class DemandResponse(BaseModel):
    id: str
    buyer_id: str
    buyer_name: str
    buyer_business_name: str
    buyer_district: str
    buyer_verified: bool
    buyer_photo_url: Optional[str] = ""
    buyer_phone: Optional[str] = ""
    product_title: str
    category: str
    required_quantity: float
    fulfilled_quantity: float
    unit: str
    required_location: str
    required_date: str
    min_expected_price: float
    max_expected_price: float
    quality_grade: str
    additional_note: Optional[str] = ""
    status: str
    offers_count: int
    created_at: str

    class Config:
        from_attributes = True

class OfferCreate(BaseModel):
    demand_id: str
    farmer_id: Optional[str] = None
    farmer_name: Optional[str] = None
    farmer_phone: Optional[str] = None
    farmer_location: Optional[str] = None
    farmer_verified: Optional[bool] = None
    offered_quantity: float
    unit: str = "কেজি (kg)"
    price_per_unit: float
    quality_grade: str
    available_date: str
    note: Optional[str] = ""

class OfferResponse(BaseModel):
    id: str
    demand_id: str
    farmer_id: str
    farmer_name: str
    farmer_phone: str
    farmer_location: str
    farmer_verified: bool
    offered_quantity: float
    unit: str
    price_per_unit: float
    quality_grade: str
    available_date: str
    note: Optional[str] = ""
    status: str
    created_at: str

    class Config:
        from_attributes = True
