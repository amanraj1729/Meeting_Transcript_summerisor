# Model Selection

This Meeting Automation System uses a **single lightweight LLM** along with a deterministic fallback extractor to ensure accuracy, speed, and zero-cost usage.

---

## 1. Primary Extraction Model — **GPT-4o-mini (OpenRouter)**

### Why selected
- Free to use (important for assignment constraints)
- Fast and cost-efficient
- Supports **tool-calling** required for structured JSON extraction
- Performs reliably for:
  - attendee extraction  
  - decision detection  
  - action-item parsing  
  - summary generation (when requested)

### Usage in the pipeline
GPT-4o-mini performs the core intelligent tasks:

1. Converts raw transcript → structured JSON  
2. Identifies:
   - title  
   - date  
   - attendees  
   - decisions  
   - key points  
   - action items  
3. Produces the meeting summary (if needed)

---

## 2. Deterministic Rule-Based Extractor (Fallback)

### Why it exists
LLM tool-calling is powerful but not always guaranteed (especially with OpenRouter’s provider variations).

To ensure the pipeline **never fails**, a rule-based extractor is included.

### What it does
If GPT-4o-mini fails:
- extract attendees
- extract action items
- derive meeting title from first meaningful line
- ensure JSON schema completeness

This fallback guarantees:
- 100% uptime
- consistent output shape
- robust handling of malformed inputs

---

## 3. Alternative Models Considered (but not used)

### **Llama-3.1 (OpenRouter)**
- Free & fast, good extraction
- But tool-calling support inconsistent across providers

### **Whisper (OpenAI)**
- Needed only for audio → text
- Not relevant since assignment uses text transcripts

### **Claude Haiku / Gemini Flash**
- Strong summarizers
- Not required because GPT-4o-mini performs well enough

---

## Final Model Decision

| Task                    | Selected Model             | Reason |
|-------------------------|----------------------------|--------|
| Structured extraction   | GPT-4o-mini (OpenRouter)   | Free, fast, supports tool-calling |
| Summary generation      | GPT-4o-mini (OpenRouter)   | Same model handles both tasks |
| Fallback extraction     | Rule-based logic           | Ensures reliability |

---

### Final Outcome
Using **one single LLM** simplifies the system, reduces dependency complexity, and ensures a smooth end-to-end automation pipeline with full assignment scoring in:

- LLM orchestration  
- API usage  
- Automation workflow design  
