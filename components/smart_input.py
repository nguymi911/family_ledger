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
        st.caption("💡 You can also manage budgets: *add Dining 3M* · *set Groceries 5M* · *remove Travel*")
        submitted = st.form_submit_button("Go")

    if submitted and expense_input:
        with st.spinner("Parsing..."):
            parsed = parse_expense(expense_input, model, category_names)
        if "error" not in parsed:
            if parsed.get("type") == "category":
                st.session_state["parsed_category"] = parsed
            else:
                st.session_state["parsed_expense"] = parsed
        else:
            st.error(parsed["error"])

    # Handle category commands
    _handle_category_command(client)

    # Handle expense form
    _handle_expense_form(client, user, categories, category_names)


def _handle_category_command(client):
    """Handle parsed category commands."""
    if "parsed_category" not in st.session_state:
        return

    cat_cmd = st.session_state["parsed_category"]
    action = cat_cmd.get("action")
    name = cat_cmd.get("name")
    budget = cat_cmd.get("budget", 0)

    st.write(f"**Category Command:** {action.title()} '{name}'")
    if budget:
        st.write(f"**Budget:** {budget:,.0f}₫")

    col_confirm, col_cancel = st.columns(2)
    with col_confirm:
        if st.button("Confirm", type="primary", key="confirm_cat"):
            try:
                if action == "add":
                    db.add_category(client, name, budget)
                    st.success(f"Added category: {name}")
                elif action == "update":
                    db.update_category_by_name(client, name, budget)
                    st.success(f"Updated {name} budget to {budget:,.0f}₫")
                elif action == "remove":
                    if db.delete_category_by_name(client, name):
                        st.success(f"Removed category: {name}")
                    else:
                        st.error(f"Category '{name}' not found")
                del st.session_state["parsed_category"]
                st.cache_data.clear()
                st.rerun()
            except Exception as e:
                st.error(f"Error: {e}")
    with col_cancel:
        if st.button("Cancel", key="cancel_cat"):
            del st.session_state["parsed_category"]
            st.rerun()


def _handle_expense_form(client, user, categories, category_names):
    """Handle parsed expense review and save."""
    if "parsed_expense" not in st.session_state:
        return

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
