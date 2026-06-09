import os
import re
import json
from fastapi import FastAPI, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import feedparser
import google.generativeai as genai
import requests

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🌐 PASTE YOUR GOOGLE WEB APP URL HERE BOSS
GSHEET_SCRIPT_URL = "YAHAN_APNA_GOOGLE_SCRIPT_URL_PASTE_KARO"
WEBSITE_URL = "https://signal-desk.onrender.com"

class SubscriptionRequest(BaseModel):
    email: str
    sector: str

SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "vish20vijay@gmail.com")
SENDGRID_KEY = os.environ.get("SENDGRID_API_KEY", "")
GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")

genai.configure(api_key=GEMINI_KEY)
model = genai.GenerativeModel('gemini-2.5-flash')

def get_live_news():
    FEED_URL = "https://news.google.com/rss/search?q=technology+infrastructure+enterprise+market&hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(FEED_URL)
        return feed.entries[:4]
    except Exception: return []

def generate_signals_dataset():
    raw_news = get_live_news()
    processed = []
    
    system_prompt = (
        "You are an expert market research analyst. Analyze the following news title and return a valid JSON object ONLY.\n"
        "Do NOT include markdown block characters like ```json. Just return raw structural data text.\n"
        "CRITICAL RESPONSE FORMAT RULES:\n"
        "1. All properties must be clean 1-line semantic strings.\n"
        "2. 'what_hi' property MUST be in HINGLISH using LATIN LETTERS ONLY (English alphabets like: 'Market me heavy spending breakout dekhne ko mil rha h').\n"
        "Structure mapping template:\n"
        "{\n"
        "  \"category\": \"Tech\",\n"
        "  \"what_en\": \"English summary line.\",\n"
        "  \"what_hi\": \"Hinglish translation line.\",\n"
        "  \"why_it_matters\": \"Strategic reason.\",\n"
        "  \"market_impact\": \"Business impact.\"\n"
        "}"
    )
    
    for idx, item in enumerate(raw_news):
        try:
            full_prompt = f"{system_prompt}\n\nTARGET NEWS BLOCK TITLE: {item.title}"
            response = model.generate_content(full_prompt)
            clean_text = response.text.strip()
            clean_text = re.sub(r"^```json\s*|```$", "", clean_text, flags=re.MULTILINE).strip()
            data = json.loads(clean_text)
            processed.append({
                "id": f"sig-{idx}",
                "title": item.title,
                "category": data.get("category", "Infrastructure"),
                "what_en": data.get("what_en", "Dynamically validated structural update available."),
                "what_hi": data.get("what_hi", "Live industry system metrics actively compile framework par run ho rha hai."),
                "why_it_matters": data.get("why_it_matters", "Scalable cloud pipeline transitions demand highly optimized tracking protocols."),
                "market_impact": data.get("market_impact", "Enterprise cloud optimization vectors project accelerated capital allocations.")
            })
        except Exception:
            short_clean_title = item.title.split(" - ")[0]
            processed.append({
                "id": f"fb-{idx}",
                "title": item.title,
                "category": "Infrastructure",
                "what_en": f"Operational analytics tracking system is actively processing market expansion metrics for: {short_clean_title}.",
                "what_hi": f"System backend directly pipeline me {short_clean_title} ke data packets track kar rha hai. Complete analysis overview website par live update ho chuki h.",
                "why_it_matters": "Enterprise computing frameworks require continuous tracking to prevent communication bottlenecks across edge networks.",
                "market_impact": "Accelerates regional tech capital expenditures while scaling overall system availability thresholds."
            })
    return processed

def dispatch_dynamic_newsletters():
    print("🚀 Running newsletter core routine engine via GSheet Dataset...")
    if not SENDGRID_KEY: return

    try:
        # 📊 Fetching multi-user array directly from permanent Google Sheet
        response = requests.get(GSHEET_SCRIPT_URL)
        users = response.json()
    except Exception as e:
        print(f"❌ GSheet API Access Exception: {e}")
        return

    if not users:
        print("⚠️ No users found in Google Sheets pipeline.")
        return

    all_signals = generate_signals_dataset()
    
    for user in users:
        email_addr = user.get("email")
        target_sector = user.get("sector", "All")
        try:
            print(f"🔄 Sending customized payload matrix to: {email_addr} [{target_sector}]")
            user_signals = [s for s in all_signals if s["category"].lower() == target_sector.lower()]
            if not user_signals or target_sector == "All":
                user_signals = all_signals

            html_content = f"""
            <html>
            <body style="font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; padding: 20px; background-color: #0f172a; color: #f8fafc; margin: 0;">
                <div style="max-width: 650px; margin: 20px auto; background: #1e293b; padding: 30px; border-radius: 14px; border: 1px solid #334155; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);">
                    <div style="text-align: center; border-bottom: 2px solid #334155; padding-bottom: 20px; margin-bottom: 25px;">
                        <h2 style="color: #34d399; margin: 0 0 8px 0; font-size: 24px; font-weight: 700;">SIGNAL DESK MATRIX</h2>
                        <span style="background: #0f172a; padding: 6px 14px; border-radius: 20px; font-size: 11px; color: #34d399; font-weight: bold; border: 1px solid #10b981;">FOCUS STREAM: {target_sector.upper()}</span>
                    </div>
            """
            for item in user_signals:
                html_content += f"""
                    <div style="margin-bottom: 25px; padding: 20px; background: #0f172a; border-left: 4px solid #34d399; border-radius: 8px;">
                        <h4 style="margin: 0 0 12px 0; color: #ffffff; font-size: 16px;">{item['title']}</h4>
                        <div style="margin-bottom: 8px; font-size: 13px;"><span style="color: #38bdf8; font-weight: bold;">[Core Analysis]:</span> <span style="color: #cbd5e1;">{item['what_en']}</span></div>
                        <div style="margin-bottom: 8px; font-size: 13px;"><span style="color: #34d399; font-weight: bold;">[Hinglish Overview]:</span> <span style="color: #a7f3d0;">{item['what_hi']}</span></div>
                        <div style="margin-bottom: 8px; font-size: 13px;"><span style="color: #fbbf24; font-weight: bold;">[Why It Matters]:</span> <span style="color: #e2e8f0; font-style: italic;">{item['why_it_matters']}</span></div>
                        <div style="font-size: 13px;"><span style="color: #f43f5e; font-weight: bold;">[Market Impact]:</span> <span style="color: #fecdd3;">{item['market_impact']}</span></div>
                    </div>
                """
            html_content += f"""
                    <div style="text-align: center; margin-top: 35px; border-top: 1px solid #334155; padding-top: 25px;">
                        <a href="{WEBSITE_URL}" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: #ffffff; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; display: inline-block;">🌐 Launch Signal Desk Web Dashboard</a>
                    </div>
                </div>
            </body>
            </html>
            """
            payload = {
                "personalizations": [{"to": [{"email": email_addr, "name": "Subscriber"}]}],
                "from": {"email": SENDER_EMAIL, "name": "Signal Desk Enterprise"},
                "subject": f"📊 Intelligence Stream Matrix: {target_sector} Focus Report",
                "content": [{"type": "text/html", "value": html_content}]
            }
            headers = {"Authorization": f"Bearer {SENDGRID_KEY}", "Content-Type": "application/json"}
            response = requests.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers)          
        except Exception: pass

@app.post("/api/subscribe")
async def register_subscriber(req: SubscriptionRequest):
    try:
        requests.post(GSHEET_SCRIPT_URL, json={"email": req.email, "sector": req.sector})
        return {"status": "Success"}
    except Exception as e: return {"status": "Error", "details": str(e)}

@app.get("/api/quick-subscribe")
async def quick_subscribe(email: str, sector: str = "All"):
    try:
        requests.post(GSHEET_SCRIPT_URL, json={"email": email, "sector": sector})
        return {"status": "Success", "message": f"Data locked for {email}."}
    except Exception as e: return {"status": "Error", "details": str(e)}

@app.get("/api/trigger-email-test")
async def trigger_email_test():
    dispatch_dynamic_newsletters()
    return {"status": "Execution Complete"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
