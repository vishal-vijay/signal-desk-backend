import feedparser
from google import genai
from fastapi import FastAPI
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

def get_live_news():
    rss_url = "https://news.google.com/rss/search?q=technology+infrastructure"
    feed = feedparser.parse(rss_url)
    
    top_news = []
    # Sirf top 2 khabrein uthate hain taaki fast load ho aur timeout na ho
    for entry in feed.entries[:2]: 
        top_news.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published
        })
    return top_news

def process_news_with_ai(news_item):
    api_key_env = os.environ.get("GEMINI_API_KEY")
    
    # AGAR KEY MISSING HAI TOH CRASH HONE KE BADLE DEFAULT DATA DEGA
    if not api_key_env:
        return {
            "title": news_item['title'],
            "what_happened": "API Key is missing in Render settings.",
            "why_it_happened": "Please check Environment Variables.",
            "market_impact": "Configuration required.",
            "sentiment": "negative"
        }

    try:
        client = genai.Client(api_key=api_key_env)
        
        system_prompt = (
            "You are an elite Tech & Market Analyst. Analyze the given news headline. "
            "Provide a JSON response with exactly four keys: "
            "'title' (the original headline), "
            "'what_happened' (2 precise sentences of the core fact), "
            "'why_it_happened' (the technical trigger or cause), "
            "'market_impact' (the direct effect on IT pipelines or stocks), and "
            "'sentiment' (strictly either 'positive' or 'negative')."
        )
        
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=f"Headline: {news_item['title']}\n\n{system_prompt}"
        )
        
        # Safe JSON parsing
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
        
    except Exception as e:
        # AGAR GEMINI CRASH BHI HO JAYE, TOH SYSTEM 500 ERROR NAHI DEGA
        print(f"❌ Error in AI Processing: {str(e)}")
        return {
            "title": news_item['title'],
            "what_happened": "Live news extracted successfully, but AI processing failed.",
            "why_it_happened": f"Triggered by: {str(e)[:50]}",
            "market_impact": "Check backend logs for full details.",
            "sentiment": "positive"
        }

@app.get("/api/signals")
def get_crypto_signals():
    print("🚀 Request received! Running live production pipeline...")
    try:
        raw_news_list = get_live_news()
        processed_signals = []
        for news in raw_news_list:
            ai_data = process_news_with_ai(news)
            processed_signals.append(ai_data)
        return processed_signals
    except Exception as main_err:
        return [{"title": "Pipeline Error", "what_happened": str(main_err)}]