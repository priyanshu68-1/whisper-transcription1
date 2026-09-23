import os
import re
import json
import logging
import urllib.request
import urllib.error
from typing import Dict, List, Any, Optional
from dotenv import load_dotenv

from database import DatabaseManager

load_dotenv()

# ---------------------------------------------------------------------------
# Logging Setup
# ---------------------------------------------------------------------------
logger = logging.getLogger("whisper_meetings.ai_search")
logger.propagate = False
if not logger.handlers:
    _handler = logging.StreamHandler()
    _formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s")
    _handler.setFormatter(_formatter)
    logger.addHandler(_handler)
logger.setLevel(logging.INFO)

AI_SEARCH_SYSTEM_INSTRUCTION = """
You are TruthShield AI's Contextual Meeting Intelligence Assistant.
Your task is to answer user questions strictly and ONLY using the provided historical meeting context.

CRITICAL RULES:
1. Fact Grounding: Answer ONLY based on the facts provided in the HISTORICAL MEETING CONTEXT.
2. Zero Hallucination: Do NOT invent, assume, extrapolate, or introduce external knowledge.
3. Information Not Found: If the answer cannot be determined or found from the provided context, you MUST state:
   "The requested information was not found in the historical meeting records."
   Set "found" to false.
4. Source Attribution: Always explicitly cite the relevant source meeting ID(s) (e.g. [Meeting ID: MEET-XXXXXX]) for every fact cited.
5. Structure: Return valid JSON matching the schema with concise, factual bullet points.
"""

AI_SEARCH_SCHEMA = {
    "type": "OBJECT",
    "properties": {
        "answer": {
            "type": "STRING",
            "description": "Factual answer to the question grounded ONLY in the provided context, citing Meeting IDs."
        },
        "found": {
            "type": "BOOLEAN",
            "description": "True if factual answer was found in context, False otherwise."
        },
        "source_meeting_ids": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "List of meeting IDs that provided the factual answer."
        },
        "key_findings": {
            "type": "ARRAY",
            "items": {"type": "STRING"},
            "description": "Bullet points summarizing key facts relevant to the question."
        }
    },
    "required": ["answer", "found", "source_meeting_ids", "key_findings"]
}

STOPWORDS = {
    "what", "who", "when", "where", "why", "how", "did", "do", "does",
    "is", "was", "were", "are", "can", "could", "would", "should",
    "we", "us", "our", "the", "a", "an", "of", "to", "in", "for",
    "on", "about", "tell", "me", "show", "find", "list", "any", "all",
    "been", "being", "have", "has", "had", "which", "there", "their",
    "at", "by", "if", "or", "so", "no", "up", "my", "he", "it", "as",
    "and", "with", "from", "into", "during", "including", "regarding", "between",
    "make", "makes", "made", "making", "take", "takes", "took", "taken", "held", "give", "given"
}

BROAD_REPO_TERMS = {
    "deadline", "deadlines", "decision", "decisions", "decide", "decided",
    "action", "actions", "task", "tasks", "todo", "todos", "summary", "summaries",
    "overview", "agenda", "discussed", "discuss", "discusses", "discussing",
    "agreed", "agree", "resolved", "resolve", "resolution", "choose", "chosen",
    "pending", "scheduled", "schedule", "assigned", "assign", "assignment",
    "priorities", "priority", "status", "meeting", "meetings", "recent",
    "item", "items", "part", "parts", "sync", "call", "review", "logistics",
    "work", "worked", "working", "works", "responsible", "responsibility",
    "owner", "ownership", "role", "roles", "update", "updates", "lead", "leading",
    "handle", "handled", "handling"
}


class AISearchEngine:
    """
    Milestone 3 – Task 3: AI / Contextual Meeting Search Engine
    Orchestrates:
    User Question -> Keyword/Intent Extraction -> Repository Context Retrieval
    -> Reusable Strict Grounding Prompt -> LLM Synthesized Answer with Source IDs.
    """
    def __init__(self, db: Optional[DatabaseManager] = None, api_key: Optional[str] = None):
        self.db = db or DatabaseManager()
        self.api_key = api_key or os.environ.get("GEMINI_API_KEY")

    def extract_keywords(self, question: str) -> List[str]:
        """
        Extracts salient search keywords from a natural language question.
        Preserves tech acronyms (UI, AI, QA, DB) while filtering common stopwords.
        Prioritizes specific content keywords ahead of broad repository terms.
        """
        if not question:
            return []

        # Find quoted phrases first
        quoted = re.findall(r'"([^"]+)"', question)
        cleaned = re.sub(r'"[^"]+"', " ", question)

        tokens = re.findall(r'[a-zA-Z0-9_\-\.]+', cleaned.lower())
        meaningful = [t for t in tokens if len(t) >= 2 and t not in STOPWORDS]

        keywords = list(dict.fromkeys(quoted + meaningful))
        # Prioritize topic-specific content keywords before generic meta terms
        content_kws = [k for k in keywords if k not in BROAD_REPO_TERMS]
        meta_kws = [k for k in keywords if k in BROAD_REPO_TERMS]
        return content_kws + meta_kws

    def retrieve_context(self, question: str, max_meetings: int = 5, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Searches the meeting knowledge repository for the most relevant records.
        Preserves meeting_id and complete intelligence for context building.
        Returns empty list for irrelevant queries with no matching repository evidence.
        """
        if limit is not None:
            max_meetings = limit
        keywords = self.extract_keywords(question)
        candidate_meetings = {}

        # 1. Search with extracted keywords (prioritizing topic content)
        content_kws = [k for k in keywords if k not in BROAD_REPO_TERMS]
        search_kws = content_kws if content_kws else keywords
        for kw in search_kws[:6]:
            hits = self.db.search_meetings(query=kw, limit=max(max_meetings * 2, 10))
            for h in hits:
                mid = h["meeting_id"]
                if mid not in candidate_meetings:
                    candidate_meetings[mid] = {"record": h, "score": 1}
                else:
                    candidate_meetings[mid]["score"] += 1

        # 2. Also search with whole question phrase if specific keywords didn't yield enough
        if len(candidate_meetings) < 2 and keywords:
            broad_hits = self.db.search_meetings(query=" ".join(keywords[:3]), limit=max_meetings)
            for h in broad_hits:
                mid = h["meeting_id"]
                if mid not in candidate_meetings:
                    candidate_meetings[mid] = {"record": h, "score": 1}

        # 3. If still no hits, check if the question is an explicit broad repository question
        # (e.g. "what deadlines were discussed?"). If it is unrelated or refers to non-existent entities,
        # return empty list to prevent returning unrelated meeting records as evidence.
        if not candidate_meetings and question:
            q_lower = question.lower()
            is_broad = any(b in q_lower for b in BROAD_REPO_TERMS)
            content_keywords = [k for k in keywords if not any(b in k for b in BROAD_REPO_TERMS)]

            # Only fall back to repository meetings if there are no unmatched content-specific keywords
            if is_broad and not content_keywords:
                recent = self.db.list_all_meetings(limit=max_meetings)
                for m in recent:
                    mid = m["meeting_id"]
                    detail = self.db.get_meeting(mid)
                    if detail:
                        candidate_meetings[mid] = {"record": detail, "score": 0}

        # Sort by score descending
        sorted_candidates = sorted(candidate_meetings.values(), key=lambda x: x["score"], reverse=True)
        top_records = []
        for c in sorted_candidates[:max_meetings]:
            rec = c["record"]
            # Ensure complete meeting details are loaded
            if "action_items" not in rec or not isinstance(rec.get("action_items"), list):
                full_m = self.db.get_meeting(rec["meeting_id"])
                if full_m:
                    rec = full_m
            top_records.append(rec)

        return top_records

    # Alias for flexibility
    retrieve_relevant_meetings = retrieve_context

    def semantic_search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Executes semantic context retrieval over historical meetings.
        Falls back safely to database keyword search if vector or semantic extraction fails.
        """
        if not query or not query.strip():
            return []
        clean_q = query.strip()
        try:
            results = self.retrieve_context(clean_q, max_meetings=limit)
            if results:
                return results
            return self.db.search_meetings(query=clean_q, limit=limit)
        except Exception as e:
            logger.warning(f"Semantic search encountered error: {e}. Falling back to database keyword search.")
            try:
                res = self.db.search_meetings(query=clean_q, limit=limit)
                if not res and " " in clean_q:
                    tokens = [w for w in clean_q.split() if len(w) >= 3 and w.lower() not in STOPWORDS]
                    for t in tokens:
                        res = self.db.search_meetings(query=t, limit=limit)
                        if res:
                            break
                return res
            except Exception as db_err:
                logger.error(f"Database search fallback failed: {db_err}")
                return []

    def build_prompt_context(self, meetings: List[Dict[str, Any]]) -> str:
        """
        Builds structured, readable meeting context blocks for LLM consumption.
        """
        if not meetings:
            return "No meeting records found in repository."

        blocks = []
        for m in meetings:
            mid = m.get("meeting_id", "UNKNOWN_ID")
            title = m.get("title", "Untitled Meeting")
            date = m.get("created_at", "Unknown Date")
            parts = ", ".join(m.get("participants", [])) or "None logged"
            summary = m.get("summary") or "No summary available"
            kp_str = "\n".join([f"  - {p}" for p in m.get("key_points", [])]) or "  - None"
            dec_str = "\n".join([f"  - {d}" for d in m.get("decisions", [])]) or "  - None"
            dl_str = ", ".join(m.get("deadlines", [])) or "None specified"

            action_list = []
            for act in m.get("action_items", []):
                t = act.get("task", "")
                a = act.get("assignee") or act.get("assigned_participant") or "Unassigned"
                p = act.get("priority", "Medium")
                d = act.get("deadline", "Not specified")
                s = act.get("status", "Pending")
                action_list.append(f"  - Task: {t} | Assignee: {a} | Priority: {p} | Deadline: {d} | Status: {s}")
            actions_str = "\n".join(action_list) or "  - No action items recorded"

            t_snippet = m.get("transcript") or ""
            if len(t_snippet) > 800:
                t_snippet = t_snippet[:800] + "..."

            block = f"""
--- MEETING RECORD [Meeting ID: {mid}] ---
Title: {title}
Created Date: {date}
Participants: {parts}
Executive Summary: {summary}
Key Discussion Points:
{kp_str}
Strategic Decisions:
{dec_str}
Deadlines: {dl_str}
Action Items & Assigned Responsibilities:
{actions_str}
Transcript Excerpt:
{t_snippet}
----------------------------------------
"""
            blocks.append(block.strip())

        return "\n\n".join(blocks)

    def _call_gemini(self, question: str, context_text: str) -> Dict[str, Any]:
        """
        Invokes Google Gemini REST endpoint with strict grounding system prompt.
        """
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY is not configured.")

        model_name = "gemini-flash-lite-latest"
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={self.api_key}"

        prompt = f"""
HISTORICAL MEETING CONTEXT:
{context_text}

USER QUESTION:
{question}

Answer the user question strictly using the historical meeting records above. If the information is not present, clearly state that it was not found.
"""
        payload = {
            "systemInstruction": {"parts": [{"text": AI_SEARCH_SYSTEM_INSTRUCTION}]},
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "responseMimeType": "application/json",
                "responseSchema": AI_SEARCH_SCHEMA,
                "temperature": 0.0
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        with urllib.request.urlopen(req, timeout=4) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            raw_text = data["candidates"][0]["content"]["parts"][0]["text"]
            return json.loads(raw_text)

    @staticmethod
    def _term_in_tokens(term: str, tokens: set) -> bool:
        """Helper to match terms against token set with safe stemming."""
        if term in tokens:
            return True
        if len(term) > 4 and term.endswith('s') and not term.endswith('ss') and term[:-1] in tokens:
            return True
        if len(term) > 4 and term.endswith('ies') and (term[:-3] + 'y') in tokens:
            return True
        if f"{term}s" in tokens:
            return True
        return False

    def _fallback_grounded_search(self, question: str, meetings: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Deterministic, strictly grounded rule-based NLP search engine used
        when Gemini API key is not configured or quota limit is encountered.
        Guarantees zero hallucination and strict meeting_id attribution.
        """
        q_lower = question.lower()
        keywords = [k.lower() for k in self.extract_keywords(question)]

        matched_facts = []
        source_mids = set()

        is_decision_q = any(w in q_lower for w in ["decide", "decision", "agreed", "resolution", "choose"])
        is_task_q = any(w in q_lower for w in ["task", "assign", "action", "work on", "responsible", "todo"])
        is_deadline_q = any(w in q_lower for w in ["deadline", "due", "when", "date", "time", "schedule"])
        is_participant_q = any(w in q_lower for w in ["who", "participant", "attendee", "person", "people"])

        decision_kws = [k for k in keywords if k not in ["decide", "decision", "decisions", "agreed", "resolution", "choose"]]
        deadline_kws = [k for k in keywords if k not in ["deadline", "deadlines", "due", "when", "date", "time", "schedule"]]
        task_kws = [k for k in keywords if k not in ["task", "tasks", "assign", "assigned", "action", "work", "work on", "responsible", "todo", "who", "what"]]

        meta_noise = {"meeting", "meetings", "call", "sync", "discussion", "update", "part", "parts", "review", "logistics"}
        substantive_query_terms = [k for k in keywords if k not in meta_noise and k not in BROAD_REPO_TERMS]
        inquiry_subject_kws = substantive_query_terms
        target_task_kws = inquiry_subject_kws if inquiry_subject_kws else (task_kws if task_kws else keywords)
        target_decision_kws = inquiry_subject_kws if inquiry_subject_kws else (decision_kws if decision_kws else keywords)
        target_deadline_kws = inquiry_subject_kws if inquiry_subject_kws else (deadline_kws if deadline_kws else keywords)

        for m in meetings:
            mid = m.get("meeting_id")
            title = m.get("title", "")
            summary = m.get("summary", "")
            key_points = m.get("key_points", [])
            transcript = m.get("transcript") or ""
            actions = m.get("action_items", [])
            decisions = m.get("decisions", [])
            meeting_context_lower = f"{title} {summary} {' '.join(str(kp) for kp in key_points)}".lower()
            full_meeting_text = f"{meeting_context_lower} {transcript} {' '.join(str(d) for d in decisions)} {' '.join(act.get('task', '') + ' ' + (act.get('assignee') or '') for act in actions)}".lower()
            meeting_tokens = set(re.findall(r'[a-zA-Z0-9_-]+', full_meeting_text))

            # If user question asks about substantive concepts (like "cryptocurrency", "budget") that are absent
            # from the entire meeting record, skip this meeting (guarantees strict zero-hallucination grounding).
            missing_substantive = [k for k in substantive_query_terms if not self._term_in_tokens(k, meeting_tokens)]
            if missing_substantive and len(missing_substantive) >= max(1, len(substantive_query_terms) // 2):
                continue

            # 1. Action Items matching
            for act in m.get("action_items", []):
                t = act.get("task", "")
                a = act.get("assignee") or act.get("assigned_participant") or ""
                act_tokens = set(re.findall(r'[a-zA-Z0-9_-]+', f"{t} {a}".lower()))

                # Check if question keywords match this task or assignee
                hit = any(self._term_in_tokens(kw, act_tokens) for kw in target_task_kws) or (is_task_q and target_task_kws and any(self._term_in_tokens(kw, act_tokens) or self._term_in_tokens(kw, meeting_tokens) for kw in target_task_kws))
                if hit:
                    matched_facts.append(f"Task '{t}' was assigned to {a} (Deadline: {act.get('deadline')}, Priority: {act.get('priority')}) [Meeting ID: {mid}]")
                    source_mids.add(mid)

            # 2. Decisions matching
            for d in m.get("decisions", []):
                d_lower = d.lower()
                d_tokens = set(re.findall(r'[a-zA-Z0-9_-]+', d_lower))
                hit = any(self._term_in_tokens(kw, d_tokens) for kw in target_decision_kws) or (is_decision_q and target_decision_kws and any(self._term_in_tokens(kw, d_tokens) or self._term_in_tokens(kw, meeting_tokens) for kw in target_decision_kws))
                if hit:
                    matched_facts.append(f"Decision made: '{d}' [Meeting ID: {mid}]")
                    source_mids.add(mid)

            # 3. Deadlines matching
            if is_deadline_q:
                meeting_relevant = not target_deadline_kws or any(self._term_in_tokens(kw, meeting_tokens) for kw in target_deadline_kws)
                for dl in m.get("deadlines", []):
                    dl_tokens = set(re.findall(r'[a-zA-Z0-9_-]+', dl.lower()))
                    dl_hit = any(self._term_in_tokens(kw, dl_tokens) for kw in target_deadline_kws) or (meeting_relevant and is_deadline_q)
                    if dl_hit:
                        matched_facts.append(f"Deadline mentioned: '{dl}' in meeting '{title}' [Meeting ID: {mid}]")
                        source_mids.add(mid)

            # 4. Summary & Key Points matching
            is_summary_q = any(w in q_lower for w in ["summary", "summarize", "overview", "what happened", "tell me about", "what was the meeting about"])

            # If user question asks about specific absent concepts (like "cryptocurrency", "budget", "warp"),
            # do not match the summary just because of background context words.
            if inquiry_subject_kws:
                subject_matched = any(self._term_in_tokens(kw, meeting_tokens) for kw in inquiry_subject_kws)
            else:
                summary_tokens = set(re.findall(r'[a-zA-Z0-9_-]+', summary.lower()))
                subject_matched = any(self._term_in_tokens(kw, summary_tokens) for kw in keywords)

            if subject_matched and (is_summary_q or not (is_decision_q or is_task_q or is_deadline_q or is_participant_q)):
                matched_facts.append(f"From meeting summary: '{summary}' [Meeting ID: {mid}]")
                source_mids.add(mid)

            # 5. Participants matching
            if is_participant_q:
                parts = m.get("participants", [])
                hit_parts = [p for p in parts if any(kw in p.lower() for kw in keywords)] if keywords else parts
                if hit_parts:
                    matched_facts.append(f"Participants in '{title}': {', '.join(hit_parts)} [Meeting ID: {mid}]")
                    source_mids.add(mid)

        if not matched_facts:
            return {
                "answer": "The requested information was not found in the historical meeting records.",
                "found": False,
                "source_meeting_ids": [],
                "key_findings": []
            }

        # Deduplicate facts preserving order
        unique_facts = list(dict.fromkeys(matched_facts))
        answer_text = "\n".join([f"• {f}" for f in unique_facts[:5]])

        return {
            "answer": answer_text,
            "found": True,
            "source_meeting_ids": sorted(list(source_mids)),
            "key_findings": [f.split("[Meeting ID:")[0].strip("• ") for f in unique_facts[:5]]
        }

    def answer_question(self, question: str) -> Dict[str, Any]:
        """
        End-to-end question answering across historical meetings.
        Validates question, retrieves context, invokes LLM with grounding,
        and returns validated answer with source citations.
        """
        if not question or not str(question).strip():
            raise ValueError("Question cannot be empty or whitespace.")

        clean_q = str(question).strip()
        if len(clean_q) > 4000:
            raise ValueError("Question exceeds maximum permitted length of 4000 characters.")
        logger.info(f"Processing AI Search question: '{clean_q[:80]}...'")

        # Step 1: Retrieve context
        meetings = self.retrieve_context(clean_q)
        if not meetings:
            logger.info("No meeting records available in repository.")
            return {
                "success": True,
                "status": "success",
                "question": clean_q,
                "answer": "The requested information was not found in the historical meeting records.",
                "found": False,
                "source_meeting_ids": [],
                "key_findings": [],
                "sources": [],
                "source_meetings": []
            }

        context_text = self.build_prompt_context(meetings)

        # Step 2: Invoke LLM with Grounding (Gemini REST with Fallback)
        result_data = None
        if self.api_key:
            try:
                result_data = self._call_gemini(clean_q, context_text)
            except Exception as err:
                logger.warning(f"Gemini API call failed ({err}). Utilizing grounded fallback engine.")

        if not result_data:
            result_data = self._fallback_grounded_search(clean_q, meetings)

        # Step 3: Validate and enrich result
        source_ids = result_data.get("source_meeting_ids", [])
        if not isinstance(source_ids, list):
            source_ids = [str(source_ids)]

        # Filter sources to only those cited in the answer
        cited_sources = [m for m in meetings if m.get("meeting_id") in source_ids]
        if not cited_sources and result_data.get("found"):
            # If the LLM cited specific IDs not in the top list or formatted differently, retain candidate meetings
            cited_sources = meetings[:2]

        source_details = [
            {
                "meeting_id": m.get("meeting_id"),
                "title": m.get("title"),
                "created_at": m.get("created_at"),
                "duration_seconds": m.get("duration_seconds", 0.0),
                "summary": m.get("summary"),
                "decisions": m.get("decisions", []),
                "action_items": m.get("action_items", []),
                "participants": m.get("participants", []),
                "action_count": len(m.get("action_items", []))
            }
            for m in cited_sources
        ]

        return {
            "success": True,
            "status": "success",
            "question": clean_q,
            "answer": result_data.get("answer", "The requested information was not found in the historical meeting records."),
            "found": bool(result_data.get("found", False)),
            "source_meeting_ids": source_ids,
            "key_findings": result_data.get("key_findings", []),
            "sources": source_details,
            "source_meetings": source_details
        }

    def generate_historical_insight(
        self,
        question: str,
        topic: Optional[str] = None,
        participant: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Generates grounded cross-meeting summaries and strategic insights across
        multiple historical meeting records. If information is insufficient or missing,
        clearly indicates that insufficient historical data is available.
        """
        clean_q = question.strip() if question else ""
        if not clean_q:
            raise ValueError("Insight question cannot be empty or whitespace.")

        query_parts = [clean_q]
        if topic and topic.strip() and topic.strip().lower() not in clean_q.lower():
            query_parts.append(topic.strip())
        if participant and participant.strip() and participant.strip().lower() not in clean_q.lower():
            query_parts.append(participant.strip())

        search_query = " ".join(query_parts)

        # Retrieve relevant meetings
        keywords = self.extract_keywords(search_query)
        candidate_meetings = self.retrieve_context(search_query, max_meetings=7)

        if not candidate_meetings:
            return {
                "success": True,
                "status": "success",
                "question": clean_q,
                "topic": topic,
                "participant": participant,
                "answer": "Insufficient historical data available in the repository for the requested topic.",
                "found": False,
                "source_meeting_ids": [],
                "key_findings": [],
                "sources": [],
                "source_meetings": []
            }

        # Leverage answer_question for strict grounded synthesis
        res = self.answer_question(clean_q)

        if not res.get("found"):
            res["answer"] = "Insufficient historical data available in the repository for the requested topic."

        res["topic"] = topic
        res["participant"] = participant
        return res
