import json
import re
from datetime import date
from typing import Optional
from gemini_client import get_gemini_model

SYSTEM_PROMPT = """You are a financial transaction parser for a family expense tracker.

Parse the user's natural language input into a JSON object with these fields:
- amount: numeric value (convert k=thousand, M=million, e.g., "200k"=200000, "1.5M"=1500000)
- description: brief description of the expense
- category: one of [Groceries, Dining, Transport, Utilities, Health, Education, Entertainment, Shopping, Hobbies, Other]
- is_annie_related: true if the expense mentions "Annie" or is clearly for a child
- date: ISO format (YYYY-MM-DD) if mentioned, otherwise null

Rules:
1. Amount is required. Look for numbers with optional k/K/m/M suffix.
2. If no category is clearly stated, infer from context or use "Other".
3. Set is_annie_related=true if "Annie", "baby", "daughter", or child-related items are mentioned.
4. For dates: "today"=today's date, "yesterday"=yesterday, or parse explicit dates.

Respond ONLY with valid JSON, no markdown or explanation.

Example inputs and outputs:
- "200k for Annie toys" -> {"amount": 200000, "description": "toys", "category": "Shopping", "is_annie_related": true, "date": null}
- "lunch 150k" -> {"amount": 150000, "description": "lunch", "category": "Dining", "is_annie_related": false, "date": null}
- "grabbed coffee 50k yesterday" -> {"amount": 50000, "description": "coffee", "category": "Dining", "is_annie_related": false, "date": "YESTERDAY"}
"""


def parse_expense(user_input: str, model=None) -> dict:
    """
    Parse natural language expense input into structured transaction data.

    Args:
        user_input: Natural language string like "200k for Annie toys"
        model: Optional Gemini model instance (will create one if not provided)

    Returns:
        dict with keys: amount, description, category, is_annie_related, date, raw_input
        Returns error dict if parsing fails
    """
    if model is None:
        model = get_gemini_model()

    # Build the prompt with today's date for reference
    today = date.today().isoformat()
    prompt = f"{SYSTEM_PROMPT}\n\nToday's date is {today}.\n\nParse this: {user_input}"

    try:
        response = model.generate_content(prompt)
        response_text = response.text.strip()

        # Clean up response (remove markdown code blocks if present)
        if response_text.startswith("```"):
            response_text = re.sub(r"```json?\n?", "", response_text)
            response_text = re.sub(r"\n?```$", "", response_text)

        parsed = json.loads(response_text)

        # Validate required field
        if "amount" not in parsed or parsed["amount"] is None:
            return {"error": "Could not parse amount from input", "raw_input": user_input}

        # Normalize the response
        result = {
            "amount": float(parsed.get("amount", 0)),
            "description": parsed.get("description", ""),
            "category": parsed.get("category", "Other"),
            "is_annie_related": bool(parsed.get("is_annie_related", False)),
            "date": _normalize_date(parsed.get("date"), today),
            "raw_input": user_input
        }

        return result

    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse AI response: {e}", "raw_input": user_input}
    except Exception as e:
        return {"error": f"Parsing error: {e}", "raw_input": user_input}


def _normalize_date(date_value: Optional[str], today: str) -> Optional[str]:
    """Convert date references to ISO format."""
    if date_value is None:
        return None

    date_str = str(date_value).upper()

    if date_str == "YESTERDAY":
        from datetime import timedelta
        yesterday = date.today() - timedelta(days=1)
        return yesterday.isoformat()
    elif date_str == "TODAY" or date_str == today:
        return today
    elif date_value:
        # Return as-is if it looks like a date
        return date_value

    return None
