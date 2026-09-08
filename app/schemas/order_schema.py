from pydantic import BaseModel
from typing import Optional

class OrderCreate(BaseModel):
    farmer_id: str
    product_title: str
    category: str
    quantity: float
    unit: str = "কেজি (kg)"
    price_per_unit: float
    delivery_location: str
    expected_delivery_date: str

class OrderStatusUpdate(BaseModel):
    order_status: str  # pending, paymentConfirmed, processing, pickupReady, inTransit, delivered, completed, cancelled
    note: Optional[str] = ""

class TransportUpdate(BaseModel):
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    vehicle_number: Optional[str] = None
    transport_status: Optional[str] = None  # waiting, loaded, onTheWay, reached, delivered
    pickup_location: Optional[str] = None
    collection_center: Optional[str] = None

class OrderDisputeCreate(BaseModel):
    reason: str
    description: str

class OrderResponse(BaseModel):
    id: str
    order_number: str
    demand_id: Optional[str] = None
    offer_id: Optional[str] = None
    buyer_id: str
    buyer_name: str
    buyer_business_name: str
    buyer_phone: str
    farmer_id: str
    farmer_name: str
    farmer_phone: str
    farmer_location: str
    product_title: str
    category: str
    quantity: float
    unit: str
    price_per_unit: float
    total_amount: float
    deposit_required: float
    is_deposit_paid: bool
    order_status: str
    delivery_location: str
    expected_delivery_date: str
    pickup_location: str
    collection_center: str
    driver_name: str
    driver_phone: str
    vehicle_number: str
    transport_status: str
    has_dispute: bool
    is_rated: bool
    created_at: str

    class Config:
        from_attributes = True
