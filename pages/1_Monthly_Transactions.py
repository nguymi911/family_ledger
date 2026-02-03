import streamlit as st
from datetime import date
import database as db
from database import get_monthly_transactions, load_categories, get_category_map, get_category_names

# Get client and user from session state (set by app.py)
client = st.session_state["client"]
user = st.session_state["user"]

# Load categories for display
categories_data = load_categories(client)
categories = get_category_map(categories_data)
category_names_list = get_category_names(categories_data)

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

        col_date, col_desc, col_amount, col_cat, col_edit, col_del = st.columns([2, 3, 2, 2, 1, 1])
        with col_date:
            st.write(tx["date"])
        with col_desc:
            st.write(f"{tx['description']}{annie_tag}")
        with col_amount:
            st.write(f"{tx['amount']:,.0f}₫")
        with col_cat:
            st.write(cat_name)
        with col_edit:
            if st.button("✏️", key=f"edit_tx_{tx['id']}"):
                st.session_state["edit_transaction"] = tx
                st.rerun()
        with col_del:
            if st.button("🗑️", key=f"del_tx_{tx['id']}"):
                try:
                    db.delete_transaction(client, tx["id"])
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
else:
    st.info(f"No transactions for {date(selected_year, selected_month, 1).strftime('%B %Y')}")

# Edit transaction form
if "edit_transaction" in st.session_state:
    tx = st.session_state["edit_transaction"]
    st.divider()
    st.subheader("Edit Transaction")
    with st.form("edit_tx_form"):
        col1, col2 = st.columns(2)
        with col1:
            edit_amount = st.number_input("Amount", value=float(tx["amount"]), min_value=0.0)
            current_cat = tx.get("categories", {}).get("name") if tx.get("categories") else None
            cat_index = category_names_list.index(current_cat) if current_cat in category_names_list else 0
            edit_category = st.selectbox("Category", options=category_names_list, index=cat_index)
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
            db.update_transaction(
                client, tx["id"], edit_amount, edit_description,
                category_id, edit_date.isoformat(), edit_annie
            )
            st.success("Transaction updated")
            del st.session_state["edit_transaction"]
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    if cancel_edit:
        del st.session_state["edit_transaction"]
        st.rerun()
