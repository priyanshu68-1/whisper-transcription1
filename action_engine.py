from dotenv import load_dotenv
import os
import json
import time
import re
import urllib.request
import urllib.error
from typing import List, Dict, Any
from pydantic import BaseModel, Field

load_dotenv()

class GranularActionItem(BaseModel):
    task: str = Field(description="Clear description of the action item")
    assignee: str = Field(description="Person responsible or 'Unassigned'")
    deadline: str = Field(description="Target completion date/time or 'Not specified'")
    priority: str = Field(description="High, Medium, or Low")
    status: str = Field(description="Pending, In Progress, or Completed (Default: Pending)")

SYSTEM_INSTRUCTION = """
You are a specialized Task Extraction Engine.
Your job is to parse meeting transcripts and extract explicit action items.

Rules:
- Extract ONLY explicit tasks or commitments made by participants.
- Identify the assigned participant, deadline, and priority.
- Set 'status' to 'Pending' by default.
- Return valid JSON matching schema.
"""

REST_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "action_items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "task": {"type": "STRING"},
                    "assignee": {"type": "STRING"},
                    "deadline": {"type": "STRING"},
                    "priority": {"type": "STRING"},
                    "status": {"type": "STRING"}
                },
                "required": ["task", "assignee", "deadline", "priority", "status"]
            }
        }
    },
    "required": ["action_items"]
}

class ActionItemEngine:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def _call_rest(self, transcript: str) -> List[Dict[str, Any]]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY missing.")
            
        model_name = "gemini-flash-lite-latest"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
        
        prompt = f"Extract all action items from this transcript:\n\n{transcript}"
        payload = {
            "systemInstruction": {"parts": [{"text": SYSTEM_INSTRUCTION}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": REST_SCHEMA,
                "temperature": 0.1
            }
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        
        with urllib.request.urlopen(req, timeout=30) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)
            return parsed.get("action_items", [])

    def _fallback_extraction(self, transcript: str) -> List[Dict[str, Any]]:
        """
        Rule-based NLP fallback engine for extracting tasks when API rate limits occur.
        """
        action_items = []
        lines = transcript.split("\n")
        
        keywords = ["will", "need to", "must", "assign", "complete", "prepare", "handle", "finish", "draft", "test"]
        day_patterns = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday", "tomorrow", "next week", "by "]
        
        for line in lines:
            line_clean = line.strip()
            if not line_clean:
                continue
                
            speaker = "Unassigned"
            match_speaker = re.search(r'(?:\[.*?\]\s*)?([A-Z][a-zA-Z\s]+):', line_clean)
            if match_speaker:
                speaker = match_speaker.group(1).strip()
                content = line_clean[match_speaker.end():].strip()
            else:
                content = line_clean

            # Check if sentence contains action commitment
            lower_content = content.lower()
            if any(k in lower_content for k in keywords):
                deadline = "Not specified"
                for day in day_patterns:
                    if day in lower_content:
                        m_deadline = re.search(r'(?:by\s+|on\s+)?(' + day + r'\b\s*\w*)', lower_content, re.IGNORECASE)
                        if m_deadline:
                            deadline = m_deadline.group(1).title()
                            break

                priority = "High" if ("high priority" in lower_content or "urgent" in lower_content or "asap" in lower_content) else "Medium"
                
                action_items.append({
                    "task": content,
                    "assignee": speaker,
                    "deadline": deadline,
                    "priority": priority,
                    "status": "Pending"
                })

        return action_items

    def extract_action_items(self, transcript: str, max_retries: int = 2) -> List[Dict[str, Any]]:
        if not transcript or not transcript.strip():
            return []

        for attempt in range(1, max_retries + 1):
            try:
                return self._call_rest(transcript)
            except urllib.error.HTTPError as http_err:
                print(f"[WARN ActionEngine] HTTP Error attempt {attempt}: {http_err}")
                if http_err.code == 429:
                    time.sleep(2 * attempt)
            except Exception as e:
                print(f"[WARN ActionEngine] Extraction attempt {attempt} failed: {e}")
                time.sleep(1)

        print("[INFO ActionEngine] Using Rule-Based NLP Fallback Engine due to API limit.")
        return self._fallback_extraction(transcript)

if __name__ == "__main__":
    sample_transcript = """
    [00:00] Priyanshu: Let's finalize the deliverables for Milestone 2.
    [00:05] Deepasri: I will set up the PostgreSQL vector schema by Wednesday.
    [00:10] Priyanshu: I am already working on the FastAPI endpoints; I'll finish that by Friday. High priority.
    [00:15] Deepasri: Great. Also, someone should draft the documentation by next week.
    [00:20] Priyanshu: I can take that documentation task as low priority.
    """

    print("\n============================================================")
    print("INPUT TRANSCRIPT")
    print("============================================================")
    print(sample_transcript.strip())

    engine = ActionItemEngine()
    actions = engine.extract_action_items(sample_transcript)

    print("\n============================================================")
    print("OUTPUT: GRANULAR ACTION ITEMS")
    print("============================================================")
    print(json.dumps(actions, indent=2))
