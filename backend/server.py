from fastapi import FastAPI, APIRouter, HTTPException, Query
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
import requests
import json
import re
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from datetime import datetime
import urllib.parse


ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")


# Define Models
class StatusCheck(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    client_name: str
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class StatusCheckCreate(BaseModel):
    client_name: str

class KeywordSuggestion(BaseModel):
    text: str
    source: str

class SuggestionResponse(BaseModel):
    query: str
    source: str
    suggestions: List[str]

# Helper function to clean Google/YouTube suggestions
def clean_google_response(text: str) -> List[str]:
    try:
        # Handle Google's JSONP format (window.google.ac.h([[...]])
        if text.startswith('window.google.ac.h('):
            # Extract the JSON part from the JSONP response
            json_str = text[text.index('(')+1:text.rindex(')')]
            data = json.loads(json_str)
            
            # Extract suggestions from Google format
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                suggestions = []
                for item in data[0]:
                    if isinstance(item, str):
                        # Remove HTML tags from suggestions
                        clean_text = re.sub(r'<[^>]+>', '', item)
                        suggestions.append(clean_text)
                return suggestions
            return []
        
        # Handle the original format as well
        elif text.startswith(')]}\''):
            text = text[4:]
            data = json.loads(text)
            
            # Extract suggestions from Google format
            if isinstance(data, list) and len(data) > 1:
                suggestions = []
                for item in data[1]:
                    if isinstance(item, list) and len(item) > 0:
                        suggestions.append(item[0])
                    elif isinstance(item, str):
                        # Remove HTML tags
                        clean_text = re.sub(r'<[^>]+>', '', item)
                        suggestions.append(clean_text)
                return suggestions
            return []
        
        # Try to parse as regular JSON
        else:
            data = json.loads(text)
            
            # Try different known Google response formats
            if isinstance(data, list):
                suggestions = []
                # Try to extract suggestions from any list structure
                for item in data:
                    if isinstance(item, list):
                        for subitem in item:
                            if isinstance(subitem, str):
                                # Remove HTML tags
                                clean_text = re.sub(r'<[^>]+>', '', subitem)
                                suggestions.append(clean_text)
                            elif isinstance(subitem, list) and len(subitem) > 0 and isinstance(subitem[0], str):
                                # Remove HTML tags
                                clean_text = re.sub(r'<[^>]+>', '', subitem[0])
                                suggestions.append(clean_text)
                    elif isinstance(item, str):
                        # Remove HTML tags
                        clean_text = re.sub(r'<[^>]+>', '', item)
                        suggestions.append(clean_text)
                return suggestions
            return []
    except Exception as e:
        logging.error(f"Error parsing Google response: {str(e)}")
        return []

def clean_amazon_response(data: dict) -> List[str]:
    try:
        suggestions = []
        if 'suggestions' in data:
            for suggestion in data['suggestions']:
                if 'value' in suggestion:
                    suggestions.append(suggestion['value'])
        return suggestions
    except:
        return []

# Add your routes to the router instead of directly to app
@api_router.get("/")
async def root():
    return {"message": "Keyword Suggestion API"}

@api_router.get("/suggestions/google", response_model=SuggestionResponse)
async def get_google_suggestions(q: str = Query(..., description="Search query")):
    try:
        encoded_query = urllib.parse.quote(q)
        url = f"http://www.google.com/complete/search?client=gws-wiz&q={encoded_query}&hl=en"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        suggestions = clean_google_response(response.text)
        
        return SuggestionResponse(
            query=q,
            source="google",
            suggestions=suggestions[:10]  # Limit to 10 suggestions
        )
    except Exception as e:
        logging.error(f"Google API error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch Google suggestions")

@api_router.get("/suggestions/amazon", response_model=SuggestionResponse)
async def get_amazon_suggestions(q: str = Query(..., description="Search query")):
    try:
        encoded_query = urllib.parse.quote(q)
        url = f"https://completion.amazon.com/api/2017/suggestions?mid=ATVPDKIKX0DER&lop=en_US&alias=aps&prefix={encoded_query}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        data = response.json()
        suggestions = clean_amazon_response(data)
        
        return SuggestionResponse(
            query=q,
            source="amazon",
            suggestions=suggestions[:10]  # Limit to 10 suggestions
        )
    except Exception as e:
        logging.error(f"Amazon API error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch Amazon suggestions")

@api_router.get("/suggestions/youtube", response_model=SuggestionResponse)
async def get_youtube_suggestions(q: str = Query(..., description="Search query")):
    try:
        encoded_query = urllib.parse.quote(q)
        url = f"http://google.com/complete/search?hl=en&client=youtube&hjson=t&ds=yt&q={encoded_query}"
        
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        suggestions = clean_google_response(response.text)
        
        return SuggestionResponse(
            query=q,
            source="youtube",
            suggestions=suggestions[:10]  # Limit to 10 suggestions
        )
    except Exception as e:
        logging.error(f"YouTube API error: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch YouTube suggestions")

@api_router.get("/suggestions/all", response_model=List[SuggestionResponse])
async def get_all_suggestions(q: str = Query(..., description="Search query")):
    """Get suggestions from all sources"""
    results = []
    
    # Get Google suggestions
    try:
        google_result = await get_google_suggestions(q)
        results.append(google_result)
    except:
        pass
    
    # Get Amazon suggestions
    try:
        amazon_result = await get_amazon_suggestions(q)
        results.append(amazon_result)
    except:
        pass
    
    # Get YouTube suggestions
    try:
        youtube_result = await get_youtube_suggestions(q)
        results.append(youtube_result)
    except:
        pass
    
    return results

@api_router.post("/status", response_model=StatusCheck)
async def create_status_check(input: StatusCheckCreate):
    status_dict = input.dict()
    status_obj = StatusCheck(**status_dict)
    _ = await db.status_checks.insert_one(status_obj.dict())
    return status_obj

@api_router.get("/status", response_model=List[StatusCheck])
async def get_status_checks():
    status_checks = await db.status_checks.find().to_list(1000)
    return [StatusCheck(**status_check) for status_check in status_checks]

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()