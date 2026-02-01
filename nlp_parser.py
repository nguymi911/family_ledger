import json
import re
from datetime import date
from typing import Optional
from gemini_client import get_gemini_model

SYSTEM_PROMPT = """You are a financial assistant for a family expense tracker.

First, determine if the input is:
1. An EXPENSE entry (contains amount/spending info)
2. A CATEGORY COMMAND (add/update/remove category)

For EXPENSE entries, return:
{
  "type": "expense",
  "amount": numeric value (convert k=thousand, M=million, e.g., "200k"=200000, "1.5M"=1500000),
  "description": brief description,
  "category": category name,
  "is_annie_related": true if mentions "Annie"/baby/daughter/child,
  "date": ISO format or null
}

For CATEGORY COMMANDS, return:
{
  "type": "category",
  "action": "add" | "update" | "remove",
  "name": category name,
  "budget": numeric value (for add/update, convert k/M notation)
}

Rules:
1. For expenses: amount is required, infer category from context or use "Other"
2. For categories: detect keywords like "add/create category", "set/update budget", "remove/delete category"
3. Convert k=thousand, M=million (e.g., "5M"=5000000, "500k"=500000)

Respond ONLY with valid JSON, no markdown or explanation.

Examples:
- "200k for Annie toys" -> {"type": "expense", "amount": 200000, "description": "toys", "category": "Shopping", "is_annie_related": true, "date": null}
- "add category Travel with budget 2M" -> {"type": "category", "action": "add", "name": "Travel", "budget": 2000000}
- "set Groceries budget to 5M" -> {"type": "category", "action": "update", "name": "Groceries", "budget": 5000000}
- "remove category Hobbies" -> {"type": "category", "action": "remove", "name": "Hobbies", "budget": null}
"""


def parse_input(user_input: str, model=None) -> dict:
    """
    Parse natural language input into either expense or category command.

    Args:
        user_input: Natural language string
        model: Optional Gemini model instance

    Returns:
        dict with 'type' key ('expense' or 'category') and relevant fields
        Returns error dict if parsing fails
    """
    if model is None:
        model = get_gemini_model()

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
        parsed["raw_input"] = user_input

        # Handle based on type
        if parsed.get("type") == "category":
            return _normalize_category_command(parsed)
        else:
            return _normalize_expense(parsed, today)

    except json.JSONDecodeError as e:
        return {"error": f"Failed to parse AI response: {e}", "raw_input": user_input}
    except Exception as e:
        return {"error": f"Parsing error: {e}", "raw_input": user_input}


def _normalize_expense(parsed: dict, today: str) -> dict:
    """Normalize expense data."""
    if "amount" not in parsed or parsed["amount"] is None:
        return {"error": "Could not parse amount from input", "raw_input": parsed.get("raw_input", "")}

    return {
        "type": "expense",
        "amount": float(parsed.get("amount", 0)),
        "description": parsed.get("description", ""),
        "category": parsed.get("category", "Other"),
        "is_annie_related": bool(parsed.get("is_annie_related", False)),
        "date": _normalize_date(parsed.get("date"), today),
        "raw_input": parsed.get("raw_input", "")
    }


def _normalize_category_command(parsed: dict) -> dict:
    """Normalize category command data."""
    action = parsed.get("action", "").lower()
    if action not in ["add", "update", "remove"]:
        return {"error": f"Unknown category action: {action}", "raw_input": parsed.get("raw_input", "")}

    name = parsed.get("name", "").strip()
    if not name:
        return {"error": "Category name is required", "raw_input": parsed.get("raw_input", "")}

    result = {
        "type": "category",
        "action": action,
        "name": name,
        "raw_input": parsed.get("raw_input", "")
    }

    if action in ["add", "update"] and parsed.get("budget") is not None:
        result["budget"] = float(parsed.get("budget", 0))

    return result


def parse_expense(user_input: str, model=None) -> dict:
    """
    Parse natural language expense input into structured transaction data.
    Wrapper for backward compatibility - calls parse_input and filters for expenses.
    """
    result = parse_input(user_input, model)
    if result.get("type") == "category":
        # Return as-is so app.py can handle it
        return result
    return result


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
