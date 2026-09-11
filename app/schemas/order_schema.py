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
    transport_agency: Optional[str] = None
    driver_name: Optional[str] = None
    driver_phone: Optional[str] = None
    vehicle_number: Optional[str] = None
    transport_status: Optional[str] = None  # waiting, loaded, onTheWay, reached, delivered, pickup, in_transit
    pickup_location: Optional[str] = None
    collection_center: Optional[str] = None

class PaymentConfirmRequest(BaseModel):
    inspector_name: Optional[str] = ""
    inspector_designation: Optional[str] = ""
    notes: Optional[str] = "টাকা পাওয়া গেছে - কনফার্মড"

class InspectorAssignRequest(BaseModel):
    inspector_name: str
    inspector_designation: Optional[str] = "কোয়ালিটি কন্ট্রোল অফিসার"
    notes: Optional[str] = ""

class QualityVerificationUpdate(BaseModel):
    actual_weight: float
    quality_grade: str = "গ্রেড A (প্রিমিয়াম মান)"
    verified_by: Optional[str] = "সেলিম রেজা (ইনস্পেক্টর)"
    inspector_name: Optional[str] = None
    inspector_designation: Optional[str] = None
    verification_notes: Optional[str] = "পণ্য ফ্রেশ ও মানসম্মত"

class QualityRejectRequest(BaseModel):
    rejection_reason: str = "কালেকশন হাবে পরীক্ষার পর পণ্যের মান সন্তোষজনক পাওয়া যায়নি"
    inspector_name: Optional[str] = "সেলিম রেজা"
    inspector_designation: Optional[str] = "সিনিয়র কোয়ালিটি অফিসার"

class RefundProcessRequest(BaseModel):
    refund_notes: Optional[str] = "পণ্য বাতিল হওয়ায় ক্রেতাকে ২০% ডিপোজিট রিফান্ড দেওয়া হয়েছে"

class FarmerPayoutRequest(BaseModel):
    notes: Optional[str] = "কৃষকের বিকাশ/ব্যাংক অ্যাকাউন্টে টাকা পরিশোধ করা হয়েছে"
    transaction_id: Optional[str] = ""

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
    product_amount: Optional[float] = None
    buyer_service_fee: Optional[float] = 0.0
    buyer_total_amount: Optional[float] = None
    farmer_service_fee: Optional[float] = 0.0
    farmer_payout_amount: Optional[float] = None
    farmer_payout_status: Optional[str] = "unpaid"
    farmer_payout_notes: Optional[str] = ""
    farmer_payout_date: Optional[str] = ""
    deposit_required: float
    is_deposit_paid: bool
    payment_status: str = "unpaid"
    payment_verification_notes: Optional[str] = ""
    order_status: str
    delivery_location: str
    expected_delivery_date: str
    pickup_location: str
    collection_center: str
    transport_agency: Optional[str] = ""
    driver_name: str
    driver_phone: str
    vehicle_number: str
    transport_status: str
    inspector_name: Optional[str] = ""
    inspector_designation: Optional[str] = ""
    actual_weight: Optional[float] = None
    quality_grade: Optional[str] = None
    verified_by: Optional[str] = None
    verification_notes: Optional[str] = None
    is_quality_verified: bool = False
    is_quality_passed: Optional[bool] = None
    rejection_reason: Optional[str] = ""
    refund_status: str = "none"
    refund_amount: float = 0.0
    refund_notes: Optional[str] = ""
    has_dispute: bool
    is_rated: bool
    created_at: str

    class Config:
        from_attributes = True

