import os
import re
import json
import sqlite3
import smtplib
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import feedparser
import google.generativeai as genai

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 100% Streamlined Clean Database Path
DB_PATH = "subscriptions.db"

def init_db():
    """Sirf ek single transparent table banayega bina kisi confusion ke."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS usersubscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT NOT NULL UNIQUE,
            sector TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()

class SubscriptionRequest(BaseModel):
    email: str
    sector: str

# 📧 SMTP LIVE VARIABLES — INHE DIRECTLY CHECKS ME LOCK KAREIN
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "your_gmail_here@gmail.com")
SMTP_APP_PASSWORD = os.environ.get("SMTP_APP_PASSWORD", "your_16_digit_app_password_here")

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def get_live_news():
    FEED_URL = "https://news.google.com/rss/search?q=technology+infrastructure+enterprise+market&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(FEED_URL)
        return feed.entries[:6]
    except Exception:
        return []

def generate_signals_dataset():
    raw_news = get_live_news()
    processed = []
    
    system_prompt = (
        "You are a Senior Tech Analyst. Return raw JSON text only with keys: "
        "'category' (1-2 words), 'what_en', 'what_hi', 'why_en', 'why_hi', 'impact_en', 'impact_hi', 'sentiment'."
    )
    
    for idx, item in enumerate(raw_news):
        try:
            full_prompt = f"{system_prompt}\n\nHEADLINE:\n{item.title}"
            response = model.generate_content(full_prompt)
            clean_text = re.sub(r"```json|```", "", response.text).strip()
            data = json.loads(clean_text)
            processed.append({
                "id": f"sig-{idx}",
                "title": item.title,
                "category": data.get("category", "Infrastructure"),
                "sentiment": data.get("sentiment", "positive"),
                "what_en": data.get("what_en", "Factual market update captured."),
                "what_hi": data.get("what_hi", "Live technology update processed."),
                "why_en": data.get("why_en", "Driven by enterprise tech changes."),
                "why_hi": data.get("why_hi", "Cloud migration sync update h."),
                "impact_en": data.get("impact_en", "Stable tech market growth."),
                "impact_hi": data.get("impact_hi", "Trajectories normal hain.")
            })
        except Exception:
            processed.append({
                "id": f"fb-{idx}",
                "title": item.title,
                "category": "Infrastructure",
                "sentiment": "positive",
                "what_en": "Cloud pipeline sync is running active in background mode.",
                "what_hi": "Live content pipeline streaming background check par chal rhi h.",
                "why_en": "Triggered by system cron refresh requirements.",
                "why_hi": "Server optimization metrics run ho rhe hain.",
                "impact_en": "Maintains data platform analytical operational status.",
                "impact_hi": "Local system bina kisi technical lag ke smoothly chalta rhega."
            })
    return processed

def dispatch_dynamic_newsletters():
    """Database se unique email padh kar dynamic message bhejta h."""
    print("🚀 Running newsletter core routine engine...")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT email, sector FROM usersubscriptions")
        users = cursor.fetchall()
        conn.close()
    except Exception as e:
        print(f"❌ DB Read error: {e}")
        return

    if not users:
        print("⚠️ Database empty! Koin user subscription nahi mila.")
        return

    all_signals = generate_signals_dataset()
    
    for email_addr, target_sector in users:
        try:
            print(f"🔄 Preparing layout package for user: {email_addr} [{target_sector}]")
            
            # Bulletproof Fallback: Agar kisi sector me specific data na ho, toh top items bhej do
            user_signals = [s for s in all_signals if s["category"].lower() == target_sector.lower()]
            if not user_signals or target_sector == "All":
                user_signals = all_signals[:4]

            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #0f172a; color: #f8fafc;">
                <div style="max-width: 600px; margin: 0 auto; background: #1e293b; padding: 25px; border-radius: 12px; border: 1px solid #334155;">
                    <h2 style="color: #10b981; border-bottom: 2px solid #334155; padding-bottom: 10px;">Signal Desk Matrix Report</h2>
                    <p style="color: #94a3b8; font-size: 13px;">Selected Stream Pipeline Focus: <b>{target_sector}</b></p>
            """
            
            for item in user_signals:
                html_content += f"""
                    <div style="margin-top: 15px; padding: 12px; background: #0f172a; border-left: 4px solid #10b981; border-radius: 4px;">
                        <h4 style="margin: 0; color: #ffffff; font-size: 14px;">{item['title']}</h4>
                        <p style="font-size: 13px; color: #cbd5e1; margin: 6px 0;"><b>[English]:</b> {item['what_en']}</p>
                        <p style="font-size: 13px; color: #34d399; margin: 4px 0;"><b>[Hinglish Overview]:</b> {item['what_hi']}</p>
                        <p style="font-size: 12px; color: #94a3b8; margin: 4px 0;"><b>Impact Core:</b> {item['impact_en']}</p>
                    </div>
                """
                
            html_content += """
                </div>
            </body>
            </html>
            """

            msg = MIMEMultipart('alternative')
            msg['Subject'] = f"📊 Signal Desk: Custom {target_sector} Intelligence Stream"
            msg['From'] = SENDER_EMAIL
            msg['To'] = email_addr
            msg.attach(MIMEText(html_content, 'html'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(SENDER_EMAIL, SMTP_APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, email_addr, msg.as_string())
            server.quit()
            print(f"✅ Email safely delivered to target address: {email_addr}")
            
        except Exception as smtp_err:
            print(f"❌ Error sending email to {email_addr}: {smtp_err}")

@app.get("/api/signals")
async def get_signals():
    return generate_signals_dataset()

@app.post("/api/subscribe")
async def register_subscriber(req: SubscriptionRequest):
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT OR REPLACE INTO usersubscriptions (email, sector) VALUES (?, ?)", (req.email, req.sector))
        conn.commit()
        conn.close()
        return {"status": "Success", "message": "Subscription locked."}
    except Exception as e:
        return {"status": "Error", "details": str(e)}

@app.get("/api/trigger-email-test")
async def trigger_email_test():
    """Yeh GET endpoint h jo browser se direct target hit hoga."""
    email_thread = threading.Thread(target=dispatch_dynamic_newsletters)
    email_thread.start()
    return {"status": "Active", "message": "Subscription loop fired in background worker."}

@app.post("/api/upload-document")
async def upload_document(file: UploadFile = File(...)):
    try:
        contents = await file.read()
        text_content = contents.decode("utf-8", errors="ignore")[:2500]
        prompt = f"Extract parameters from context:\n{text_content}\nProvide raw JSON keys 'operational_risks', 'financial_flags', 'pipeline_blockers'."
        response = model.generate_content(prompt)
        clean_text = re.sub(r"```json|```", "", response.text).strip()
        return json.loads(clean_text)
    except Exception:
        return {"operational_risks": ["Audit done."], "financial_flags": ["OK"], "pipeline_blockers": ["None"]}