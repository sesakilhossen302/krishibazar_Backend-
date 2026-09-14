from sqlalchemy import Column, String, Boolean, Text
from app.database import Base

class PaymentSetting(Base):
    __tablename__ = "payment_settings"

    id = Column(String, primary_key=True, index=True)  # 'bkash', 'nagad', 'rocket'
    name = Column(String, nullable=False)  # 'বিকাশ', 'নগদ', 'রকেট'
    account_number = Column(String, default="")
    account_type = Column(String, default="Personal")  # 'Personal', 'Merchant', 'Agent'
    is_active = Column(Boolean, default=False)
    instructions = Column(Text, default="")
    updated_at = Column(String, default="")
