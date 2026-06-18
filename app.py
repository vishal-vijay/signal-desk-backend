import os
import re
import json
import time
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List
import feedparser
from google import genai
from google.genai import types
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
WEBSITE_URL = "https://signal-desk-enterprise.onrender.com"

class SubscriptionRequest(BaseModel):
    email: str
    sector: str

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "vish20vijay@gmail.com")
SENDGRID_KEY = os.environ.get("SENDGRID_API_KEY", "")

client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

CACHE_DATA = None
CACHE_TIME = 0
CACHE_DURATION = 300  # Data refresh cycle reduced to 5 minutes for highly active feeds

def get_live_news():
    # 🌟 SCALE UP: Limits completely removed to fetch every single live article available
    queries = [
        "Nifty+OR+BSE+OR+NSE+OR+infra+OR+capex+OR+acquisition+geo:India",
        "enterprise+tech+OR+cloud+computing+OR+cybersecurity"
    ]
    all_entries = []
    try:
        for q in queries:
            url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
            feed = feedparser.parse(url)
            if feed.entries:
                # Slicing limits completely removed to capture full feed capacity
                all_entries.extend(feed.entries)  
        return all_entries
    except Exception as e:
        print(f"❌ RSS Fetch Error: {e}")
        return []

def generate_signals_dataset():
    global CACHE_DATA, CACHE_TIME
    current_time = time.time()
    
    if CACHE_DATA and (current_time - CACHE_TIME < CACHE_DURATION):
        print("⚡ Returning Data directly from Memory Cache!")
        return CACHE_DATA

    raw_news = get_live_news()
    if not raw_news:
        return []

    processed = []
    
    # 🌟 THE STARTUP REVOLUTION FIX: Iterating single-item loops instead of choking with batches
    # Isse parsing errors hamesha ke liye khatam aur har ek item ka high-density profile milega
    for idx, item in enumerate(raw_news):
        title = item.title
        short_title = title.split(" - ")[0].split(" | ")[0]
        
        # Smart pre-routing system defaults
        cat = "Financial Regulations"
        sentiment_val = "positive"
        if any(w in title.lower() for w in ["cyber", "security", "attack", "breach", "train", "oracle"]): 
            cat = "Cybersecurity"
        elif any(w in title.lower() for w in ["cloud", "ai", "microsoft", "aws", "azure", "github", "computing", "meesho"]): 
            cat = "Cloud & AI"
        elif any(w in title.lower() for w in ["nifty", "sensex", "share", "price", "dividend", "alphageo", "matrix", "turnaround"]): 
            cat = "Smart Grid"
            
        if any(w in title.lower() for w in ["lawsuit", "negative", "drop", "loss", "shaky", "tension"]):
            sentiment_val = "negative"

        api_item_success = False
        
        if client:
            try:
                # Sharp single-item analysis template
                prompt = (
                    f"Analyze this corporate technology/market headline: '{title}'\n\n"
                    "Generate a valid JSON object matching the exact format keys below:\n"
                    "{\n"
                    "  \"category\": \"Strictly one of: 'Cloud & AI', 'Cybersecurity', 'Smart Grid', 'Telecom', 'Transport & Logistics', 'Financial Regulations'\",\n"
                    "  \"sentiment\": \"'positive', 'negative' or 'neutral'\",\n"
                    "  \"what_en\": \"Detailed professional analysis summarizing this disruption in English.\",\n"
                    "  \"what_hi\": \"Dense comprehensive analytical summary in conversational HINGLISH using Latin letters only.\",\n"
                    "  \"why_en\": \"Strategic explanation outlining why this is critical for enterprise ecosystems or Nifty/BSE markets in English.\",\n"
                    "  \"why_hi\": \"Detailed macro analysis breakdown in fluent Hinglish using Latin letters.\",\n"
                    "  \"impact_en\": \"Forward-looking technical/financial expenditures reallocation models and potential stock rating expansions.\",\n"
                    "  \"impact_hi\": \"Ecosystem capital velocity projections and short-term swing breakout tracking matrix in clean Hinglish.\"\n"
                    "}\n\n"
                    "LAWS:\n"
                    "1. Return ONLY the raw valid JSON object block. Do not include markdown code ticks, backticks, or extra text.\n"
                    "2. All '_hi' fields must use pure Latin characters only (No Devanagari script)."
                )
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                
                clean_text = response.text.strip()
                clean_text = clean_text.replace("```json", "").replace("
```JSON", "").replace("```", "").strip()
                
                data = json.loads(clean_text)
                
                processed.append({
                    "id": f"sig-{idx}",
                    "title": title,
                    "category": data.get("category", cat),
                    "sentiment": data.get("sentiment", sentiment_val),
                    "what_en": data.get("what_en", f"Analysis of '{short_title}' verifies structural asset movements inside domestic enterprise frameworks."),
                    "what_hi": data.get("what_hi", f"Is development se '{short_title[:45]}' segment me corporate expansion tracking update complete ho rhi hai."),
                    "why_en": data.get("why_en", "Establishing platform benchmarks and corporate capex metrics optimization parameters check."),
                    "why_hi": data.get("why_hi", "Margin profiles ko scale karne aur execution capabilities ko stable karne ke liye critical upgrade hai."),
                    "impact_en": data.get("impact_en", "Forward models project dynamic tech capital reallocation velocities inside the sector."),
                    "impact_hi": data.get("impact_hi", "Retail portfolio risk mapping aur short-term swing matrices par is high-conviction metrics ka clear impact visible rahega.")
                })
                api_item_success = True
                
            except Exception as e:
                print(f"⚠️ Item indexing parsing glitch at index {idx}: {e}")
                api_item_success = False

        # Bullet-proof fail-safe per item level fallback mapping tracking
        if not api_item_success:
            processed.append({
                "id": f"fb-{idx}",
                "title": title,
                "category": cat,
                "sentiment": sentiment_val,
                "what_en": f"Analysis of '{short_title}' highlights tactical structural movements and asset deployment parameters updating domestic baselines.",
                "what_hi": f"Is latest market track se '{short_title[:45]}' segment me immediate enterprise triggers aur corporate scaling updates visible ho rhe hain.",
                "why_en": f"This metrics deployment is vital for core corporate capex optimization, risk mitigation, and avoiding vendor platform bottlenecks.",
                "why_hi": f"Yeh expansion long-term growth aur multi-vendor management strategies ko strengthen karne ke liye critical infrastructure upgrade hai.",
                "impact_en": f"Forward tracking models project immediate industry rating re-evaluations and dynamic technical capital reallocation velocities.",
                "impact_hi": f"Retail portfolio risk mapping aur industry development frameworks par is continuous momentum ka solid impact dikhega."
            })

    CACHE_DATA = processed
    CACHE_TIME = current_time
    return processed

def dispatch_dynamic_newsletters():
    print("🚀 Running newsletter core routine engine via GSheet Dataset...")
    if not SENDGRID_KEY: 
        print("⚠️ SendGrid API Key missing.")
        return
    try:
        response = requests.get(GSHEET_SCRIPT_URL)
        users = response.json()
    except Exception as e:
        print(f"❌ GSheet API Access Exception: {e}")
        return

    if not users: 
        print("⚠️ No subscribers found inside the database.")
        return

    all_signals = generate_signals_dataset()
    
    for user in users:
        email_addr = user.get("email")
        raw_sector = user.get("sector", "All")
        
        user_lang = "en"
        clean_sector = raw_sector
        
        if "[" in raw_sector and "]" in raw_sector:
            match = re.search(r"(.+?)\s*\[(en|hi)\]", raw_sector)
            if match:
                clean_sector = match.group(1).strip()
                user_lang = match.group(2).strip()

        try:
            user_signals = [s for s in all_signals if s["category"].lower() == clean_sector.lower()]
            if not user_signals or clean_sector == "All":
                user_signals = all_signals

            subject_line = f"📊 Intelligence Stream Matrix: {clean_sector} Focus Report" if user_lang == "en" else f"📊 Market Intelligence Matrix Report: {clean_sector}"

            html_content = f"""
            <html>
            <body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; background-color: #0f172a; color: #f8fafc; margin:0;">
                <div style="max-width: 650px; margin: 20px auto; background: #1e293b; padding: 30px; border-radius: 14px; border: 1px solid #334155; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);">
                    <div style="text-align: center; border-bottom: 2px solid #334155; padding-bottom: 20px; margin-bottom: 25px;">
                        <h2 style="color: #34d399; margin: 0 0 8px 0; font-size: 24px; font-weight: 700;">SIGNAL DESK INSIGHTS</h2>
                        <span style="background: #0f172a; padding: 6px 14px; border-radius: 20px; font-size: 11px; color: #34d399; font-weight: bold; border: 1px solid #10b981;">STREAM: {clean_sector.upper()} | LANG: {user_lang.upper()}</span>
                    </div>
            """
            for item in user_signals:
                color_tag = "#34d399" if item['sentiment'] == "positive" else "#f43f5e"
                
                if user_lang == "hi":
                    body_block = f"""
                        <div style="margin-bottom: 8px; font-size: 13px;"><span style="color: #34d399; font-weight: bold;">[Kya Hua Hai]:</span> <span style="color: #a7f3d0;">{item['what_hi']}</span></div>
                        <div style="margin-bottom: 8px; font-size: 13px;"><span style="color: #fbbf24; font-weight: bold;">[Kyon Important Hai]:</span> <span style="color: #e2e8f0; font-style: italic;">{item['why_hi']}</span></div>
                        <div style="font-size: 13px;"><span style="color: #f43f5e; font-weight: bold;">[Market Par Impact]:</span> <span style="color: #fecdd3;">{item['impact_hi']}</span></div>
                    """
                else:
                    body_block = f"""
                        <div style="margin-bottom: 8px; font-size: 13px;"><span style="color: #38bdf8; font-weight: bold;">[Core Analysis]:</span> <span style="color: #cbd5e1;">{item['what_en']}</span></div>
                        <div style="margin-bottom: 8px; font-size: 13px;"><span style="color: #fbbf24; font-weight: bold;">[Why It Matters]:</span> <span style="color: #e2e8f0; font-style: italic;">{item['why_en']}</span></div>
                        <div style="font-size: 13px;"><span style="color: #f43f5e; font-weight: bold;">[Market Impact]:</span> <span style="color: #fecdd3;">{item['impact_en']}</span></div>
                    """

                html_content += f"""
                    <div style="margin-bottom: 25px; padding: 20px; background: #0f172a; border-left: 4px solid {color_tag}; border-radius: 8px;">
                        <h4 style="margin: 0 0 12px 0; color: #ffffff; font-size: 16px;">{item['title']} <span style="color: {color_tag}; font-size: 11px; font-weight: bold; margin-left: 10px;">[{item['sentiment'].upper()}]</span></h4>
                        {body_block}
                    </div>
                """
            html_content += f"""
                    <div style="text-align: center; margin-top: 35px; border-top: 1px solid #334155; padding-top: 25px;">
                        <a href="{WEBSITE_URL}" style="background: linear-gradient(135deg, #10b981 0%, #059669 100%); color: white; padding: 14px 28px; text-decoration: none; border-radius: 6px; font-weight: bold; font-size: 14px; display: inline-block;">🌐 Launch Live Dashboard</a>
                    </div>
                </div>
            </body>
            </html>
            """
            payload = {
                "personalizations": [{"to": [{"email": email_addr, "name": "Subscriber"}]}],
                "from": {"email": SENDER_EMAIL, "name": "Signal Desk Enterprise"},
                "subject": subject_line,
                "content": [{"type": "text/html", "value": html_content}]
            }
            headers = {"Authorization": f"Bearer {SENDGRID_KEY}", "Content-Type": "application/json"}
            requests.post("[https://api.sendgrid.com/v3/mail/send](https://api.sendgrid.com/v3/mail/send)", json=payload, headers=headers)          
        except Exception: 
            pass

@app.get("/api/signals")
async def get_live_signals_for_ui():
    return generate_signals_dataset()

@app.post("/api/subscribe")
async def register_subscriber(req: SubscriptionRequest):
    try:
        requests.post(GSHEET_SCRIPT_URL, json={"email": req.email, "sector": req.sector})
        return {"status": "Success"}
    except Exception as e: 
        return {"status": "Error", "details": str(e)}

@app.get("/api/trigger-email-test")
async def trigger_email_test():
    dispatch_dynamic_newsletters()
    return {"status": "Execution Complete"}

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run(app, host="0.0.0.0", port=port)
