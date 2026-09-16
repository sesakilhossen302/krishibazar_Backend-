from pydantic import BaseModel
from typing import Optional

class PaymentSettingBase(BaseModel):
    id: str  # 'bkash', 'nagad', 'rocket'
    name: str  # 'বিকাশ', 'নগদ', 'রকেট'
    account_number: str = ""
    account_type: str = "Personal"
    is_active: bool = False
    instructions: Optional[str] = ""

class PaymentSettingUpdate(BaseModel):
    account_number: Optional[str] = None
    account_type: Optional[str] = None
    is_active: Optional[bool] = None
    instructions: Optional[str] = None

class PaymentSettingResponse(PaymentSettingBase):
    updated_at: Optional[str] = ""

    class Config:
        from_attributes = True


class DeliveryChartBase(BaseModel):
    product_name: str = "সকল পণ্য"
    category: str = "সকল ক্যাটাগরি"
    min_quantity: float = 0.0
    max_quantity: float = 100000.0
    unit: str = "কেজি (kg)"
    delivery_charge: float = 0.0
    charge_type: str = "fixed"  # 'fixed' or 'per_unit'
    description: Optional[str] = ""
    is_active: bool = True


class DeliveryChartCreate(DeliveryChartBase):
    id: Optional[str] = None


class DeliveryChartUpdate(BaseModel):
    product_name: Optional[str] = None
    category: Optional[str] = None
    min_quantity: Optional[float] = None
    max_quantity: Optional[float] = None
    unit: Optional[str] = None
    delivery_charge: Optional[float] = None
    charge_type: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None


class DeliveryChartResponse(DeliveryChartBase):
    id: str
    created_at: Optional[str] = ""
    updated_at: Optional[str] = ""

    class Config:
        from_attributes = True

