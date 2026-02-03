import streamlit as st
from datetime import date
from database import get_monthly_transactions, load_categories, get_category_map

# Get client and user from session state (set by app.py)
client = st.session_state["client"]
user = st.session_state["user"]

# Load categories for display
categories_data = load_categories(client)
categories = get_category_map(categories_data)
category_id_to_name = {v: k for k, v in categories.items()}

st.title("Monthly Transactions")

# Filters: Year, Month, Category
col1, col2, col3 = st.columns(3)
with col1:
    selected_year = st.selectbox(
        "Year",
        options=range(date.today().year, date.today().year - 5, -1),
        index=0
    )
with col2:
    selected_month = st.selectbox(
        "Month",
        options=range(1, 13),
        format_func=lambda m: date(2000, m, 1).strftime("%B"),
        index=date.today().month - 1
    )
with col3:
    category_names = ["All"] + list(categories.keys())
    selected_category = st.selectbox("Category", options=category_names, index=0)

# Fetch transactions
result = get_monthly_transactions(client, user.id, selected_year, selected_month)
transactions = result.data

# Filter by category if selected
if selected_category != "All":
    transactions = [
        tx for tx in transactions
        if tx.get("categories") and tx["categories"].get("name") == selected_category
    ]

if transactions:
    # Calculate total
    total = sum(tx["amount"] for tx in transactions)
    st.metric("Total Spending", f"{total:,.0f}₫")

    st.divider()

    # Display transactions
    for tx in transactions:
        cat_name = tx.get("categories", {}).get("name", "—") if tx.get("categories") else "—"
        annie_tag = " 👶" if tx.get("is_annie_related") else ""

        col_date, col_desc, col_amount, col_cat = st.columns([2, 4, 2, 2])
        with col_date:
            st.write(tx["date"])
        with col_desc:
            st.write(f"{tx['description']}{annie_tag}")
        with col_amount:
            st.write(f"{tx['amount']:,.0f}₫")
        with col_cat:
            st.write(cat_name)
else:
    st.info(f"No transactions for {date(selected_year, selected_month, 1).strftime('%B %Y')}")
