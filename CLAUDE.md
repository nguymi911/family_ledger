# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Family Ledger is a household financial tracking web application with AI-assisted natural language expense entry. It uses envelope-based budgeting and includes mortgage acceleration tracking.

## Tech Stack

- **Frontend:** Streamlit (Python 3.11+)
- **Backend:** Supabase (PostgreSQL + Auth with Row-Level Security)
- **AI Engine:** Google Gemini 2.0 Flash Lite (for NLP expense parsing)
- **Deployment:** Streamlit Community Cloud

## Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application locally
streamlit run app.py
```

## Configuration

Secrets are stored in `.streamlit/secrets.toml` (local) or Streamlit Cloud dashboard (production):

```toml
[connections.supabase]
url = "your_supabase_url"
key = "your_supabase_publishable_key"
```

Database schema changes should be made in `schema.sql` and executed in the Supabase SQL Editor.

## Architecture

```
User Input (Natural Language) → Gemini NLP Parser → Supabase PostgreSQL → Streamlit Dashboard
```

**Database Tables:**
- `profiles` - User metadata (linked to Supabase auth.users)
- `categories` - Budget envelopes with monthly limits
- `transactions` - The ledger with optional "Annie" tag for child-related expenses
- `mortgage_config` - Single-row table for Green Valley mortgage details

**Key Patterns:**
- M/k currency notation in NLP (e.g., "200k" = $200,000)
- "Annie" toggle for child-related expense tracking across all categories
- Envelope budgeting with rollover capability to mortgage principal

**UI Layout:**
- Main area: Budget burn-down view, quick entry form, recent transactions
- Sidebar: Category management (add/edit categories and budgets)

## Implementation Status

- **Phase 1 (Complete):** Infrastructure, auth, database connection
- **Phase 2 (Complete):** Gemini integration, NLP parser, transaction input form
- **Phase 3 (In Progress):** Budget burn-down view complete; Annie expense report and mortgage freedom clock pending

See `tech_specs.md` for the full implementation roadmap and `product_specs.md` for user requirements.
