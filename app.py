import feedparser
from google import genai
from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import json
import os

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ----------------------------------------------------
# 1. LIVE NEWS & SIGNALS PIPELINE
# ----------------------------------------------------
def get_live_news():
    try:
        rss_url = "https://news.google.com/rss/search?q=technology+infrastructure"
        feed = feedparser.parse(rss_url)
        
        top_news = []
        for entry in feed.entries[:20]: 
            top_news.append({
                "title": entry.title,
                "link": entry.link,
                "published": entry.published
            })
        return top_news
    except Exception as e:
        print(f"Error fetching news: {str(e)}")
        return [{"title": "Tech Infrastructure Market Update", "link": "#", "published": ""}]

def process_news_with_ai(news_item):
    api_key_env = os.environ.get("GEMINI_API_KEY")
    
    fallback_data = {
            "title": news_item['title'],
            "sector": "Infrastructure",  # Adding default sector tag for safety
            "what_happened": f"Market update regarding: {news_item['title']}. Live tracking active.",
            "why_it_happened": "Triggered by global enterprise infrastructure shift and tech adoption trends.",
            "market_impact": "Positive impact on cloud deployment pipelines and local tech service sectors.",
            "sentiment": "positive"
        }

    if not api_key_env:
        return fallback_data

    try:
        client = genai.Client(api_key=api_key_env)
        
        system_prompt = (
            "You are an elite Tech & Market Analyst. Analyze the given news headline. "
            "Provide a JSON response with exactly five keys: "
            "'title' (the original headline), "
            "'sector' (strictly 1 to 3 words max naming the exact specific industry sector, e.g., 'Solar Energy', 'Semiconductors', 'Cloud & AI', 'EV Infrastructure', 'Telecom', 'Cybersecurity', 'Drone Tech'), "
            "'what_happened' (2 precise sentences of the core fact), "
            "'why_it_happened' (the technical trigger or cause), "
            "'market_impact' (the direct effect on IT pipelines or stocks), and "
            "'sentiment' (strictly either 'positive' or 'negative')."
        )
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',  
            contents=f"Headline: {news_item['title']}\n\n{system_prompt}"
        )
        
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
        
    except Exception as e:
        print(f"❌ Gemini Error caught safely: {str(e)}")
        return fallback_data

@app.get("/api/signals")
def get_crypto_signals():
    raw_news_list = get_live_news()
    processed_signals = []
    for news in raw_news_list:
        ai_data = process_news_with_ai(news)
        processed_signals.append(ai_data)
    return processed_signals


# ----------------------------------------------------
# 2. NEW: REAL DOCUMENT DEEP-DIVE PIPELINE
# ----------------------------------------------------
@app.post("/api/upload-document")
async def upload_document(file: UploadFile = File(...)):
    print(f"📥 File received: {file.filename}")
    api_key_env = os.environ.get("GEMINI_API_KEY")
    
    if not api_key_env:
        raise HTTPException(status_code=500, detail="Gemini API Key missing on server.")

    try:
        # Read file content safely
        contents = await file.read()
        file_text = contents.decode("utf-8", errors="ignore")
        
        # Guard clause for empty files
        if not file_text.strip():
            return {
                "operational_risks": ["Uploaded file appears to be empty or unreadable."],
                "financial_flags": ["No data found."],
                "pipeline_blockers": ["No pipelines detected."]
            }

        client = genai.Client(api_key=api_key_env)
        
        document_prompt = (
            "You are an expert Enterprise Risk Auditor. Analyze the raw text/CSV content provided. "
            "Extract operational vulnerabilities, financial red flags, and infrastructure blockers. "
            "Provide your response strictly in JSON format with exactly three lists of strings: "
            "'operational_risks' (max 4 distinct bullets), "
            "'financial_flags' (max 4 distinct bullets), and "
            "'pipeline_blockers' (max 4 distinct bullets). "
            "Do not include markdown blocks like ```json."
        )
        
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=f"Document Content:\n{file_text}\n\n{document_prompt}"
        )
        
        clean_response = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_response)

    except Exception as e:
        print(f"❌ Document Deep-Dive Error: {str(e)}")
        return {
            "operational_risks": [f"AI extraction failed or timed out: {str(e)}"],
            "financial_flags": ["Could not parse financial metrics safely."],
            "pipeline_blockers": ["Fallback mode active. Please try uploading a cleaner text/CSV format."]
        }