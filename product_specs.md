# Product Specification: Family Ledger

## 1. Product Vision
A private, mindful, and collaborative financial tool designed for a dual-income household to manage daily expenses, track the specific costs of raising a child, and accelerate mortgage repayment through high-frequency tracking and AI-assisted manual entry.

## 2. Core Pillars
* **Mindfulness over Automation:** 100% manual entry to maintain awareness of spending habits.
* **Frictionless UX:** Entering data must be as fast as sending a text message (the "10-Second Rule").
* **Dual-User Collaboration:** Unified data view for both users (Thanh and Happy).
* **Goal-Oriented:** Focused specifically on the "Green Valley" mortgage and Annie’s needs.

## 3. Functional Requirements

### A. Budgeting & Allocation
* **Envelope-Based:** Define monthly limits for categories (Groceries, Dining, Hobbies, etc.).
* **Fixed vs. Variable:** Separate view for fixed costs (bills/mortgage) and variable discretionary spending.
* **Rollover Logic:** Capability to move "leftover" funds into the mortgage principal pot or roll them to the next month.

### B. Intelligent Manual Entry
* **Natural Language Input:** A single text field that uses AI to parse strings like "200k for Annie toys" into structured data.
* **The "Annie" Toggle:** A global flag/tag to track the "Total Cost of Annie" across all categories (Health, Education, Food).

### C. Mortgage Dashboard
* **Visual Debt-Free Clock:** A countdown and progress bar showing the remaining loan term.
* **Extra Repayment Simulator:** Real-time calculation of interest saved and months shaved off based on "leftover" monthly budget.

## 4. User Stories

| ID | Persona | User Story |
| :--- | :--- | :--- |
| 01 | Parent | As a busy parent, I want to manually type a short sentence about my spending so that I can log expenses on the go without navigating complex menus. |
| 02 | Father | As a father, I want to tag specific expenses as "Annie-related" so that I can see the total cost of her needs separate from our general household spending. |
| 03 | Parents | As parents, Happy and I want to compare our actual spending against our pre-allocated monthly budget so we can make informed decisions for our family. |
| 04 | Homeowner | As a homeowner in Green Valley, I want to see how an extra repayment reduces my loan term so that I feel motivated to save. |
| 05 | Couple | As a couple, Happy and I want to see each other's entries in real-time so that we don't lose track of our shared "envelope." |