import os
import re
import json
import time
import email.utils
from datetime import datetime, timezone
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
CACHE_DURATION = 300  # 5 Minutes refresh loop window

def get_relative_time(published_str):
    """Parses standard RSS GMT publication date format to clean relative human strings."""
    if not published_str:
        return "Just now"
    try:
        dt = email.utils.parsedate_to_datetime(published_str)
        now = datetime.now(timezone.utc)
        diff = now - dt
        diff_seconds = int(diff.total_seconds())
        if diff_seconds < 0:
            return "Just now"
        minutes = diff_seconds // 60
        if minutes < 60:
            return f"{minutes}m ago" if minutes > 0 else "Just now"
        hours = minutes // 60
        if hours < 24:
            return f"{hours}h ago"
        days = hours // 24
        if days < 7:
            return f"{days}d ago"
        return dt.strftime("%b %d")
    except Exception:
        return "Just now"

def get_live_news():
    # FREQUENCY UPGRADE: Appended 'when:1d' filter to force Google News to only yield fresh last 24h reports!
    queries = [
        "Nifty+OR+BSE+OR+NSE+OR+infra+OR+capex+OR+acquisition+when:1d+geo:India",
        "enterprise+tech+OR+cloud+computing+OR+cybersecurity+when:1d"
    ]
    all_entries = []
    try:
        for q in queries:
            url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
            feed = feedparser.parse(url)
            if feed.entries:
                all_entries.extend(feed.entries)  
        
        # SORT BY RECENT: Sorting feeds chronologically using publication timestamp
        all_entries.sort(key=lambda x: x.get('published_parsed') or time.gmtime(), reverse=True)
        # Slicing at 25 keeps the token window extremely safe and delivers maximum live volume
        return all_entries[:25]
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
    
    # SPEED HYBRID OPTIMIZATION:
    # Only process the top 8 most critical articles through Gemini (takes only ~3s to generate!)
    # The rest (9-25) will fall back instantly to our super-fast heuristic engine.
    ai_limit = min(8, len(raw_news))
    ai_news = raw_news[:ai_limit]
    fallback_news = raw_news[ai_limit:]

    # Safe batching payload text
    news_input_text = ""
    for idx, item in enumerate(ai_news):
        news_input_text += f"INDEX: {idx}\nTITLE: {item.title}\n\n"

    system_prompt = (
        "You are an elite financial tech analyst. Analyze the provided raw headlines data pool and convert them into premium financial intelligence.\n"
        "Your response must be a raw valid JSON array containing structured objects matching the exact layout below:\n"
        "[\n"
        "  {\n"
        "    \"index\": 0,\n"
        "    \"category\": \"Strictly one of: 'Cloud & AI', 'Cybersecurity', 'Smart Grid', 'Telecom', 'Transport & Logistics', 'Financial Regulations'\",\n"
        "    \"sentiment\": \"'positive', 'negative' or 'neutral'\",\n"
        "    \"region\": \"Must be strictly either '🇮🇳 India Market' or '🌐 Global Tech'\",\n"
        "    \"tag_metric\": \"Must be strictly one of: '📈 Sector Re-rating', '💰 Yield Payout', '💼 Corporate Capex', '🚀 Tech Disruption', '🔒 Compliance Risk'\",\n"
        "    \"what_en\": \"Detailed English summary.\",\n"
        "    \"what_hi\": \"Hinglish summary using Latin script characters only.\",\n"
        "    \"why_en\": \"Strategic analysis explanation in English.\",\n"
        "    \"why_hi\": \"Detailed macro analysis breakdown in fluent Hinglish using Latin letters.\",\n"
        "    \"impact_en\": \"Forward financial expenditure trends in English.\",\n"
        "    \"impact_hi\": \"Technical breakout projections matrix in Hinglish using Latin letters.\"\n"
        "  }\n"
        "]\n\n"
        "LAWS:\n"
        "1. Match the object array count exactly to the indexes parsed inside input data pool.\n"
        "2. All '_hi' fields must use pure Latin script characters only. No Devanagari allowed.\n"
        "3. Return ONLY the raw valid JSON array block without any markdown wrapping backticks."
    )

    api_success = False
    if client and ai_news:
        try:
            print(f"🚀 Dispatching Speed-Optimized Batch Request for top {ai_limit} items...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"{system_prompt}\n\nINPUT DATA POOL:\n{news_input_text}",
            )
            
            clean_text = response.text.strip()
            
            # Encoded raw backticks hex-sequences to avoid Render compilation block leakage!
            clean_text = clean_text.replace("\x60\x60\x60json", "").replace("\x60\x60\x60JSON", "").replace("\x60\x60\x60", "").strip()
            if clean_text.lower().startswith("json"):
                clean_text = clean_text[4:].strip()

            batch_data = json.loads(clean_text)
            
            for item_data in batch_data:
                idx = int(item_data.get("index", 0))
                if idx >= len(ai_news): continue
                
                item = ai_news[idx]
                published_date = item.get("published", "")
                rel_time = get_relative_time(published_date)
                
                processed.append({
                    "id": f"sig-{idx}",
                    "title": item.title,
                    "time": rel_time,
                    "category": item_data.get("category", "Cloud & AI"),
                    "sentiment": item_data.get("sentiment", "positive"),
                    "region": item_data.get("region", "🇮🇳 India Market"),
                    "tag_metric": item_data.get("tag_metric", "💼 Corporate Capex"),
                    "what_en": item_data.get("what_en", "Analysis verified."),
                    "what_hi": item_data.get("what_hi", "Core frame checked."),
                    "why_en": item_data.get("why_en", "Strategic metrics tracked."),
                    "why_hi": item_data.get("why_hi", "Upgrade stability check ok."),
                    "impact_en": item_data.get("impact_en", "Trajectory models stable."),
                    "impact_hi": item_data.get("impact_hi", "Technical breakout trajectory visible.")
                })
            if processed:
                api_success = True
        except Exception as e:
            print(f"⚠️ Batch Parsing Glitch: {e}")
            api_success = False

    # FALLBACK & TAIL PIPELINE PROCESSING (Appended instantly!)
    print(f"🔄 Appending fallback engine data for tail-end news count: {len(fallback_news)}")
    for f_idx, item in enumerate(fallback_news):
        idx = ai_limit + f_idx
        title = item.title
        short_title = title.split(" - ")[0].split(" | ")[0]
        published_date = item.get("published", "")
        rel_time = get_relative_time(published_date)
        
        cat = "Financial Regulations"
        sentiment_val = "positive"
        region_val = "🇮🇳 India Market" if any(w in title.lower() for w in ["nifty", "sensex", "bse", "nse", "india", "alphageo", "meesho", "inspira"]) else "🌐 Global Tech"
        metric_val = "💼 Corporate Capex"

        if any(w in title.lower() for w in ["cyber", "security", "attack", "breach", "train", "oracle"]): 
            cat = "Cybersecurity"
            metric_val = "🔒 Compliance Risk"
        elif any(w in title.lower() for w in ["cloud", "ai", "microsoft", "aws", "azure", "github", "computing", "meesho"]): 
            cat = "Cloud & AI"
            metric_val = "🚀 Tech Disruption"
        elif any(w in title.lower() for w in ["nifty", "sensex", "share", "price", "dividend", "alphageo", "matrix", "turnaround"]): 
            cat = "Smart Grid"
            metric_val = "📈 Momentum Breakout"

        processed.append({
            "id": f"sig-{idx}",
            "title": title,
            "time": rel_time,
            "category": cat,
            "sentiment": sentiment_val,
            "region": region_val,
            "tag_metric": metric_val,
            "what_en": f"Analysis of '{short_title}' highlights tactical asset movements.",
            "what_hi": f"Is latest market track se '{short_title[:45]}' segment me structural changes clear hain.",
            "why_en": "Critical for core risk mitigation parameters.",
            "why_hi": "Ecosystem requirements and execution profiles update ke liye critical upgrade hai.",
            "impact_en": "Forward indicators trace rating revisions.",
            "impact_hi": "Ecosystem capital trajectory aur metrics stability par impact visible rahega."
        })

    CACHE_DATA = processed
    CACHE_TIME = current_time
    return processed

def dispatch_dynamic_newsletters():
    if not SENDGRID_KEY: return
    try:
        response = requests.get(GSHEET_SCRIPT_URL)
        users = response.json()
    except Exception: return
    if not users: return

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
            if not user_signals or clean_sector == "All": user_signals = all_signals

            subject_line = f"📊 Intelligence Stream: {clean_sector} Focus Report"
            html_content = f"""<html><body style="font-family: Arial, sans-serif; background-color: #0f172a; color: #f8fafc; padding: 20px;">
            <div style="max-width: 650px; margin: auto; background: #1e293b; padding: 25px; border-radius: 12px;">
            <h2 style="color: #34d399; border-bottom: 2px solid #334155; padding-bottom: 10px;">SIGNAL DESK INSIGHTS</h2>"""
            
            for item in user_signals:
                color_tag = "#34d399" if item['sentiment'] == "positive" else "#f43f5e"
                html_content += f"""
                <div style="margin-bottom: 20px; padding: 15px; background: #0f172a; border-left: 4px solid {color_tag}; border-radius: 6px;">
                    <h4 style="margin: 0 0 10px 0; color: #ffffff;">{item['title']}</h4>
                    <p style="font-size: 11px; color: #94a3b8;">{item['region']} | {item['tag_metric']} | ⏱️ {item['time']}</p>
                    <p style="font-size: 13px; color: #cbd5e1;">{item['what_en'] if user_lang == 'en' else item['what_hi']}</p>
                </div>"""
                
            html_content += f"""<p style="text-align: center;"><a href="{WEBSITE_URL}" style="background: #10b981; color: white; padding: 10px 20px; text-decoration: none; border-radius: 6px; font-weight: bold;">Launch Live Dashboard</a></p></div></body></html>"""
            payload = {
                "personalizations": [{"to": [{"email": email_addr}]}],
                "from": {"email": SENDER_EMAIL, "name": "Signal Desk Enterprise"},
                "subject": subject_line,
                "content": [{"type": "text/html", "value": html_content}]
            }
            requests.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers={"Authorization": f"Bearer {SENDGRID_KEY}", "Content-Type": "application/json"})
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
