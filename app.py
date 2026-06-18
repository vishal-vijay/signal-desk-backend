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

# 📋 PYDANTIC SCHEMAS FOR FORCED LLM STRUCTURED OUTPUT
class SignalItemSchema(BaseModel):
    title: str = Field(description="Exact title matching one from the input list.")
    category: str = Field(description="Must be strictly one of: 'Cloud & AI', 'Cybersecurity', 'Smart Grid', 'Telecom', 'Transport & Logistics', 'Financial Regulations'")
    sentiment: str = Field(description="Must be strictly 'positive' or 'negative'")
    what_en: str = Field(description="Detailed elite professional English market analysis summarizing the core news.")
    what_hi: str = Field(description="Deep comprehensive summary in highly readable conversational HINGLISH using Latin letters only.")
    why_en: str = Field(description="Strategic operational insight explaining why this matters to corporate ecosystems in English.")
    why_hi: str = Field(description="Detailed macro analysis in high-quality contextual Hinglish outlining why this is critical.")
    impact_en: str = Field(description="Forward-looking metrics and technical/financial expenditure impact patterns in English.")
    impact_hi: str = Field(description="Ecosystem capital trajectory and operational valuation projections detailed in pure Hinglish.")

GEMINI_KEY = os.environ.get("GEMINI_API_KEY", "")
SENDER_EMAIL = os.environ.get("SENDER_EMAIL", "vish20vijay@gmail.com")
SENDGRID_KEY = os.environ.get("SENDGRID_API_KEY", "")

client = genai.Client(api_key=GEMINI_KEY) if GEMINI_KEY else None

CACHE_DATA = None
CACHE_TIME = 0
CACHE_DURATION = 600  # 10 Minutes

def get_live_news():
    # 🌟 ULTIMATE MARKET SEARCH: Focuses strictly on Indian stocks, capex breaks, and actionable tech changes
    queries = [
        "Nifty+OR+BSE+OR+NSE+OR+infra+OR+capex+OR+acquisition+geo:India",
        "enterprise+tech+OR+cloud+computing+OR+cybersecurity+OR+datacenter"
    ]
    
    all_entries = []
    try:
        for q in queries:
            url = f"https://news.google.com/rss/search?q={q}&hl=en-IN&gl=IN&ceid=IN:en"
            feed = feedparser.parse(url)
            if feed.entries:
                # Top 4 entries fetch karenge taaki data fresh aur targeted rahe
                all_entries.extend(feed.entries[:4])  
        return all_entries[:8]
    except Exception as e:
        print(f"❌ RSS Fetch Error: {e}")
        return []

# 📋 Pydantic Wrapper ko badal kar ek Top-Level Schema banaya taaki Gemini confuse na ho
class SignalsListResponse(BaseModel):
    signals: List[SignalItemSchema]

def generate_signals_dataset():
    global CACHE_DATA, CACHE_TIME
    current_time = time.time()
    
    if CACHE_DATA and (current_time - CACHE_TIME < CACHE_DURATION):
        print("⚡ Returning Data directly from Memory Cache!")
        return CACHE_DATA

    raw_news = get_live_news()
    if not raw_news:
        return []

    # 🌟 Input payload me title ke sath index de rahe hain taaki parsing miss na ho
    news_payload = [{"index": idx, "title": item.title} for idx, item in enumerate(raw_news)]
    
    system_prompt = (
        "You are an elite Indian Stock Market Analyst, Quant Researcher, and Lead Venture Capital Director.\n"
        "Your absolute mandate is to analyze raw tech/market headlines and convert them into premium, actionable financial intelligence for active investors and professionals.\n\n"
        "CRITICAL ANALYSIS TEMPLATE RULES:\n"
        "1. Map each news item strictly to one category from the list.\n"
        "2. Do NOT use placeholder text. Generate dense, high-value custom analysis for each article.\n"
        "3. Focus heavily on market value creation, margin expansion, corporate capex tracking, and regulatory penalties.\n"
        "4. All '_hi' fields must be inside professional, clear HINGLISH using Latin script characters only (e.g., 'Is deal se infrastructure capital flow strong hoga aur short-term breakouts dikhenge'). No Devanagari text allowed."
    )
    
    processed = []
    api_success = False

    if client:
        try:
            print("🚀 Executing Strict Top-Level Schema Object Ingestion...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"{system_prompt}\n\nINPUT DATA POOL:\n{json.dumps(news_payload)}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    # 🌟 FIX: List wrapper hata kar direct response object schema bound kiya hai
                    response_schema=SignalsListResponse,
                    temperature=0.1
                ),
            )
            
            clean_text = response.text.strip()
            parsed_json = json.loads(clean_text)
            batch_data = parsed_json.get("signals", [])
            
            for idx, data in enumerate(batch_data):
                if idx >= len(raw_news): break
                processed.append({
                    "id": f"sig-{idx}",
                    "title": raw_news[idx].title, # Static array tracking fallback safety
                    "category": data.get("category", "Cloud & AI"),
                    "sentiment": data.get("sentiment", "positive"),
                    "what_en": data.get("what_en", "Domestic enterprise infrastructure update verified."),
                    "what_hi": data.get("what_hi", "Core technical framework status setup ready."),
                    "why_en": data.get("why_en", "Operational efficiency scaling asset validation check."),
                    "why_hi": data.get("why_hi", "Margin expand karne aur capability scale up karne ke liye zaroori hai."),
                    "impact_en": data.get("impact_en", "Tech expenditure reallocation models stable."),
                    "impact_hi": data.get("impact_hi", "Short-term momentum matrices par alpha expansion trend visible hai.")
                })
            
            if processed:
                api_success = True
                print(f"✅ Master System Connected! Successfully parsed {len(processed)} production signals.")

        except Exception as e:
            print(f"⚠️ Gemini API Master Layer Error: {e}")
            api_success = False
            
    # 🛡️ DYNAMIC HARD REPAIR FALLBACK (Agar API phir bhi temporary glitch kare)
    if not api_success or not processed:
        print("🔄 API Dropped: Running Hardcoded Structural Mapping Logic...")
        processed = []
        for idx, item in enumerate(raw_news):
            title = item.title
            
            # Smart category default routing
            cat = "Financial Regulations"
            if "cyber" in title.lower() or "security" in title.lower() or "train" in title.lower(): cat = "Cybersecurity"
            elif "cloud" in title.lower() or "ai" in title.lower() or "microsoft" in title.lower(): cat = "Cloud & AI"
            elif "geo" in title.lower() or "infra" in title.lower() or "share" in title.lower(): cat = "Smart Grid"
            
            processed.append({
                "id": f"fb-{idx}",
                "title": title,
                "category": cat,
                "sentiment": "positive" if "dividend" in title.lower() or "drive" in title.lower() or "deal" in title.lower() else "negative",
                "what_en": f"Market analysis tracking indicates high volume velocity actions for '{title[:50]}'. This directly correlates with corporate developments.",
                "what_hi": f"Is announcement se enterprise ecosystem me major shifts trace ho rhe hain jo framework automation ko drive karenge.",
                "why_en": f"This deployment is vital because it establishes clear enterprise dominance, optimizes vendor margins, and avoids multi-cloud platform bottlenecks.",
                "why_hi": f"Yeh factor isliye crucial h kyonki corporate capex spending aur execution capacities ko short-term me scale up karega.",
                "impact_en": f"Forward projections suggest immediate stock rating expansions and technical spending reallocations within the domestic sector.",
                "impact_hi": f"Retail portfolio allocation aur structural investment trajectories par iska strong positive trend dekhne ko mil sakta hai."
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
            requests.post("https://api.sendgrid.com/v3/mail/send", json=payload, headers=headers)          
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
