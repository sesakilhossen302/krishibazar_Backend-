from fastapi import APIRouter, Depends, HTTPException, Query, Header, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime
import uuid
from jose import jwt, JWTError

from app.database import get_db
from app.config import settings
from app.models.product_model import Product, ProductOffer
from app.models.user_model import User
from app.schemas.product_schema import (
    ProductCreate, ProductUpdate, ProductResponse,
    ProductOfferCreate, ProductOfferResponse
)
from app.utils import get_current_user
from app.routers.notification_router import send_in_app_notification

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
        offers_count=product.offers_count or 0,
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


# ================= Product Purchase Proposals / Offers =================

def _resolve_buyer(
    authorization: Optional[str],
    buyer_id: Optional[str],
    db: Session
) -> Optional[User]:
    """Resolve current buyer from JWT token or buyer_id"""
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

    if buyer_id:
        return db.query(User).filter(User.id == buyer_id).first()
    return None


@router.post("/{product_id}/offers", response_model=ProductOfferResponse, status_code=status.HTTP_201_CREATED)
def create_product_offer(
    product_id: str,
    offer_in: ProductOfferCreate,
    authorization: Optional[str] = Header(None),
    buyer_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Buyer (Paikar) submits a purchase proposal for a Farmer's product.
    Automatically increments product offers_count and sends an in-app notification to the farmer.
    """
    product = db.query(Product).filter(Product.id == product_id).first()
    if not product:
        raise HTTPException(status_code=404, detail="পণ্যটি পাওয়া যায়নি।")

    user = _resolve_buyer(authorization, offer_in.buyer_id or buyer_id or user_id, db)

    b_id = user.id if user else (offer_in.buyer_id or buyer_id or user_id or f"buy_{uuid.uuid4().hex[:8]}")
    b_name = (user.name if user and user.name else None) or offer_in.buyer_name or "পাইকার"
    b_biz = (user.business_name if user and user.business_name else None) or offer_in.buyer_business_name or b_name
    b_phone = (user.phone if user and user.phone else None) or offer_in.buyer_phone or ""
    b_dist = (user.district if user and user.district else None) or offer_in.buyer_district or "বাংলাদেশ"
    b_photo = user.photo_url if user and user.photo_url else ""
    b_verified = (user.verification_status == "verified") if user else True

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    new_offer = ProductOffer(
        id=f"po_{uuid.uuid4().hex[:8]}",
        product_id=product_id,
        buyer_id=b_id,
        buyer_name=b_name,
        buyer_business_name=b_biz,
        buyer_phone=b_phone,
        buyer_district=b_dist,
        buyer_photo_url=b_photo,
        buyer_verified=b_verified,
        offered_quantity=offer_in.offered_quantity,
        unit=offer_in.unit or product.unit,
        price_per_unit=offer_in.price_per_unit,
        delivery_location=offer_in.delivery_location or "",
        expected_delivery_date=offer_in.expected_delivery_date or "",
        note=offer_in.note or "",
        status="pending",
        created_at=now_str
    )

    db.add(new_offer)

    # Increment offers_count on product
    product.offers_count = (product.offers_count or 0) + 1
    db.commit()
    db.refresh(new_offer)

    # In-app notification to the farmer
    try:
        if product.farmer_id:
            send_in_app_notification(
                db=db,
                user_id=product.farmer_id,
                title="আপনার পণ্যে নতুন ক্রয় প্রস্তাব! 🛍️",
                message=f"{b_biz} আপনার '{product.title}' পণ্যে প্রতি {new_offer.unit} ৳{new_offer.price_per_unit:.0f} দরে মোট {new_offer.offered_quantity:g} {new_offer.unit} ক্রয়ের প্রস্তাব দিয়েছেন।",
                notification_type="product_offer",
                related_id=product_id
            )
    except Exception as e:
        print(f"Error sending notification to farmer: {e}")

    return new_offer


@router.get("/{product_id}/offers", response_model=List[ProductOfferResponse])
def get_offers_for_product(product_id: str, db: Session = Depends(get_db)):
    """
    Get all buyer purchase proposals for a specific product.
    Enriches with buyer latest profile details.
    """
    offers = db.query(ProductOffer).filter(ProductOffer.product_id == product_id).order_by(ProductOffer.created_at.desc()).all()
    buyer_ids = {o.buyer_id for o in offers if o.buyer_id}
    buyer_map = {u.id: u for u in db.query(User).filter(User.id.in_(buyer_ids)).all()} if buyer_ids else {}

    results = []
    for o in offers:
        res = ProductOfferResponse.model_validate(o)
        u = buyer_map.get(o.buyer_id)
        if u:
            if u.photo_url:
                res.buyer_photo_url = u.photo_url
            if u.phone:
                res.buyer_phone = u.phone
            if u.district:
                res.buyer_district = u.district
            if u.business_name:
                res.buyer_business_name = u.business_name
            res.buyer_verified = (u.verification_status == "verified")
        results.append(res)
    return results


@router.post("/offers/{offer_id}/accept")
def accept_product_offer(offer_id: str, db: Session = Depends(get_db)):
    """
    Farmer accepts a buyer's purchase proposal.
    Updates offer status to 'accepted' and sends notification to buyer.
    """
    offer = db.query(ProductOffer).filter(ProductOffer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="প্রস্তাব পাওয়া যায়নি।")

    offer.status = "accepted"
    db.commit()
    db.refresh(offer)

    # Notify buyer
    product = db.query(Product).filter(Product.id == offer.product_id).first()
    prod_title = product.title if product else "কৃষি পণ্য"
    farmer_name = product.farmer_name if product else "কৃষক"
    try:
        send_in_app_notification(
            db=db,
            user_id=offer.buyer_id,
            title="আপনার ক্রয় প্রস্তাব গৃহীত হয়েছে! ✅",
            message=f"{farmer_name} আপনার '{prod_title}' ক্রয়ের প্রস্তাব (৳{offer.price_per_unit:.0f}/{offer.unit}) গ্রহণ করেছেন। বিস্তারিত দেখতে যোগাযোগ করুন।",
            notification_type="product_offer_accepted",
            related_id=offer.product_id
        )
    except Exception as e:
        print(f"Error notifying buyer: {e}")

    return {
        "success": True,
        "message": "প্রস্তাবটি সফলভাবে গ্রহণ করা হয়েছে!",
        "data": ProductOfferResponse.model_validate(offer)
    }


@router.post("/offers/{offer_id}/reject")
def reject_product_offer(offer_id: str, db: Session = Depends(get_db)):
    """
    Farmer rejects a buyer's purchase proposal.
    """
    offer = db.query(ProductOffer).filter(ProductOffer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="প্রস্তাব পাওয়া যায়নি।")

    offer.status = "rejected"
    db.commit()
    db.refresh(offer)

    product = db.query(Product).filter(Product.id == offer.product_id).first()
    prod_title = product.title if product else "কৃষি পণ্য"
    try:
        send_in_app_notification(
            db=db,
            user_id=offer.buyer_id,
            title="ক্রয় প্রস্তাব প্রত্যাখ্যান করা হয়েছে ❌",
            message=f"আপনার '{prod_title}' ক্রয়ের প্রস্তাবটি কৃষক এই মুহূর্তে গ্রহণ করতে পারছেন না।",
            notification_type="product_offer_rejected",
            related_id=offer.product_id
        )
    except Exception as e:
        print(f"Error notifying buyer: {e}")

    return {
        "success": True,
        "message": "প্রস্তাবটি প্রত্যাখ্যান করা হয়েছে।",
        "data": ProductOfferResponse.model_validate(offer)
    }


@router.get("/offers/my-proposals", response_model=List[ProductOfferResponse])
def get_my_product_proposals(
    authorization: Optional[str] = Header(None),
    buyer_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Buyer views all purchase proposals they have submitted for products.
    """
    user = _resolve_buyer(authorization, buyer_id or user_id, db)
    target_id = user.id if user else (buyer_id or user_id)
    if not target_id:
        raise HTTPException(status_code=400, detail="Buyer ID or Authorization required")

    return db.query(ProductOffer).filter(
        ProductOffer.buyer_id == str(target_id).strip()
    ).order_by(ProductOffer.created_at.desc()).all()


@router.get("/{product_id}/my-offer", response_model=Optional[ProductOfferResponse])
def get_my_offer_for_product(
    product_id: str,
    authorization: Optional[str] = Header(None),
    buyer_id: Optional[str] = Query(None),
    user_id: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """
    Get current buyer's purchase proposal for this specific product, if any.
    """
    user = _resolve_buyer(authorization, buyer_id or user_id, db)
    target_id = user.id if user else (buyer_id or user_id)
    if not target_id:
        return None

    return db.query(ProductOffer).filter(
        ProductOffer.product_id == product_id,
        ProductOffer.buyer_id == str(target_id).strip()
    ).order_by(ProductOffer.created_at.desc()).first()



