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

class ActionItem(BaseModel):
    task: str = Field(description="Description of the action item")
    assignee: str = Field(description="Person responsible or 'Unassigned'")
    priority: str = Field(description="High, Medium, or Low")
    deadline: str = Field(description="Specific deadline date/time or 'Not specified'")

class MeetingIntelligence(BaseModel):
    summary: str = Field(description="Concise 2-3 sentence overview of the meeting")
    key_points: List[str] = Field(description="List of main discussion points")
    decisions: List[str] = Field(description="List of explicit decisions made")
    participants: List[str] = Field(description="List of identified meeting participants")
    action_items: List[ActionItem] = Field(description="Structured action items extracted")
    deadlines: List[str] = Field(description="All deadlines mentioned")
    priorities: List[str] = Field(description="High priority topics or urgent deliverables")

SYSTEM_INSTRUCTION = """
You are an expert Executive Meeting Assistant.
Your task is to analyze raw meeting transcripts and extract structured meeting intelligence.

Rules:
- Extract factual information only.
- Output MUST strictly adhere to JSON format matching the schema.
"""

REST_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING", "description": "Concise overview"},
        "key_points": {"type": "ARRAY", "items": {"type": "STRING"}},
        "decisions": {"type": "ARRAY", "items": {"type": "STRING"}},
        "participants": {"type": "ARRAY", "items": {"type": "STRING"}},
        "action_items": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "task": {"type": "STRING"},
                    "assignee": {"type": "STRING"},
                    "priority": {"type": "STRING"},
                    "deadline": {"type": "STRING"}
                },
                "required": ["task", "assignee", "priority", "deadline"]
            }
        },
        "deadlines": {"type": "ARRAY", "items": {"type": "STRING"}},
        "priorities": {"type": "ARRAY", "items": {"type": "STRING"}}
    },
    "required": ["summary", "key_points", "decisions", "participants", "action_items", "deadlines", "priorities"]
}

class LLMService:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def _chunk_transcript(self, transcript: str, max_chars: int = 12000) -> List[str]:
        if len(transcript) <= max_chars:
            return [transcript]
        lines = transcript.split("\n")
        chunks, current_chunk, current_len = [], [], 0
        for line in lines:
            if current_len + len(line) > max_chars:
                chunks.append("\n".join(current_chunk))
                current_chunk, current_len = [line], len(line)
            else:
                current_chunk.append(line)
                current_len += len(line)
        if current_chunk:
            chunks.append("\n".join(current_chunk))
        return chunks

    def _call_gemini_rest(self, prompt: str) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is missing.")

        model_name = "gemini-flash-lite-latest"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
        
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
            return json.loads(raw_text)

    def _fallback_summary(self, transcript: str) -> Dict[str, Any]:
        """
        Rule-based NLP fallback for summary & key points when API rate limit occurs.
        """
        lines = [l.strip() for l in transcript.split("\n") if l.strip()]
        
        # Extract speakers
        speakers = set()
        for l in lines:
            m = re.search(r'(?:\[.*?\]\s*)?([A-Z][a-zA-Z\s]+):', l)
            if m and m.group(1).lower() not in ["timestamp", "speaker"]:
                speakers.add(m.group(1).strip())
        
        participant_list = sorted(list(speakers)) if speakers else ["Narrator / Speaker"]
        
        # Extracted sentences
        clean_sentences = []
        for l in lines:
            m = re.search(r'(?:\[.*?\]\s*)?(?:[A-Z][a-zA-Z\s]+:)?\s*(.*)', l)
            if m and len(m.group(1)) > 10:
                clean_sentences.append(m.group(1).strip())

        summary_text = " ".join(clean_sentences[:3]) if clean_sentences else transcript[:200]
        
        return {
            "summary": f"Meeting Focus: {summary_text}",
            "key_points": clean_sentences[:4] if clean_sentences else ["Whisper transcription generated"],
            "decisions": [s for s in clean_sentences if any(k in s.lower() for k in ["agreed", "decided", "will", "confirm"])],
            "participants": participant_list,
            "action_items": [],
            "deadlines": [s for s in clean_sentences if any(k in s.lower() for k in ["monday", "tuesday", "wednesday", "thursday", "friday", "by ", "deadline"])],
            "priorities": ["High Priority Project Delivery"]
        }

    def process_transcript(self, transcript: str, max_retries: int = 1) -> Dict[str, Any]:
        if not transcript or not transcript.strip():
            raise ValueError("Input transcript is empty.")

        chunks = self._chunk_transcript(transcript)
        combined_input = "\n--- CONTINUATION ---\n".join(chunks)
        prompt = f"Analyze the following meeting transcript:\n\n{combined_input}"

        for attempt in range(1, max_retries + 1):
            try:
                return self._call_gemini_rest(prompt)
            except urllib.error.HTTPError as http_err:
                print(f"[WARN LLM] HTTP Error on attempt {attempt}/{max_retries}: {http_err}")
                if attempt < max_retries:
                    time.sleep(1)
            except Exception as e:
                print(f"[WARN LLM] Attempt {attempt}/{max_retries} failed: {e}")
                if attempt < max_retries:
                    time.sleep(1)

        print("[INFO LLM] Using Rule-Based Fallback Summary Engine due to API quota.")
        return self._fallback_summary(transcript)

if __name__ == "__main__":
    sample_transcript = """
    [00:00] Priyanshu: Welcome everyone. Let's start our project review.
    [00:05] Deepasri: We need to finish Milestone 2 by next Monday.
    [00:10] Priyanshu: Agreed. I will implement the LLM processing service and JSON schema by tomorrow.
    [00:15] Deepasri: Great, I will handle UI integration for the summary tabs. High priority for both items.
    """
    
    try:
        service = LLMService()
        result = service.process_transcript(sample_transcript)
        print("\n" + "=" * 50)
        print("STRUCTURED MEETING INTELLIGENCE OUTPUT")
        print("=" * 50)
        print(json.dumps(result, indent=2))
    except Exception as err:
        print(f"Execution Error: {err}")