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
    # 🌟 THE HYBRID INDO-GLOBAL INGESTION SYSTEM: Focuses on premium Global Tech shifts 
    # AND core Indian Corporate Markets, Nifty/BSE sectoral indices, and Infra developments.
    queries = [
        "enterprise+tech+OR+cloud+computing+OR+cybersecurity",
        "Nifty+OR+BSE+OR+NSE+OR+infra+OR+corporate+capex+geo:India"
    ]
    
    all_entries = []
    try:
        for q in queries:
            url = f"https://news.google.com/rss/search?q={q}&hl=en-US&gl=US&ceid=US:en"
            feed = feedparser.parse(url)
            if feed.entries:
                all_entries.extend(feed.entries[:4])  # Balanced 4 from global tech, 4 from Indian macros
        return all_entries[:8]
    except Exception:
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

    news_titles_list = [item.title for item in raw_news]
    
    # 🌟 ACTIONABLE PREMIUM PROMPT: Delivers deep macro-financial context like an elite quant/strategist
    system_prompt = (
        "You are an elite Lead Venture Capitalist and Indian Stock Market Strategic Advisor.\n"
        "Your role is to cut through generic news noise and deliver sharp, high-conviction market alpha and technical intelligence for professionals and active practitioners.\n\n"
        "STRICT INGESTION AND FILTERING LAWS:\n"
        "1. Discard any generic global political drama that does not directly impact structural enterprise spending, macro capex trajectories, or domestic tech frameworks.\n"
        "2. Strictly map 'category' to one of these production verticals: 'Cloud & AI', 'Cybersecurity', 'Smart Grid', 'Telecom', 'Transport & Logistics', 'Financial Regulations'.\n"
        "3. Focus on capital allocations, infrastructure orders, tech data-breaches, regulatory compliance audits, and asset expansions.\n\n"
        "VALUE EXTRACTION MATRIX FOR USERS:\n"
        "- what_en / what_hi: Crisp, metric-focused tracking of the exact event or technical breakthrough that just triggered.\n"
        "- why_en / why_hi: Why does this matter for systemic scalability, portfolio allocation, or vendor locks? Focus on margin expansions or policy disruptions.\n"
        "- impact_en / impact_hi: Sector re-rating, long-term technical expenditures reallocation models, or localized capital trajectory projections.\n\n"
        "Write all '_hi' responses in high-energy, fluent, professional HINGLISH using Latin letters only (e.g., 'Is corporate capex push se logistics aur infra providers ko long-term momentum milega'). Keep it clean and impactful."
    )
    
    processed = []
    api_success = False

    if client:
        try:
            print("🚀 Executing Strict JSON-Mime Indo-Global Ingestion Pipeline...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"{system_prompt}\n\nINPUT TARGET TITLES LIST:\n{json.dumps(news_titles_list)}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    temperature=0.15  # Strict analytical mapping consistency
                ),
            )
            
            clean_text = response.text.strip()
            batch_data = json.loads(clean_text)
            
            for idx, data in enumerate(batch_data):
                processed.append({
                    "id": f"sig-{idx}",
                    "title": data.get("title", news_titles_list[idx] if idx < len(news_titles_list) else "Market Update"),
                    "category": data.get("category", "Cloud & AI"),
                    "sentiment": data.get("sentiment", "positive"),
                    "what_en": data.get("what_en", "Domestic infrastructure baseline capability verified."),
                    "what_hi": data.get("what_hi", "Indian corporate tech parameters update complete."),
                    "why_en": data.get("why_en", "Sector re-rating and operational valuation momentum check."),
                    "why_hi": data.get("why_hi", "Margin expansion aur structural volume scaling ke liye yeh parameter critical hai."),
                    "impact_en": data.get("impact_en", "Capex spending projections and retail stock trajectories stable."),
                    "impact_hi": data.get("impact_hi", "Short-term swing trajectory aur technical breakout matrix par sharp positive indices visible hain.")
                })
            api_success = True
            print("✅ Dynamic Indo-Global analytical datasets locked successfully!")

        except Exception as e:
            print(f"⚠️ Gemini API Layer Processing Failed: {e}")
            api_success = False
            
    # 🛡️ BULLET-PROOF DYNAMIC FALLBACK SYSTEM (If API drops or data is empty)
    if not api_success or not processed:
        print("🔄 Executing Dynamic Content Generation Logic on Fallback Level...")
        processed = []
        for idx, item in enumerate(raw_news):
            title = item.title
            short_title = title.split(" - ")[0]
            
            assigned_cat = "Cloud & AI"
            if any(w in title.lower() for w in ["security", "cyber", "hack", "attack", "breach", "fund", "block"]): 
                assigned_cat = "Cybersecurity"
            elif any(w in title.lower() for w in ["deal", "peace", "market", "billion", "trillion", "nifty", "bse", "nse", "order"]): 
                assigned_cat = "Financial Regulations"
                
            sentiment_val = "negative" if any(w in title.lower() for w in ["miss", "deadline", "storm", "attack", "block", "drop", "loss"]) else "positive"
            
            processed.append({
                "id": f"fb-{idx}",
                "title": title,
                "category": assigned_cat,
                "sentiment": sentiment_val,
                "what_en": f"The development concerning '{short_title}' is triggering market infrastructure tracking. Monitoring updates confirm critical operational changes across frameworks.",
                "what_hi": f"Latest market indicators ke mutabik '{short_title[:50]}' ka direct correlation structural parameters se trace kiya ja rha hai.",
                "why_en": f"Understanding the catalyst behind '{short_title[:40]}' is essential for risk mitigation, policy mapping, and overall strategic sector re-alignments.",
                "why_hi": f"Yeh scenario isliye matter karta h kyonki isse structural ecosystem tracking aur monitoring systems par direct breakout effect padta h.",
                "impact_en": f"This dynamic shift alters capital allocation velocities, asset frameworks, and operational spending trajectory models inside the {assigned_cat} sector.",
                "impact_hi": f"Is complete event analysis se long-term perspective par macro indices scale up honge aur overall sectoral spending matrices par momentum dikh sakta h."
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
