import feedparser
from google import genai
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
import os

app = FastAPI()

# CORS Setup: Taaki Lovable frontend isse baat kar sake
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
    for entry in feed.entries[:3]: # Top 3 live khabrein
        top_news.append({
            "title": entry.title,
            "link": entry.link,
            "published": entry.published
        })
    return top_news

def process_news_with_ai(news_item):
    # SECURITY FIX: Yeh automatic aapke computer ya cloud ki settings se key uthayega
# Brackets ke andar sirf ek NAAM (Variable) rakhna hai, asali key nahi!
    api_key_env = os.environ.get("GEMINI_API_KEY")

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
    
    try:
        clean_text = response.text.replace("```json", "").replace("```", "").strip()
        return json.loads(clean_text)
    except:
        return {
            "title": news_item['title'],
            "what_happened": response.text,
            "why_it_happened": "Analysis done.",
            "market_impact": "Analysis done.",
            "sentiment": "positive"
        }

@app.get("/api/signals")
def get_crypto_signals():
    print("🚀 Request received! Running pipeline...")
    raw_news_list = get_live_news()
    
    processed_signals = []
    for news in raw_news_list:
        ai_data = process_news_with_ai(news)
        processed_signals.append(ai_data)
        
    return processed_signals