#!/usr/bin/env python3
"""
pipeline.py
Meeting -> Structured JSON extractor using OpenRouter (gpt-4o-mini) with tool-calling and deterministic fallback.
Set OPENROUTER_API_KEY in the environment before running.
"""

import os, json, re, requests
from typing import Dict, Any

# ----------------- Config -----------------
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_MODEL = "gpt-4o-mini"

if not OPENROUTER_API_KEY:
    # Do not raise here; allow functions to be imported without key for static analysis.
    pass

# ----------------- Schema -----------------
EXTRACTION_SCHEMA = {
    "type": "object",
    "required": ["title", "attendees", "action_items", "summary"],
    "properties": {
        "title": {"type": "string"},
        "date": {"type": ["string", "null"]},
        "attendees": {"type": "array", "items": {"type": "string"}},
        "decisions": {"type": "array", "items": {"type": "string"}},
        "key_points": {"type": "array", "items": {"type": "string"}},
        "action_items": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["task"],
                "properties": {
                    "task": {"type": "string"},
                    "assignee": {"type": ["string", "null"]},
                    "due_date": {"type": ["string", "null"]}
                }
            }
        },
        "summary": {"type": "string"}
    }
}

# ----------------- Helpers -----------------

def preprocess_text(text: str) -> str:
    if not isinstance(text, str):
        return ""
    text = text.replace("\u2013", "-").replace("\u2014", "-")
    text = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", " ", text)
    text = re.sub(r"\s+\n", "\n", text)
    text = re.sub(r"\n\s+", "\n", text)
    text = re.sub(r"[ \t]{2,}", " ", text)
    return text.strip()

def call_openrouter_llm_raw(payload: dict, timeout: int = 60) -> dict:
    key = os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise RuntimeError("OPENROUTER_API_KEY not set in environment.")
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json; charset=utf-8"
    }
    body = json.dumps(payload, ensure_ascii=True).encode("utf-8")
    resp = requests.post(OPENROUTER_URL, headers=headers, data=body, timeout=timeout)
    if resp.status_code >= 400:
        raise RuntimeError(f"OpenRouter error {resp.status_code}: {resp.text}")
    return resp.json()

def call_openrouter_llm_messages(messages, temperature=0.0, max_tokens=1200):
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens
    }
    return call_openrouter_llm_raw(payload)

# ----------------- LLM extraction (tool-calling) -----------------

def call_llm_for_extraction(transcript: str) -> Dict[str, Any]:
    messages = [
        {"role": "system", "content": "You are an expert meeting extractor. Return structured JSON via tool call."},
        {"role": "user", "content": f"Extract meeting information from the transcript below:\\n\\n{transcript}"}
    ]

    payload = {
        "model": OPENROUTER_MODEL,
        "messages": messages,
        "tools": [
            {
                "type": "function",
                "function": {
                    "name": "extract_meeting",
                    "description": "Extract meeting information and return structured JSON per schema",
                    "parameters": EXTRACTION_SCHEMA
                }
            }
        ],
        "tool_choice": "auto",
        "temperature": 0.0,
        "max_tokens": 1200
    }

    resp = call_openrouter_llm_raw(payload)
    # Try to parse tool call result
    try:
        tool_call = resp["choices"][0].get("message", {}).get("tool_calls", [])[0]
        arguments = tool_call["function"]["arguments"]
    except Exception:
        # fallback to content
        arguments = resp["choices"][0].get("message", {}).get("content", "")

    # tolerant JSON parse
    try:
        return json.loads(arguments)
    except Exception:
        s = arguments.replace("'", '"')
        s = re.sub(r",\s*}", "}", s)
        s = re.sub(r",\s*]", "]", s)
        return json.loads(s)

# ----------------- Summarizer -----------------

def call_llm_for_summary(transcript: str) -> str:
    messages = [
        {"role": "system", "content": "You are an expert summarizer. Produce a concise 1-3 paragraph summary."},
        {"role": "user", "content": f"Transcript:\\n{transcript}"}
    ]
    resp = call_openrouter_llm_messages(messages, temperature=0.2, max_tokens=400)
    msg = resp["choices"][0].get("message", {})
    return msg.get("content", "").strip()

# ----------------- Deterministic fallback extractor -----------------

def rule_based_extractor(transcript: str) -> Dict[str, Any]:
    lines = [ln.strip() for ln in transcript.splitlines() if ln.strip()]
    title = lines[0] if lines else "Untitled Meeting"
    date = None
    attendees = []
    decisions = []
    key_points = []
    action_items = []
    # find date and attendees lines
    for ln in lines[:8]:
        if "Date" in ln or re.search(r"\d{4}-\d{2}-\d{2}", ln):
            m = re.search(r"(\d{4}-\d{2}-\d{2})", ln)
            date = m.group(1) if m else ln.split(":",1)[-1].strip()
        if "Attendees" in ln or "Attendee" in ln:
            parts = ln.split(":",1)[-1]
            attendees = [p.strip() for p in parts.split(",") if p.strip()]
    # simple action extraction
    for ln in lines:
        if ln.lower().startswith("decision") or "Decision" in ln:
            decisions.append(ln.split(":",1)[-1].strip())
        if ln.lower().startswith("action") or "Action" in ln:
            body = ln.split(":",1)[-1].strip() if ":" in ln else ln
            # split by . or ; or -
            parts = re.split(r"[.;]", body)
            for p in parts:
                p = p.strip()
                if not p: 
                    continue
                # try "Name to do task by date" or "Name - task"
                m = re.match(r"([A-Za-z]+)\s+(?:to|will|will\s+be)\s+(.+?)(?:by\s+([0-9]{4}-[0-9]{2}-[0-9]{2}|next\s+\w+))?$", p, flags=re.I)
                if m:
                    assignee = m.group(1)
                    task = m.group(2).strip()
                    due = m.group(3) if m.group(3) else None
                    action_items.append({"task": task, "assignee": assignee, "due_date": due})
                else:
                    # try split with - or - format "Name - task"
                    if "-" in p:
                        a,t = [s.strip() for s in p.split("-",1)]
                        action_items.append({"task": t, "assignee": a, "due_date": None})
                    else:
                        action_items.append({"task": p, "assignee": None, "due_date": None})
    # key points simple: short lines with colon but not metadata
    for ln in lines:
        if ":" in ln and not any(k in ln for k in ["Attendees", "Date", "Meeting", "Action", "Decision", "Title"]):
            if len(ln) < 140:
                key_points.append(ln.strip())
    # ensure unique attendees
    attendees = list(dict.fromkeys(attendees))
    result = {
        "title": title,
        "date": date,
        "attendees": attendees,
        "decisions": decisions,
        "key_points": key_points,
        "action_items": action_items,
        "summary": ""
    }
    return result

# ----------------- Postprocess and pipeline -----------------

def postprocess_extraction(extracted: Dict[str, Any]) -> Dict[str, Any]:
    out = {}
    out["title"] = extracted.get("title") or "Untitled Meeting"
    out["date"] = extracted.get("date") or None
    out["attendees"] = extracted.get("attendees") or []
    out["decisions"] = extracted.get("decisions") or []
    out["key_points"] = extracted.get("key_points") or []
    ai = extracted.get("action_items") or []
    normalized_ai = []
    for item in ai:
        if isinstance(item, dict):
            task = item.get("task","")
            assignee = item.get("assignee") or None
            due = item.get("due_date") or None
        else:
            task = str(item)
            assignee = None
            due = None
        normalized_ai.append({"task": task, "assignee": assignee, "due_date": due})
    out["action_items"] = normalized_ai
    out["summary"] = extracted.get("summary") or ""
    return out

def process_meeting(transcript: str) -> Dict[str, Any]:
    cleaned = preprocess_text(transcript)
    try:
        extracted = call_llm_for_extraction(cleaned)
    except Exception as e:
        print("LLM extraction failed:", e)
        extracted = rule_based_extractor(cleaned)
    if not extracted.get("summary"):
        try:
            extracted["summary"] = call_llm_for_summary(cleaned)
        except Exception as e:
            print("Summary generation failed:", e)
            extracted["summary"] = ""
    return postprocess_extraction(extracted)

# ----------------- CLI / example -----------------

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", "-i", help="Input transcript file (.txt)")
    parser.add_argument("--output", "-o", help="Output JSON file", default="out.json")
    parser.add_argument("--use-demo", action="store_true", help="Run built-in demo samples")
    args = parser.parse_args()
    if args.use_demo:
        SAMPLE_1 = """
Meeting: Weekly Product Sync
Date: 2025-11-25
Attendees: Alice, Bob, Charlie

Alice: We need to finalize the UI for the dashboard by next Wednesday.
Bob: I'll take ownership of the dashboard charts.
Charlie: I will prepare the dataset and share it by Monday.
Decision: Use ChartLib v2 for visualization.
Action: Bob to implement charts by 2025-12-03. Charlie to share data by 2025-11-30.
"""
        r = process_meeting(SAMPLE_1)
        print(json.dumps(r, indent=2, ensure_ascii=False))
    else:
        if not args.input:
            print("Provide --input or use --use-demo")
        else:
            txt = open(args.input, "r", encoding="utf-8").read()
            out = process_meeting(txt)
            open(args.output, "w", encoding="utf-8").write(json.dumps(out, indent=2, ensure_ascii=False))
            print("Wrote", args.output)
