import google.generativeai as genai
import streamlit as st


def get_gemini_model():
    """Initialize and return the Gemini 1.5 Flash model."""
    genai.configure(api_key=st.secrets["connections"]["gemini"]["api_key"])
    return genai.GenerativeModel('gemini-1.5-flash')
