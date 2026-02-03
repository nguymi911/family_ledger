import streamlit as st
from st_supabase_connection import SupabaseConnection


def get_connection():
    """Get Supabase connection."""
    return st.connection(
        "supabase",
        type=SupabaseConnection,
        url=st.secrets["connections"]["supabase"]["url"],
        key=st.secrets["connections"]["supabase"]["key"],
    )


@st.cache_data(ttl=300)
def load_categories(_client):
    """Load all categories with budget info, sorted by budget descending."""
    result = _client.from_("categories").select("id, name, monthly_budget").order("monthly_budget", desc=True).execute()
    return result.data


def get_category_map(categories_data):
    """Convert categories list to name->id map for dropdowns."""
    if not categories_data:
        return {}
    return {cat["name"]: cat["id"] for cat in categories_data}


def get_category_names(categories_data):
    """Get list of category names."""
    if not categories_data:
        return ["Groceries", "Dining", "Transport", "Utilities", "Health",
                "Education", "Entertainment", "Shopping", "Hobbies", "Other"]
    return list(get_category_map(categories_data).keys())


def get_monthly_spending(client, year: int, month: int, user_id: str):
    """Get spending totals by category for a given month."""
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    result = client.from_("transactions").select(
        "category_id, amount"
    ).eq("user_id", user_id).gte("date", start_date).lt("date", end_date).execute()

    spending = {}
    for tx in result.data:
        cat_id = tx.get("category_id")
        if cat_id:
            spending[cat_id] = spending.get(cat_id, 0) + float(tx["amount"])
    return spending


def add_category(client, name: str, budget: float):
    """Add a new category."""
    client.from_("categories").insert({
        "name": name,
        "monthly_budget": budget
    }).execute()


def update_category(client, category_id: str, budget: float):
    """Update category budget."""
    client.from_("categories").update({
        "monthly_budget": budget
    }).eq("id", category_id).execute()


def update_category_by_name(client, name: str, budget: float):
    """Update category budget by name."""
    client.from_("categories").update({
        "monthly_budget": budget
    }).eq("name", name).execute()


def delete_category(client, category_id: str):
    """Delete a category (unlinks transactions first)."""
    client.from_("transactions").update({
        "category_id": None
    }).eq("category_id", category_id).execute()
    client.from_("categories").delete().eq("id", category_id).execute()


def delete_category_by_name(client, name: str):
    """Delete a category by name."""
    result = client.from_("categories").select("id").eq("name", name).execute()
    if result.data:
        delete_category(client, result.data[0]["id"])
        return True
    return False


def get_recent_transactions(client, user_id: str, limit: int = 10):
    """Get recent transactions for a user."""
    return client.from_("transactions").select(
        "*, categories(name)"
    ).eq("user_id", user_id).order("date", desc=True).limit(limit).execute()


def get_monthly_transactions(client, user_id: str, year: int, month: int):
    """Get all transactions for a specific month."""
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    return client.from_("transactions").select(
        "*, categories(name)"
    ).eq("user_id", user_id).gte("date", start_date).lt("date", end_date).order("date", desc=True).execute()


def add_transaction(client, user_id: str, amount: float, description: str,
                    category_id: str, tx_date: str, is_annie_related: bool):
    """Add a new transaction."""
    transaction = {
        "user_id": user_id,
        "amount": amount,
        "description": description,
        "is_annie_related": is_annie_related,
        "date": tx_date,
    }
    if category_id:
        transaction["category_id"] = category_id
    client.from_("transactions").insert(transaction).execute()


def update_transaction(client, tx_id: str, amount: float, description: str,
                       category_id: str, tx_date: str, is_annie_related: bool):
    """Update an existing transaction."""
    update_data = {
        "amount": amount,
        "description": description,
        "is_annie_related": is_annie_related,
        "date": tx_date,
        "category_id": category_id
    }
    client.from_("transactions").update(update_data).eq("id", tx_id).execute()


def delete_transaction(client, tx_id: str):
    """Delete a transaction."""
    client.from_("transactions").delete().eq("id", tx_id).execute()
