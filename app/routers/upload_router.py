import os
import uuid
from typing import List
from fastapi import APIRouter, UploadFile, File, HTTPException, status
from fastapi.responses import JSONResponse

router = APIRouter(prefix="/upload", tags=["Uploads"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)

IMAGE_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp", ".pdf"]
VIDEO_EXTENSIONS = [".mp4", ".mov", ".mkv", ".avi", ".3gp", ".webm"]
ALLOWED_EXTENSIONS = IMAGE_EXTENSIONS + VIDEO_EXTENSIONS


@router.post("/image", status_code=status.HTTP_201_CREATED)
async def upload_image(file: UploadFile = File(...)):
    """
    Upload a single image file (NID, Product Photo, etc.)
    Returns public URL of the uploaded image
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in IMAGE_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"অবৈধ ছবির ফরম্যাট। সমর্থিত ফরম্যাট: {', '.join(IMAGE_EXTENSIONS)}"
        )

    unique_filename = f"{uuid.uuid4().hex[:12]}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ছবি সংরক্ষণ করতে ব্যর্থ হয়েছে: {str(e)}"
        )

    public_url = f"/uploads/{unique_filename}"
    return {
        "message": "File uploaded successfully",
        "filename": unique_filename,
        "url": public_url,
        "full_url": f"http://127.0.0.1:8000{public_url}"
    }


@router.post("/images", status_code=status.HTTP_201_CREATED)
async def upload_multiple_images(files: List[UploadFile] = File(...)):
    """
    Upload multiple product images at once.
    Returns list of public URLs.
    """
    uploaded_urls = []
    full_urls = []

    for file in files:
        ext = os.path.splitext(file.filename or "")[1].lower()
        if ext not in IMAGE_EXTENSIONS:
            continue

        unique_filename = f"{uuid.uuid4().hex[:12]}{ext}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)

        try:
            contents = await file.read()
            with open(file_path, "wb") as f:
                f.write(contents)
            public_url = f"/uploads/{unique_filename}"
            uploaded_urls.append(public_url)
            full_urls.append(f"http://127.0.0.1:8000{public_url}")
        except Exception:
            continue

    if not uploaded_urls:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="কোনো বৈধ ছবি আপলোড করা যায়নি।"
        )

    return {
        "message": f"{len(uploaded_urls)} টি ছবি সফলভাবে আপলোড হয়েছে",
        "urls": uploaded_urls,
        "full_urls": full_urls,
        "primary_url": uploaded_urls[0]
    }


@router.post("/video", status_code=status.HTTP_201_CREATED)
async def upload_video(file: UploadFile = File(...)):
    """
    Upload a product video clip (gallery video or live camera recording).
    """
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in VIDEO_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"অবৈধ ভিডিও ফরম্যাট। সমর্থিত ফরম্যাট: {', '.join(VIDEO_EXTENSIONS)}"
        )

    unique_filename = f"vid_{uuid.uuid4().hex[:12]}{ext}"
    file_path = os.path.join(UPLOAD_DIR, unique_filename)

    try:
        contents = await file.read()
        with open(file_path, "wb") as f:
            f.write(contents)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"ভিডিও সংরক্ষণ করতে ব্যর্থ হয়েছে: {str(e)}"
        )

    public_url = f"/uploads/{unique_filename}"
    return {
        "message": "Video uploaded successfully",
        "filename": unique_filename,
        "url": public_url,
        "full_url": f"http://127.0.0.1:8000{public_url}"
    }

