import streamlit as st
import json
from src.pipeline import process_meeting

st.set_page_config(page_title="Meeting → JSON", layout="wide")
st.title("Meeting Transcript → Structured JSON + Summary")
st.markdown("Paste a meeting transcript and click Extract. Uses OpenRouter (gpt-4o-mini) if OPENROUTER_API_KEY is set.")

transcript = st.text_area("Transcript", height=300, value="Meeting: \nDate: \nAttendees: \n\n")
if st.button("Extract"):
    with st.spinner("Processing..."):
        try:
            result = process_meeting(transcript)
            st.success("Processed")
            st.subheader("Summary")
            st.write(result.get("summary",""))
            st.subheader("Structured JSON")
            st.json(result)
            st.download_button("Download JSON", json.dumps(result, indent=2, ensure_ascii=False), file_name="meeting_output.json")
        except Exception as e:
            st.error(f"Processing failed: {e}")
