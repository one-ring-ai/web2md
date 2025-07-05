import os
from typing import List, Dict
import sqlite3
import uuid
import datetime
import json as json_module
import time
import threading
from concurrent.futures import ThreadPoolExecutor

from pydantic import BaseModel

from dotenv import load_dotenv
import httpx
from fastapi import FastAPI, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse

from bs4 import BeautifulSoup, Comment
import json
import html2text
from youtube_transcript_api import YouTubeTranscriptApi
import re

load_dotenv()

SEARXNG_URL = os.getenv('SEARXNG_URL')
BROWSERLESS_URL = os.getenv('BROWSERLESS_URL')
TOKEN = os.getenv('BROWSERLESS_TOKEN')
PROXY_PROTOCOL = os.getenv('PROXY_PROTOCOL', 'http')
PROXY_URL = os.getenv('PROXY_URL')
PROXY_USERNAME = os.getenv('PROXY_USERNAME')
PROXY_PASSWORD = os.getenv('PROXY_PASSWORD')
PROXY_PORT = os.getenv('PROXY_PORT')

REQUEST_TIMEOUT = int(os.getenv('REQUEST_TIMEOUT', '30'))

FILTER_SEARCH_RESULT_BY_AI = os.getenv('FILTER_SEARCH_RESULT_BY_AI', 'false').lower() == 'true'

AI_API_KEY = os.getenv('WEB2MD_LLM_API_KEY')
AI_MODEL = os.getenv('AI_MODEL', 'gpt-3.5-turbo')
AI_BASE_URL = os.getenv('AI_BASE_URL', 'https://api.openai.com/v1')

MAX_IMAGES_PER_SITE = int(os.getenv('MAX_IMAGES_PER_SITE', '3'))
MIN_IMAGE_SIZE = int(os.getenv('MIN_IMAGE_SIZE', '256'))
MAX_TOKENS_PER_REQUEST = int(os.getenv('MAX_TOKENS_PER_REQUEST', '100000'))

# Auto-research feature settings
AUTO_MAX_REQUESTS = int(os.getenv('AUTO_MAX_REQUESTS', '5'))
AUTO_MAX_CONTEXT_TOKENS = int(os.getenv('AUTO_MAX_CONTEXT_TOKENS', '850000'))
DB_CLEANUP_RETENTION_DAYS = int(os.getenv('DB_CLEANUP_RETENTION_DAYS', '90'))

# YouTube Rate Limit Protection
class YouTubeRateLimitManager:
    _disabled_until = None
    _disable_duration = 3600  # 1 hour in seconds
    _lock = threading.Lock()
    
    @classmethod
    def is_youtube_blocked_error(cls, error_message: str) -> bool:
        """Check if error indicates YouTube rate limiting"""
        blocking_indicators = [
            "YouTube is blocking requests from your IP",
            "You have done too many requests",
            "IP has been blocked by YouTube",
            "requests from an IP belonging to a cloud provider",
            "most IPs from cloud providers are blocked"
        ]
        return any(indicator in str(error_message) for indicator in blocking_indicators)
    
    @classmethod
    def disable_videos_temporarily(cls):
        """Disable video endpoint for 1 hour due to rate limiting"""
        with cls._lock:
            cls._disabled_until = time.time() + cls._disable_duration
            print(f"🚫 YouTube rate limit detected! Disabling video endpoint for {cls._disable_duration//60} minutes to prevent permanent ban.")
    
    @classmethod
    def is_videos_disabled(cls) -> bool:
        """Check if video endpoint is currently disabled"""
        with cls._lock:
            if cls._disabled_until is None:
                return False
            
            if time.time() >= cls._disabled_until:
                cls._disabled_until = None
                print("✅ Video endpoint re-enabled after cooldown period.")
                return False
            
            return True
    
    @classmethod
    def get_remaining_cooldown(cls) -> int:
        """Get remaining cooldown time in seconds"""
        with cls._lock:
            if cls._disabled_until is None:
                return 0
            remaining = max(0, int(cls._disabled_until - time.time()))
            return remaining

domains_only_for_browserless = ["twitter", "x", "facebook", "ucarspro"]

# Database setup
DB_PATH = "web2md.db"

def init_database():
    """Initialize SQLite database with required tables"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create responses table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS responses (
            id TEXT PRIMARY KEY,
            user_query TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            result TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            completed_at TIMESTAMP,
            total_tokens INTEGER DEFAULT 0,
            total_cost REAL DEFAULT 0.0
        )
    ''')
    
    # Create response_steps table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS response_steps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            response_id TEXT NOT NULL,
            step_number INTEGER NOT NULL,
            endpoint TEXT NOT NULL,
            query_used TEXT NOT NULL,
            summary TEXT,
            full_response TEXT,
            tokens_used INTEGER DEFAULT 0,
            message_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (response_id) REFERENCES responses (id)
        )
    ''')
    
    # Create queue table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS queue (
            id TEXT PRIMARY KEY,
            status TEXT NOT NULL DEFAULT 'pending',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create indexes for performance
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_responses_status ON responses (status)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_responses_created_at ON responses (created_at)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_response_steps_response_id ON response_steps (response_id)')
    cursor.execute('CREATE INDEX IF NOT EXISTS idx_queue_status ON queue (status)')
    
    conn.commit()
    conn.close()

def get_db_connection():
    """Get a database connection"""
    return sqlite3.connect(DB_PATH)

# Initialize database on startup
init_database()

# Database operations
class DatabaseManager:
    @staticmethod
    def create_response(user_query: str) -> str:
        """Create a new response record and return its ID"""
        response_id = str(uuid.uuid4())
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO responses (id, user_query, status) VALUES (?, ?, ?)',
            (response_id, user_query, 'pending')
        )
        conn.commit()
        conn.close()
        return response_id
    
    @staticmethod
    def update_response_status(response_id: str, status: str, result: str = None, total_tokens: int = None, total_cost: float = None):
        """Update response status and optionally result"""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        update_fields = ['status = ?']
        values = [status]
        
        if result is not None:
            update_fields.append('result = ?')
            values.append(result)
        
        if total_tokens is not None:
            update_fields.append('total_tokens = ?')
            values.append(total_tokens)
            
        if total_cost is not None:
            update_fields.append('total_cost = ?')
            values.append(total_cost)
        
        if status == 'completed':
            update_fields.append('completed_at = ?')
            values.append(datetime.datetime.now().isoformat())
        
        values.append(response_id)
        
        cursor.execute(
            f'UPDATE responses SET {", ".join(update_fields)} WHERE id = ?',
            values
        )
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_response(response_id: str) -> dict:
        """Get response by ID"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM responses WHERE id = ?', (response_id,))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            return {
                'id': row[0],
                'user_query': row[1],
                'status': row[2],
                'result': row[3],
                'created_at': row[4],
                'completed_at': row[5],
                'total_tokens': row[6],
                'total_cost': row[7]
            }
        return None
    
    @staticmethod
    def add_response_step(response_id: str, step_number: int, endpoint: str, query_used: str, 
                         summary: str = None, full_response: str = None, tokens_used: int = 0, message_id: str = None):
        """Add a step to the response"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO response_steps 
            (response_id, step_number, endpoint, query_used, summary, full_response, tokens_used, message_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (response_id, step_number, endpoint, query_used, summary, full_response, tokens_used, message_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_response_steps(response_id: str) -> List[dict]:
        """Get all steps for a response"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM response_steps WHERE response_id = ? ORDER BY step_number', (response_id,))
        rows = cursor.fetchall()
        conn.close()
        
        return [{
            'id': row[0],
            'response_id': row[1],
            'step_number': row[2],
            'endpoint': row[3],
            'query_used': row[4],
            'summary': row[5],
            'full_response': row[6],
            'tokens_used': row[7],
            'message_id': row[8],
            'created_at': row[9]
        } for row in rows]
    
    @staticmethod
    def add_to_queue(request_id: str):
        """Add request to queue"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('INSERT INTO queue (id, status) VALUES (?, ?)', (request_id, 'pending'))
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_next_in_queue() -> str:
        """Get next pending request from queue"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id FROM queue WHERE status = ? ORDER BY created_at LIMIT 1', ('pending',))
        row = cursor.fetchone()
        conn.close()
        return row[0] if row else None
    
    @staticmethod
    def update_queue_status(request_id: str, status: str):
        """Update queue item status"""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('UPDATE queue SET status = ? WHERE id = ?', (status, request_id))
        conn.commit()
        conn.close()
    
    @staticmethod
    def cleanup_old_records():
        """Clean up records older than retention period"""
        cutoff_date = datetime.datetime.now() - datetime.timedelta(days=DB_CLEANUP_RETENTION_DAYS)
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get old response IDs
        cursor.execute('SELECT id FROM responses WHERE created_at < ?', (cutoff_date.isoformat(),))
        old_response_ids = [row[0] for row in cursor.fetchall()]
        
        # Delete old response steps
        for response_id in old_response_ids:
            cursor.execute('DELETE FROM response_steps WHERE response_id = ?', (response_id,))
        
        # Delete old responses
        cursor.execute('DELETE FROM responses WHERE created_at < ?', (cutoff_date.isoformat(),))
        
        # Delete old queue items
        cursor.execute('DELETE FROM queue WHERE created_at < ?', (cutoff_date.isoformat(),))
        
        conn.commit()
        conn.close()
        print(f"Cleaned up {len(old_response_ids)} old records")

# LLM Decision Schemas
class LLMDecision(BaseModel):
    should_continue: bool
    confidence: float  # 0.0 to 1.0
    reasoning: str
    next_action: str = None  # 'search', 'videos', 'images', or 'stop'
    adapted_query: str = None

class LLMFinalResponse(BaseModel):
    markdown_response: str
    summary: str

class AutoResearchResult(BaseModel):
    markdown_response: str
    media_references: dict
    metadata: dict
    websearch_price: float

def create_decision_prompt(user_query: str, current_step: int, previous_summaries: List[str], total_tokens: int) -> str:
    """Create prompt for LLM decision making"""
    
    # Check if videos are currently disabled
    videos_status = ""
    if YouTubeRateLimitManager.is_videos_disabled():
        remaining = YouTubeRateLimitManager.get_remaining_cooldown()
        videos_status = f"\n⚠️  IMPORTANT: 'videos' endpoint is temporarily DISABLED due to YouTube rate limiting (cooldown: {remaining//60} minutes remaining). DO NOT choose 'videos' as next_action."
    
    context = f"""
You are an intelligent research assistant. You've been asked to research: "{user_query}"

Current Status:
- Step: {current_step}/{AUTO_MAX_REQUESTS}
- Total tokens used so far: {total_tokens:,}
- Token limit: {AUTO_MAX_CONTEXT_TOKENS:,}{videos_status}

Previous research summaries:
{chr(10).join([f"Step {i+1}: {summary}" for i, summary in enumerate(previous_summaries)])}

Your task is to decide whether you have enough information to provide a comprehensive answer to the user's query, or if you need to gather more information.

Available actions:
- 'search': Get more web content (general articles, documentation, guides)
- 'videos': Get video tutorials, demonstrations, or explanations{' (CURRENTLY DISABLED)' if YouTubeRateLimitManager.is_videos_disabled() else ''}
- 'images': Get visual content, diagrams, screenshots, or illustrations
- 'stop': You have sufficient information to provide a comprehensive answer

If you decide to continue, adapt the original query to be more specific for the chosen endpoint.

Example adaptations:
- Original: "How to implement authentication in web apps"
- For videos: "web authentication tutorial step by step"
- For images: "authentication flow diagram web security"
- For search: "web application authentication implementation best practices"

CRITICAL: You must respond with EXACTLY this JSON structure (no other fields):
{{
  "should_continue": true or false,
  "confidence": 0.8,
  "reasoning": "Why you made this decision",
  "next_action": "search" or "videos" or "images" or "stop",
  "adapted_query": "Modified query for the chosen endpoint"
}}

Example valid responses:
{{
  "should_continue": true,
  "confidence": 0.7,
  "reasoning": "Need more visual examples to understand the concepts better",
  "next_action": "images",
  "adapted_query": "python testing diagram examples"
}}

{{
  "should_continue": false,
  "confidence": 0.9,
  "reasoning": "Have comprehensive information covering all aspects of the topic",
  "next_action": "stop",
  "adapted_query": null
}}
"""
    return context

def create_final_response_prompt(user_query: str, all_summaries: List[str], collected_data: List[dict]) -> str:
    """Create prompt for final response generation"""
    return f"""
You are an expert research assistant. You have conducted comprehensive research on: "{user_query}"

Research Data Collected:
{chr(10).join([f"Step {i+1} ({data['endpoint']}): {data['summary']}" for i, data in enumerate(collected_data)])}

Your task is to create a comprehensive, well-structured markdown response that:

1. Directly addresses the user's query
2. Synthesizes information from all research steps
3. Includes proper markdown formatting (headers, lists, code blocks, etc.)
4. References sources appropriately
5. Is thorough but concise
6. Provides actionable information

Guidelines:
- Use markdown formatting for clear structure
- Include relevant links where appropriate
- Organize information logically
- Provide a brief summary at the end
- Make it comprehensive yet readable

Generate a complete markdown response that fully answers the user's query using all the research data.
"""

# Token Management
class TokenManager:
    @staticmethod
    def count_tokens(text: str) -> int:
        """Estimate token count using existing function"""
        return estimate_tokens(text)
    
    @staticmethod
    def is_within_limit(current_tokens: int, new_content: str) -> bool:
        """Check if adding new content would exceed token limit with tolerance"""
        new_tokens = TokenManager.count_tokens(new_content)
        total_tokens = current_tokens + new_tokens
        # Allow 50k tolerance as specified
        return total_tokens <= (AUTO_MAX_CONTEXT_TOKENS + 50000)
    
    @staticmethod
    def truncate_content(content: str, max_tokens: int) -> str:
        """Truncate content to fit within token limit"""
        current_tokens = TokenManager.count_tokens(content)
        if current_tokens <= max_tokens:
            return content
        
        # Rough estimation: 1 token ≈ 4 characters
        max_chars = max_tokens * 4
        truncated = content[:max_chars]
        return truncated + "\n\n[Content truncated due to token limit]"
    
    @staticmethod
    def prepare_context_summaries(steps: List[dict], max_tokens: int) -> List[str]:
        """Prepare summaries ensuring they fit within token limit"""
        summaries = []
        current_tokens = 0
        
        for step in steps:
            summary = step.get('summary', '')
            summary_tokens = TokenManager.count_tokens(summary)
            
            if current_tokens + summary_tokens <= max_tokens:
                summaries.append(summary)
                current_tokens += summary_tokens
            else:
                # Truncate this summary to fit
                remaining_tokens = max_tokens - current_tokens
                if remaining_tokens > 100:  # Only add if reasonable space left
                    truncated_summary = TokenManager.truncate_content(summary, remaining_tokens)
                    summaries.append(truncated_summary)
                break
        
        return summaries

# Core Auto-Research Logic
class AutoResearcher:
    @staticmethod
    def process_request(request_id: str, user_query: str) -> dict:
        """Main entry point for processing auto-research requests"""
        try:
            print(f"Starting auto-research for request {request_id}: {user_query}")
            
            # Initialize message IDs tracking
            AutoResearcher._current_message_ids = []
            
            total_tokens = 0
            step_number = 1
            collected_data = []
            
            # Step 1: Initial search (always performed)
            print(f"Step {step_number}: Performing initial search")
            search_result = AutoResearcher._call_search_endpoint(user_query, num_results=5)
            
            if search_result:
                step_summary = AutoResearcher._create_summary(search_result, 'search')
                step_tokens = TokenManager.count_tokens(str(search_result))
                total_tokens += step_tokens
                
                # Store step in database
                DatabaseManager.add_response_step(
                    request_id, step_number, 'search', user_query,
                    summary=step_summary, full_response=str(search_result),
                    tokens_used=step_tokens
                )
                
                collected_data.append({
                    'endpoint': 'search',
                    'query': user_query,
                    'summary': step_summary,
                    'data': search_result,
                    'tokens': step_tokens
                })
                
                step_number += 1
            else:
                raise Exception("Initial search failed")
            
            # Continue with additional steps if needed
            while step_number <= AUTO_MAX_REQUESTS:
                # Check token limit
                if total_tokens >= AUTO_MAX_CONTEXT_TOKENS:
                    print(f"Token limit reached: {total_tokens:,} tokens")
                    break
                
                # Get previous summaries for context
                previous_summaries = [data['summary'] for data in collected_data]
                context_summaries = TokenManager.prepare_context_summaries(
                    collected_data, 
                    AUTO_MAX_CONTEXT_TOKENS // 4  # Use 1/4 of limit for context
                )
                
                # Ask LLM for decision
                decision = AutoResearcher._get_llm_decision(
                    user_query, step_number, context_summaries, total_tokens
                )
                
                if not decision or not decision.should_continue:
                    print(f"LLM decided to stop at step {step_number}")
                    break
                
                if decision.next_action == 'stop':
                    break
                
                # Execute the next action
                result = None
                if decision.next_action == 'search':
                    result = AutoResearcher._call_search_endpoint(decision.adapted_query, num_results=3)
                elif decision.next_action == 'videos':
                    result = AutoResearcher._call_videos_endpoint(decision.adapted_query, num_results=3)
                elif decision.next_action == 'images':
                    result = AutoResearcher._call_images_endpoint(decision.adapted_query, num_results=5)
                
                if result:
                    step_summary = AutoResearcher._create_summary(result, decision.next_action)
                    step_tokens = TokenManager.count_tokens(str(result))
                    
                    # Check if adding this would exceed token limit
                    if not TokenManager.is_within_limit(total_tokens, str(result)):
                        print(f"Adding step {step_number} would exceed token limit")
                        break
                    
                    total_tokens += step_tokens
                    
                    # Store step in database
                    DatabaseManager.add_response_step(
                        request_id, step_number, decision.next_action, decision.adapted_query,
                        summary=step_summary, full_response=str(result),
                        tokens_used=step_tokens
                    )
                    
                    collected_data.append({
                        'endpoint': decision.next_action,
                        'query': decision.adapted_query,
                        'summary': step_summary,
                        'data': result,
                        'tokens': step_tokens
                    })
                    
                    step_number += 1
                else:
                    print(f"Step {step_number} failed, continuing...")
                    step_number += 1
            
            # Generate final response
            final_result = AutoResearcher._generate_final_response(
                user_query, collected_data, total_tokens
            )
            
            # Calculate costs from tracked message IDs
            message_ids = getattr(AutoResearcher, '_current_message_ids', [])
            total_cost = AutoResearcher._calculate_total_cost(message_ids)
            final_result['websearch_price'] = total_cost
            
            print(f"Auto-research completed for request {request_id}")
            return final_result
            
        except Exception as e:
            print(f"Error in auto-research for request {request_id}: {e}")
            
            # Create a fallback error response
            error_response = {
                "markdown_response": f"# Error Processing Request\n\nAn error occurred while processing your research request: {str(e)}\n\nPartial results may have been collected.",
                "media_references": {"videos": [], "images": []},
                "metadata": {
                    "total_requests_used": len(collected_data) if 'collected_data' in locals() else 0,
                    "endpoints_called": [data['endpoint'] for data in collected_data] if 'collected_data' in locals() else [],
                    "queries_used": [data['query'] for data in collected_data] if 'collected_data' in locals() else [],
                    "total_tokens": total_tokens if 'total_tokens' in locals() else 0,
                    "error": str(e)
                },
                "websearch_price": 0.0
            }
            
            return error_response
    
    @staticmethod
    def _call_search_endpoint(query: str, num_results: int = 5) -> dict:
        """Call the internal search endpoint"""
        try:
            # Use the existing search function
            result = search(query, num_results, json_response=True)
            # Extract the actual data from JSONResponse
            if hasattr(result, 'body'):
                import json
                return json.loads(result.body.decode())
            return result
        except Exception as e:
            print(f"Search endpoint error: {e}")
            return None
    
    @staticmethod
    def _call_videos_endpoint(query: str, num_results: int = 3) -> dict:
        """Call the internal videos endpoint"""
        try:
            # Check if videos are disabled due to rate limiting
            if YouTubeRateLimitManager.is_videos_disabled():
                remaining = YouTubeRateLimitManager.get_remaining_cooldown()
                print(f"🚫 Skipping video search - disabled for {remaining//60} more minutes due to YouTube rate limiting")
                return None
            
            # Use the existing searxng function for videos
            result_list = searxng(query, categories="videos")
            results = result_list["results"] if isinstance(result_list, dict) and "results" in result_list else result_list
            
            # Apply AI reranking if enabled
            if FILTER_SEARCH_RESULT_BY_AI:
                try:
                    ai_input = {"query": query, "results": results}
                    reranked_results = reranker_ai_videos(ai_input)
                    results = reranked_results["results"]
                except Exception as e:
                    print(f"AI reranking failed for videos in auto-research: {e}")
                    # Continue with non-reranked results
            
            return results[:num_results]
        except Exception as e:
            error_msg = str(e)
            print(f"Videos endpoint error: {error_msg}")
            
            # Check if this error indicates YouTube rate limiting
            if YouTubeRateLimitManager.is_youtube_blocked_error(error_msg):
                YouTubeRateLimitManager.disable_videos_temporarily()
            
            return None
    
    @staticmethod
    def _call_images_endpoint(query: str, num_results: int = 5) -> dict:
        """Call the internal images endpoint"""
        try:
            # Use the existing searxng function for images
            result_list = searxng(query, categories="images")
            results = result_list["results"] if isinstance(result_list, dict) and "results" in result_list else result_list
            
            # Apply AI reranking if enabled
            if FILTER_SEARCH_RESULT_BY_AI:
                ai_input = {"query": query, "results": results}
                reranked_results = reranker_ai_images(ai_input)
                results = reranked_results["results"]
            
            return results[:num_results]
        except Exception as e:
            print(f"Images endpoint error: {e}")
            return None
    
    @staticmethod
    def _create_summary(data: any, endpoint_type: str) -> str:
        """Create a summary of the step results"""
        if not data:
            return "No data retrieved"
        
        if endpoint_type == 'search':
            if isinstance(data, list) and len(data) > 0:
                titles = [item.get('title', 'No title') for item in data[:3]]
                return f"Retrieved {len(data)} search results: {', '.join(titles)}"
        elif endpoint_type == 'videos':
            if isinstance(data, list) and len(data) > 0:
                titles = [item.get('title', 'No title') for item in data[:3]]
                return f"Found {len(data)} videos: {', '.join(titles)}"
        elif endpoint_type == 'images':
            if isinstance(data, list) and len(data) > 0:
                sources = [item.get('source', 'Unknown source') for item in data[:3]]
                return f"Retrieved {len(data)} images from: {', '.join(sources)}"
        
        return f"Retrieved data from {endpoint_type} endpoint"
    
    @staticmethod
    def _get_llm_decision(user_query: str, current_step: int, previous_summaries: List[str], total_tokens: int) -> LLMDecision:
        """Get LLM decision for next action"""
        if not AI_API_KEY or not AI_BASE_URL:
            return None
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                import openai
                client = openai.OpenAI(
                    api_key=AI_API_KEY,
                    base_url=AI_BASE_URL,
                    default_headers={
                        "HTTP-Referer": "https://github.com/lucanori/web2md",
                        "X-Title": "Web2MD"
                    }
                )
                
                prompt = create_decision_prompt(user_query, current_step, previous_summaries, total_tokens)
                
                response = client.chat.completions.create(
                    model=AI_MODEL,
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an intelligent research assistant. Analyze the research progress and decide on the next action. Respond only with valid JSON matching the LLMDecision schema."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.3,
                    max_tokens=1000,
                    response_format={"type": "json_object"}
                )
                
                # Track message ID for cost calculation
                message_id = response.id if hasattr(response, 'id') else None
                if message_id:
                    # Store message ID in a way that can be accessed by the main process
                    # We'll use a simple class attribute to collect them
                    if not hasattr(AutoResearcher, '_current_message_ids'):
                        AutoResearcher._current_message_ids = []
                    AutoResearcher._current_message_ids.append(message_id)
                
                decision_data = json_module.loads(response.choices[0].message.content)
                return LLMDecision(**decision_data)
                
            except Exception as e:
                print(f"LLM decision attempt {attempt + 1} failed: {e}")
                if attempt == max_retries - 1:
                    return None
                time.sleep(1)
        
        return None
    
    @staticmethod
    def _generate_final_response(user_query: str, collected_data: List[dict], total_tokens: int) -> dict:
        """Generate the final markdown response"""
        # Extract media references
        videos = []
        images = []
        
        for data in collected_data:
            if data['endpoint'] == 'videos' and isinstance(data['data'], list):
                for video in data['data']:
                    videos.append({
                        'url': video.get('url', ''),
                        'title': video.get('title', ''),
                        'relevance': f"Query: {data['query']}"
                    })
            elif data['endpoint'] == 'images' and isinstance(data['data'], list):
                for image in data['data']:
                    images.append({
                        'url': image.get('img_src', image.get('url', '')),
                        'title': image.get('title', ''),
                        'description': image.get('content', '')
                    })
        
        # Generate markdown using LLM
        try:
            if not AI_API_KEY or not AI_BASE_URL:
                raise Exception("AI credentials not available")
            
            import openai
            client = openai.OpenAI(
                api_key=AI_API_KEY,
                base_url=AI_BASE_URL,
                default_headers={
                    "HTTP-Referer": "https://github.com/lucanori/web2md",
                    "X-Title": "Web2MD"
                }
            )
            
            prompt = create_final_response_prompt(user_query, [], collected_data)
            
            response = client.chat.completions.create(
                model=AI_MODEL,
                messages=[
                    {
                        "role": "system",
                        "content": "You are an expert research assistant. Create a comprehensive markdown response based on the research data."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                temperature=0.4,
                max_tokens=4000
            )
            
            # Track message ID for cost calculation
            message_id = response.id if hasattr(response, 'id') else None
            if message_id:
                if not hasattr(AutoResearcher, '_current_message_ids'):
                    AutoResearcher._current_message_ids = []
                AutoResearcher._current_message_ids.append(message_id)
            
            markdown_response = response.choices[0].message.content
            
        except Exception as e:
            print(f"Failed to generate LLM response: {e}")
            # Fallback: create basic markdown from collected data
            markdown_response = AutoResearcher._create_fallback_response(user_query, collected_data)
        
        return {
            "markdown_response": markdown_response,
            "media_references": {
                "videos": videos,
                "images": images
            },
            "metadata": {
                "total_requests_used": len(collected_data),
                "endpoints_called": [data['endpoint'] for data in collected_data],
                "queries_used": [data['query'] for data in collected_data],
                "total_tokens": total_tokens
            },
            "websearch_price": 0.0  # Will be calculated later
        }
    
    @staticmethod
    def _create_fallback_response(user_query: str, collected_data: List[dict]) -> str:
        """Create a basic markdown response if LLM generation fails"""
        markdown = f"# Research Results: {user_query}\n\n"
        
        for i, data in enumerate(collected_data, 1):
            markdown += f"## Step {i}: {data['endpoint'].title()} Results\n\n"
            markdown += f"**Query used:** {data['query']}\n\n"
            markdown += f"**Summary:** {data['summary']}\n\n"
        
        markdown += "## Summary\n\n"
        markdown += f"Research completed with {len(collected_data)} steps across different data sources.\n"
        
        return markdown
    
    @staticmethod
    def _calculate_total_cost(message_ids: List[str]) -> float:
        """Calculate total cost from OpenRouter API"""
        if not message_ids:
            return 0.0
        
        total_cost = 0.0
        
        for message_id in message_ids:
            try:
                # Wait a bit for OpenRouter to process the cost
                time.sleep(0.5)
                
                # Fetch cost from OpenRouter API
                with httpx.Client() as client:
                    response = client.get(
                        f"https://openrouter.ai/api/v1/generations/{message_id}",
                        headers={
                            "Authorization": f"Bearer {AI_API_KEY}",
                            "Content-Type": "application/json"
                        },
                        timeout=10
                    )
                    
                    if response.status_code == 200:
                        data = response.json()
                        cost = data.get('data', {}).get('total_cost', 0.0)
                        if cost:
                            total_cost += float(cost)
                            print(f"Message {message_id}: ${cost}")
                    else:
                        print(f"Failed to get cost for message {message_id}: {response.status_code}")
                        
            except Exception as e:
                print(f"Error fetching cost for message {message_id}: {e}")
        
        return total_cost

# Queue management system
class QueueManager:
    _processing_lock = threading.Lock()
    _executor = ThreadPoolExecutor(max_workers=1)  # Process one request at a time
    
    @staticmethod
    def add_request(user_query: str) -> str:
        """Add a new request to the queue and return request ID"""
        request_id = DatabaseManager.create_response(user_query)
        DatabaseManager.add_to_queue(request_id)
        
        # Start processing if not already running
        QueueManager._executor.submit(QueueManager._process_queue)
        
        return request_id
    
    @staticmethod
    def _process_queue():
        """Process queue - only one request at a time"""
        with QueueManager._processing_lock:
            while True:
                request_id = DatabaseManager.get_next_in_queue()
                if not request_id:
                    break
                
                try:
                    # Update status to processing
                    DatabaseManager.update_queue_status(request_id, 'processing')
                    DatabaseManager.update_response_status(request_id, 'processing')
                    
                    # Get the request details
                    response_data = DatabaseManager.get_response(request_id)
                    if not response_data:
                        continue
                    
                    # Process the auto-research request
                    result = AutoResearcher.process_request(request_id, response_data['user_query'])
                    
                    # Update with final result
                    DatabaseManager.update_response_status(
                        request_id, 
                        'completed', 
                        result=json_module.dumps(result),
                        total_tokens=result.get('metadata', {}).get('total_tokens', 0),
                        total_cost=result.get('websearch_price', 0.0)
                    )
                    
                except Exception as e:
                    print(f"Error processing request {request_id}: {e}")
                    DatabaseManager.update_response_status(request_id, 'failed', result=str(e))
                
                finally:
                    # Remove from queue
                    DatabaseManager.update_queue_status(request_id, 'completed')
    
    @staticmethod
    def get_status(request_id: str) -> dict:
        """Get status of a request"""
        response_data = DatabaseManager.get_response(request_id)
        if not response_data:
            return {"error": "Request not found"}
        
        if response_data['status'] == 'completed':
            return {
                "status": "completed",
                "result": json_module.loads(response_data['result']) if response_data['result'] else None
            }
        elif response_data['status'] == 'failed':
            return {
                "status": "failed",
                "error": response_data['result']
            }
        else:
            return {
                "status": response_data['status']
            }

# Background cleanup scheduler
class CleanupScheduler:
    _cleanup_thread = None
    _running = False
    
    @staticmethod
    def start_cleanup_scheduler():
        """Start the cleanup scheduler"""
        if CleanupScheduler._running:
            return
        
        CleanupScheduler._running = True
        CleanupScheduler._cleanup_thread = threading.Thread(
            target=CleanupScheduler._cleanup_worker,
            daemon=True
        )
        CleanupScheduler._cleanup_thread.start()
        print("Cleanup scheduler started")
    
    @staticmethod
    def _cleanup_worker():
        """Background worker that runs cleanup weekly"""
        try:
            import schedule
            
            # Schedule cleanup every week
            schedule.every().week.do(DatabaseManager.cleanup_old_records)
            
            while CleanupScheduler._running:
                schedule.run_pending()
                time.sleep(3600)  # Check every hour
        except ImportError:
            print("Schedule module not available, cleanup will be manual only")
            # Fallback: just run cleanup once a day
            while CleanupScheduler._running:
                time.sleep(86400)  # 24 hours
                if CleanupScheduler._running:
                    try:
                        DatabaseManager.cleanup_old_records()
                    except Exception as e:
                        print(f"Cleanup error: {e}")

# Start cleanup scheduler on application startup
CleanupScheduler.start_cleanup_scheduler()

app = FastAPI()

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def get_proxies(without=False):
    if PROXY_URL and PROXY_USERNAME and PROXY_PORT:
        if without:
            return {
                "http": f"{PROXY_PROTOCOL}://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}:{PROXY_PORT}",
                "https": f"{PROXY_PROTOCOL}://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}:{PROXY_PORT}"
            }
        return {
            "http://": f"{PROXY_PROTOCOL}://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}:{PROXY_PORT}",
            "https://": f"{PROXY_PROTOCOL}://{PROXY_USERNAME}:{PROXY_PASSWORD}@{PROXY_URL}:{PROXY_PORT}"
        }
    return None

def fetch_content(url):
    proxies = get_proxies(without=True)
    def fetch_normal_content(url):
        try:
            if proxies:
                with httpx.Client(proxies=proxies) as client:
                    response = client.get(
                        url,
                        headers=HEADERS,
                        timeout=REQUEST_TIMEOUT,
                        follow_redirects=True
                    )
            else:
                response = httpx.get(
                    url,
                    headers=HEADERS,
                    timeout=REQUEST_TIMEOUT,
                    follow_redirects=True
                )
            response.raise_for_status()
            return response.text
        except httpx.RequestError as e:
            print(f"An error occurred while requesting {url}: {e}")
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e}")
        return None

    def fetch_browserless_content(url):
        try:
            browserless_url = f"{BROWSERLESS_URL}/content"
            params = {
                "headless": False,
                "stealth": True,
            }
            if TOKEN:
                params['token'] = TOKEN

            proxy_url = f"{PROXY_PROTOCOL}://{PROXY_URL}:{PROXY_PORT}" if PROXY_URL and PROXY_PORT else None
            if proxy_url:
                params['--proxy-server'] = proxy_url

            browserless_data = {
                "url": url,
                "rejectResourceTypes": ["image", "stylesheet"],
                "gotoOptions": {"waitUntil": "networkidle0", "timeout": REQUEST_TIMEOUT * 1000},
                "bestAttempt": True,
                "setJavaScriptEnabled": True,
            }
            if PROXY_USERNAME and PROXY_PASSWORD:
                browserless_data["authenticate"] = {
                    "username": PROXY_USERNAME,
                    "password": PROXY_PASSWORD
                }

            headers = {
                'Cache-Control': 'no-cache',
                'Content-Type': 'application/json'
            }

            response = httpx.post(browserless_url, params=params, headers=headers, data=json.dumps(browserless_data), timeout=REQUEST_TIMEOUT * 2)
            response.raise_for_status()
            return response.text
        except httpx.RequestError as e:
            print(f"An error occurred while requesting Browserless for {url}: {e}")
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred with Browserless: {e}")
        return None

    if any(domain in url for domain in domains_only_for_browserless):
        content = fetch_browserless_content(url)
    else:
        content = fetch_normal_content(url)
        if content is None:
            content = fetch_browserless_content(url)

    return content

def get_transcript(video_id: str, format: str = "markdown"):
    try:
        proxies = get_proxies(without=True)
        if proxies:
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, proxies=proxies)
            except TypeError:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        else:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        transcript = " ".join([entry['text'] for entry in transcript_list])

        video_url = f"https://www.youtube.com/watch?v={video_id}"
        video_page = fetch_content(video_url)
        title = extract_title(video_page)

        if format == "json":
            return JSONResponse({"url": video_url, "title": title, "transcript": transcript})
        return PlainTextResponse(f"Title: {title}\n\nURL Source: {video_url}\n\nTranscript:\n{transcript}")
    except Exception as e:
        error_msg = str(e)
        
        # Check if this is a YouTube rate limiting error
        if YouTubeRateLimitManager.is_youtube_blocked_error(error_msg):
            YouTubeRateLimitManager.disable_videos_temporarily()
        
        return PlainTextResponse(f"Failed to retrieve transcript: {error_msg}")

def extract_title(html_content):
    if html_content:
        soup = BeautifulSoup(html_content, 'html.parser')
        title = soup.find("title")
        return title.string.replace(" - YouTube", "") if title else 'No title'
    return 'No title'

def clean_html(html):
    soup = BeautifulSoup(html, 'html.parser')
    
    for script_or_style in soup(["script", "style", "header", "footer", "noscript", "form", "input", "textarea", "select", "option", "button", "svg", "iframe", "object", "embed", "applet", "nav", "navbar"]):
        script_or_style.decompose()

    ids = ['layers']
    
    for id_ in ids:
        tag = soup.find(id=id_)
        if tag:
            tag.decompose()
    
    for tag in soup.find_all(True):
        tag.attrs = {key: value for key, value in tag.attrs.items() if key not in ['class', 'id', 'style']}
    
    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()
    
    return str(soup)

def estimate_tokens(text):
    return len(text) // 4

def filter_images_by_size_and_limit(html, base_url):
    """Filter images by size and limit the number of images"""
    from bs4 import BeautifulSoup
    from urllib.parse import urljoin, urlparse
    
    soup = BeautifulSoup(html, 'html.parser')
    images = soup.find_all('img')
    
    if MAX_IMAGES_PER_SITE == 0:
        for img in images:
            img.decompose()
        return str(soup)
    
    valid_images = []
    
    for img in images:
        if len(valid_images) >= MAX_IMAGES_PER_SITE:
            break
            
        src = img.get('src')
        if not src:
            continue
            
        if src.startswith('//'):
            src = 'https:' + src
        elif src.startswith('/'):
            parsed_base = urlparse(base_url)
            base_domain = f"{parsed_base.scheme}://{parsed_base.netloc}"
            src = urljoin(base_domain, src)
        
        width = img.get('width')
        height = img.get('height')
        
        if width and height:
            try:
                w, h = int(width), int(height)
                if w >= MIN_IMAGE_SIZE and h >= MIN_IMAGE_SIZE:
                    valid_images.append(img)
                    continue
            except (ValueError, TypeError):
                pass
        
        valid_images.append(img)
    
    for img in images:
        if img not in valid_images:
            img.decompose()
    
    return str(soup)

def parse_html_to_markdown(html, url, title=None):
    cleaned_html = clean_html(html)
    filtered_html = filter_images_by_size_and_limit(cleaned_html, url)
    title_ = title or extract_title(html)

    text_maker = html2text.HTML2Text()
    text_maker.ignore_links = False
    text_maker.ignore_tables = False
    text_maker.bypass_tables = False
    text_maker.ignore_images = False
    text_maker.protect_links = True
    text_maker.mark_code = True
    
    markdown_content = text_maker.handle(filtered_html)
    
    estimated_tokens = estimate_tokens(markdown_content)
    if estimated_tokens > MAX_TOKENS_PER_REQUEST:
        max_chars = MAX_TOKENS_PER_REQUEST * 4
        markdown_content = markdown_content[:max_chars] + "\n\n[Content truncated due to token limit]"
        print(f"Content truncated: {estimated_tokens} tokens estimated, limit is {MAX_TOKENS_PER_REQUEST}")
    
    return {
        "title": title_,
        "url": url,
        "markdown_content": markdown_content
    }

def get_transcript_content(video_id: str) -> str:
    """Get transcript content as plain text for AI reranking"""
    try:
        proxies = get_proxies(without=True)
        if proxies:
            try:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id, proxies=proxies)
            except TypeError:
                transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        else:
            transcript_list = YouTubeTranscriptApi.get_transcript(video_id)
        return " ".join([entry['text'] for entry in transcript_list])
    except Exception as e:
        error_msg = str(e)
        print(f"Failed to get transcript for {video_id}: {error_msg}")
        
        # Check if this is a YouTube rate limiting error
        if YouTubeRateLimitManager.is_youtube_blocked_error(error_msg):
            YouTubeRateLimitManager.disable_videos_temporarily()
        
        return ""

def reranker_ai_videos(data: Dict[str, List[dict]], max_token: int = 8000) -> List[dict]:
    """AI reranker specifically for videos with transcript content"""
    client = None
    model = None
    
    class VideoResultItem(BaseModel):
        title: str
        url: str
        content: str
        thumbnail: str = ""
        length: str = ""
        author: str = ""
        publishedDate: str = ""
    
    class VideoSearchResult(BaseModel):
        results: List[VideoResultItem]
    
    system_message = (
        'You will be given a JSON format of video search results and a search query. '
        'Each video result includes metadata and transcript content where available. '
        'Extract only the "exact and most" relevant videos based on the query content. '
        'Use the transcript content to determine relevance - this is the actual spoken content of the video. '
        'Prioritize videos where the transcript content closely matches the user query. '
        'Return the results in the same JSON format with all original fields preserved.'
    )
    
    if not AI_API_KEY or not AI_BASE_URL:
        raise ValueError("AI_API_KEY and AI_BASE_URL must be set for AI integration")
    
    import openai
    client = openai.OpenAI(
        api_key=AI_API_KEY,
        base_url=AI_BASE_URL,
        default_headers={
            "HTTP-Referer": "https://github.com/lucanori/web2md",
            "X-Title": "Web2MD"
        }
    )
    model = AI_MODEL
    
    filtered_results = []
    batch_size = 5  # Smaller batch size for videos due to transcript content
    query = data["query"]
    results = data["results"]
    
    # Limit results to process for efficiency (video processing is expensive)
    max_results_to_process = min(len(results), 15)  # Process max 15 video results
    results = results[:max_results_to_process]
    print(f"Processing {len(results)} videos for AI reranking (limited from original {len(data['results'])} results)")
    
    # Fetch transcripts for YouTube videos
    enhanced_results = []
    for result in results:
        enhanced_result = result.copy()
        if "youtube.com" in result.get("url", ""):
            video_id_match = re.search(r"v=([^&]+)", result.get("url", ""))
            if video_id_match:
                video_id = video_id_match.group(1)
                transcript = get_transcript_content(video_id)
                enhanced_result["content"] = transcript[:3000]  # Limit transcript length for AI processing
            else:
                enhanced_result["content"] = result.get("content", "")
        else:
            enhanced_result["content"] = result.get("content", "")
        enhanced_results.append(enhanced_result)
    
    for i in range(0, len(enhanced_results), batch_size):
        batch = enhanced_results[i:i+batch_size]
        processed_batch = [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "thumbnail": item.get("thumbnail", ""),
                "length": item.get("length", item.get("duration", "")),
                "author": item.get("author", ""),
                "publishedDate": item.get("publishedDate", "")
            } 
            for item in batch
        ]

        response = client.chat.completions.create(
            model=model,
            stream=False,
            messages=[
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": json.dumps({"query": query, "results": processed_batch}) + f"\n\nAnalyze these video results for the query '{query}'. Use the transcript content (when available) to determine which videos are most relevant. Return the most relevant videos in JSON format with all original fields preserved."
                }
            ],
            temperature=0.3,
            max_tokens=max_token,
            response_format={"type":"json_object"}
        )
        
        print(f"AI Video Reranking Response: {response.choices[0].message.content}")
        batch_filtered_results = json.loads(response.choices[0].message.content)
        
        # Handle both formats: {"results": [...]} and direct array [...]
        ai_results = []
        if isinstance(batch_filtered_results, dict) and 'results' in batch_filtered_results:
            ai_results = batch_filtered_results['results']
        elif isinstance(batch_filtered_results, list):
            ai_results = batch_filtered_results
        else:
            print(f"Warning: Unexpected video batch response format: {batch_filtered_results}")
            continue
        
        # Merge AI results back with original metadata
        for ai_result in ai_results:
            # Find original result to preserve all metadata
            original_result = next((r for r in batch if r['url'] == ai_result['url']), None)
            if original_result:
                # Get the full original result from the input data
                full_original = next((r for r in results if r['url'] == ai_result['url']), original_result)
                # Preserve all original fields while keeping AI selection
                filtered_results.append(full_original)

    return {"results": filtered_results, "query": query}

def rerenker_ai(data: Dict[str, List[dict]], max_token: int = 8000) -> List[dict]:
    """Original AI reranker for main search endpoint"""
    client = None
    model = None
    class ResultItem(BaseModel):
        title: str
        url: str
        content: str
    class SearchResult(BaseModel):
        results: List[ResultItem]
    system_message = (
        'You will be given a JSON format of search results and a search query. '
        'Extract only "exact and most" related search `results` based on the `query`. '
        'If the "content" field is empty, use the "title" or "url" field to determine relevance. '
        f' Return the results in same JSON format as you would be given, the JSON object must use the schema: {json.dumps(SearchResult.schema())}'
    )
    
    if not AI_API_KEY or not AI_BASE_URL:
        raise ValueError("AI_API_KEY and AI_BASE_URL must be set for AI integration")
    
    import openai
    client = openai.OpenAI(
        api_key=AI_API_KEY,
        base_url=AI_BASE_URL,
        default_headers={
            "HTTP-Referer": "https://github.com/lucanori/web2md",
            "X-Title": "Web2MD"
        }
    )
    model = AI_MODEL
    
    filtered_results = []
    batch_size = 15  # Slightly larger batches for efficiency
    query = data["query"]
    results = data["results"]
    
    # Limit results to process for efficiency (we typically need 5-10 final results)
    max_results_to_process = min(len(results), 30)  # Process max 30 search results
    results = results[:max_results_to_process]
    print(f"Processing {len(results)} search results for AI reranking (limited from original {len(data['results'])} results)")
    
    for i in range(0, len(results), batch_size):
        batch = results[i:i+batch_size]
        processed_batch = [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", "")
            } 
            for item in batch
        ]

        response = client.chat.completions.create(
            model=model,
            stream=False,
            messages=[
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": json.dumps({"query": query, "results": processed_batch}) + "\n\nExtract the most relevant search results based on the query and ensure each result contains \"content.\" Return them in JSON format with \"title,\" \"url,\" and \"content\" fields only."
                }
            ],
            temperature=0.5,
            max_tokens=max_token,
            response_format={"type":"json_object"}

        )
        print(response.choices[0].message.content)
        batch_filtered_results = json.loads(response.choices[0].message.content)
        
        # Handle both formats: {"results": [...]} and direct array [...]
        if isinstance(batch_filtered_results, dict) and 'results' in batch_filtered_results:
            filtered_results.extend(batch_filtered_results['results'])
        elif isinstance(batch_filtered_results, list):
            filtered_results.extend(batch_filtered_results)
        else:
            print(f"Warning: Unexpected batch response format: {batch_filtered_results}")

    return {"results": filtered_results, "query": query}

def reranker_ai_images(data: Dict[str, List[dict]], max_token: int = 8000) -> List[dict]:
    """AI reranker for images based on metadata"""
    client = None
    model = None
    
    class ImageResultItem(BaseModel):
        title: str
        url: str
        content: str
        thumbnail_src: str = ""
        img_src: str = ""
        resolution: str = ""
        source: str = ""
    
    class ImageSearchResult(BaseModel):
        results: List[ImageResultItem]
    
    system_message = (
        'You will be given a JSON format of image search results and a search query. '
        'Extract only the "exact and most" relevant images based on the query. '
        'Use the title, content, and source information to determine relevance. '
        'Prioritize high-quality, high-resolution images from reputable sources. '
        'Return the results in the same JSON format with all original fields preserved.'
    )
    
    if not AI_API_KEY or not AI_BASE_URL:
        raise ValueError("AI_API_KEY and AI_BASE_URL must be set for AI integration")
    
    import openai
    client = openai.OpenAI(
        api_key=AI_API_KEY,
        base_url=AI_BASE_URL,
        default_headers={
            "HTTP-Referer": "https://github.com/lucanori/web2md",
            "X-Title": "Web2MD"
        }
    )
    model = AI_MODEL
    
    filtered_results = []
    batch_size = 20  # Larger batches for fewer API calls
    query = data["query"]
    results = data["results"]
    
    # Limit results to process for efficiency (we typically only need 5-10 images)
    max_results_to_process = min(len(results), 20)  # Process max 20 results instead of all
    results = results[:max_results_to_process]
    print(f"Processing {len(results)} images for AI reranking (limited from original {len(data['results'])} results)")
    
    for i in range(0, len(results), batch_size):
        batch = results[i:i+batch_size]
        processed_batch = [
            {
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "content": item.get("content", ""),
                "thumbnail_src": item.get("thumbnail_src", ""),
                "img_src": item.get("img_src", ""),
                "resolution": item.get("resolution", ""),
                "source": item.get("source", "")
            } 
            for item in batch
        ]

        response = client.chat.completions.create(
            model=model,
            stream=False,
            messages=[
                {
                    "role": "system",
                    "content": system_message
                },
                {
                    "role": "user",
                    "content": json.dumps({"query": query, "results": processed_batch}) + f"\n\nFind the most relevant images for the query '{query}'. Consider image quality, resolution, and source reliability. Return them in JSON format with all original fields preserved."
                }
            ],
            temperature=0.3,
            max_tokens=max_token,
            response_format={"type":"json_object"}
        )
        
        print(f"AI Image Reranking Response: {response.choices[0].message.content}")
        batch_filtered_results = json.loads(response.choices[0].message.content)
        
        # Handle both formats: {"results": [...]} and direct array [...]
        ai_results = []
        if isinstance(batch_filtered_results, dict) and 'results' in batch_filtered_results:
            ai_results = batch_filtered_results['results']
        elif isinstance(batch_filtered_results, list):
            ai_results = batch_filtered_results
        else:
            print(f"Warning: Unexpected image batch response format: {batch_filtered_results}")
            continue
        
        # Merge AI results back with original metadata  
        for ai_result in ai_results:
            # Find original result to preserve all metadata
            original_result = next((r for r in results if r['url'] == ai_result['url']), None)
            if original_result:
                filtered_results.append(original_result)

    return {"results": filtered_results, "query": query}

def searxng(query: str, categories: str = "general") -> dict:
    searxng_url = f"{SEARXNG_URL}/search?q={query}&categories={categories}&format=json"
    try:
        response = httpx.get(searxng_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        response.raise_for_status()
    except httpx.RequestError as e:
        print(f"SearXNG request error: {e}")
        return {"results": [{"error": f"Search query failed with error: {e}"}]}
    except httpx.HTTPStatusError as e:
        print(f"SearXNG HTTP error: {e}")
        return {"results": [{"error": f"Search query failed with HTTP error: {e}"}]}

    try:
        search_results = response.json()
        print(f"SearXNG response structure: {type(search_results)}, keys: {search_results.keys() if isinstance(search_results, dict) else 'not a dict'}")
        return search_results
    except json.JSONDecodeError as e:
        print(f"SearXNG JSON decode error: {e}")
        return {"results": [{"error": f"Failed to parse search results: {e}"}]}

def search(query: str, num_results: int, json_response: bool = False) -> list:
    search_results = searxng(query)
    if FILTER_SEARCH_RESULT_BY_AI:
        ai_input = {
            "query": query,
            "results": search_results["results"] if isinstance(search_results, dict) and "results" in search_results else search_results
        }
        search_results = rerenker_ai(ai_input)

    json_return = []
    markdown_return = ""
    
    results_list = search_results["results"] if isinstance(search_results, dict) and "results" in search_results else search_results
    
    for result in results_list[:num_results]:
        if not isinstance(result, dict) or "url" not in result or "title" not in result:
            print(f"Skipping invalid result: {result}")
            continue
            
        url = result["url"]
        title = result["title"]
        
        if "youtube" in url:
            video_id = re.search(r"v=([^&]+)", url)
            if video_id:
                if json_response:
                    json_return.append(get_transcript(video_id.group(1), "json"))
                else:
                    markdown_return += get_transcript(video_id.group(1)) + "\n\n ---------------- \n\n"
            continue
            
        html_content = fetch_content(url)
        if html_content:
            markdown_data = parse_html_to_markdown(html_content, url, title=title)
            if markdown_data["markdown_content"].strip():
                if json_response:
                    json_return.append(markdown_data)
                else:
                    markdown_return += (
                    f"Title: {markdown_data['title']}\n\n"
                    f"URL Source: {markdown_data['url']}\n\n"
                    f"Markdown Content:\n{markdown_data['markdown_content']}"
                ) + "\n\n ---------------- \n\n"
                
    
    if json_response:
        return JSONResponse(json_return)
    return PlainTextResponse(markdown_return)

@app.get("/images")
def get_search_images(
    q: str = Query(..., description="Search images"),
    num_results: int = Query(5, description="Number of results")
    ):
    result_list = searxng(q, categories="images")
    results = result_list["results"] if isinstance(result_list, dict) and "results" in result_list else result_list
    
    # Apply AI reranking if enabled
    if FILTER_SEARCH_RESULT_BY_AI:
        ai_input = {
            "query": q,
            "results": results
        }
        reranked_results = reranker_ai_images(ai_input)
        results = reranked_results["results"]
    
    return JSONResponse(results[:num_results])

@app.get("/videos")
def get_search_videos(
    q: str = Query(..., description="Search videos"),
    num_results: int = Query(5, description="Number of results"),
    format: str = Query("metadata", description="Output format (metadata, transcripts, or json)")
    ):
    
    # Check if videos are temporarily disabled due to rate limiting
    if YouTubeRateLimitManager.is_videos_disabled():
        remaining = YouTubeRateLimitManager.get_remaining_cooldown()
        return JSONResponse(
            {
                "error": "Video endpoint temporarily disabled due to YouTube rate limiting",
                "reason": "Preventing permanent IP ban from YouTube",
                "cooldown_remaining_seconds": remaining,
                "cooldown_remaining_minutes": remaining // 60,
                "retry_after": f"{remaining // 60} minutes"
            },
            status_code=503
        )
    
    result_list = searxng(q, categories="videos")
    results = result_list["results"] if isinstance(result_list, dict) and "results" in result_list else result_list
    
    # Apply AI reranking if enabled
    if FILTER_SEARCH_RESULT_BY_AI:
        try:
            ai_input = {
                "query": q,
                "results": results
            }
            reranked_results = reranker_ai_videos(ai_input)
            results = reranked_results["results"]
        except Exception as e:
            print(f"AI reranking failed for videos: {e}")
            # Continue with non-reranked results
    
    # Handle different output formats
    if format == "transcripts":
        # Return with full transcripts
        enhanced_results = []
        for result in results[:num_results]:
            enhanced_result = result.copy()
            if "youtube.com" in result.get("url", ""):
                video_id_match = re.search(r"v=([^&]+)", result.get("url", ""))
                if video_id_match:
                    video_id = video_id_match.group(1)
                    transcript = get_transcript_content(video_id)
                    enhanced_result["full_transcript"] = transcript
            enhanced_results.append(enhanced_result)
        return JSONResponse(enhanced_results)
    
    elif format == "json":
        return JSONResponse(results[:num_results])
    
    else:  # metadata (default)
        return JSONResponse(results[:num_results])

@app.get("/search")
def get_search_results(
    q: str = Query(..., description="Search query"), 
    num_results: int = Query(5, description="Number of results"),
    format: str = Query("markdown", description="Output format (markdown or json)")):
    result_list = search(q, num_results, format == "json")
    return result_list

@app.get("/auto")
def start_auto_research(
    q: str = Query(..., description="Research query"),
    ):
    """Start auto-research process and return request ID"""
    try:
        request_id = QueueManager.add_request(q)
        return JSONResponse({
            "request_id": request_id,
            "status": "queued",
            "check_endpoint": f"/auto/status/{request_id}"
        })
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to queue request: {str(e)}"}, 
            status_code=500
        )

@app.get("/auto/status/{request_id}")
def get_auto_research_status(request_id: str):
    """Get status of auto-research request"""
    try:
        status_data = QueueManager.get_status(request_id)
        return JSONResponse(status_data)
    except Exception as e:
        return JSONResponse(
            {"error": f"Failed to get status: {str(e)}"}, 
            status_code=500
        )

@app.get("/status/videos")
def get_videos_status():
    """Get video endpoint status (rate limiting info)"""
    is_disabled = YouTubeRateLimitManager.is_videos_disabled()
    remaining = YouTubeRateLimitManager.get_remaining_cooldown()
    
    return JSONResponse({
        "videos_disabled": is_disabled,
        "cooldown_remaining_seconds": remaining,
        "cooldown_remaining_minutes": remaining // 60,
        "reason": "YouTube rate limiting protection" if is_disabled else None,
        "status": "disabled" if is_disabled else "available"
    })

@app.get("/r/{url:path}")
def fetch_url(request: Request, url: str, format: str = Query("markdown", description="Output format (markdown or json)")):
    if "youtube" in url:
        return get_transcript(request.query_params.get('v'), format)
    
    html_content = fetch_content(url)
    if html_content:
        markdown_data = parse_html_to_markdown(html_content, url)
        if format == "json":
            return JSONResponse(markdown_data)
        
        response_text = (
            f"Title: {markdown_data['title']}\n\n"
            f"URL Source: {markdown_data['url']}\n\n"
            f"Markdown Content:\n{markdown_data['markdown_content']}"
        )
        return PlainTextResponse(response_text)
    return PlainTextResponse("Failed to retrieve content")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)