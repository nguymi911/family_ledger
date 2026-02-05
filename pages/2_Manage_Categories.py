import streamlit as st
import database as db
from database import load_categories

# Get client from session state (set by app.py)
if "client" not in st.session_state:
    st.error("Session not initialized. Please refresh the page.")
    st.stop()

client = st.session_state["client"]

st.title("Categories")

# Add new category
st.subheader("Add Category")
with st.form("add_category_form"):
    new_name = st.text_input("Name")
    new_budget = st.number_input("Monthly Budget (₫)", min_value=0.0, step=100000.0)
    submitted = st.form_submit_button("Add Category", type="primary", use_container_width=True)
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
            # Category name and budget on same line
            budget_val = float(cat.get("monthly_budget") or 0)
            st.markdown(f"**{cat['name']}** · {budget_val:,.0f}₫")

            # Budget input
            new_budget = st.number_input(
                "Budget",
                value=budget_val,
                key=f"budget_{cat['id']}",
                label_visibility="collapsed",
                step=100000.0
            )

            # Action buttons side by side
            pending_delete = st.session_state.get("confirm_delete_category")
            if pending_delete == cat["id"]:
                st.warning(f"Delete **{cat['name']}**? This will unlink all transactions.")
                col1, col2 = st.columns(2, gap="small")
                with col1:
                    if st.button("Confirm", key=f"confirm_{cat['id']}", type="primary", use_container_width=True):
                        try:
                            db.delete_category(client, cat["id"])
                            del st.session_state["confirm_delete_category"]
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                with col2:
                    if st.button("Cancel", key=f"cancel_{cat['id']}", use_container_width=True):
                        del st.session_state["confirm_delete_category"]
                        st.rerun()
            else:
                col1, col2 = st.columns(2, gap="small")
                with col1:
                    if st.button("Save", key=f"update_{cat['id']}", use_container_width=True):
                        try:
                            db.update_category(client, cat["id"], new_budget)
                            st.success("Updated")
                            st.cache_data.clear()
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error: {e}")
                with col2:
                    if st.button("Delete", key=f"delete_{cat['id']}", use_container_width=True):
                        st.session_state["confirm_delete_category"] = cat["id"]
                        st.rerun()

            st.divider()
else:
    st.info("No categories yet. Add one above.")
