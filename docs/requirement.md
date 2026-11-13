# Requirement: DMart Regional Director Assistant

## 1. Goal

**Outcome:** After the assistant replies, Kavita has a plain-English answer whose every number can be traced to a data field.

**Stakeholder:** Kavita Rao, regional operations director for five stores. She needs answers to her routine questions that she can trust before she funds any programme

**Scope:** Three datasets (store_daily_clean, inventory, feedback) and five stores: Mumbai, Pune, Hyderabad, Bengaluru, Ahmedabad.

**Decision boundary:** The assistant may answer questions using only the approved fields of the three datasets. The assistant may not send messages, reorder stock, guess missing values or say a correlation is a cause.

## 2. Approved fields (exactly 11 reportable metric fields)

| Dataset | Fields |
|---|---|
| store_daily | revenue_inr, daily_target_inr, footfall, stockout_hours, discount_pct, achievement_pct, performance_band |
| inventory | stock_units, reorder_threshold |
| feedback | rating, theme |

These are the only fields a query may select or an answer may report.
marketing_spend_inr is deliberately not approved.

The key columns store, store_id, date, product and product_id are always allowed as
filters and grouping keys. They are never returned as metrics and are not counted
among the 11.

## 3. Prohibited actions
1. Sending a message or email to anyone.
2. Reordering or buying stock.
3. Estimating or guessing a missing value.
4. Stating a correlation as a cause.

## 4. What the assistant answers and what it refuses

| Kind | Example question | Why |
|---|---|---|
| Answer | What was Pune's revenue on 15 May 2026? | one approved field, one store, one date |
| Answer | Did Pune hit its target on 2026-05-16? | revenue against target |
| Answer | Which stores are below the reorder threshold for Amul Milk? | approved inventory fields |
| Answer | What are customers saying about Hyderabad? | approved feedback fields |
| Refuse | What was Pune's profit margin on 2026-05-15? | field not approved |
| Refuse | What is the capital of India? | out of scope |
| Refuse | Why is Pune's revenue so low? | needs an analyst, not a lookup |
| Refuse | Reorder 200 units of Amul Milk for Pune | prohibited action |