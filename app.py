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
CACHE_DURATION = 600  # 10 Minutes

def get_live_news():
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
                all_entries.extend(feed.entries[:4])  
        return all_entries[:8]
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

    news_input_text = ""
    for idx, item in enumerate(raw_news):
        news_input_text += f"INDEX: {idx}\nTITLE: {item.title}\n\n"
    
    system_prompt = (
        "You are an elite Indian Stock Market Analyst, Quant Researcher, and Lead Venture Capital Director.\n"
        "Analyze the provided raw headlines and convert them into premium financial intelligence. Your response must be a raw JSON array matching the layout structure below.\n\n"
        "STRICT JSON OUTPUT FORMAT EXAMPLE:\n"
        "[\n"
        "  {\n"
        "    \"index\": 0,\n"
        "    \"category\": \"Cloud & AI\",\n"
        "    \"sentiment\": \"positive\",\n"
        "    \"what_en\": \"Detailed English analysis of the disruption.\",\n"
        "    \"what_hi\": \"Comprehensive data analysis summary in Hinglish using Latin letters only.\",\n"
        "    \"why_en\": \"Strategic explanation outlining why this matters to corporate enterprise footprints.\",\n"
        "    \"why_hi\": \"Detailed macro analysis breakdown in fluent Hinglish.\",\n"
        "    \"impact_en\": \"Forward-looking financial expenditure impact trends and stock rating revisions.\",\n"
        "    \"impact_hi\": \"Ecosystem capital trajectory and short-term technical breakout projections in Hinglish.\"\n"
        "  }\n"
        "]\n\n"
        "LAWS:\n"
        "1. Map categories strictly to: 'Cloud & AI', 'Cybersecurity', 'Smart Grid', 'Telecom', 'Transport & Logistics', 'Financial Regulations'.\n"
        "2. All '_hi' fields must be in clear HINGLISH using Latin script characters only (e.g., 'Is structural move se infrastructure capital flows robust honge'). No Devanagari script allowed.\n"
        "3. Return ONLY the raw valid JSON array block. Do not wrap it in ```json blocks or include any extra text formatting."
    )
    
    processed = []
    api_success = False

    if client:
        try:
            print("🚀 Executing Direct Plaintext-Bound Batch Extraction...")
            response = client.models.generate_content(
                model='gemini-2.5-flash',
                contents=f"{system_prompt}\n\nINPUT DATA POOL:\n{news_input_text}",
            )
            
            clean_text = response.text.strip()
            if clean_text.startswith("```"):
                clean_text = re.sub(r"^
http://googleusercontent.com/immersive_entry_chip/0
