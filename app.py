import streamlit as st
from gemini_client import get_gemini_model
from database import get_connection, load_categories, get_category_map, get_category_names
from auth import require_login
from components import render_sidebar, render_budget, render_smart_input, render_transactions

# Page config
st.set_page_config(page_title="Annie Budget", page_icon="💰")

# Initialize connections
conn = get_connection()
client = conn.client

# Authentication
user = require_login(client)

# Initialize Gemini model
model = get_gemini_model()

# Load data
categories_data = load_categories(client)
categories = get_category_map(categories_data)
category_names = get_category_names(categories_data)

# Layout
st.title("Annie Budget")

render_sidebar(client, user, categories_data)

render_budget(client, user, categories_data)

st.divider()

render_smart_input(client, user, model, categories, category_names)

st.divider()

render_transactions(client, user, categories, category_names)
