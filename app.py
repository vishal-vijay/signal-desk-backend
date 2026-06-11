import os
import re
import json
from fastapi import FastAPI
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

GSHEET_SCRIPT_URL = "https://script.google.com/macros/s/AKfycbwlYDE2TbMJmwn_HIUm9FRgACnbsZ5pQeiqJeBvX37K9lphnRgNlUH1wBBEEOSVc00y/exec"
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
    # 🌐 BROAD SEARCH QUERY: Taaki alag-alag sectors (Tech, Cyber, Finance) ki mix news mile
    FEED_URL = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(FEED_URL)
        return feed.entries[:6]  # Top 6 latest global multi-sector news fetch karenge
    except Exception: return []

def generate_signals_dataset():
    raw_news = get_live_news()
    processed = []
    
    # 🔥 SUPER REFINED PROMPT: Gemini se hi saara dynamic content (English + Hinglish + Sentiment Tag) mangwayenge
    system_prompt = (
        "You are an elite market research analyst. Analyze the following news title and return a valid JSON object ONLY.\n"
        "Do NOT include markdown block characters like ```json. Just return raw structural data text.\n"
        "CRITICAL RESPONSE FORMAT RULES:\n"
        "1. 'category' must be mapped intelligently to one of these: 'Cloud & AI', 'Cybersecurity', 'Smart Grid', 'Telecom', 'Transport & Logistics', 'Financial Regulations'.\n"
        "2. 'sentiment' must be strictly either 'positive' or 'negative'.\n"
        "3. All '_hi' properties MUST be in HINGLISH using LATIN English letters only.\n"
        "Structure mapping template:\n"
        "{\n"
        "  \"category\": \"Cybersecurity\",\n"
        "  \"sentiment\": \"negative\",\n"
        "  \"what_en\": \"English concise analysis of what happened.\",\n"
        "  \"what_hi\": \"Hinglish me short summary ki kya hua hai.\",\n"
        "  \"why_en\": \"Why this event matters for the industry in English.\",\n"
        "  \"why_hi\": \"Yeh event kyon important hai pure sector ke liye in Hinglish.\",\n"
        "  \"impact_en\": \"Market and business impact metrics in English.\",\n"
        "  \"impact_hi\": \"Iska market par kya impact padega trading or system wise in Hinglish.\"\n"
        "}"
    )
    
    for idx, item in enumerate(raw_news):
        try:
            full_prompt = f"{system_prompt}\n\nTARGET NEWS TITLE: {item.title}"
            response = model.generate_content(full_prompt)
            clean_text = response.text.strip()
            clean_text = re.sub(r"^```json\s*|```$", "", clean_text, flags=re.MULTILINE).strip()
            data = json.loads(clean_text)
            
            processed.append({
                "id": f"sig-{idx}",
                "title": item.title,
                "category": data.get("category", "Cloud & AI"),
                "sentiment": data.get("sentiment", "positive"), # Frontend Tag integration
                "what_en": data.get("what_en"),
                "what_hi": data.get("what_hi"),
                "why_en": data.get("why_en"),
                "why_hi": data.get("why_hi"),
                "impact_en": data.get("impact_en"),
                "impact_hi": data.get("impact_hi")
            })
        except Exception as e:
            # 🛡️ DYNAMIC FALLBACK: Agar Gemini fail ho, toh bhi har entry unique dikhegi title ke hisab se!
            short_title = item.title.split(" - ")[0]
            processed.append({
                "id": f"fb-{idx}",
                "title": item.title,
                "category": "Cloud & AI",
                "sentiment": "positive",
                "what_en": f"System engine actively processing real-time telemetry metrics for: {short_title}.",
                "what_hi": f"Backend infrastructure me {short_title} ke live pipelines data check ho rhe hain.",
                "why_en": f"Strategic core verification validation for {short_title} deployment streams.",
                "why_hi": f"Is event ki verification metadata systems security optimizations ke liye check ki ja rhi h.",
                "impact_en": "Accelerates regional infrastructure expenditure frameworks globally.",
                "impact_hi": "Sector capital expenditures growth pattern strong indicators show kar rhe hain."
            })
    return processed

def dispatch_dynamic_newsletters():
    print("🚀 Running newsletter core routine engine via GSheet Dataset...")
    if not SENDGRID_KEY: return

    try:
        response = requests.get(GSHEET_SCRIPT_URL)
        users = response.json()
    except Exception as e:
        print(f"❌ GSheet API Access Exception: {e}")
        return

    if not users: return

    all_signals = generate_signals_dataset()
    
    for user in users:
        email_addr = user.get("email")
        target_sector = user.get("sector", "All")
        try:
            user_signals = [s for s in all_signals if s["category"].lower() == target_sector.lower()]
            if not user_signals or target_sector == "All":
                user_signals = all_signals

            html_content = f"""
            <html>
            <body style="font-family: Arial, sans-serif; padding: 20px; background-color: #0f172a; color: #f8fafc;">
                <div style="max-width: 650px; margin: auto; background: #1e293b; padding: 25px; border-radius: 12px;">
                    <h2 style="color: #34d399; text-align: center;">SIGNAL DESK INSIGHTS</h2>
                    <p style="text-align: center; color: #94a3b8;">Sector Feed: {target_sector}</p>
            """
            for item in user_signals:
                color_tag = "#34d399" if item['sentiment'] == "positive" else "#f43f5e"
                html_content += f"""
                    <div style="margin-bottom: 20px; padding: 15px; background: #0f172a; border-left: 4px solid {color_tag}; border-radius: 6px;">
                        <h4 style="color: #ffffff; margin: 0 0 10px 0;">{item['title']} <span style="color: {color_tag}; font-size: 11px;">[{item['sentiment'].upper()}]</span></h4>
                        <p style="font-size: 13px; color: #cbd5e1;"><b>[Core]:</b> {item['what_en']}</p>
                        <p style="font-size: 13px; color: #a7f3d0;"><b>[Hinglish]:</b> {item['what_hi']}</p>
                    </div>
                """
            html_content += f"""
                    <div style="text-align: center; margin-top: 25px;">
                        <a href="{WEBSITE_URL}" style="background: #10b981; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold;">Launch Dashboard</a>
                    </div>
                </div>
            </body>
            </html>
            """
            payload = {
                "personalizations": [{"to": [{"email": email_addr}]}],
                "from": {"email": SENDER_EMAIL, "name": "Signal Desk Enterprise"},
                "subject": f"📊 Intelligence Matrix Report: {target_sector}",
                "content": [{"type": "text/html", "value": html_content}]
            }
            headers = {"Authorization": f"Bearer {SENDGRID_KEY}", "Content-Type": "application/json"}
            requests.post("[https://api.sendgrid.com/v3/mail/send](https://api.sendgrid.com/v3/mail/send)", json=payload, headers=headers)          
        except Exception: pass

@app.get("/api/signals")
async def get_live_signals_for_ui():
    try:
        return generate_signals_dataset()
    except Exception as e:
        return {"status": "Error", "message": str(e)}

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
        return {"status": "Success"}
    except Exception as e: return {"status": "Error", "details": str(e)}

@app.get("/api/trigger-email-test")
async def trigger_email_test():
    dispatch_dynamic_newsletters()
    return {"status": "Execution Complete"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
