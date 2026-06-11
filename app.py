import os
import re
import json
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import feedparser
from google import genai
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

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "vish20vijay@gmail.com")
SENDGRID_KEY = os.environ.get("SENDGRID_API_KEY", "")

client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

# 🧠 MEMORY CACHE VARIABLES: Taaki baar-baar refresh par API hit na ho
CACHE_DATA = None
CACHE_TIME = 0
CACHE_DURATION = 600  # 10 Minutes in seconds

def get_live_news():
    FEED_URL = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(FEED_URL)
        return feed.entries[:5]
    except Exception:
        return []

def generate_signals_dataset():
    global CACHE_DATA, CACHE_TIME
    current_time = time.time()
    
    # 🛡️ If cache is valid, return cached data instantly
    if CACHE_DATA and (current_time - CACHE_TIME < CACHE_DURATION):
        print("⚡ Returning Data directly from Memory Cache!")
        return CACHE_DATA

    raw_news = get_live_news()
    if not raw_news:
        return []

    # 📦 Prepare titles array for Batch Processing
    news_titles_list = [item.title for item in raw_news]
    
    system_prompt = (
        "You are an elite expert market research analyst. Analyze the following array of news titles and return a valid JSON array of objects ONLY.\n"
        "Do NOT include markdown block characters like ```json. Just return raw structural JSON text.\n"
        "CRITICAL RESPONSE FORMAT RULES:\n"
        "1. For each input title, generate an object with corresponding fields.\n"
        "2. 'category' must be strictly one of: 'Cloud & AI', 'Cybersecurity', 'Smart Grid', 'Telecom', 'Transport & Logistics', 'Financial Regulations'.\n"
        "3. 'sentiment' must be strictly 'positive' or 'negative'.\n"
        "4. All '_hi' properties MUST be in clean, meaningful HINGLISH using LATIN English alphabets only.\n"
        "Output Structure should be a valid JSON Array like this:\n"
        "[\n"
        "  {\n"
        "    \"title\": \"Exact input title string matching input\",\n"
        "    \"category\": \"Cybersecurity\",\n"
        "    \"sentiment\": \"negative\",\n"
        "    \"what_en\": \"English analysis.\",\n"
        "    \"what_hi\": \"Hinglish translation summary.\",\n"
        "    \"why_en\": \"Why this matters in English.\",\n"
        "    \"why_hi\": \"Yeh kyon important hai in Hinglish.\",\n"
        "    \"impact_en\": \"Market impact metrics in English.\",\n"
        "    \"impact_hi\": \"Iska market par kya impact padega in Hinglish.\"\n"
        "  }\n"
        "]"
    )
    
    if client:
        try:
            print("🚀 Executing Single-Shot Batch Request to Gemini API...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"{system_prompt}\n\nINPUT TARGET TITLES ARRAY:\n{json.dumps(news_titles_list)}",
            )
            clean_text = response.text.strip()
            clean_text = re.sub(r"^```json\s*|```$", "", clean_text, flags=re.MULTILINE).strip()
            
            batch_data = json.loads(clean_text)
            
            # Map IDs to the response
            processed = []
            for idx, data in enumerate(batch_data):
                processed.append({
                    "id": f"sig-{idx}",
                    "title": data.get("title", news_titles_list[idx] if idx < len(news_titles_list) else "Market Update"),
                    "category": data.get("category", "Cloud & AI"),
                    "sentiment": data.get("sentiment", "positive"),
                    "what_en": data.get("what_en"),
                    "what_hi": data.get("what_hi"),
                    "why_en": data.get("why_en"),
                    "why_hi": data.get("why_hi"),
                    "impact_en": data.get("impact_en"),
                    "impact_hi": data.get("impact_hi")
                })
            
            # Update cache memory
            CACHE_DATA = processed
            CACHE_TIME = current_time
            return processed

        except Exception as e:
            print(f"⚠️ Gemini Batch Processing Failed: {e}")
            
    # 🛡️ SECURE FALLBACK: Executes dynamic mapping if API fails
    processed = []
    for idx, item in enumerate(raw_news):
        snippet = item.get("summary", item.title)
        clean_snippet = re.sub('<[^<]+?>', '', snippet)[:120]
        processed.append({
            "id": f"fb-{idx}",
            "title": item.title,
            "category": "Cloud & AI",
            "sentiment": "positive",
            "what_en": f"Live coverage analysis: {clean_snippet}...",
            "what_hi": f"Real-time update: Is news block ka operational context trace kiya ja rha h.",
            "why_en": "Global market monitoring frameworks capture macroeconomic updates dynamically.",
            "why_hi": "Sector intelligence metrics mapping ke mutabik indexes analyze ho rhe hain.",
            "impact_en": "Monitors sectoral trend shifts across core enterprise tech ecosystems.",
            "impact_hi": "Overall market stability aur infrastructure expenditure strong growth signals show karenge."
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
                        <p style="font-size: 13px;"><b>[Core Analysis]:</b> {item['what_en']}</p>
                        <p style="font-size: 13px; color: #a7f3d0;"><b>[Hinglish Overview]:</b> {item['what_hi']}</p>
                        <p style="font-size: 13px;"><b>[Why It Matters]:</b> {item['why_en']}</p>
                        <p style="font-size: 13px;"><b>[Market Impact]:</b> {item['impact_en']}</p>
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
    return generate_signals_dataset()

@app.post("/api/subscribe")
async def register_subscriber(req: SubscriptionRequest):
    try:
        requests.post(GSHEET_SCRIPT_URL, json={"email": req.email, "sector": req.sector})
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
