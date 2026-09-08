from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid

from app.database import get_db
from app.models.product_model import Product
from app.models.user_model import User
from app.schemas.product_schema import ProductCreate, ProductUpdate, ProductResponse
from app.utils import get_current_user

router = APIRouter(prefix="/products", tags=["Products (কৃষি পণ্য)"])


@router.get("/", response_model=List[ProductResponse])
def get_products(
    category: Optional[str] = None,
    district: Optional[str] = None,
    farmer_id: Optional[str] = None,
    verified_only: bool = False,
    search: Optional[str] = None,
    min_price: Optional[float] = None,
    max_price: Optional[float] = None,
    db: Session = Depends(get_db)
):
    """
    Get active products with flexible filters (Category, District, Search query, Price range).
    """
    query = db.query(Product).filter(Product.status == "active")

    if category and category != "all":
        query = query.filter(Product.category == category)
    if district:
        query = query.filter(Product.farmer_district.contains(district))
    if farmer_id:
        query = query.filter(Product.farmer_id == farmer_id)
    if verified_only:
        query = query.filter(Product.farmer_verified == True)
    if min_price is not None:
        query = query.filter(Product.expected_price >= min_price)
    if max_price is not None:
        query = query.filter(Product.expected_price <= max_price)
    if search:
        query = query.filter(Product.title.contains(search))

    return query.order_by(Product.created_at.desc()).all()


@router.get("/my-products", response_model=List[ProductResponse])
def get_my_products(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get all products posted by the currently authenticated farmer.
    """
    return db.query(Product).filter(
        Product.farmer_id == current_user.id
    ).order_by(Product.created_at.desc()).all()


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Create a new agricultural product posting (by Farmer).
    """
    new_id = f"prod_{uuid.uuid4().hex[:8]}"
    db_product = Product(
        id=new_id,
        farmer_id=current_user.id,
        farmer_name=current_user.name,
        farmer_district=current_user.district,
        farmer_verified=(current_user.verification_status == "verified"),
        title=product_in.title,
        category=product_in.category,
        quantity=product_in.quantity,
        remaining_quantity=product_in.quantity,
        unit=product_in.unit,
        expected_price=product_in.expected_price,
        min_price=product_in.min_price,
        location=product_in.location or current_user.address,
        available_date=product_in.available_date,
        harvest_date=product_in.harvest_date,
        quality_grade=product_in.quality_grade,
        description=product_in.description or "",
        image_url=product_in.image_url or "",
        video_url=product_in.video_url or "",
        video_note=product_in.video_note or "",
        status="active",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return db_product


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information for a single product by ID.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return product


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    product_update: ProductUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update product details or stock (only by product owner).
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="পণ্যটি পাওয়া যায়নি।")

    if product.farmer_id != current_user.id:
        raise HTTPException(status_code=403, detail="শুধুমাত্র পণ্যের মালিক এটি এডিট করতে পারবেন।")

    update_data = product_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        if value is not None:
            setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return product


@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Delete or archive a product (only by product owner).
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="পণ্যটি পাওয়া যায়নি।")

    if product.farmer_id != current_user.id:
        raise HTTPException(status_code=403, detail="অনুমতি নেই।")

    product.status = "archived"
    db.commit()
    return {"success": True, "message": "পণ্যটি সফলভাবে আর্কাইভ/মুছে ফেলা হয়েছে।"}
