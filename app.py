import streamlit as st
from datetime import date
from st_supabase_connection import SupabaseConnection
from gemini_client import get_gemini_model
from nlp_parser import parse_expense

st.set_page_config(page_title="Family Ledger", page_icon="💰")

# Initialize connection
st_conn = st.connection(
    "supabase",
    type=SupabaseConnection,
    url=st.secrets["connections"]["supabase"]["url"],
    key=st.secrets["connections"]["supabase"]["key"],
)

# Authentication
def get_user():
    """Get current authenticated user from session."""
    try:
        session = st_conn.client.auth.get_session()
        if session:
            return session.user
    except Exception:
        pass
    return None

def login_with_google():
    """Initiate Google OAuth login."""
    try:
        response = st_conn.client.auth.sign_in_with_oauth({
            "provider": "google",
            "options": {
                "redirect_to": st.secrets.get("app_url", "http://localhost:8501")
            }
        })
        if response.url:
            st.markdown(f'<meta http-equiv="refresh" content="0;url={response.url}">', unsafe_allow_html=True)
    except Exception as e:
        st.error(f"Login error: {e}")

def logout():
    """Sign out the current user."""
    try:
        st_conn.client.auth.sign_out()
        st.rerun()
    except Exception as e:
        st.error(f"Logout error: {e}")

# Check for OAuth callback
query_params = st.query_params
if "access_token" in query_params or "code" in query_params:
    # Clear query params after OAuth callback
    st.query_params.clear()
    st.rerun()

# Get current user
user = get_user()

# Login page
if not user:
    st.title("Annie Budget 💰")
    st.write("Please sign in to continue.")

    if st.button("Sign in with Google", type="primary"):
        login_with_google()

    st.stop()

# Initialize Gemini model (only after auth)
model = get_gemini_model()

# Load categories with budget info
@st.cache_data(ttl=300)
def load_categories():
    result = st_conn.client.from_("categories").select("id, name, monthly_budget, is_fixed").execute()
    return result.data

def get_category_map(categories_data):
    """Convert categories list to name->id map for dropdowns."""
    return {cat["name"]: cat["id"] for cat in categories_data}

def get_monthly_spending(year: int, month: int, user_id: str):
    """Get spending totals by category for a given month."""
    start_date = f"{year}-{month:02d}-01"
    if month == 12:
        end_date = f"{year + 1}-01-01"
    else:
        end_date = f"{year}-{month + 1:02d}-01"

    result = st_conn.client.from_("transactions").select(
        "category_id, amount"
    ).eq("user_id", user_id).gte("date", start_date).lt("date", end_date).execute()

    # Sum by category
    spending = {}
    for tx in result.data:
        cat_id = tx.get("category_id")
        if cat_id:
            spending[cat_id] = spending.get(cat_id, 0) + float(tx["amount"])
    return spending

categories_data = load_categories()
categories = get_category_map(categories_data) if categories_data else {}
category_names = list(categories.keys()) if categories else [
    "Groceries", "Dining", "Transport", "Utilities", "Health",
    "Education", "Entertainment", "Shopping", "Hobbies", "Other"
]

st.title("Family Ledger")

# Sidebar - User & Settings
with st.sidebar:
    st.write(f"**{user.email}**")
    if st.button("Logout"):
        logout()

    st.divider()
    st.header("Settings")

    if st.button("🔄 Refresh Data"):
        st.cache_data.clear()
        st.rerun()

    st.subheader("Manage Categories")

    # Add new category
    with st.expander("Add Category"):
        new_name = st.text_input("Name", key="new_cat_name")
        new_budget = st.number_input("Monthly Budget", min_value=0.0, key="new_cat_budget")
        new_fixed = st.checkbox("Fixed expense", key="new_cat_fixed")
        if st.button("Add"):
            if new_name:
                try:
                    st_conn.client.from_("categories").insert({
                        "name": new_name,
                        "monthly_budget": new_budget,
                        "is_fixed": new_fixed
                    }).execute()
                    st.success(f"Added {new_name}")
                    st.cache_data.clear()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")

    # Edit existing categories
    if categories_data:
        with st.expander("Edit Categories"):
            for cat in categories_data:
                st.write(f"**{cat['name']}**")
                col1, col2 = st.columns(2)
                with col1:
                    new_budget = st.number_input(
                        "Budget",
                        value=float(cat.get("monthly_budget") or 0),
                        key=f"budget_{cat['id']}"
                    )
                with col2:
                    is_fixed = st.checkbox(
                        "Fixed",
                        value=cat.get("is_fixed", False),
                        key=f"fixed_{cat['id']}"
                    )
                col_update, col_delete = st.columns(2)
                with col_update:
                    if st.button("Update", key=f"update_{cat['id']}"):
                        try:
                            st_conn.client.from_("categories").update({
                                "monthly_budget": new_budget,
                                "is_fixed": is_fixed
                            }).eq("id", cat["id"]).execute()
                            st.success("Updated")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                with col_delete:
                    if st.button("🗑️", key=f"delete_{cat['id']}"):
                        try:
                            # Unlink transactions first
                            st_conn.client.from_("transactions").update({
                                "category_id": None
                            }).eq("category_id", cat["id"]).execute()
                            # Then delete category
                            st_conn.client.from_("categories").delete().eq("id", cat["id"]).execute()
                            st.success("Deleted")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")

# Budget Burn-Down View
st.subheader("Monthly Budget")
today = date.today()
monthly_spending = get_monthly_spending(today.year, today.month, user.id)

if categories_data:
    # Separate fixed and variable categories
    fixed_cats = [c for c in categories_data if c.get("is_fixed")]
    variable_cats = [c for c in categories_data if not c.get("is_fixed")]

    # Calculate totals
    total_budget = sum(float(c.get("monthly_budget") or 0) for c in categories_data)
    total_spent = sum(monthly_spending.values())
    total_remaining = total_budget - total_spent

    # Summary metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Budget", f"{total_budget:,.0f}₫")
    with col2:
        st.metric("Spent", f"{total_spent:,.0f}₫")
    with col3:
        delta_color = "normal" if total_remaining >= 0 else "inverse"
        st.metric("Remaining", f"{total_remaining:,.0f}₫", delta=f"{total_remaining:,.0f}₫", delta_color=delta_color)

    # Variable expenses (envelopes)
    if variable_cats:
        st.write("**Variable Expenses**")
        for cat in variable_cats:
            budget = float(cat.get("monthly_budget") or 0)
            spent = monthly_spending.get(cat["id"], 0)
            remaining = budget - spent

            if budget > 0:
                progress = min(spent / budget, 1.0)
                status = "🔴" if spent > budget else "🟡" if progress > 0.8 else "🟢"
            else:
                progress = 0
                status = "⚪"

            col_name, col_bar, col_nums = st.columns([2, 4, 2])
            with col_name:
                st.write(f"{status} {cat['name']}")
            with col_bar:
                st.progress(progress)
            with col_nums:
                st.write(f"{spent:,.0f}₫ / {budget:,.0f}₫")

    # Fixed expenses
    if fixed_cats:
        st.write("**Fixed Expenses**")
        for cat in fixed_cats:
            budget = float(cat.get("monthly_budget") or 0)
            spent = monthly_spending.get(cat["id"], 0)

            col_name, col_status, col_nums = st.columns([2, 4, 2])
            with col_name:
                st.write(f"📌 {cat['name']}")
            with col_status:
                if spent >= budget and budget > 0:
                    st.write("✓ Paid")
                elif spent > 0:
                    st.write("Partial")
                else:
                    st.write("Pending")
            with col_nums:
                st.write(f"{spent:,.0f}₫ / {budget:,.0f}₫")
else:
    st.info("No categories configured. Add categories in Supabase to enable budget tracking.")

st.divider()

# NLP Expense Entry
st.subheader("Quick Entry")
with st.form("expense_form"):
    expense_input = st.text_input(
        "Enter expense",
        placeholder="e.g., 200k for Annie toys, lunch 150k, coffee 50k yesterday"
    )
    submitted = st.form_submit_button("Parse")

if submitted and expense_input:
    with st.spinner("Parsing..."):
        parsed = parse_expense(expense_input, model)
    if "error" not in parsed:
        st.session_state["parsed_expense"] = parsed

# Show parsed result and save form
if "parsed_expense" in st.session_state:
    parsed = st.session_state["parsed_expense"]

    st.write("**Review & Save:**")
    with st.form("save_form"):
        col1, col2 = st.columns(2)
        with col1:
            amount = st.number_input("Amount", value=parsed["amount"], min_value=0.0)
            category = st.selectbox(
                "Category",
                options=category_names,
                index=category_names.index(parsed["category"]) if parsed["category"] in category_names else 0
            )
        with col2:
            description = st.text_input("Description", value=parsed["description"])
            tx_date = st.date_input(
                "Date",
                value=date.fromisoformat(parsed["date"]) if parsed["date"] else date.today()
            )

        is_annie = st.checkbox("Annie-related expense", value=parsed["is_annie_related"])

        col_save, col_cancel = st.columns(2)
        with col_save:
            save_clicked = st.form_submit_button("Save Transaction", type="primary")
        with col_cancel:
            cancel_clicked = st.form_submit_button("Cancel")

    if save_clicked:
        # Get category_id
        category_id = categories.get(category) if categories else None

        # Insert transaction
        transaction = {
            "user_id": user.id,
            "amount": amount,
            "description": description,
            "is_annie_related": is_annie,
            "date": tx_date.isoformat(),
        }
        if category_id:
            transaction["category_id"] = category_id

        try:
            st_conn.client.from_("transactions").insert(transaction).execute()
            st.success(f"Saved: {description} - {amount:,.0f}₫")
            del st.session_state["parsed_expense"]
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save: {e}")

    if cancel_clicked:
        del st.session_state["parsed_expense"]
        st.rerun()

elif submitted and expense_input:
    # Show error if parsing failed
    parsed = parse_expense(expense_input, model)
    if "error" in parsed:
        st.error(parsed["error"])

st.divider()

# Recent Transactions
st.subheader("Recent Transactions")
rows = st_conn.client.from_("transactions").select(
    "*, categories(name)"
).eq("user_id", user.id).order("date", desc=True).limit(10).execute()

if rows.data:
    for row in rows.data:
        cat_name = row.get("categories", {}).get("name", "—") if row.get("categories") else "—"
        annie_tag = " 👶" if row.get("is_annie_related") else ""
        col_info, col_edit, col_del = st.columns([7, 1, 1])
        with col_info:
            st.write(f"**{row['date']}** | {row['description']} | {row['amount']:,.0f}₫ | {cat_name}{annie_tag}")
        with col_edit:
            if st.button("✏️", key=f"edit_tx_{row['id']}"):
                st.session_state["edit_transaction"] = row
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_tx_{row['id']}"):
                try:
                    st_conn.client.from_("transactions").delete().eq("id", row["id"]).execute()
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
else:
    st.info("No transactions yet")

# Edit transaction form
if "edit_transaction" in st.session_state:
    tx = st.session_state["edit_transaction"]
    st.subheader("Edit Transaction")
    with st.form("edit_tx_form"):
        col1, col2 = st.columns(2)
        with col1:
            edit_amount = st.number_input("Amount", value=float(tx["amount"]), min_value=0.0)
            current_cat = tx.get("categories", {}).get("name") if tx.get("categories") else None
            cat_index = category_names.index(current_cat) if current_cat in category_names else 0
            edit_category = st.selectbox("Category", options=category_names, index=cat_index)
        with col2:
            edit_description = st.text_input("Description", value=tx.get("description") or "")
            edit_date = st.date_input("Date", value=date.fromisoformat(tx["date"]) if tx.get("date") else date.today())
        edit_annie = st.checkbox("Annie-related", value=tx.get("is_annie_related", False))

        col_save, col_cancel = st.columns(2)
        with col_save:
            save_edit = st.form_submit_button("Save Changes", type="primary")
        with col_cancel:
            cancel_edit = st.form_submit_button("Cancel")

    if save_edit:
        category_id = categories.get(edit_category) if categories else None
        try:
            update_data = {
                "amount": edit_amount,
                "description": edit_description,
                "is_annie_related": edit_annie,
                "date": edit_date.isoformat(),
                "category_id": category_id
            }
            st_conn.client.from_("transactions").update(update_data).eq("id", tx["id"]).execute()
            st.success("Transaction updated")
            del st.session_state["edit_transaction"]
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    if cancel_edit:
        del st.session_state["edit_transaction"]
        st.rerun()
