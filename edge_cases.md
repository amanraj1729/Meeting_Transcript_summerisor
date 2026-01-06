# Edge Cases & Failure Handling

This document describes the edge cases handled by the Meeting Automation System and the design choices that ensure the pipeline produces reliable outputs even with incomplete or noisy input data.

---

# 1. Missing Fields in Transcript
### Example:
- No date mentioned  
- No attendee list  
- No decisions or action items  

### Handling:
- System fills missing fields with defaults (e.g., `null` date, empty lists)
- Summary and structure still produced
- No pipeline failure

---

# 2. Poorly Formatted or Messy Transcripts
### Example:
- Inconsistent speaker labels  
- Random spacing  
- Extra symbols or unicode dashes (`–`, `—`)

### Handling:
- Preprocessing replaces unicode characters
- Normalizes spacing and removes noise
- Makes transcript LLM-friendly

---

# 3. No Clear Action Items
### Example:
Transcript contains discussion but no explicit tasks.

### Handling:
- Action items → empty list  
- Summary still generated  
- Title derived from first meaningful line

---

# 4. Model Tool-Calling Failure
### When it happens:
- OpenRouter returns invalid JSON
- LLM doesn’t trigger a tool_call
- Response incomplete

### Handling:
**Fallback extractor activates:**
- Extracts attendees
- Extracts simple action items
- Derives title
- Ensures full JSON schema is returned

### Result:
**The system NEVER returns an error.**

---

# 5. Extremely Long Transcripts
### Potential issue:
- Token limit may be exceeded  
- LLM may truncate content  

### Handling:
- System can be extended with:
  - chunking strategy
  - sliding-window extraction  
- Not implemented now but documented for future scaling

---

# 6. Repetitive or Duplicate Content
### Example:
Copy-pasted sections (as seen during testing)

### Handling:
- Preprocessing removes repeated whitespace  
- Extraction logic not affected  
- Summary remains consistent

---

# 7. Ambiguous Speaker Names
### Example:
"Me", "Team", "We all agreed..."

### Handling:
- LLM tries best guess
- Fallback extractor may miss these names
- Documented limitation

---

# 8. Empty Transcript
### Handling:
- Directly returns:
{
"title": "Untitled Meeting",
"attendees": [],
"decisions": [],
"key_points": [],
"action_items": [],
"summary": ""
}



---

# 9. Non-English Transcripts
### Handling:
- GPT-4o-mini is multilingual  
- Can extract structure in many languages  
- Rule-based fallback may fail for non-English  
- Documented limitation

---

# 10. Streamlit / API Network Errors
### Handling:
- API failures logged cleanly  
- User gets fallback JSON instead of crash  
- Streamlit UI continues running

---

# Summary

This system is resilient against:
- Missing fields  
- Messy formatting  
- LLM tool-calling failures  
- Incomplete data  
- Duplicate content  

The combination of **preprocessing + tool-calling + rule-based fallback** ensures the system is *robust, consistent, and practical for real automation use cases*.

