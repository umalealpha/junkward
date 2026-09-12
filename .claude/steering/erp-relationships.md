# Alpha Direct Omni ERP — Module Relationship Rules

CRITICAL: Every module you build MUST respect these relationships.
Never build a module in isolation. Always verify all connections exist.

## Core Accounting Chain
Journal Entry → General Ledger → Trial Balance → P&L + Balance Sheet + Cash Flow

## Procurement Chain
Supplier (Contacts) → Purchase Order → Goods Receipt → Vendor Bill → Payables → Payment → GL

## Revenue Chain
Customer (Contacts) → Invoice → Debtors → GL (Debit: Debtors, Credit: Revenue)

## Age Analysis Chain
Payables → Creditors Age Analysis (30/60/90/120+ days)
Debtors → Debtors Age Analysis (30/60/90/120+ days)

## Fixed Assets Chain
Asset Register → Depreciation Journal → GL (Debit: Depreciation Expense, Credit: Accumulated Depreciation)

## Insurance-Specific Chain
Policy → Premium → GL (Debit: Cash/Debtors, Credit: Premium Income)
Claim → Settlement → GL (Debit: Claims Expense, Credit: Cash/Payables)
Reinsurance Treaty → Cession → GL (Debit: Reinsurance Expense, Credit: Reinsurance Payable)

## HRIS Chain
Employee → Leave Application → Leave Balance → Payroll → GL (Debit: Salary Expense, Credit: Cash/Payables)

## Rules
1. Every form that creates a financial transaction MUST post to the GL
2. Every supplier/vendor MUST appear in the Creditors Age Analysis
3. Every customer MUST appear in the Debtors Age Analysis
4. Every PO approval MUST create a GL commitment entry
5. Every invoice MUST be linkable to a PO (3-way match: PO → GRN → Invoice)
6. The Trial Balance MUST always balance (Debits = Credits)
7. The Balance Sheet MUST always balance (Assets = Liabilities + Equity)
