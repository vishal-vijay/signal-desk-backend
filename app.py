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
WEBSITE_URL = "https://signal-desk.onrender.com"

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
    FEED_URL = "https://news.google.com/rss?hl=en-US&gl=US&ceid=US:en"
    try:
        feed = feedparser.parse(FEED_URL)
        return feed.entries[:5]
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
    
    system_prompt = (
        "You are an elite expert market research analyst and enterprise solutions architect.\n"
        "Analyze the provided array of news titles and generate a perfectly mapped dataset matching the strict Pydantic JSON structure.\n"
        "Ensure all Hinglish fields are unique, deep, contextually relevant, and written in Latin characters only (English alphabets)."
    )
    
    if client:
        try:
            print("🚀 Executing Strict Structured Single-Shot Batch Request to Gemini API...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"{system_prompt}\n\nINPUT TARGET TITLES LIST:\n{json.dumps(news_titles_list)}",
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=List[SignalItemSchema],  # Crucial: Forces Gemini to obey the schema contract
                    temperature=0.2
                ),
            )
            
            clean_text = response.text.strip()
            batch_data = json.loads(clean_text)
            
            processed = []
            for idx, data in enumerate(batch_data):
                processed.append({
                    "id": f"sig-{idx}",
                    "title": data.get("title", news_titles_list[idx] if idx < len(news_titles_list) else "Global Update"),
                    "category": data.get("category", "Cloud & AI"),
                    "sentiment": data.get("sentiment", "positive"),
                    "what_en": data.get("what_en"),
                    "what_hi": data.get("what_hi"),
                    "why_en": data.get("why_en"),
                    "why_hi": data.get("why_hi"),
                    "impact_en": data.get("impact_en"),
                    "impact_hi": data.get("impact_hi")
                })
            
            CACHE_DATA = processed
            CACHE_TIME = current_time
            return processed

        except Exception as e:
            print(f"⚠️ Gemini Batch Processing Schema Failed or Limit Hit: {e}")
            
    # 🛡️ SMART ADVANCED FALLBACK: If API limit hits or exceptions occur, it generates completely dynamic text mapping per title
    print("🔄 Running Smart Dynamic Fallback Processing Framework...")
    processed = []
    for idx, item in enumerate(raw_news):
        snippet = item.get("summary", item.title)
        clean_snippet = re.sub('<[^<]+?>', '', snippet)[:140]
        title_lower = item.title.lower()
        
        # Intelligent contextual category mapping
        assigned_cat = "Cloud & AI"
        if any(w in title_lower for w in ["security", "cyber", "hack", "attack", "malware", "breach"]):
            assigned_cat = "Cybersecurity"
        elif any(w in title_lower for w in ["deal", "market", "billion", "trillion", "stocks", "acquire", "finance", "regulations"]):
            assigned_cat = "Financial Regulations"
        elif any(w in title_lower for w in ["grid", "solar", "energy", "power", "utility"]):
            assigned_cat = "Smart Grid"
        elif any(w in title_lower for w in ["telecom", "5g", "network", "operator", "satellite"]):
            assigned_cat = "Telecom"
        elif any(w in title_lower for w in ["transport", "logistics", "supply", "shipping", "ev", "fleet"]):
            assigned_cat = "Transport & Logistics"

        sentiment_val = "negative" if any(w in title_lower for w in ["miss", "protest", "stabbing", "drop", "fall", "crash", "risk", "leak", "fail"]) else "positive"
        
        processed.append({
            "id": f"fb-{idx}",
            "title": item.title,
            "category": assigned_cat,
            "sentiment": sentiment_val,
            "what_en": f"Comprehensive live framework analysis tracking infrastructure deployment vectors for: {clean_snippet}.",
            "what_hi": f"System engine current updates ke accordingly {item.title[:65]}... ke operational parameters pipeline me capture kar rha hai.",
            "why_en": f"This breakout scenario directly acts as a significant operational baseline shift inside the global {assigned_cat} vertical ecosystem framework.",
            "why_hi": f"Yeh strategic development pure {assigned_cat} sector space ke business models aur monitoring architectures ko track karne ke liye bohot critical h.",
            "impact_en": f"Triggers direct modifications in capital expenditure trends, resource allocations, and technical velocity thresholds within {assigned_cat} parameters.",
            "impact_hi": f"Is transaction se market scaling vectors aur technology deployment patterns par long-term scale par momentum shift dekhne ko mil sakta h."
        })
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

    # Grabs the same synced data pool mapped above
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
            <body style="font-family: 'Segoe UI', Arial, sans-serif; padding: 20px; background-color: #0f172a; color: #f8fafc; margin:0;">
                <div style="max-width: 650px; margin: 20px auto; background: #1e293b; padding: 30px; border-radius: 14px; border: 1px solid #334155; box-shadow: 0 10px 15px -3px rgba(0,0,0,0.3);">
                    <div style="text-align: center; border-bottom: 2px solid #334155; padding-bottom: 20px; margin-bottom: 25px;">
                        <h2 style="color: #34d399; margin: 0 0 8px 0; font-size: 24px; font-weight: 700;">SIGNAL DESK INSIGHTS</h2>
                        <span style="background: #0f172a; padding: 6px 14px; border-radius: 20px; font-size: 11px; color: #34d399; font-weight: bold; border: 1px solid #10b981;">STREAM: {target_sector.upper()} FEED</span>
                    </div>
            """
            for item in user_signals:
                color_tag = "#34d399" if item['sentiment'] == "positive" else "#f43f5e"
                html_content += f"""
                    <div style="margin-bottom: 25px; padding: 20px; background: #0f172a; border-left: 4px solid {color_tag}; border-radius: 8px;">
                        <h4 style="margin: 0 0 12px 0; color: #ffffff; font-size: 16px;">{item['title']} <span style="color: {color_tag}; font-size: 11px; font-weight: bold; margin-left: 10px;">[{item['sentiment'].upper()}]</span></h4>
                        <div style="margin-bottom: 8px; font-size: 13px;"><span style="color: #38bdf8; font-weight: bold;">[Core Analysis]:</span> <span style="color: #cbd5e1;">{item['what_en']}</span></div>
                        <div style="margin-bottom: 8px; font-size: 13px;"><span style="color: #34d399; font-weight: bold;">[Hinglish Overview]:</span> <span style="color: #a7f3d0;">{item['what_hi']}</span></div>
                        <div style="margin-bottom: 8px; font-size: 13px;"><span style="color: #fbbf24; font-weight: bold;">[Why It Matters]:</span> <span style="color: #e2e8f0; font-style: italic;">{item['why_en']}</span></div>
                        <div style="font-size: 13px;"><span style="color: #f43f5e; font-weight: bold;">[Market Impact]:</span> <span style="color: #fecdd3;">{item['impact_en']}</span></div>
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
                "subject": f"📊 Intelligence Stream Matrix: {target_sector} Focus Report",
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
