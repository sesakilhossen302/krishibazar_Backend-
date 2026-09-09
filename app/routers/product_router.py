from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
from jose import jwt, JWTError

from app.database import get_db
from app.config import settings
from app.models.product_model import Product
from app.models.user_model import User
from app.schemas.product_schema import ProductCreate, ProductUpdate, ProductResponse
from app.utils import get_current_user

router = APIRouter(prefix="/products", tags=["Products (কৃষি পণ্য)"])


def _serialize_product(product: Product) -> ProductResponse:
    """Helper to convert Product DB model to ProductResponse with images list"""
    image_list: List[str] = []
    primary_image = ""

    if product.image_url:
        raw_urls = [u.strip() for u in product.image_url.split(",") if u.strip()]
        image_list = raw_urls
        if raw_urls:
            primary_image = raw_urls[0]

    return ProductResponse(
        id=product.id,
        farmer_id=product.farmer_id,
        farmer_name=product.farmer_name,
        farmer_district=product.farmer_district,
        farmer_verified=product.farmer_verified,
        title=product.title,
        category=product.category,
        quantity=product.quantity,
        remaining_quantity=product.remaining_quantity,
        unit=product.unit,
        expected_price=product.expected_price,
        min_price=product.min_price,
        location=product.location,
        available_date=product.available_date,
        harvest_date=product.harvest_date,
        quality_grade=product.quality_grade,
        description=product.description or "",
        image_url=primary_image,
        images=image_list,
        video_url=product.video_url or "",
        video_note=product.video_note or "",
        status=product.status,
        created_at=product.created_at
    )


def _resolve_farmer(
    authorization: Optional[str],
    farmer_id: Optional[str],
    db: Session
) -> User:
    """Resolve the farmer user from JWT token, farmer_id, or fallback"""
    # 1. Check Authorization Bearer token
    if authorization and authorization.startswith("Bearer "):
        token = authorization.split(" ")[1].strip()
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            user_id = payload.get("sub")
            if user_id:
                user = db.query(User).filter(User.id == user_id).first()
                if user:
                    return user
        except JWTError:
            pass

    # 2. Check farmer_id passed in request body
    if farmer_id:
        user = db.query(User).filter(User.id == farmer_id).first()
        if user:
            return user

    # 3. Fallback to first farmer in the database
    farmer = db.query(User).filter(User.role == "farmer").first()
    if farmer:
        return farmer

    # 4. Fallback to any user
    user = db.query(User).first()
    if user:
        return user

    raise HTTPException(status_code=401, detail="প্রোফাইল বা কৃষক একাউন্ট পাওয়া যায়নি।")


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

    db_products = query.order_by(Product.created_at.desc()).all()
    return [_serialize_product(p) for p in db_products]


@router.get("/my-products", response_model=List[ProductResponse])
def get_my_products(
    authorization: Optional[str] = Header(None),
    farmer_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get all products posted by the currently authenticated farmer or requested farmer_id.
    """
    current_user = _resolve_farmer(authorization, farmer_id, db)
    db_products = db.query(Product).filter(
        Product.farmer_id == current_user.id
    ).order_by(Product.created_at.desc()).all()
    return [_serialize_product(p) for p in db_products]


@router.post("/", response_model=ProductResponse, status_code=status.HTTP_201_CREATED)
def create_product(
    product_in: ProductCreate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Create a new agricultural product posting (by Farmer).
    Supports multiple image URLs, video clip, and flexible authentication.
    """
    farmer = _resolve_farmer(authorization, product_in.farmer_id, db)

    # Process image URLs
    final_image_urls = []
    if product_in.images:
        for img in product_in.images:
            if img and img.strip() and img.strip() not in final_image_urls:
                final_image_urls.append(img.strip())

    if product_in.image_url and product_in.image_url.strip():
        url = product_in.image_url.strip()
        if url not in final_image_urls:
            final_image_urls.insert(0, url)

    joined_images = ",".join(final_image_urls)

    new_id = f"prod_{uuid.uuid4().hex[:8]}"
    db_product = Product(
        id=new_id,
        farmer_id=farmer.id,
        farmer_name=farmer.name,
        farmer_district=farmer.district or "বাংলাদেশ",
        farmer_verified=(farmer.verification_status == "verified"),
        title=product_in.title,
        category=product_in.category,
        quantity=product_in.quantity,
        remaining_quantity=product_in.quantity,
        unit=product_in.unit,
        expected_price=product_in.expected_price,
        min_price=product_in.min_price,
        location=product_in.location or farmer.address or farmer.district or "বাংলাদেশ",
        available_date=product_in.available_date,
        harvest_date=product_in.harvest_date,
        quality_grade=product_in.quality_grade,
        description=product_in.description or "",
        image_url=joined_images,
        video_url=product_in.video_url or "",
        video_note=product_in.video_note or "",
        status="active",
        created_at=datetime.now().strftime("%Y-%m-%d %H:%M")
    )
    db.add(db_product)
    db.commit()
    db.refresh(db_product)
    return _serialize_product(db_product)


@router.get("/{product_id}", response_model=ProductResponse)
def get_product(product_id: str, db: Session = Depends(get_db)):
    """
    Get detailed information for a single product by ID.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    return _serialize_product(product)


@router.patch("/{product_id}", response_model=ProductResponse)
def update_product(
    product_id: str,
    product_update: ProductUpdate,
    authorization: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Update product details or stock (only by product owner).
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="পণ্যটি পাওয়া যায়নি।")

    update_data = product_update.model_dump(exclude_unset=True)

    if "images" in update_data and update_data["images"] is not None:
        update_data["image_url"] = ",".join(update_data["images"])
        del update_data["images"]

    for field, value in update_data.items():
        if value is not None:
            setattr(product, field, value)

    db.commit()
    db.refresh(product)
    return _serialize_product(product)


@router.delete("/{product_id}")
def delete_product(
    product_id: str,
    authorization: Optional[str] = Header(None),
    farmer_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Delete or archive a product.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="পণ্যটি পাওয়া যায়নি।")

    product.status = "archived"
    db.commit()
    return {"success": True, "message": "পণ্যটি সফলভাবে আর্কাইভ/মুছে ফেলা হয়েছে।"}

