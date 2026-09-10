from dotenv import load_dotenv
import os
import json
import time
import uuid
import re
import urllib.request
import urllib.error
from typing import List, Dict, Any
from pydantic import BaseModel, Field

load_dotenv()

class ResponsibilityLink(BaseModel):
    task: str = Field(description="Description of the action item or responsibility")
    assignees: List[str] = Field(description="List of normalized participant names responsible")
    deadline: str = Field(description="Deadline date or 'Not specified'")
    priority: str = Field(description="High, Medium, or Low")

class ParticipantMappingOutput(BaseModel):
    meeting_id: str = Field(description="Unique identifier for the meeting session")
    unique_participants: List[str] = Field(description="Deduplicated, canonical names of all participants")
    responsibilities: List[ResponsibilityLink] = Field(description="List of mapped action items linked to meeting")

SYSTEM_INSTRUCTION = """
You are an expert Participant & Responsibility Mapping Engine.
Analyze raw transcripts and map participants to their explicit responsibilities.

Rules:
1. Standardize and deduplicate participant names (e.g., 'Priya' and 'Priya S.' -> 'Priya').
2. If no explicit names are mentioned, set unique_participants to ['Narrator / Speaker'].
3. If a task owner is unclear, set assignees to ['Unassigned'].
4. Deduplicate identical participant entries.
5. Return JSON matching the schema.
"""

REST_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "meeting_id": {"type": "STRING"},
        "unique_participants": {"type": "ARRAY", "items": {"type": "STRING"}},
        "responsibilities": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "properties": {
                    "task": {"type": "STRING"},
                    "assignees": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "deadline": {"type": "STRING"},
                    "priority": {"type": "STRING"}
                },
                "required": ["task", "assignees", "deadline", "priority"]
            }
        }
    },
    "required": ["meeting_id", "unique_participants", "responsibilities"]
}

class ParticipantMapper:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def _call_rest(self, transcript: str, session_id: str) -> Dict[str, Any]:
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY missing.")
            
        model_name = "gemini-flash-lite-latest"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"
        
        prompt = f"Meeting ID: {session_id}\n\nTranscript:\n{transcript}"
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
            parsed["unique_participants"] = sorted(list(set(parsed.get("unique_participants", []))))
            return parsed

    def _fallback_mapping(self, transcript: str, session_id: str) -> Dict[str, Any]:
        """
        Regex-based speaker extraction & deduplication fallback.
        """
        speakers = set()
        responsibilities = []
        
        lines = transcript.split("\n")
        for line in lines:
            match = re.search(r'(?:\[.*?\]\s*)?([A-Z][a-zA-Z\s]+):', line)
            if match:
                name = match.group(1).strip()
                if name.lower() not in ["timestamp", "speaker", "unknown speaker"]:
                    speakers.add(name)
                
                content = line[match.end():].strip()
                if any(w in content.lower() for w in ["will", "need", "handle", "complete", "prepare", "finish"]):
                    responsibilities.append({
                        "task": content,
                        "assignees": [name],
                        "deadline": "Not specified",
                        "priority": "Medium"
                    })

        unique_list = sorted(list(speakers)) if speakers else ["Narrator / Speaker"]
        
        return {
            "meeting_id": session_id,
            "unique_participants": unique_list,
            "responsibilities": responsibilities
        }

    def map_participants_and_tasks(
        self, transcript: str, meeting_id: str = None, max_retries: int = 2
    ) -> Dict[str, Any]:
        session_id = meeting_id or f"MEET-{uuid.uuid4().hex[:8].upper()}"
        if not transcript or not transcript.strip():
            return {
                "meeting_id": session_id,
                "unique_participants": ["Narrator / Speaker"],
                "responsibilities": [],
            }

        for attempt in range(1, max_retries + 1):
            try:
                return self._call_rest(transcript, session_id)
            except urllib.error.HTTPError as http_err:
                print(f"[WARN ParticipantMapper] HTTP Error attempt {attempt}: {http_err}")
                if http_err.code == 429:
                    time.sleep(2 * attempt)
            except Exception as e:
                print(f"[WARN ParticipantMapper] Mapping attempt {attempt} failed: {e}")
                time.sleep(1)

        print("[INFO ParticipantMapper] Using Regex Fallback Mapping Engine due to API limit.")
        return self._fallback_mapping(transcript, session_id)

if __name__ == "__main__":
    sample_transcript = """
    [00:00] Priyanshu Singh: Welcome everyone. Let's align on Milestone 2.
    [00:05] Priya: I can handle the UI testing and prepare the report by Friday.
    [00:10] Priyanshu: Great. Ravi and I will co-own the API integration and database schema by Wednesday.
    """

    print("\n============================================================")
    print("INPUT TRANSCRIPT")
    print("============================================================")
    print(sample_transcript.strip())

    mapper = ParticipantMapper()
    mapping_result = mapper.map_participants_and_tasks(
        sample_transcript, meeting_id="MEET-2026-0904"
    )

    print("\n============================================================")
    print("OUTPUT: PARTICIPANT & RESPONSIBILITY MAPPING")
    print("============================================================")
    print(json.dumps(mapping_result, indent=2))
