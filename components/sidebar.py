import streamlit as st
from auth import logout
import database as db


def render_sidebar(client, user, categories_data):
    """Render the sidebar with user info and category management."""
    with st.sidebar:
        st.write(f"**{user.email}**")
        if st.button("Logout"):
            logout(client)

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
            if st.button("Add"):
                if new_name:
                    try:
                        db.add_category(client, new_name, new_budget)
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
                    new_budget = st.number_input(
                        "Budget",
                        value=float(cat.get("monthly_budget") or 0),
                        key=f"budget_{cat['id']}"
                    )
                    col_update, col_delete = st.columns(2)
                    with col_update:
                        if st.button("Update", key=f"update_{cat['id']}"):
                            try:
                                db.update_category(client, cat["id"], new_budget)
                                st.success("Updated")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    with col_delete:
                        if st.button("🗑️", key=f"delete_{cat['id']}"):
                            try:
                                db.delete_category(client, cat["id"])
                                st.success("Deleted")
                                st.cache_data.clear()
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
