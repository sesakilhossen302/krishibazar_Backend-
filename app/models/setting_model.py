from sqlalchemy import Column, String, Boolean, Text, Float
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


class DeliveryChart(Base):
    __tablename__ = "delivery_charts"

    id = Column(String, primary_key=True, index=True)
    product_name = Column(String, nullable=False, default="সকল পণ্য")  # e.g. 'আলু', 'পেঁয়াজ', 'সকল পণ্য'
    category = Column(String, default="সকল ক্যাটাগরি")  # 'সবজি', 'ফল', 'শস্য', 'সকল ক্যাটাগরি'
    min_quantity = Column(Float, default=0.0)
    max_quantity = Column(Float, default=100000.0)
    unit = Column(String, default="কেজি (kg)")  # 'কেজি (kg)', 'মণ (mon)'
    delivery_charge = Column(Float, nullable=False, default=0.0)
    charge_type = Column(String, default="fixed")  # 'fixed' or 'per_unit'
    description = Column(String, default="")
    is_active = Column(Boolean, default=True)
    created_at = Column(String, default="")
    updated_at = Column(String, default="")

