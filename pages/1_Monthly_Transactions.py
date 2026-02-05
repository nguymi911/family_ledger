import streamlit as st
from datetime import date
import database as db
from database import get_monthly_transactions, load_categories, get_category_map, get_category_names, get_all_profiles

# Get client and user from session state (set by app.py)
if "client" not in st.session_state or "user" not in st.session_state:
    st.error("Session not initialized. Please refresh the page.")
    st.stop()

client = st.session_state["client"]
user = st.session_state["user"]

# Load categories and profiles for display
categories_data = load_categories(client)
categories = get_category_map(categories_data)
category_names_list = get_category_names(categories_data)
profiles_data = get_all_profiles(client)
profiles_map = {p["id"]: p["display_name"] for p in profiles_data} if profiles_data else {}

st.title("Transactions")

# Filters: Year and Month on one row
col1, col2 = st.columns(2)
with col1:
    selected_year = st.selectbox(
        "Year",
        options=range(date.today().year, date.today().year - 5, -1),
        index=0,
        label_visibility="collapsed"
    )
with col2:
    selected_month = st.selectbox(
        "Month",
        options=range(1, 13),
        format_func=lambda m: date(2000, m, 1).strftime("%B"),
        index=date.today().month - 1,
        label_visibility="collapsed"
    )

# Optional filters in expander
with st.expander("Filters"):
    category_names = ["All"] + list(categories.keys())
    selected_category = st.selectbox("Category", options=category_names, index=0)
    user_names = ["All"] + [p["display_name"] for p in profiles_data] if profiles_data else ["All"]
    selected_user = st.selectbox("User", options=user_names, index=0)

# Fetch transactions (all users in household)
result = get_monthly_transactions(client, selected_year, selected_month)
transactions = result.data

# Apply filters
if "selected_category" in dir() and selected_category != "All":
    transactions = [
        tx for tx in transactions
        if tx.get("categories") and tx["categories"].get("name") == selected_category
    ]

if "selected_user" in dir() and selected_user != "All":
    transactions = [
        tx for tx in transactions
        if tx.get("profiles") and tx["profiles"].get("display_name") == selected_user
    ]

# Mobile-friendly styles
st.markdown("""
    <style>
    /* Larger text for transaction content */
    [data-testid="stMarkdown"] p {
        font-size: 1.1rem;
    }
    [data-testid="stCaptionContainer"] {
        font-size: 0.95rem;
    }
    /* Smaller buttons */
    [data-testid="stButton"] button {
        padding: 0.25rem 0.5rem;
        font-size: 0.85rem;
        min-height: 0;
    }
    </style>
""", unsafe_allow_html=True)

if transactions:
    # Calculate total
    total = sum(tx["amount"] for tx in transactions)
    st.metric("Total", f"{total:,.0f}₫")

    st.divider()

    # Display transactions as cards
    for tx in transactions:
        cat_name = tx.get("categories", {}).get("name", "") if tx.get("categories") else ""
        user_name = tx.get("profiles", {}).get("display_name", "") if tx.get("profiles") else ""
        annie_tag = " 👶" if tx.get("is_annie_related") else ""
        tx_date = tx["date"][5:] if tx.get("date") else ""

        with st.container():
            # Amount and description on same line
            st.markdown(f"**{tx['amount']:,.0f}₫** · **{tx['description']}{annie_tag}**")
            meta_parts = [tx_date]
            if cat_name:
                meta_parts.append(cat_name)
            if user_name:
                meta_parts.append(user_name)
            st.caption(" · ".join(meta_parts))

            # Action buttons side by side
            pending_delete = st.session_state.get("confirm_delete_transaction")
            if pending_delete == tx["id"]:
                st.warning("Delete this transaction?")
                col1, col2 = st.columns(2, gap="small")
                with col1:
                    if st.button("Confirm", key=f"confirm_{tx['id']}", type="primary", use_container_width=True):
                        try:
                            db.delete_transaction(client, tx["id"])
                            del st.session_state["confirm_delete_transaction"]
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                with col2:
                    if st.button("Cancel", key=f"cancel_{tx['id']}", use_container_width=True):
                        del st.session_state["confirm_delete_transaction"]
                        st.rerun()
            else:
                col1, col2 = st.columns(2, gap="small")
                with col1:
                    if st.button("Edit", key=f"edit_{tx['id']}", use_container_width=True):
                        st.session_state["edit_transaction"] = tx
                        st.rerun()
                with col2:
                    if st.button("Delete", key=f"delete_{tx['id']}", use_container_width=True):
                        st.session_state["confirm_delete_transaction"] = tx["id"]
                        st.rerun()

            st.divider()
else:
    st.info(f"No transactions for {date(selected_year, selected_month, 1).strftime('%B %Y')}")

# Edit transaction form (stacked vertically for mobile)
if "edit_transaction" in st.session_state:
    tx = st.session_state["edit_transaction"]
    st.subheader("Edit Transaction")

    with st.form("edit_tx_form"):
        edit_description = st.text_input("Description", value=tx.get("description") or "")
        edit_amount = st.number_input("Amount (₫)", value=float(tx["amount"]), min_value=0.0, step=1000.0)

        current_cat = tx.get("categories", {}).get("name") if tx.get("categories") else None
        cat_index = category_names_list.index(current_cat) if current_cat in category_names_list else 0
        edit_category = st.selectbox("Category", options=category_names_list, index=cat_index)

        edit_date = st.date_input("Date", value=date.fromisoformat(tx["date"]) if tx.get("date") else date.today())
        edit_annie = st.checkbox("Annie-related", value=tx.get("is_annie_related", False))

        col_save, col_cancel = st.columns(2)
        with col_save:
            save_edit = st.form_submit_button("Save", type="primary", use_container_width=True)
        with col_cancel:
            cancel_edit = st.form_submit_button("Cancel", use_container_width=True)

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
