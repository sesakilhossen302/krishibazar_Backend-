import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config import settings

logger = logging.getLogger("krishibazar.email")

def generate_otp_html_template(otp_code: str, user_name: str = "সম্মানিত গ্রাহক", purpose_text: str = "অ্যাকাউন্ট ভেরিফিকেশন") -> str:
    """
    Generates a modern, responsive HTML email template for KrishiBazar OTP.
    """
    return f"""<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>কৃষিবাজার ওটিপি ভেরিফিকেশন</title>
    <style>
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background-color: #F4F7F4;
            margin: 0;
            padding: 20px;
        }}
        .email-card {{
            max-width: 540px;
            margin: 0 auto;
            background: #FFFFFF;
            border-radius: 16px;
            overflow: hidden;
            box-shadow: 0 4px 20px rgba(0, 70, 20, 0.08);
            border: 1px solid #E0EBE0;
        }}
        .header {{
            background: linear-gradient(135deg, #1B5E20 0%, #2E7D32 100%);
            padding: 32px 24px;
            text-align: center;
            color: #FFFFFF;
        }}
        .header h1 {{
            margin: 0;
            font-size: 26px;
            font-weight: 700;
            letter-spacing: 0.5px;
        }}
        .header p {{
            margin: 6px 0 0;
            font-size: 14px;
            opacity: 0.9;
        }}
        .content {{
            padding: 32px 28px;
            color: #2D3748;
            line-height: 1.6;
        }}
        .greeting {{
            font-size: 16px;
            font-weight: 600;
            color: #1B5E20;
            margin-bottom: 12px;
        }}
        .otp-container {{
            margin: 28px 0;
            text-align: center;
        }}
        .otp-box {{
            display: inline-block;
            background: #E8F5E9;
            border: 2px dashed #2E7D32;
            border-radius: 12px;
            padding: 16px 36px;
            font-size: 34px;
            font-weight: 800;
            letter-spacing: 10px;
            color: #1B5E20;
            user-select: all;
        }}
        .otp-timer {{
            margin-top: 10px;
            font-size: 13px;
            color: #D32F2F;
            font-weight: 600;
        }}
        .warning-box {{
            background: #FFF8E1;
            border-left: 4px solid #FFA000;
            padding: 12px 16px;
            border-radius: 6px;
            font-size: 13px;
            color: #795548;
            margin-top: 24px;
        }}
        .footer {{
            background: #F9FAF9;
            padding: 20px;
            text-align: center;
            border-top: 1px solid #E8EFE8;
            font-size: 12px;
            color: #718096;
        }}
    </style>
</head>
<body>
    <div class="email-card">
        <div class="header">
            <h1>🌾 কৃষিবাজার (KrishiBazar)</h1>
            <p>ডিজিটাল কৃষি প্ল্যাটফর্ম ও পাইকারি বাজার</p>
        </div>
        <div class="content">
            <div class="greeting">আসসালামু আলাইকুম, {user_name}!</div>
            <p>কৃষিবাজারে আপনার <strong>{purpose_text}</strong> সম্পন্ন করার জন্য নিচের ৬ সংখ্যার ওটিপি (OTP) কোডটি ব্যবহার করুন:</p>
            
            <div class="otp-container">
                <div class="otp-box">{otp_code}</div>
                <div class="otp-timer">⏰ এই কোডটির মেয়াদ ৫ মিনিট পর্যন্ত কার্যকর থাকবে।</div>
            </div>

            <div class="warning-box">
                🔒 <strong>নিরাপত্তা সতর্কবার্তা:</strong> এই ওটিপি কোডটি কারো সাথে শেয়ার করবেন না। কৃষিবাজার কর্তৃপক্ষ কখনো আপনার পাসওয়ার্ড বা ওটিপি জানতে চাইবে না।
            </div>
            
            <p style="margin-top: 24px; font-size: 13px; color: #718096;">
                আপনি যদি এই অনুরোধ না করে থাকেন, তবে অনুগ্রহ করে ইমেইলটি উপেক্ষা করুন।
            </p>
        </div>
        <div class="footer">
            © 2026 KrishiBazar Bangladesh. সর্বস্বত্ব সংরক্ষিত।<br>
            কৃষক ও পাইকারের সরাসরি ডিজিটাল মেলবন্ধন।
        </div>
    </div>
</body>
</html>"""


def send_otp_via_gmail(to_email: str, otp_code: str, user_name: str = "সম্মানিত ব্যবহারকারী", purpose: str = "signup") -> dict:
    """
    Sends OTP email to the user's Gmail using configured Gmail SMTP credentials.
    Returns a dict with success status and message.
    """
    purpose_labels = {
        "signup": "নতুন অ্যাকাউন্ট সাইনআপ ও ভেরিফিকেশন",
        "login": "লগইন ভেরিফিকেশন",
        "reset_password": "পাসওয়ার্ড রিসেট",
        "verify_email": "ইমেইল ভেরিফিকেশন"
    }
    purpose_text = purpose_labels.get(purpose, "ভেরিফিকেশন")
    subject = f"কৃষিবাজার ওটিপি কোড: {otp_code} - {purpose_text}"

    sender_email = settings.SMTP_USER or settings.SMTP_FROM_EMAIL
    sender_password = settings.SMTP_PASSWORD

    # If SMTP is not configured yet, log clearly and return demo success
    if not sender_email or not sender_password:
        log_msg = f"[DEV MODE - SMTP NOT CONFIGURED] OTP for {to_email} ({purpose}): {otp_code}"
        print("="*60)
        print(log_msg)
        print("="*60)
        logger.warning(log_msg)
        return {
            "success": True,
            "mode": "dev_simulation",
            "message": f"SMTP is not yet configured in .env. OTP: {otp_code}",
            "otp_code": otp_code
        }

    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{settings.SMTP_FROM_NAME} <{sender_email}>"
        msg["To"] = to_email

        html_body = generate_otp_html_template(
            otp_code=otp_code,
            user_name=user_name,
            purpose_text=purpose_text
        )
        plain_text = f"কৃষিবাজার ওটিপি কোড: {otp_code}\nএই কোডটি ৫ মিনিটের জন্য কার্যকর থাকবে। কারো সাথে শেয়ার করবেন না।"

        msg.attach(MIMEText(plain_text, "plain", "utf-8"))
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # Connect to Gmail SMTP
        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, sender_password)
            server.sendmail(sender_email, to_email, msg.as_string())

        logger.info(f"OTP successfully sent via Gmail to {to_email}")
        return {
            "success": True,
            "mode": "live_gmail_smtp",
            "message": f"OTP email successfully sent to {to_email}"
        }
    except Exception as e:
        err_msg = f"Failed to send email to {to_email}: {str(e)}"
        logger.error(err_msg)
        print(f"[SMTP ERROR]: {err_msg}")
        return {
            "success": False,
            "mode": "error",
            "message": f"Failed to send email: {str(e)}",
            "otp_code": otp_code
        }
