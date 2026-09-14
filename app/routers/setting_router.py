from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from datetime import datetime

from app.database import get_db
from app.models.setting_model import PaymentSetting
from app.schemas.setting_schema import (
    PaymentSettingResponse,
    PaymentSettingUpdate,
    PaymentSettingBase
)

router = APIRouter(prefix="/settings", tags=["System Settings (পেমেন্ট ও সিস্টেম সেটিংস)"])

DEFAULT_METHODS = [
    {
        "id": "bkash",
        "name": "বিকাশ",
        "account_number": "01712-345678",
        "account_type": "Merchant",
        "is_active": True,
        "instructions": "বিকাশ মার্চেন্ট নম্বরে পেমেন্ট করুন অথবা রেফারেন্সে অর্ডার নং দিন।"
    },
    {
        "id": "nagad",
        "name": "নগদ",
        "account_number": "01812-345678",
        "account_type": "Personal",
        "is_active": True,
        "instructions": "নগদ পার্সোনাল নম্বরে সেন্ড মানি করে TrxID ও স্ক্রিনশট দিন।"
    },
    {
        "id": "rocket",
        "name": "রকেট",
        "account_number": "01912-345678-9",
        "account_type": "Personal",
        "is_active": False,
        "instructions": "রকেট নম্বরে টাকা পাঠিয়ে ট্রানজেকশন আইডি দিন।"
    },
]

def ensure_default_settings(db: Session):
    for item in DEFAULT_METHODS:
        existing = db.query(PaymentSetting).filter(PaymentSetting.id == item["id"]).first()
        if not existing:
            setting = PaymentSetting(
                id=item["id"],
                name=item["name"],
                account_number=item["account_number"],
                account_type=item["account_type"],
                is_active=item["is_active"],
                instructions=item["instructions"],
                updated_at=datetime.now().strftime("%Y-%m-%d %H:%M")
            )
            db.add(setting)
    db.commit()

@router.get("/payment-methods", response_model=List[PaymentSettingResponse])
def get_payment_methods(db: Session = Depends(get_db)):
    """
    Get all payment methods with On/Off state, phone numbers and account types.
    """
    ensure_default_settings(db)
    return db.query(PaymentSetting).all()

@router.post("/payment-methods", response_model=PaymentSettingResponse)
def save_payment_method(setting_in: PaymentSettingBase, db: Session = Depends(get_db)):
    """
    Admin adds or updates a payment method.
    """
    setting = db.query(PaymentSetting).filter(PaymentSetting.id == setting_in.id).first()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    if not setting:
        setting = PaymentSetting(
            id=setting_in.id,
            name=setting_in.name,
            account_number=setting_in.account_number,
            account_type=setting_in.account_type,
            is_active=setting_in.is_active,
            instructions=setting_in.instructions or "",
            updated_at=now_str
        )
        db.add(setting)
    else:
        setting.name = setting_in.name
        setting.account_number = setting_in.account_number
        setting.account_type = setting_in.account_type
        setting.is_active = setting_in.is_active
        if setting_in.instructions is not None:
            setting.instructions = setting_in.instructions
        setting.updated_at = now_str

    db.commit()
    db.refresh(setting)
    return setting

@router.patch("/payment-methods/{method_id}", response_model=PaymentSettingResponse)
def update_payment_method(method_id: str, update_in: PaymentSettingUpdate, db: Session = Depends(get_db)):
    """
    Toggle on/off, change number, or update instructions for a specific payment method.
    """
    setting = db.query(PaymentSetting).filter(PaymentSetting.id == method_id).first()
    if not setting:
        raise HTTPException(status_code=404, detail="পেমেন্ট মেথড পাওয়া যায়নি।")

    if update_in.account_number is not None:
        setting.account_number = update_in.account_number
    if update_in.account_type is not None:
        setting.account_type = update_in.account_type
    if update_in.is_active is not None:
        setting.is_active = update_in.is_active
    if update_in.instructions is not None:
        setting.instructions = update_in.instructions

    setting.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    db.commit()
    db.refresh(setting)
    return setting
