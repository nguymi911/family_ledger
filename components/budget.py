import streamlit as st
from datetime import date
import database as db


def render_budget(client, categories_data):
    """Render the budget burn-down view."""
    st.subheader("Monthly Budget")
    today = date.today()
    monthly_spending = db.get_monthly_spending(client, today.year, today.month)

    if categories_data:
        # Calculate totals
        total_budget = sum(float(c.get("monthly_budget") or 0) for c in categories_data)
        total_spent = sum(monthly_spending.values())
        total_remaining = total_budget - total_spent

        # Summary metrics
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Budget", f"{total_budget:,.0f}₫")
        with col2:
            st.metric("Spent", f"{total_spent:,.0f}₫")
        with col3:
            delta_color = "normal" if total_remaining >= 0 else "inverse"
            st.metric("Remaining", f"{total_remaining:,.0f}₫", delta=f"{total_remaining:,.0f}₫", delta_color=delta_color)

        # Category breakdown
        for cat in categories_data:
            budget = float(cat.get("monthly_budget") or 0)
            spent = monthly_spending.get(cat["id"], 0)

            if budget > 0:
                progress = min(spent / budget, 1.0)
                status = "🔴" if spent > budget else "🟡" if progress > 0.8 else "🟢"
            else:
                progress = 0
                status = "⚪"

            col_name, col_bar, col_nums = st.columns([2, 4, 2])
            with col_name:
                st.write(f"{status} {cat['name']}")
            with col_bar:
                st.progress(progress)
            with col_nums:
                st.write(f"{spent:,.0f}₫ / {budget:,.0f}₫")
    else:
        st.info("No categories configured. Add categories in the sidebar to enable budget tracking.")
