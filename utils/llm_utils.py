import json
import re
from datetime import datetime, timezone

def extract_filters_from_question(question: str, llm) -> dict:
    """
    Uses ollama to automatically detect metadata filters from the user's question.
    Returns a dict like: {"source": "filename", "slide": 3, "date_ingested": "2026-04-14"}
    """

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    system_prompt = f"""You are a filter extraction assistant. Today's date is {today}.

Your job is to read a user's question and extract search filters from it.

Return ONLY a valid JSON object with these optional keys:
- "source": filename they mention (string, no extension)
- "slide": slide number they mention (integer)
- "content_type": if they mention "table" or "chart" (string)
- "date_ingested": exact date in YYYY-MM-DD format if they mention a specific date (string)
- "days": number of days if they say "last N days" or "past N days" (integer)

Rules:
- Only include a key if the question clearly mentions it
- If nothing matches, return an empty object: {{}}
- Return ONLY the JSON. No explanation. No markdown. No extra text.

Examples:
Question: "What is on slide 3?" → {{"slide": 3}}
Question: "Show me tables from the onboarding file" → {{"source": "sample_onboarding", "content_type": "table"}}
Question: "What did we discuss in the last 7 days?" → {{"days": 7}}
Question: "What is the capital of France?" → {{}}

Now extract filters from this question:
Question: "{question}"
Answer: """

    response = llm.invoke(system_prompt)
    # Clean up response — remove markdown code fences if Ollama adds them
    cleaned = response.strip()
    cleaned = re.sub(r"```json|```", "", cleaned).strip()

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        # If the LLM returned something unexpected, return empty (no filters)
        return {}
