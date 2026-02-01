import streamlit as st
from datetime import date
from st_supabase_connection import SupabaseConnection
from gemini_client import get_gemini_model
from nlp_parser import parse_expense

# Initialize connection
st_conn = st.connection(
    "supabase",
    type=SupabaseConnection,
    url=st.secrets["connections"]["supabase"]["url"],
    key=st.secrets["connections"]["supabase"]["key"],
)

# Initialize Gemini model
model = get_gemini_model()

# Load categories for dropdown
@st.cache_data(ttl=300)
def load_categories():
    result = st_conn.client.from_("categories").select("id, name").execute()
    return {cat["name"]: cat["id"] for cat in result.data}

categories = load_categories()
category_names = list(categories.keys()) if categories else [
    "Groceries", "Dining", "Transport", "Utilities", "Health",
    "Education", "Entertainment", "Shopping", "Hobbies", "Other"
]

st.title("Family Ledger")

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
            "amount": amount,
            "description": description,
            "is_annie_related": is_annie,
            "date": tx_date.isoformat(),
        }
        if category_id:
            transaction["category_id"] = category_id

        try:
            st_conn.client.from_("transactions").insert(transaction).execute()
            st.success(f"Saved: {description} - {amount:,.0f}")
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
).order("date", desc=True).limit(10).execute()

if rows.data:
    for row in rows.data:
        cat_name = row.get("categories", {}).get("name", "—") if row.get("categories") else "—"
        annie_tag = " 👶" if row.get("is_annie_related") else ""
        st.write(f"**{row['date']}** | {row['description']} | {row['amount']:,.0f} | {cat_name}{annie_tag}")
else:
    st.info("No transactions yet")
