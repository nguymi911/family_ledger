import streamlit as st
from datetime import date
from nlp_parser import parse_expense
import database as db


def render_smart_input(client, user, model, categories, category_names):
    """Render the smart input form and handle parsing."""
    st.subheader("What did you spend?")
    with st.form("expense_form"):
        expense_input = st.text_input(
            "Type naturally",
            placeholder="coffee 50k, lunch with Annie 200k, groceries 1.5M yesterday"
        )
        submitted = st.form_submit_button("Go", use_container_width=True)

    if submitted and expense_input:
        with st.spinner("Parsing..."):
            parsed = parse_expense(expense_input, model, category_names)
        if "error" not in parsed:
            st.session_state["parsed_expense"] = parsed
        else:
            st.error(parsed["error"])

    # Handle expense form
    _handle_expense_form(client, user, categories, category_names)


def _handle_expense_form(client, user, categories, category_names):
    """Handle parsed expense review and save."""
    if "parsed_expense" not in st.session_state:
        return

    parsed = st.session_state["parsed_expense"]

    st.write("**Review & Save:**")
    with st.form("save_form"):
        description = st.text_input("Description", value=parsed["description"])
        amount = st.number_input("Amount (₫)", value=parsed["amount"], min_value=0.0, step=1000.0)
        category = st.selectbox(
            "Category",
            options=category_names,
            index=category_names.index(parsed["category"]) if parsed["category"] in category_names else 0
        )
        tx_date = st.date_input(
            "Date",
            value=date.fromisoformat(parsed["date"]) if parsed["date"] else date.today()
        )
        is_annie = st.checkbox("Annie-related expense", value=parsed["is_annie_related"])

        col_save, col_cancel = st.columns(2, gap="small")
        with col_save:
            save_clicked = st.form_submit_button("Save", type="primary", use_container_width=True)
        with col_cancel:
            cancel_clicked = st.form_submit_button("Cancel", use_container_width=True)

    if save_clicked:
        category_id = categories.get(category) if categories else None
        try:
            db.add_transaction(
                client, user.id, amount, description,
                category_id, tx_date.isoformat(), is_annie
            )
            st.success(f"Saved: {description} - {amount:,.0f}₫")
            del st.session_state["parsed_expense"]
            st.rerun()
        except Exception as e:
            st.error(f"Failed to save: {e}")

    if cancel_clicked:
        del st.session_state["parsed_expense"]
        st.rerun()
