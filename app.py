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
    # 🌟 FREQUENCY UPGRADE: Appended 'when:1d' filter to force Google News to only yield fresh last 24h reports!
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
        
        # 🌟 SORT BY RECENT: Sorting feeds chronologically using publication timestamp
        all_entries.sort(key=lambda x: x.get('published_parsed') or time.gmtime(), reverse=True)
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
    
    for idx, item in enumerate(raw_news):
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
            
        if "dividend" in title.lower():
            metric_val = "💰 Yield Payout"
        if any(w in title.lower() for w in ["lawsuit", "negative", "drop", "loss", "shaky", "tension"]):
            sentiment_val = "negative"

        api_item_success = False
        
        if client:
            try:
                prompt = (
                    f"Analyze this technology/market headline: '{title}'\n\n"
                    "Generate a valid JSON object matching the exact format keys below:\n"
                    "{\n"
                    "  \"category\": \"Strictly one of: 'Cloud & AI', 'Cybersecurity', 'Smart Grid', 'Telecom', 'Transport & Logistics', 'Financial Regulations'\",\n"
                    "  \"sentiment\": \"'positive', 'negative' or 'neutral'\",\n"
                    "  \"region\": \"Must be strictly either '🇮🇳 India Market' or '🌐 Global Tech'\",\n"
                    "  \"tag_metric\": \"Must be strictly one of: '📈 Sector Re-rating', '💰 Yield Payout', '💼 Corporate Capex', '🚀 Tech Disruption', '🔒 Compliance Risk'\",\n"
                    "  \"what_en\": \"Detailed professional analysis summarizing this disruption in English.\",\n"
                    "  \"what_hi\": \"Dense comprehensive analytical summary in conversational HINGLISH using Latin letters only.\",\n"
                    "  \"why_en\": \"Strategic explanation outlining why this is critical for enterprise ecosystems or Nifty/BSE markets in English.\",\n"
                    "  \"why_hi\": \"Detailed macro analysis breakdown in fluent Hinglish using Latin letters.\",\n"
                    "  \"impact_en\": \"Forward-looking technical/financial expenditures reallocation models and potential stock rating expansions.\",\n"
                    "  \"impact_hi\": \"Ecosystem capital velocity projections and short-term swing breakout tracking matrix in clean Hinglish.\"\n"
                    "}\n\n"
                    "LAWS:\n"
                    "1. Return ONLY the raw valid JSON text block object. No markdown wrapping strings.\n"
                    "2. All '_hi' fields must use pure Latin script characters only."
                )
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=prompt,
                )
                
                clean_text = response.text.strip()
                
                # 🌟 MANUALLY STRIP MARKDOWN FENCES (VITE/RENDER COMPILER SAFE)
                if clean_text.startswith("```"):
                    lines = clean_text.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].strip() == "```":
                        lines = lines[:-1]
                    clean_text = "\n".join(lines).strip()
                
                data = json.loads(clean_text)
                
                processed.append({
                    "id": f"sig-{idx}",
                    "title": title,
                    "time": rel_time, # 🌟 PASSING DYNAMIC TIME VALUE TO FRONTEND!
                    "category": data.get("category", cat),
                    "sentiment": data.get("sentiment", sentiment_val),
                    "region": data.get("region", region_val),
                    "tag_metric": data.get("tag_metric", metric_val),
                    "what_en": data.get("what_en", f"Analysis of '{short_title}' verifies structural asset movements inside domestic frameworks."),
                    "what_hi": data.get("what_hi", f"Is development se '{short_title[:45]}' segment me corporate expansion tracking update complete ho rhi hai."),
                    "why_en": data.get("why_en", "Establishing platform benchmarks and corporate capex metrics optimization parameters check."),
                    "why_hi": data.get("why_hi", "Margin profiles ko scale karne aur capability scale up karne ke liye critical upgrade hai."),
                    "impact_en": data.get("impact_en", "Forward models project dynamic tech capital reallocation velocities inside the sector."),
                    "impact_hi": data.get("impact_hi", "Retail portfolio risk mapping aur short-term swing matrices par is high-conviction metrics ka clear impact visible rahega.")
                })
                api_item_success = True
                
            except Exception as e:
                print(f"⚠️ Single-Item JSON parse escape trigger context {idx}: {e}")
                api_item_success = False

        if not api_item_success:
            processed.append({
                "id": f"fb-{idx}",
                "title": title,
                "time": rel_time, # 🌟 PASSING DYNAMIC FALLBACK TIME!
                "category": cat,
                "sentiment": sentiment_val,
                "region": region_val,
                "tag_metric": metric_val,
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
                        <span style="background: #0f172a; padding: 6px 14px; border-radius: 20px; font-size: 11px; color: #34d399; font-weight: bold; border: 1px solid #10b981; margin-right: 5px;">STREAM: {clean_sector.upper()}</span>
                        <span style="background: #0f172a; padding: 6px 14px; border-radius: 20px; font-size: 11px; color: #fbbf24; font-weight: bold; border: 1px solid #d97706;">LANG: {user_lang.upper()}</span>
                    </div>
            """
            for item in user_signals:
                color_tag = "#34d399" if item['sentiment'] == "positive" else "#f43f5e"
                
                html_badge_block = f"""
                    <div style="margin-bottom: 12px; display: flex; gap: 6px;">
                        <span style="background: #1e293b; color: #34d399; font-size: 10px; padding: 3px 8px; border-radius: 4px; font-weight: bold; border: 1px solid #334155;">{item.get('region', '🇮🇳 India Market')}</span>
                        <span style="background: #1e293b; color: #fbbf24; font-size: 10px; padding: 3px 8px; border-radius: 4px; font-weight: bold; border: 1px solid #334155; margin-left: 5px;">{item.get('tag_metric', '💼 Corporate Cape')}</span>
                        <span style="background: #1e293b; color: #94a3b8; font-size: 10px; padding: 3px 8px; border-radius: 4px; font-weight: normal; border: 1px solid #334155; margin-left: 5px;">⏱️ {item.get('time', 'Just now')}</span>
                    </div>
                """

                if user_lang == "hi":
                    body_block = f"""
                        {html_badge_block}
                        <div style="margin-bottom: 8px; font-size: 13px;"><span style="color: #34d399; font-weight: bold;">[Kya Hua Hai]:</span> <span style="color: #a7f3d0;">{item['what_hi']}</span></div>
                        <div style="margin-bottom: 8px; font-size: 13px;"><span style="color: #fbbf24; font-weight: bold;">[Kyon Important Hai]:</span> <span style="color: #e2e8f0; font-style: italic;">{item['why_hi']}</span></div>
                        <div style="font-size: 13px;"><span style="color: #f43f5e; font-weight: bold;">[Market Par Impact]:</span> <span style="color: #fecdd3;">{item['impact_hi']}</span></div>
                    """
                else:
                    body_block = f"""
                        {html_badge_block}
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
