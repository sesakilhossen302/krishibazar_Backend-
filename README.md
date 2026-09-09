# 🌾 KrishiBazar Backend (FastAPI + SQLite + Gmail SMTP)

কৃষিবাজার (Krishi Bazaar) মোবাইল অ্যাপ ও ওয়েব ড্যাশবোর্ডের জন্য তৈরি করা আধুনিক, দ্রুতগতির এবং সম্পূর্ণ Python (FastAPI) ব্যাকএন্ড আর্কিটেকচার।

---

## 📧 আপনার জিমেইল দিয়ে OTP পাঠানোর কনফিগারেশন (Gmail SMTP Setup)

ব্যবহারকারী সাইনআপ বা লগইন করার সময় যে জিমেইল দেবেন, আপনার নিজের জিমেইল থেকে স্বয়ংক্রিয়ভাবে একটি সুন্দর HTML ফরম্যাটে ওটিপি পাঠানো হবে। এটি সক্রিয় করতে `.env` ফাইলে নিচের তথ্যগুলো পূরণ করুন:

```env
# Gmail SMTP Configuration
SMTP_HOST="smtp.gmail.com"
SMTP_PORT=587
SMTP_USER="your_email@gmail.com"           # আপনার জিমেইল অ্যাড্রেস
SMTP_PASSWORD="xxxx xxxx xxxx xxxx"       # আপনার গুগল একাউন্টের ১৬ অক্ষরের App Password
SMTP_FROM_NAME="কৃষিবাজার (Krishi Bazaar)"
SMTP_FROM_EMAIL="your_email@gmail.com"
```

> **💡 গুগল অ্যাপ পাসওয়ার্ড (App Password) পাওয়ার উপায়:**
> 1. আপনার Google Account এর Security ট্যাবে যান।
> 2. 2-Step Verification অন করুন।
> 3. "App Passwords" সার্চ করে অ্যাপ নাম দিন (যেমন: KrishiBazar) এবং প্রাপ্ত ১৬ অক্ষরের পাসওয়ার্ডটি `.env` এর `SMTP_PASSWORD` এ পেস্ট করুন।

---

## 📂 ব্যাকএন্ড ফোল্ডার স্ট্রাকচার (Folder Structure Guide)

| ব্যাকএন্ড ফোল্ডার / ফাইল | বিবরণ (Description) |
| :--- | :--- |
| 🚀 `app/main.py` | প্রধান এন্ট্রি পয়েন্ট। সার্ভার চালু করে এবং সব API Router ও CORS লোড করে। |
| ⚙️ `app/config.py` | কনফিগারেশন ও পরিবেশগত সেটিংস (.env রিডার)। |
| 🔌 `app/database/` | SQLite ডেটাবেজ কানেকশন এবং Session ম্যানেজমেন্ট (`connection.py`)। |
| 🗄️ `app/models/` | SQLAlchemy DB Tables: <br>• `user_model.py` - কৃষক/পাইকার <br>• `otp_model.py` - ওটিপি লগ ও মেয়াদ <br>• `notification_model.py` - নোটিফিকেশন <br>• `product_model.py` - কৃষি পণ্য <br>• `demand_model.py` - চাহিদা ও অফার <br>• `order_model.py` - অর্ডার ও ট্র্যাকিং |
| 📑 `app/schemas/` | Pydantic Schemas: রিকোয়েস্ট ভ্যালিডেশন এবং রেসপন্স সিরিয়ালাইজেশন। |
| 🚦 `app/routers/` | API এন্ডপয়েন্ট: `auth_router.py`, `user_router.py`, `product_router.py`, `demand_router.py`, `order_router.py`, `upload_router.py`, `notification_router.py` |
| 🔐 `app/utils/` | Bcrypt Password Hashing, JWT টোকেন জেনারেটর (`security.py`), এবং Auth Dependency (`deps.py`)। |
| 🛠️ `app/services/` | `email_service.py` - প্রফেশনাল বাংলা ও ইংরেজি রেসপন্সিভ HTML OTP ইমেইল সেন্ডার। |

---

## 🚀 সার্ভার রান করার নিয়ম (Running Backend Server)

```bash
# ১. ডিপেন্ডেন্সি ইনস্টল (যদি প্রয়োজন হয়)
pip install -r requirements.txt

# ২. সার্ভার চালু করুন
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

### লাইভ ড্যাশবোর্ড ও API Documentation:
• **Swagger Interactive API Testing**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)  
• **Redoc API Specs**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

---

## 📱 মূল API Endpoint সমূহের তালিকা (Key APIs)

### ১. Auth & OTP APIs (`/api/v1/auth`)
- **`POST /api/v1/auth/send-otp`**: ব্যবহারকারীর জিমেইলে ৬ ডিজিটের ওটিপি প্রেরণ।
- **`POST /api/v1/auth/verify-otp`**: ওটিপি কোড যাচাই।
- **`POST /api/v1/auth/signup`**: কৃষক বা পাইকারের সাইনআপ সম্পন্ন এবং সাথে সাথে JWT Token ও প্রোফাইল রিটার্ন।
- **`POST /api/v1/auth/login`**: ফোন নম্বর/ইমেইল এবং পাসওয়ার্ড দিয়ে লগইন।
- **`POST /api/v1/auth/login-otp`**: পাসওয়ার্ড ছাড়া সরাসরি জিমেইল ওটিপি দিয়ে লগইন।
- **`POST /api/v1/auth/forgot-password`**: পাসওয়ার্ড ভুলে গেলে জিমেইলে ওটিপি পাঠানো।
- **`POST /api/v1/auth/reset-password`**: ওটিপি দিয়ে নতুন পাসওয়ার্ড সেট করা।
- **`POST /api/v1/auth/change-password`**: লগইন থাকা অবস্থায় পাসওয়ার্ড পরিবর্তন।
- **`GET /api/v1/auth/me`**: বর্তমান লগইন থাকা ব্যবহারকারীর প্রোফাইল তথ্য।

### ২. User Profile & Dashboard APIs (`/api/v1/users`)
- **`GET /api/v1/users/`**: সমস্ত ব্যবহারকারীর তালিকা এবং ফিল্টারিং (Admin / Management)।
- **`GET /api/v1/users/profile`**: সম্পূর্ণ প্রোফাইল তথ্য দেখা।
- **`PATCH /api/v1/users/profile`**: নাম, জেলা, ঠিকানা, ট্রেড লাইসেন্স বা ছবি আপডেট।
- **`PATCH /api/v1/users/{user_id}/status`**: ব্যবহারকারীর ভেরিফিকেশন স্ট্যাটাস, অ্যাডমিন নোট এবং NID স্ট্যাটাস অনুমোদন/প্রত্যাখ্যান করা।
- **`POST /api/v1/users/reupload-nid`**: NID প্রত্যাখ্যাত হলে পুনরায় নতুন NID ছবি ও তথ্য সাবমিট করা।
- **`GET /api/v1/users/dashboard-stats`**: কৃষক ও পাইকারদের জন্য রিয়েলটাইম পরিসংখ্যান (মোট অর্ডার, সক্রিয় পণ্য/চাহিদা, আয়/ব্যয় ইত্যাদি)।

### ৩. Product APIs (`/api/v1/products`)
- **`GET /api/v1/products/`**: পণ্য সার্চ এবং ক্যাটাগরি, জেলা ও দাম অনুযায়ী ফিল্টার।
- **`GET /api/v1/products/my-products`**: কৃষকের নিজের আপলোডকৃত পণ্যের তালিকা।
- **`GET /api/v1/products/{product_id}`**: পণ্যের বিস্তারিত তথ্য।
- **`POST /api/v1/products/`**: নতুন পণ্য যুক্ত করা (কৃষকের জন্য)।
- **`PATCH /api/v1/products/{product_id}`**: পণ্যের স্টক বা তথ্য এডিট করা।
- **`DELETE /api/v1/products/{product_id}`**: পণ্য মুছে ফেলা বা আর্কাইভ করা।

### ৪. Demand & Offer APIs (`/api/v1/demands`)
- **`GET /api/v1/demands/`**: পাইকারি চাহিদাপত্র দেখা ও ফিল্টার করা।
- **`GET /api/v1/demands/my-demands`**: পাইকারের নিজের চাহিদাপত্র।
- **`POST /api/v1/demands/`**: নতুন চাহিদা পোস্ট করা (পাইকারের জন্য)।
- **`POST /api/v1/demands/offers`**: চাহিদায় কৃষকের দরপত্র (Offer) পাঠানো।
- **`GET /api/v1/demands/offers/my-offers`**: কৃষকের পাঠানো সকল অফারের তালিকা।
- **`POST /api/v1/demands/offers/{offer_id}/accept`**: পাইকার অফার গ্রহণ করলে **স্বয়ংক্রিয়ভাবে অর্ডার তৈরি এবং ২০% জামানত হিসাব সম্পন্ন হয়**।
- **`POST /api/v1/demands/offers/{offer_id}/reject`**: অফার প্রত্যাখ্যান করা।

### ৫. Order & Tracking APIs (`/api/v1/orders`)
- **`GET /api/v1/orders/`**: সকল অর্ডারের তালিকা।
- **`GET /api/v1/orders/my-orders`**: ব্যবহারকারীর নিজস্ব অর্ডার তালিকা।
- **`GET /api/v1/orders/{order_id}`**: একক অর্ডারের বিস্তারিত তথ্য।
- **`POST /api/v1/orders/{order_id}/pay-deposit`**: ২০% এসক্রো ডিপোজিট পেমেন্ট কনফার্ম করা।
- **`PATCH /api/v1/orders/{order_id}/status`**: অর্ডারের লাইফসাইকেল স্ট্যাটাস পরিবর্তন (`pending` → `paymentConfirmed` → `processing` → `pickupReady` → `inTransit` → `delivered` → `completed`)।
- **`PATCH /api/v1/orders/{order_id}/transport`**: ড্রাইভারের নাম, ফোন, গাড়ির নাম্বার এবং লাইভ পরিবহন ট্র্যাকিং আপডেট।
- **`POST /api/v1/orders/{order_id}/dispute`**: অর্ডারে কোনো সমস্যা হলে অভিযোগ/ডিসপিউট দাখিল।

### ৬. Notification APIs (`/api/v1/notifications`)
- **`GET /api/v1/notifications/`**: ব্যবহারকারীর সকল ইন-অ্যাপ নোটিফিকেশন।
- **`PATCH /api/v1/notifications/{id}/read`**: নোটিফিকেশন পঠিত হিসেবে চিহ্নিত করা।

### ৭. File Upload API (`/api/v1/upload`)
- **`POST /api/v1/upload/image`**: NID, ট্রেড লাইসেন্স, কৃষি কার্ড এবং পণ্যের ছবি আপলোড।

---

## 🧪 টেস্ট সুইট চালানো (Automated Test Execution)

```bash
python test_backend.py
```
সমস্ত এন্ডপয়েন্ট স্বয়ংক্রিয়ভাবে টেস্ট হয়ে রেসপন্স ভ্যালিডেট করবে।
