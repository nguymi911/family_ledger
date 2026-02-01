# Technical Specification & Roadmap: Annie Budget (v1.0)

## 1. System Overview
Annie Budget is a private, web-based financial tracking application designed for a single household. It prioritizes manual entry facilitated by AI natural language processing.

### Tech Stack
* **Frontend:** Streamlit (Python 3.11+)
* **Backend/BaaS:** Supabase (PostgreSQL, Auth)
* **AI Engine:** Gemini 1.5 Flash (via API)
* **Deployment:** Streamlit Community Cloud (via Private GitHub Repository)

## 2. Database Schema (PostgreSQL)

```sql
-- 1. Profiles: User metadata
CREATE TABLE public.profiles (
  id UUID REFERENCES auth.users ON DELETE CASCADE PRIMARY KEY,
  display_name TEXT NOT NULL,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 2. Categories: Monthly "Envelopes"
CREATE TABLE public.categories (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  name TEXT NOT NULL UNIQUE,
  monthly_budget NUMERIC(15,2) DEFAULT 0,
  is_fixed BOOLEAN DEFAULT FALSE
);

-- 3. Transactions: The Ledger
CREATE TABLE public.transactions (
  id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
  user_id UUID REFERENCES auth.users(id),
  category_id UUID REFERENCES public.categories(id),
  amount NUMERIC(15,2) NOT NULL,
  description TEXT,
  is_annie_related BOOLEAN DEFAULT FALSE,
  date DATE DEFAULT CURRENT_DATE,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- 4. Mortgage Config: Single-row configuration
CREATE TABLE public.mortgage_config (
  id INTEGER PRIMARY KEY DEFAULT 1 CHECK (id = 1),
  home_name TEXT DEFAULT 'Green Valley',
  total_principal NUMERIC(15,2),
  annual_interest_rate FLOAT,
  monthly_payment NUMERIC(15,2),
  start_date DATE
);
```

## 3. Implementation Roadmap

### Phase 1: Infrastructure & Data
* **Task 1.1: Environment Provisioning**
    * Setup Supabase project, GitHub repo, and Streamlit Cloud account.
* **Task 1.2: Database Schema Execution**
    * Run the SQL DDL above in the Supabase SQL Editor.
* **Task 1.3: Supabase Auth & Connection**
    * Secure login and implement the DB handshake using st-supabase-connection.

### Phase 2: The "Smart Entry" Engine
* **Task 2.1: Gemini API Integration**
    * Obtain API key and connect to Gemini 1.5 Flash.
* **Task 2.2: The NLP Parser Logic**
    * Prompt engineering for M/k currency notation and "Annie" toggle detection.
* **Task 2.3: Transaction Commit Logic**
    * UI button to save parsed JSON objects into the Transactions table.

### Phase 3: Dashboards & Insights
* **Task 3.1: Budget Burn-Down View**
    * Visualizing monthly spent vs. budget via progress bars.
* **Task 3.2: The "Annie" Expense Report**
    * Filtered metric cards for child-specific costs.
* **Task 3.3: Mortgage "Freedom Clock"**
    * Amortization logic to show updated debt-free date and months saved.

## 4. Operational Requirements
* **Security:** Row Level Security (RLS) enabled; Secrets stored in Streamlit Cloud.
* **Privacy:** No 3rd-party bank syncing.
* **Portability:** "Download CSV" button for local backups.