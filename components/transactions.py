import streamlit as st
from datetime import date
import database as db


def render_transactions(client, user, categories, category_names):
    """Render recent transactions list and edit form."""
    st.subheader("Recent Transactions")
    rows = db.get_recent_transactions(client, user.id)

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
                        db.delete_transaction(client, row["id"])
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
    else:
        st.info("No transactions yet")

    # Edit transaction form
    _handle_edit_form(client, categories, category_names)


def _handle_edit_form(client, categories, category_names):
    """Handle transaction edit form."""
    if "edit_transaction" not in st.session_state:
        return

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
            db.update_transaction(
                client, tx["id"], edit_amount, edit_description,
                category_id, edit_date.isoformat(), edit_annie
            )
            st.success("Transaction updated")
            del st.session_state["edit_transaction"]
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

    if cancel_edit:
        del st.session_state["edit_transaction"]
        st.rerun()
