import google.generativeai as genai
import streamlit as st


@st.cache_resource
def get_gemini_model():
    """Initialize and return the Gemini model (cached)."""
    genai.configure(api_key=st.secrets["connections"]["gemini"]["api_key"])
    return genai.GenerativeModel('gemini-2.0-flash-lite')
