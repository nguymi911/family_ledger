import json
import re
from datetime import date
from typing import Optional
from gemini_client import get_gemini_model

SYSTEM_PROMPT = """Parse input as JSON. k=thousand, M=million.

EXPENSE: {"type":"expense","amount":NUMBER,"description":"TEXT","category":"NAME","is_annie_related":BOOL,"date":"YYYY-MM-DD or null"}
CATEGORY CMD: {"type":"category","action":"add|update|remove","name":"NAME","budget":NUMBER or null}

Rules: "add/set X 5M"=category cmd. "coffee 50k"=expense. Annie/baby/child=is_annie_related:true.
"""


def parse_input(user_input: str, model=None, categories: list = None) -> dict:
    """
    Parse natural language input into either expense or category command.
    """
    if model is None:
        model = get_gemini_model()

    today = date.today().isoformat()

    # Build prompt with available categories if provided
    category_hint = ""
    if categories:
        category_hint = f"\n\nAvailable categories: {', '.join(categories)}. Use one of these for expenses, or 'Other' if none fit."

    prompt = f"{SYSTEM_PROMPT}{category_hint}\n\nToday's date is {today}.\n\nParse this: {user_input}"

    try:
        response = model.generate_content(
            prompt,
            request_options={"timeout": 30}
        )
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


def parse_expense(user_input: str, model=None, categories: list = None) -> dict:
    """
    Parse natural language expense input into structured transaction data.
    Wrapper for backward compatibility - calls parse_input and filters for expenses.
    """
    result = parse_input(user_input, model, categories)
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
