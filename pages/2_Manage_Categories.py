import streamlit as st
import database as db
from database import load_categories

# Get client from session state (set by app.py)
client = st.session_state["client"]

st.title("Manage Categories")

if st.button("🔄 Refresh Data"):
    st.cache_data.clear()
    st.rerun()

st.divider()

# Add new category
st.subheader("Add Category")
with st.form("add_category_form"):
    col1, col2 = st.columns(2)
    with col1:
        new_name = st.text_input("Name")
    with col2:
        new_budget = st.number_input("Monthly Budget (₫)", min_value=0.0, step=100000.0)
    submitted = st.form_submit_button("Add Category", type="primary")
    if submitted and new_name:
        try:
            db.add_category(client, new_name, new_budget)
            st.success(f"Added {new_name}")
            st.cache_data.clear()
            st.rerun()
        except Exception as e:
            st.error(f"Error: {e}")

st.divider()

# Edit existing categories
st.subheader("Existing Categories")
categories_data = load_categories(client)

if categories_data:
    for cat in categories_data:
        with st.container():
            col_name, col_budget, col_actions = st.columns([3, 3, 2])
            with col_name:
                st.write(f"**{cat['name']}**")
            with col_budget:
                new_budget = st.number_input(
                    "Budget",
                    value=float(cat.get("monthly_budget") or 0),
                    key=f"budget_{cat['id']}",
                    label_visibility="collapsed",
                    step=100000.0
                )
            with col_actions:
                col_update, col_delete = st.columns(2)
                with col_update:
                    if st.button("💾", key=f"update_{cat['id']}", help="Save"):
                        try:
                            db.update_category(client, cat["id"], new_budget)
                            st.success("Updated")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                with col_delete:
                    if st.button("🗑️", key=f"delete_{cat['id']}", help="Delete"):
                        try:
                            db.delete_category(client, cat["id"])
                            st.success("Deleted")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
else:
    st.info("No categories yet. Add one above.")
