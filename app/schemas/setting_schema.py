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
