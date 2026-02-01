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