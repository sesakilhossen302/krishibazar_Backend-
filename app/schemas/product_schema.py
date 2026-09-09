from pydantic import BaseModel
from typing import Optional, List

class ProductCreate(BaseModel):
    farmer_id: Optional[str] = None
    title: str
    category: str
    quantity: float
    unit: str = "কেজি (kg)"
    expected_price: float
    min_price: float
    location: str
    available_date: str
    harvest_date: str
    quality_grade: str
    description: Optional[str] = ""
    image_url: Optional[str] = ""
    images: Optional[List[str]] = []
    video_url: Optional[str] = ""
    video_note: Optional[str] = ""

class ProductUpdate(BaseModel):
    title: Optional[str] = None
    category: Optional[str] = None
    quantity: Optional[float] = None
    remaining_quantity: Optional[float] = None
    unit: Optional[str] = None
    expected_price: Optional[float] = None
    min_price: Optional[float] = None
    location: Optional[str] = None
    available_date: Optional[str] = None
    harvest_date: Optional[str] = None
    quality_grade: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    images: Optional[List[str]] = None
    video_url: Optional[str] = None
    video_note: Optional[str] = None
    status: Optional[str] = None

class ProductResponse(BaseModel):
    id: str
    farmer_id: str
    farmer_name: str
    farmer_district: str
    farmer_verified: bool
    title: str
    category: str
    quantity: float
    remaining_quantity: float
    unit: str
    expected_price: float
    min_price: float
    location: str
    available_date: str
    harvest_date: str
    quality_grade: str
    description: Optional[str] = ""
    image_url: Optional[str] = ""
    images: Optional[List[str]] = []
    video_url: Optional[str] = ""
    video_note: Optional[str] = ""
    status: str
    created_at: str

    class Config:
        from_attributes = True

