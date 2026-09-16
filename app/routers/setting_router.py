import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime

from app.database import get_db
from app.models.setting_model import PaymentSetting, DeliveryChart
from app.schemas.setting_schema import (
    PaymentSettingResponse,
    PaymentSettingUpdate,
    PaymentSettingBase,
    DeliveryChartResponse,
    DeliveryChartCreate,
    DeliveryChartUpdate,
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
        "is_active": True,
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


# ============================================================================
# DELIVERY CHART (ডেলিভারি চার্জ চার্ট)
# ============================================================================

DEFAULT_DELIVERY_CHARTS = [
    {
        "id": "dc_potato_kg_1",
        "product_name": "আলু",
        "category": "সবজি",
        "min_quantity": 0.0,
        "max_quantity": 20.0,
        "unit": "কেজি (kg)",
        "delivery_charge": 80.0,
        "charge_type": "fixed",
        "description": "আলু ০-২০ কেজি ফিক্সড ডেলিভারি ফি"
    },
    {
        "id": "dc_potato_kg_2",
        "product_name": "আলু",
        "category": "সবজি",
        "min_quantity": 20.0,
        "max_quantity": 50.0,
        "unit": "কেজি (kg)",
        "delivery_charge": 150.0,
        "charge_type": "fixed",
        "description": "আলু ২০-৫০ কেজি ফিক্সড ডেলিভারি ফি"
    },
    {
        "id": "dc_potato_mon_1",
        "product_name": "আলু",
        "category": "সবজি",
        "min_quantity": 1.0,
        "max_quantity": 10.0,
        "unit": "মণ (mon)",
        "delivery_charge": 400.0,
        "charge_type": "fixed",
        "description": "আলু ১-১০ মণ ফিক্সড ডেলিভারি ফি"
    },
    {
        "id": "dc_potato_mon_2",
        "product_name": "আলু",
        "category": "সবজি",
        "min_quantity": 10.0,
        "max_quantity": 50.0,
        "unit": "মণ (mon)",
        "delivery_charge": 1500.0,
        "charge_type": "fixed",
        "description": "আলু ১০-৫০ মণ ফিক্সড ডেলিভারি ফি"
    },
    {
        "id": "dc_potato_mon_3",
        "product_name": "আলু",
        "category": "সবজি",
        "min_quantity": 50.0,
        "max_quantity": 1000.0,
        "unit": "মণ (mon)",
        "delivery_charge": 35.0,
        "charge_type": "per_unit",
        "description": "আলু ৫০+ মণ প্রতি মণ ৩৫ টাকা"
    },
    {
        "id": "dc_default_kg_1",
        "product_name": "সকল পণ্য",
        "category": "সকল ক্যাটাগরি",
        "min_quantity": 0.0,
        "max_quantity": 20.0,
        "unit": "কেজি (kg)",
        "delivery_charge": 70.0,
        "charge_type": "fixed",
        "description": "সাধারণ পণ্য ০-২০ কেজি ডেলিভারি ফি"
    },
    {
        "id": "dc_default_kg_2",
        "product_name": "সকল পণ্য",
        "category": "সকল ক্যাটাগরি",
        "min_quantity": 20.0,
        "max_quantity": 50.0,
        "unit": "কেজি (kg)",
        "delivery_charge": 140.0,
        "charge_type": "fixed",
        "description": "সাধারণ পণ্য ২০-৫০ কেজি ডেলিভারি ফি"
    },
    {
        "id": "dc_default_mon_1",
        "product_name": "সকল পণ্য",
        "category": "সকল ক্যাটাগরি",
        "min_quantity": 1.0,
        "max_quantity": 50.0,
        "unit": "মণ (mon)",
        "delivery_charge": 1200.0,
        "charge_type": "fixed",
        "description": "সাধারণ পণ্য ১-৫০ মণ ফিক্সড ডেলিভারি ফি"
    },
    {
        "id": "dc_default_mon_2",
        "product_name": "সকল পণ্য",
        "category": "সকল ক্যাটাগরি",
        "min_quantity": 50.0,
        "max_quantity": 2000.0,
        "unit": "মণ (mon)",
        "delivery_charge": 30.0,
        "charge_type": "per_unit",
        "description": "সাধারণ পণ্য ৫০+ মণ প্রতি মণ ৩০ টাকা"
    },
]


def ensure_default_delivery_charts(db: Session):
    count = db.query(DeliveryChart).count()
    if count == 0:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
        for item in DEFAULT_DELIVERY_CHARTS:
            chart = DeliveryChart(
                id=item["id"],
                product_name=item["product_name"],
                category=item["category"],
                min_quantity=item["min_quantity"],
                max_quantity=item["max_quantity"],
                unit=item["unit"],
                delivery_charge=item["delivery_charge"],
                charge_type=item["charge_type"],
                description=item["description"],
                is_active=True,
                created_at=now_str,
                updated_at=now_str
            )
            db.add(chart)
        db.commit()


def calculate_delivery_charge_internal(
    db: Session,
    product_name: str,
    quantity: float,
    unit: str,
    category: str = ""
) -> float:
    ensure_default_delivery_charts(db)
    charts = db.query(DeliveryChart).filter(DeliveryChart.is_active == True).all()
    if not charts:
        return 0.0

    p_norm = (product_name or "").strip().lower()
    c_norm = (category or "").strip().lower()
    u_is_mon = any(k in (unit or "").lower() for k in ["মণ", "মন", "mon"])

    matched_rule: Optional[DeliveryChart] = None

    # Priority 1: Matching product title + matching unit + quantity in range
    for r in charts:
        r_unit_is_mon = any(k in r.unit.lower() for k in ["মণ", "মন", "mon"])
        if r_unit_is_mon == u_is_mon:
            r_name = r.product_name.strip().lower()
            if r_name and r_name not in ["সকল পণ্য", "all products", "all"]:
                if r_name in p_norm or p_norm in r_name:
                    if r.min_quantity <= quantity <= r.max_quantity:
                        matched_rule = r
                        break

    # Priority 2: Category match + matching unit + quantity in range
    if not matched_rule and c_norm:
        for r in charts:
            r_unit_is_mon = any(k in r.unit.lower() for k in ["মণ", "মন", "mon"])
            if r_unit_is_mon == u_is_mon:
                r_cat = (r.category or "").strip().lower()
                if r_cat and r_cat not in ["সকল ক্যাটাগরি", "all"]:
                    if r_cat in c_norm or c_norm in r_cat:
                        if r.min_quantity <= quantity <= r.max_quantity:
                            matched_rule = r
                            break

    # Priority 3: "সকল পণ্য" + matching unit + quantity in range
    if not matched_rule:
        for r in charts:
            r_unit_is_mon = any(k in r.unit.lower() for k in ["মণ", "মন", "mon"])
            if r_unit_is_mon == u_is_mon:
                if r.product_name.strip() in ["সকল পণ্য", "All Products", "all", ""]:
                    if r.min_quantity <= quantity <= r.max_quantity:
                        matched_rule = r
                        break

    # Priority 4: Any matching unit rule
    if not matched_rule:
        for r in charts:
            r_unit_is_mon = any(k in r.unit.lower() for k in ["মণ", "মন", "mon"])
            if r_unit_is_mon == u_is_mon:
                matched_rule = r
                break

    if not matched_rule:
        return round(quantity * 30.0, 2) if u_is_mon else round(quantity * 2.0, 2)

    if matched_rule.charge_type == "per_unit":
        return round(matched_rule.delivery_charge * quantity, 2)
    else:
        return round(matched_rule.delivery_charge, 2)


@router.get("/delivery-charts", response_model=List[DeliveryChartResponse])
def get_delivery_charts(db: Session = Depends(get_db)):
    """
    List all delivery chart rules configured by Admin.
    """
    ensure_default_delivery_charts(db)
    return db.query(DeliveryChart).order_by(DeliveryChart.created_at.asc()).all()


@router.post("/delivery-charts", response_model=DeliveryChartResponse)
def create_delivery_chart(chart_in: DeliveryChartCreate, db: Session = Depends(get_db)):
    """
    Admin creates a new delivery chart rule.
    """
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_id = (chart_in.id.strip() if chart_in.id and chart_in.id.strip() else None) or f"dc_{uuid.uuid4().hex[:8]}"
    chart = DeliveryChart(
        id=new_id,
        product_name=chart_in.product_name.strip() or "সকল পণ্য",
        category=chart_in.category.strip() or "সকল ক্যাটাগরি",
        min_quantity=chart_in.min_quantity,
        max_quantity=chart_in.max_quantity,
        unit=chart_in.unit,
        delivery_charge=chart_in.delivery_charge,
        charge_type=chart_in.charge_type,
        description=chart_in.description or "",
        is_active=chart_in.is_active,
        created_at=now_str,
        updated_at=now_str
    )
    db.add(chart)
    db.commit()
    db.refresh(chart)
    return chart


@router.patch("/delivery-charts/{chart_id}", response_model=DeliveryChartResponse)
def update_delivery_chart(chart_id: str, update_in: DeliveryChartUpdate, db: Session = Depends(get_db)):
    """
    Admin updates an existing delivery chart rule.
    """
    chart = db.query(DeliveryChart).filter(DeliveryChart.id == chart_id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="ডেলিভারি চার্ট পাওয়া যায়নি।")

    if update_in.product_name is not None:
        chart.product_name = update_in.product_name
    if update_in.category is not None:
        chart.category = update_in.category
    if update_in.min_quantity is not None:
        chart.min_quantity = update_in.min_quantity
    if update_in.max_quantity is not None:
        chart.max_quantity = update_in.max_quantity
    if update_in.unit is not None:
        chart.unit = update_in.unit
    if update_in.delivery_charge is not None:
        chart.delivery_charge = update_in.delivery_charge
    if update_in.charge_type is not None:
        chart.charge_type = update_in.charge_type
    if update_in.description is not None:
        chart.description = update_in.description
    if update_in.is_active is not None:
        chart.is_active = update_in.is_active

    chart.updated_at = datetime.now().strftime("%Y-%m-%d %H:%M")
    db.commit()
    db.refresh(chart)
    return chart


@router.delete("/delivery-charts/{chart_id}")
def delete_delivery_chart(chart_id: str, db: Session = Depends(get_db)):
    """
    Admin deletes a delivery chart rule.
    """
    chart = db.query(DeliveryChart).filter(DeliveryChart.id == chart_id).first()
    if not chart:
        raise HTTPException(status_code=404, detail="ডেলিভারি চার্ট পাওয়া যায়নি।")

    db.delete(chart)
    db.commit()
    return {"success": True, "message": "ডেলিভারি চার্ট সফলভাবে মুছে ফেলা হয়েছে।"}


@router.get("/calculate-delivery-charge")
def calculate_delivery_charge_endpoint(
    product_name: str = Query("আলু"),
    quantity: float = Query(1.0),
    unit: str = Query("কেজি (kg)"),
    category: Optional[str] = Query(""),
    db: Session = Depends(get_db)
):
    """
    Dynamically calculate delivery charge for given product and quantity using active delivery chart.
    """
    charge = calculate_delivery_charge_internal(
        db=db,
        product_name=product_name,
        quantity=quantity,
        unit=unit,
        category=category or ""
    )
    return {
        "product_name": product_name,
        "quantity": quantity,
        "unit": unit,
        "delivery_charge": charge,
        "currency": "৳"
    }

