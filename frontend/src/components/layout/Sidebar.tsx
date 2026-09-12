'use client'

import Image from 'next/image'
import Link from 'next/link'
import { usePathname, useRouter } from 'next/navigation'
import { useState, useEffect, useMemo, useRef } from 'react'
import {
  LayoutDashboard,
  Zap,
  Users,
  FileText,
  Clock,
  Receipt,
  UserCheck,
  CreditCard,
  Banknote,
  Building2,
  BarChart3,
  Scale,
  TrendingUp,
  Layers,
  CircleDollarSign,
  BookOpen,
  FileSpreadsheet,
  AlertTriangle,
  Target,
  Landmark,
  Calendar,
  Settings,
  Search,
  Sparkles,
  Bug,
  ChevronDown,
  ChevronLeft,
  ChevronRight,
  LogOut,
  Menu,
  X,
  Briefcase,
  ClipboardCheck,
  ClipboardList,
  PieChart,
  Calculator,
  Boxes,
  Plus,
  Upload,
  Shield,
  ShieldCheck,
  ShieldAlert,
  Power,
  UserCog,
  RotateCw,
  Coins,
  Package,
  Wallet,
  Globe,
  ArrowDownLeft,
  ArrowRightLeft,
  ArrowUpRight,
  Users as UsersIcon,
  UserPlus,
  Lock,
  Inbox,
  ListChecks,
  Mail,
  Eraser,
  Stethoscope,
  Grid3x3,
  GitBranch,
  Compass,
  Navigation,
  Sparkle,
  Gift,
  Trophy,
  Store,
  Database,
  HeartPulse,
  LifeBuoy,
  Orbit,
  Route,
  MessageCircle,
  Gauge,
  Pencil,
  FileSignature,
  type LucideIcon, Archive, Send,
 Bot, MapPin, CalendarClock, Gavel, Activity } from 'lucide-react'
import { cn } from '@/lib/utils'
import { useTheme } from '@/contexts/ThemeContext'
import { removeToken, getMe, apiFetch } from '@/lib/api'
import type { UserProfile } from '@/lib/api'
import { useSalvageAccess } from '@/hooks/useSalvageAccess'
import { useHrisAccess, useHrisSelfService } from '@/hooks/useHrisAccess'
import { useCompany } from '@/contexts/CompanyContext'
import { ADIPL_ONLY_HREFS, isAdiplPlanVisible, isCompanyResolving } from '@/lib/entityScope'

// ─── Navigation structure ────────────────────────────────────────────────────

interface NavItem {
  label: string
  icon: LucideIcon
  href: string
  /** CFO directive 2026-05-21 menu consolidation. When true the item
   *  renders as a non-clickable sub-header inside an expanded group
   *  (e.g. "Reporting" inside Accounting). `href` is ignored. */
  header?: boolean
  /** When true, render as a plain <a> (full-page nav) instead of a Next
   *  <Link>. Used for same-origin apps served outside the Next.js app,
   *  e.g. /claims-po (the Claims PO tool behind Caddy). */
  external?: boolean
}

interface NavGroup {
  label: string
  icon: LucideIcon
  children?: NavItem[]
  /** If set, the group is a direct link (no dropdown). */
  href?: string
  /** If set with href, render as plain <a> instead of Next Link. Used for
   *  Django-served pages such as /hris/ that sit outside the Next.js app. */
  external?: boolean
}

// CFO directive 2026-08-22 declutter: the old flat 17-item list mixed
// dashboards, personal work, spend and support in one pile. Now split into
// readable sections (header:true rows, same mechanism as the Accounting group).
// WhatsApp Reminders moved to Settings → Communications (CFO-only tool, not a
// front-of-house menu item). CFO Snapshot retired from the menu — its figures
// are static and do NOT reconcile to the GL, so it was a trap; the /cfo-snapshot
// route still exists but is no longer surfaced.
const topItems: NavItem[] = [
  // Overview (section title supplied by sectionize fallback)
  // My Omni — the personal employee home (default front door for every user).
  { label: 'My Omni',       icon: Sparkles,        href: '/my-omni' },
  // The CFO's own build log. Filtered out below for everybody else — the API
  // and the page are both gated too, this only keeps it off other people's menu.
  { label: 'Build log',     icon: ListChecks,      href: '/cfo/build-log' },
  // Live gate board — every /cfo/ item is filtered to the CFO below.
  { label: 'Gate board',    icon: Gauge,           href: '/cfo/ci' },
  { label: 'Forgiveness watch', icon: ShieldAlert,  href: '/cfo/forgiveness' },
  { label: 'Scheduled jobs', icon: Power,        href: '/cfo/jobs' },
  { label: 'Dashboard',     icon: LayoutDashboard, href: '/dashboard' },
  // CFO Dashboard retired 2026-08-22 — its control tiles merged into /dashboard
  // (CfoControlsSection, finance/CFO only). /cfo now redirects to /dashboard.
  { label: 'Intelligence Summary', icon: BarChart3, href: '/intel-summary' },
  { label: 'Graphite Aware',icon: Orbit,           href: '/aware' },
  { label: 'Graphite Feeds', icon: Database,       href: '/graphite-feeds' },
  { label: 'Adoption',      icon: BarChart3,       href: '/adoption' },
  { label: 'Smart Entry',   icon: Zap,             href: '/quick-entry' },
  // My Work
  { label: 'My Work',       icon: Inbox,           href: '#', header: true },
  { label: 'Tasks',         icon: Inbox,           href: '/tasks' },
  { label: 'My League',     icon: Trophy,          href: '/my-league' },
  { label: 'Task Dashboard', icon: ListChecks,     href: '/task-dashboard' },
  { label: 'My Requests',    icon: ListChecks,     href: '/my-requests' },
  { label: 'My Approvals',   icon: Inbox,          href: '/my-approvals' },
  { label: 'My Equity',      icon: PieChart,       href: '/my-equity' },
  // Spend & Payments
  { label: 'Spend & Payments', icon: Banknote,     href: '#', header: true },
  { label: 'Payment Requests', icon: Banknote,     href: '/payment-requests' },
  { label: 'Spend Requests', icon: Receipt,        href: '/spend-requests' },
  // Company cards (CFO 2026-08-07) — load the statement, see what has no
  // receipt, and keep the card register. Backend is finance-gated; a
  // non-finance user who lands here is told so.
  { label: 'Company Cards',  icon: CreditCard,     href: '/company-cards' },
  { label: 'Refunds',        icon: Receipt,        href: '/refunds' },
  // Support
  { label: 'Support',       icon: LifeBuoy,        href: '#', header: true },
  { label: 'IT Help Desk',  icon: LifeBuoy,        href: '/helpdesk/', external: true },
]

// CFO directive 2026-07-02: the rewards / wellness / Nexus surfaces are one
// programme — "Project Nexus". They get their own module (icon-rail entry)
// instead of crowding the Overview top list. Ungated, exactly as before.
const nexusItems: NavItem[] = [
  { label: 'Alpha Rewards', icon: Gift,       href: '/rewards' },
  { label: 'Staff Rewards', icon: Sparkles,   href: '/staff-rewards' },
  { label: 'Leaderboard',   icon: Trophy,     href: '/rewards/leaderboard' },
  { label: 'Redeem',        icon: Store,      href: '/rewards/redeem' },
  { label: 'Nexus Drive',   icon: Compass,    href: '/nexus' },
  { label: 'Thrive',        icon: HeartPulse, href: '/thrive' },
  { label: 'Nexus Testers', icon: Trophy,     href: '/rewards/nexus-testers' },
]

// CFO directive 2026-05-21 menu consolidation. Old layout had 20+ top-level
// entries; new layout collapses Reporting, Debtors, Investments, Fixed Assets
// and Reinsurance under Accounting; Petty Cash moves into Banking; and
// Approvals / Exceptions / Tax Calendar / Audit Log move into Administration.
// Section sub-headers (header:true items) keep each sub-area readable inside
// the expanded group without needing a second-level dropdown.
const groups: NavGroup[] = [
  {
    label: 'Accounting',
    icon: BookOpen,
    children: [
      // Ledger
      { label: 'Ledger',             icon: BookOpen,        href: '#', header: true },
      { label: 'Browse Accounts',    icon: Layers,          href: '/accounts' },
      { label: 'Journal Entries',    icon: FileSpreadsheet, href: '/journal-entries' },
      { label: 'Recurring JEs',      icon: RotateCw,        href: '/settings/recurring-journal-entries' },
      { label: 'TB / GL Upload',     icon: Upload,          href: '/upload' },
      // Reporting
      { label: 'Reporting',          icon: BarChart3,       href: '#', header: true },
      { label: 'Trial Balance',      icon: Scale,           href: '/reports/trial-balance' },
      { label: 'Profit & Loss',      icon: TrendingUp,      href: '/reports/profit-loss' },
      { label: 'P&L by Entity',      icon: TrendingUp,      href: '/reports/entity-pl' },
      { label: 'Balance Sheet',      icon: Layers,          href: '/reports/balance-sheet' },
      { label: 'IFRS 16 Leases',     icon: Building2,       href: '/leases' },
      { label: 'Consolidated',       icon: Layers,          href: '/reports/consolidated' },
      { label: 'Equity / Cap Table', icon: PieChart,        href: '/equity' },
      { label: 'Cash Position',      icon: CircleDollarSign,href: '/reports/cash-position' },
      { label: 'General Ledger',     icon: BookOpen,        href: '/reports/general-ledger' },
      { label: 'Budget vs Actual',   icon: Target,          href: '/reports/budget-vs-actual' },
      { label: 'Budget Library',     icon: Wallet,          href: '/budgets' },
      { label: 'Budget Cockpit',     icon: Sparkles,        href: '/budgets/simulator' },
      { label: '5-Year Plan Cockpit', icon: TrendingUp,      href: '/budgets/five-year' },
      { label: 'IFRS 17 Cockpit',   icon: Scale,           href: '/ifrs17' },
      // Finance 2026-08-04: the archive behind the cockpit, kept next to it so the
      // plan and its source of record are in one place.
      { label: 'Strategic Plan Library', icon: BookOpen,     href: '/budgets/five-year/library' },
      { label: 'Expense Analysis',   icon: PieChart,        href: '/reports/expense-analysis' },
      { label: 'VAT Return',         icon: Calculator,      href: '/reports/vat-return' },
      { label: 'Reverse-Charge VAT', icon: Globe,           href: '/reverse-charge' },
      { label: 'Management Pack',    icon: Briefcase,       href: '/reports/management-pack' },
      { label: 'Market Benchmark',   icon: BarChart3,       href: '/reports/peer-benchmark' },
      { label: 'Bank Proofs (FNB)', icon: Landmark,        href: '/bank-proofs' },
      { label: 'Reconciliation Hub', icon: Scale,           href: '/reconciliation' },
      { label: 'Audit Pack (IFRS)',  icon: ClipboardCheck,  href: '/reports/audit-pack' },
      { label: 'Tax Pack (IAS 12)',  icon: Calculator,      href: '/reports/tax-reconciliation' },
      { label: 'TB → BS Trace',      icon: AlertTriangle,   href: '/reports/ma-trace' },
      { label: 'Draft JE Triage',    icon: ClipboardCheck,  href: '/reports/draft-triage' },
      { label: 'AI Integrity Scan',  icon: Sparkles,        href: '/reports/ai-integrity' },
      { label: 'Cash Flow',          icon: TrendingUp,      href: '/reports/cash-flow' },
      { label: 'AP Aging',           icon: Clock,           href: '/reports/ap-aging' },
      { label: 'Regulatory Capital', icon: Scale,           href: '/reports/regulatory-capital' },
      { label: 'Related-Party Txns', icon: Users,           href: '/reports/related-party-transactions' },
      { label: 'Budget Setup',       icon: Target,          href: '/reports/budget-setup' },
      { label: 'Asset Movement',     icon: FileSpreadsheet, href: '/reports/asset-movement' },
      { label: 'Exceptions Report',  icon: AlertTriangle,   href: '/reports/exceptions' },
      // BONU legal benefit — a screen nobody can find is a screen nobody uses, so all
      // four go in the menu, not just the overview (CFO go-live 2026-08-03).
      { label: 'BONU legal',         icon: Scale,           href: '#', header: true },
      { label: 'BONU Overview',      icon: Scale,           href: '/bonu' },
      { label: 'Claim Intake',       icon: ClipboardList,   href: '/bonu/intake' },
      { label: 'Legal Office',       icon: Gavel,           href: '/bonu/legal' },
      { label: 'Bills to Check',     icon: FileText,        href: '/bonu/inbox' },
      { label: 'Law Firm Panel',     icon: TrendingUp,      href: '/bonu/panel' },
      { label: 'Fee Queries',        icon: AlertTriangle,   href: '/bonu/queries' },
      { label: 'Lawyer Payments',    icon: Banknote,        href: '/bonu/payments' },
      // Debtors
      { label: 'Debtors',            icon: Users,           href: '#', header: true },
      { label: 'Customer Invoices',  icon: FileText,        href: '/invoices' },
      { label: 'AR Aging',           icon: Clock,           href: '/reports/ar-aging' },
      { label: 'Graphite Age Analysis', icon: Clock,        href: '/reports/age-analysis' },
      { label: 'Receipts',           icon: Receipt,         href: '/payments?type=receipt' },
      { label: 'Customers',          icon: UserCheck,       href: '/contacts?type=customer' },
      { label: 'Debtors Home',       icon: Users,           href: '/debtors' },
      // Investments
      { label: 'Investments',        icon: TrendingUp,      href: '#', header: true },
      { label: 'Portfolio',          icon: BarChart3,       href: '/investments' },
      { label: 'Transactions',       icon: FileSpreadsheet, href: '/investments/transactions' },
      // Fixed Assets
      { label: 'Fixed Assets',       icon: Boxes,           href: '#', header: true },
      { label: 'Asset Register',     icon: Boxes,           href: '/assets' },
      { label: 'Company Fleet',      icon: Navigation,      href: '/fleet' },
      { label: 'Vehicle Register',   icon: ListChecks,      href: '/vehicle-register' },
      { label: 'New Asset',          icon: Plus,            href: '/assets/new' },
      { label: 'Import from Odoo',   icon: Upload,          href: '/assets/import' },
      { label: 'Register Report',    icon: FileSpreadsheet, href: '/reports/asset-register' },
      // Asset Control & Handover (CFO spec 2026-09-02)
      { label: 'Asset Control',      icon: ClipboardCheck,  href: '#', header: true },
      { label: 'Requisitions',       icon: ClipboardList,   href: '/assets/requisitions' },
      { label: 'Approvals Queue',    icon: Inbox,           href: '/assets/approvals' },
      { label: 'Spare Pool',         icon: Package,         href: '/assets/spare-pool' },
      { label: 'My Assets',          icon: UserCheck,       href: '/assets/my-assets' },
      { label: 'Count Reconciliation', icon: Scale,         href: '/assets/reconciliation' },
      // Reinsurance
      { label: 'Reinsurance',        icon: Shield,          href: '#', header: true },
      { label: 'Renewal 2026/27',    icon: Sparkles,        href: '/reinsurance/renewal' },
      { label: '11-Year Performance', icon: BarChart3,      href: '/reinsurance/history' },
      { label: 'Treaties',           icon: FileText,        href: '/reinsurance/treaties' },
      { label: 'Cessions',           icon: ArrowDownLeft,   href: '/reinsurance/cessions' },
      { label: 'Recoveries',         icon: ArrowUpRight,    href: '/reinsurance/recoveries' },
      { label: 'Reinsurers',         icon: Building2,       href: '/reinsurance/reinsurers' },
      { label: 'Bordereaux',         icon: FileSpreadsheet, href: '/reinsurance/bordereaux' },
    ],
  },
  // HRIS sits between Accounting and Banking per CFO ordering (position 5).
  // Actual entry is rendered conditionally below via hrisGroup + access probe.
  {
    label: 'Banking',
    icon: Landmark,
    children: [
      { label: 'Banks',               icon: Landmark, href: '#', header: true },
      { label: 'Bank Reconciliation', icon: Scale,    href: '/banking' },
      { label: 'Bank Accounts',       icon: Landmark, href: '/bank-accounts' },
      { label: 'FNB Integration',     icon: Banknote, href: '/banking/fnb' },
      { label: 'FX Payment Planning', icon: CalendarClock, href: '/banking/fx-planning' },
      { label: 'Voucher Clearing',    icon: Eraser,   href: '/banking/voucher-clearing' },
      { label: 'Bank Feeds',          icon: RotateCw, href: '/bank-feeds' },
      { label: 'Collections',         icon: ArrowDownLeft, href: '#', header: true },
      { label: 'RealPay',             icon: ArrowDownLeft, href: '/banking/realpay' },
      { label: 'Debit Tracker',       icon: AlertTriangle, href: '/banking/realpay/collections/debit-tracker' },
      { label: 'Collections Dashboard', icon: BarChart3,   href: '/banking/realpay/collections/dashboard' },
      { label: 'Collections Analytics', icon: TrendingUp,  href: '/banking/realpay/collections/analytics' },
      // Upload-and-reconcile against Graphite (Keetile Mokhendo, 2026-08-17).
      { label: 'Reconcile vs Policies', icon: ArrowRightLeft, href: '/banking/realpay/collections/recon' },
      // The six monitoring reports off the same handover note.
      { label: 'Finance Monitoring',  icon: ShieldAlert, href: '/banking/realpay/monitoring' },
      // Petty Cash nested per CFO ask.
      { label: 'Petty Cash',          icon: Coins,    href: '#', header: true },
      { label: 'Vouchers',            icon: Receipt,  href: '/petty-cash' },
      { label: 'New Voucher',         icon: Plus,     href: '/petty-cash/new' },
      { label: 'Reimbursements',      icon: Coins,    href: '/petty-cash/reimbursements' },
      { label: 'Top up the Tin',      icon: Plus,     href: '/petty-cash/reimbursements/new' },
    ],
  },
  {
    label: 'Payables',
    icon: CreditCard,
    children: [
      { label: 'Vendor Bills',     icon: FileText,  href: '/bills' },
      { label: 'AP Aging',         icon: Clock,     href: '/payables/aging' },
      { label: 'Supplier Recon',   icon: ShieldCheck, href: '/payables/recon' },
      { label: 'Payments',         icon: Banknote,  href: '/payments?type=payment' },
      { label: 'Payment Approvals', icon: ShieldCheck, href: '/payments/approvals' },
      { label: 'Vendors',          icon: Building2, href: '/vendors' },
      { label: 'Supplier Addresses', icon: Building2, href: '/vendors/addresses' },
    ],
  },
  {
    label: 'Claims Recoveries',
    icon: Coins,
    children: [
      { label: 'Claims Register', icon: FileSpreadsheet, href: '/claims/register' },
      { label: 'Claim Forms',  icon: FileText, href: '/claims/forms' },
      { label: 'Subrogations', icon: Coins,   href: '/claims/subrogations' },
      { label: 'Salvages',     icon: Package, href: '/claims/salvages' },
    ],
  },
  {
    label: 'Underwriting',
    icon: FileText,
    children: [
      { label: 'Document Generator', icon: FileText, href: '/underwriting' },
      // One standard quote template, filled from plain English (CFO/EXCO
      // 2026-08-08). Sits beside the cover-note / WCA generator because it is
      // the same job, done by the same people, in the same place.
      { label: 'Quotations',         icon: FileText, href: '/underwriting/quotes' },
      // Who actually USES the two tools above, and who is still doing it by
      // hand (CFO Amendment 3, 2026-09-08). Per-underwriter AI readiness.
      { label: 'Tool Adoption',      icon: TrendingUp, href: '/underwriting/adoption' },
    ],
  },
  {
    label: 'Procurement',
    icon: Package,
    children: [
      { label: 'Procurement Home',    icon: Package,     href: '/procurement' },
      { label: 'Purchase Orders',     icon: FileText,    href: '/purchase-orders' },
      { label: 'Goods Received Notes', icon: ClipboardCheck, href: '/goods-received' },
      { label: 'New PO',              icon: Plus,        href: '/purchase-orders/new' },
      // Kao (Claims) 2026-07-13: claims must be able to add a repairer /
      // supplier that isn't on the vendor list yet. The create form lived
      // only behind Payables → Vendors, which claims never open — surface
      // it here where the PO work actually happens.
      { label: 'Add Supplier / Repairer', icon: Plus,    href: '/contacts/new?type=vendor' },
      // Claims PO (assessment PDF → draft repairer/parts POs in omni).
      // Phase-4 review screen — now a native Next.js page (was the old
      // Caddy-served Odoo tool, retired with the omni port).
      { label: 'Claims PO (Assessments)', icon: Upload,  href: '/claims-po' },
      // Claims-PO analytics dashboard (CFO 2026-07-07) — spend / excess /
      // turnaround / repairer-vs-parts over department=claims POs.
      { label: 'Claims PO — Analytics', icon: BarChart3, href: '/claims-po/analytics' },
      { label: 'Vendor Bank Accounts', icon: ShieldCheck, href: '/vendor-banking' },
      { label: 'FX Revaluation',      icon: Globe,       href: '/fx-revaluation' },
    ],
  },
  // Build Brief 1 (Data department, 2-Sep-2026): the Instant Insurance book, and
  // the RealPay-vs-ledger check added after ~22,500 collections went unrecorded.
  {
    label: 'Instant Insurance',
    icon: ShieldCheck,
    children: [
      { label: 'Book & collections', icon: BarChart3, href: '/instant-insurance' },
    ],
  },
  // CFO directive 2026-05-26 — Health Care quick-quote (revenue stream)
  {
    label: 'Health Care',
    icon: Stethoscope,
    children: [
      // CFO directive 2026-07-02 — Overview hub leads the section; it surfaces
      // the live bordereaux GWP + book + pipeline + claims in one place.
      { label: 'Overview', icon: LayoutDashboard, href: '/health/dashboard' },
      // Health Cover — the member-facing plan + benefits page (CFO 2026-08-07),
      // ported from Steven Diaz's design mockup.
      { label: 'Health Cover', icon: HeartPulse, href: '/health-care/cover' },
      { label: 'Provider Network', icon: MapPin,     href: '/health-care/providers' },
      { label: 'Quick Quote', icon: Calculator, href: '/health/quick-quote' },
      { label: 'Quotations', icon: FileText, href: '/health/quotes' },
      // CFO directive 2026-06-05 — Tlamelo's Smart-Upload trackers.
      { label: 'Revenue (Bordereaux)', icon: FileSpreadsheet, href: '/healthcare/revenue' },
      { label: 'Claims (AFT)',         icon: Receipt,         href: '/healthcare/claims' },
      { label: 'Treaty (IN / OUT)',    icon: ShieldCheck,     href: '/healthcare/treaty' },
      { label: 'Vendor Onboarding',    icon: HeartPulse,      href: '/health/vendor-onboarding' },
      { label: 'Service Providers',   icon: Stethoscope,     href: '/health/service-providers' },
      { label: 'Network Dashboard',   icon: LayoutDashboard, href: '/health/provider-dashboard' },
      { label: 'ADH Dashboard',       icon: Activity,        href: '/health/adh-dashboard' },
      { label: 'AFA Load File',       icon: Send,            href: '/health/afa-load-file' },
    ],
  },
  // CFO directive 2026-05-22 — NBFIRA Compliance module. Structure +
  // navigation only at this stage; the underlying pages are not yet built.
  {
    label: 'Compliance',
    icon: ClipboardCheck,
    children: [
      // Corporate Governance — the company-wide SOP + Policy library, open to
      // ALL staff (CFO directive 2026-07-27, Unami's request). Moved here from
      // the Banking menu, where a "SOP Bank" + bank icon read as a bank account
      // and nobody could find it. Placed first so it is unmissable.
      { label: 'Corporate Governance', icon: ShieldCheck, href: '#', header: true },
      { label: 'SOPs & Policies',      icon: FileText,    href: '/sop-bank' },
      // CFO directive 2026-07-02 — two collapsible folders (header:true rows
      // become accordion section titles): NBFIRA returns, and the ISO 27001
      // register. The ISO items lose their "ISO — " prefix since the folder
      // header already says ISO 27001.
      { label: 'NBFIRA',                          icon: LayoutDashboard, href: '#', header: true },
      { label: 'NBFIRA Dashboard',                icon: LayoutDashboard, href: '/compliance/nbfira' },
      { label: 'Quarterly Returns',               icon: Calendar,        href: '/compliance/nbfira/quarterly' },
      { label: 'Annual Returns',                  icon: Calendar,        href: '/compliance/nbfira/annual' },
      { label: 'Capital Adequacy / Solvency',     icon: Scale,           href: '/compliance/nbfira/capital-adequacy' },
      { label: 'Prudential Limits Monitor',       icon: AlertTriangle,   href: '/compliance/nbfira/prudential' },
      { label: 'Submission History & Audit Trail', icon: FileSpreadsheet, href: '/compliance/nbfira/submissions' },
      { label: 'Settings',                        icon: Settings,        href: '/compliance/nbfira/settings' },
      // CFO directive 2026-06-01 — ISO 27001 audit register (auditor-grade).
      { label: 'ISO 27001',                       icon: ShieldCheck,     href: '#', header: true },
      { label: '10 Commandments',                 icon: ShieldCheck,     href: '/compliance/iso' },
      { label: 'Statement of Applicability',      icon: ShieldCheck,     href: '/compliance/iso/soa' },
      { label: 'Risk Register',                   icon: AlertTriangle,   href: '/compliance/iso/risks' },
      { label: 'CAPA Register',                   icon: ClipboardCheck,  href: '/compliance/iso/capas' },
      { label: 'Policy Register',                 icon: FileSpreadsheet, href: '/compliance/iso/policies' },
      { label: 'Auditor Pack',                    icon: FileSpreadsheet, href: '/compliance/iso/audit-pack' },
      // CFO directive 2026-08-13 — Data Protection Officer register: DPIAs
      // (Data Protection Impact Assessments) under the Botswana DPA.
      { label: 'Data Protection',                 icon: ShieldCheck,     href: '#', header: true },
      { label: 'DPIA Register',                   icon: ClipboardCheck,  href: '/compliance/dpo' },
      { label: 'Policy & Legal Library',          icon: FileSpreadsheet, href: '/compliance/policy-library' },
      { label: 'ROPA Registry',                   icon: ClipboardCheck,  href: '/compliance/ropa' },
      { label: 'ROPA Vendor Register',            icon: FileSpreadsheet, href: '/compliance/ropa/vendors' },
      { label: 'ROPA Field Detector',            icon: ShieldCheck,     href: '/compliance/ropa-fields' },
    ],
  },
]

// Internal Audit — full audit-management module (spec: Internal Audit Module,
// GIAS Jan-2024). Its own top-level module, rendered ONLY for the audit
// function + the exec/board viewers (me.can_view_internal_audit). Independence:
// editing is gated separately in-page on can_edit_internal_audit.
const internalAuditGroup: NavGroup = {
  label: 'Internal Audit',
  icon: ShieldCheck,
  children: [
    { label: 'Dashboard',           icon: BarChart3,      href: '/internal-audit' },
    { label: 'Findings Register',   icon: AlertTriangle,  href: '/internal-audit/findings' },
    { label: 'Follow-up Tracking',  icon: ClipboardCheck, href: '/internal-audit/follow-up' },
  ],
}

// CFO directive 2026-05-21: Administration group renamed → Settings.
// Fiscal Periods + Period Close moved here from Accounting → Ledger
// (period management is configuration, not day-to-day bookkeeping).
// Standalone bottom "Settings" link removed as redundant.
// CFO directive 2026-06-02 — Period Management is a Finance Manager
// capability, not CFO/admin-only. Split out of `adminGroup` so it can be
// rendered behind `can_manage_periods` (CFO / FM / FC / admin / super).
const periodMgmtGroup: NavGroup = {
  label: 'Period Management',
  icon: Lock,
  children: [
    { label: 'Period Management',    icon: Lock,            href: '/periods' },
    { label: 'Fiscal Periods',       icon: Calendar,        href: '/fiscal-periods' },
    { label: 'Period Close',         icon: Lock,            href: '/period-close' },
  ],
}

const adminGroup: NavGroup = {
  label: 'Settings',
  icon: Settings,
  children: [
    { label: 'Workflow',             icon: ShieldCheck,     href: '#', header: true },
    { label: 'Approvals',            icon: ShieldCheck,     href: '/approvals' },
    // Renamed from "Exceptions" (5-Sep-2026): a committee member opened this list
    // looking for the PAYMENT exceptions board, which lives behind the Exceptions
    // button on Payment Requests. Two screens, one name — so this one changed.
    { label: 'Anomalies',            icon: AlertTriangle,   href: '/exceptions' },
    { label: 'Tax Calendar',         icon: Calendar,        href: '/tax-calendar' },
    { label: 'Audit Log',            icon: FileSpreadsheet, href: '/audit-log' },
    { label: 'Manus Activity',       icon: Bot,             href: '/manus-activity' },
    // Communications (CFO 2026-08-22) — moved out of the Overview top list.
    { label: 'Communications',       icon: MessageCircle,   href: '#', header: true },
    { label: 'WhatsApp Reminders',   icon: MessageCircle,   href: '/whatsapp' },
    { label: 'Configuration',        icon: Shield,          href: '#', header: true },
    { label: 'FX Rates (BoB)',       icon: Globe,           href: '/settings/fx-rates' },
    { label: 'Chart of Accounts',    icon: BookOpen,        href: '/settings/chart-of-accounts' },
    { label: 'Reinsurance Treaties', icon: Shield,          href: '/settings/reinsurance-treaties' },
    { label: 'Users & Permissions',  icon: UserCog,         href: '/settings/users' },
    { label: 'Roles & Hierarchy',    icon: Shield,          href: '/settings/roles' },
    { label: 'User-Entity Access',   icon: ShieldCheck,     href: '/settings/user-access' },
    { label: 'API Keys',             icon: Lock,            href: '/settings/api-keys' },
    { label: 'Secrets Vault',        icon: ShieldCheck,     href: '/settings/secrets' },
    { label: 'Frozen Controls',      icon: Lock,            href: '/settings/frozen-controls' },
    { label: 'Job Titles',           icon: UserCog,         href: '/settings/user-titles' },
    { label: 'Email IDs',            icon: Mail,            href: '/settings/user-emails' },
    { label: 'M365 Active Users',    icon: Users,           href: '/settings/m365-active-users' },
    { label: 'Digital Assistant',    icon: Sparkles,        href: '/settings/digital-assistant' },
    { label: 'Integrations',         icon: RotateCw,        href: '/integrations' },
    { label: 'CFO Upload',           icon: Upload,          href: '/cfo-upload' },
    { label: 'Settings Home',        icon: Settings,        href: '/settings' },
  ],
}

// Salvage Yard — VCM + ADIC only, gated by /salvage/me-can-access/ probe.
const salvageGroup: NavGroup = {
  label: 'Salvage Yard',
  icon: Boxes,
  children: [
    { label: 'Dashboard',       icon: LayoutDashboard, href: '/salvage' },
    { label: 'Inventory',       icon: Package,         href: '/salvage/inventory' },
    // CFO 2026-09-10 — the Parts & Assessments team's monthly workbooks.
    { label: 'Parts & Savings', icon: TrendingUp,      href: '/salvage/parts' },
  ],
}

// HRIS — restricted to a 5-person whitelist (Prathap, Arun, Kago, Pako,
// Unami) plus superusers / admins, gated by /admin/hris-access/ probe.
// CFO directive 2026-05-18: payroll details live here, so visibility
// is hidden, not just blocked at the page. Probe loading → hide group
// (avoids flash); explicit `true` → show.
const hrisGroup: NavGroup = {
  label: 'HRIS',
  icon: UsersIcon,
  children: [
    // CFO directive 2026-07-02: bulk the HRIS surfaces into collapsible folders
    // (header:true rows become accordion titles) — Payroll, HR, Talent — so the
    // panel isn't one long flat list. Visibility is gated server-side too — only
    // HR / HR Manager / CFO / Finance Manager / Financial Controller see data.
    { label: 'Payroll',           icon: Wallet,    href: '#',                    header: true },
    { label: 'Payroll Dashboard', icon: Wallet,    href: '/payroll/dashboard' },
    { label: 'Payroll',           icon: Wallet,    href: '/hris/payroll' },
    { label: 'Payroll Register',  icon: Wallet,    href: '/payroll/payslips' },
    { label: 'Payroll · GL Mapping', icon: Wallet, href: '/hris/payroll-setup' },
    { label: 'Run Payroll',       icon: Wallet,    href: '/payroll/run' },
    // CFO 2026-07-26: payroll now needs an explicit CFO sign-off per entity per
    // month before payslips reach staff. Menu entry added with the feature —
    // Kago could not find Development Dialogue because it shipped without one.
    { label: 'Payroll Sign-off',  icon: ShieldCheck, href: '/payroll/sign-off' },
    // Monthly pack + incentive/authority control check (CFO 2026-08-24).
    { label: 'Monthly Pack & Checks', icon: Wallet, href: '/payroll/monthly-pack' },
    { label: 'Staff Loans',       icon: Wallet,    href: '/payroll/staff-loans' },
    { label: 'Payroll Employees', icon: UsersIcon, href: '/payroll/employees' },
    { label: 'All Payslips',      icon: Wallet,    href: '/hris/payslips' },
    { label: 'HR',                icon: UsersIcon, href: '#',                    header: true },
    { label: 'HRIS Home',         icon: UsersIcon, href: '/hris' },
    { label: 'Inbox',             icon: Inbox,     href: '/hris/inbox' },
    { label: 'People',            icon: UsersIcon, href: '/hris/directory' },
    { label: 'Onboard Employee',  icon: UserPlus,  href: '/hris/onboard' },
    // CFO 2026-07-26: this page already did job titles + reporting lines, but it
    // was palette-only and named "Payroll Amendments", so it read as a money
    // screen and nobody found it (the CFO asked for it to be built from scratch).
    // Same page, honest label, now in the menu.
    { label: 'Job Titles & Reporting Lines', icon: Pencil, href: '/hris/amendments' },
    { label: 'Documents',         icon: FileText,  href: '/hris/documents' },
    { label: 'Letters',           icon: Mail,      href: '/hris/letters' },
    { label: 'Leave Admin',       icon: Calendar,  href: '/hris/leave' },
    // Disciplinary cases — manager/HR raise → HR review → CFO sign-off for
    // suspension / dismissal → issued. Confidential HR record (CFO 2026-07-22).
    { label: 'Disciplinary',      icon: ShieldAlert, href: '/hris/disciplinary' },
    // Staff Incentive Approval — manager request → CFO + HR sign → payroll (CFO 2026-07-13).
    { label: 'Incentives',        icon: Coins,     href: '/hris/incentives' },
    // Staff + vehicle loans — apply → CFO approve → HR disburse (CFO 2026-07-15).
    { label: 'Staff Loans',       icon: Banknote,  href: '/hris/staff-loans' },
    // Leave Encashment + leave-pay provision register — basic ÷ 22 × days
    // (CFO 2026-07-21). HR/Finance raise → CFO signs → payroll.
    { label: 'Leave Encashment',  icon: Banknote,  href: '/hris/leave-encashment' },
    // ELRA-2025 monthly performance monitor — all employees (CFO 2026-07-02).
    { label: 'Performance Monitor', icon: Target,  href: '/hris/performance' },
    // Monthly manager feedback — short note + target check per report (CFO 2026-07-20).
    { label: 'Monthly Feedback',  icon: ClipboardCheck, href: '/hris/monthly-feedback' },
    // New HRIS feature pack (CFO 2026-07-21 — "excite Unami"): pulse, flight-risk,
    // skills, OKR tree, manager scorecard. HR team signs off each one in-page.
    { label: 'Pulse Check',       icon: HeartPulse,    href: '/hris/pulse' },
    { label: 'Flight-Risk Radar', icon: AlertTriangle, href: '/hris/flight-risk' },
    { label: 'Skills & Gaps',     icon: Grid3x3,       href: '/hris/skills' },
    { label: 'OKR Alignment',     icon: GitBranch,     href: '/hris/okr-tree' },
    { label: 'Manager Scorecard', icon: Gauge,         href: '/hris/manager-scorecard' },
    { label: 'Time Doctor',       icon: Clock,     href: '/hris/time-doctor' },
    // Screen-Integrity Monitor — frozen-screen / weight-on-a-key exceptions,
    // pulled from the nightly Time Doctor sweep (CFO 2026-09-06).
    { label: 'Screen Integrity',  icon: ShieldAlert, href: '/hris/screen-integrity' },
    { label: 'Excuses feed',      icon: MessageCircle, href: '/hris/excuses' },
    // Leave Excuse Response — low/no productive-hours people for a day + their
    // explanation + Aria + Rule A/B auto-verdict. Exec/HR only (CFO 2026-07-22).
    { label: 'Leave Excuse',      icon: ClipboardList, href: '/hris/leave-excuse' },
    { label: 'Rewards',           icon: Sparkles,  href: '/hris/rewards' },
    // Talent Management cluster (CFO directive 2026-05-26 — Unami TMS Orbit parity).
    { label: 'Talent Management', icon: Target,    href: '#',                    header: true },
    // Development Dialogue self-service — staff were emailed "Talent Management →
    // Development Dialogue" but only /hris/profile linked it (Kago 2026-07-18).
    { label: 'Development Dialogue', icon: ClipboardCheck, href: '/hris/my-dialogue' },
    { label: 'Team Dialogues',    icon: Users,     href: '/hris/team-dialogues' },
    // The SHORT monthly accountability return (CFO 2026-07-26). Sits next to the
    // Development Dialogue because the year's returns roll up INTO it — the DD is
    // the big annual conversation, this is the five-minute monthly one.
    { label: 'Monthly Return',    icon: ClipboardCheck, href: '/hris/monthly-return' },
    // Unami decides these: a manager said someone isn't theirs / has left
    // (CFO 2026-07-26). The person stays on the roster until she decides.
    { label: 'Roster Flags',      icon: AlertTriangle, href: '/hris/roster-flags' },
    { label: 'Recruitment',       icon: Briefcase, href: '/recruitment' },
    // Restricted to the five signatories — the page itself says so to anyone
    // else, but the link stays visible so a signatory can always find it
    // (CFO 2026-08-03: a page with no menu link is a page nobody uses).
    { label: 'Authority to Recruit', icon: FileSignature, href: '/recruitment/authorities' },
    // Position tiers + salary bands (Unami Hiring-SOP, CFO 2026-09-02). Restricted
    // like the authorities page — the page itself gates it; the link stays visible.
    { label: 'Tiers & Salary Bands', icon: Layers, href: '/recruitment/tiers' },
    { label: '9-Box Grid',        icon: Grid3x3,   href: '/hris/ninebox' },
    { label: 'Succession',        icon: GitBranch, href: '/hris/succession' },
    { label: 'Dev Plan (IDP)',    icon: Compass,   href: '/hris/idp' },
    // Career Tracks — promotion-readiness records (CFO directive 2026-07-13).
    { label: 'Career Track',      icon: Route,     href: '/hris/career-track' },
    { label: 'AI Readiness',      icon: Sparkle,   href: '/hris/ai-readiness' },
    { label: 'HR Analytics',      icon: BarChart3, href: '/hr-analytics' },
  ],
}

// Employee Self-Service — the narrow HRIS slice EVERY staff member gets, even
// when they're not on the 5-person HRIS whitelist (CFO directive 2026-06-16,
// Lakshmi Anand / ADRisk bug aec2f3ce). Strictly own-data surfaces: log own
// leave, view own payslips, view/update own profile. Payroll, People
// directory, compensation and talent stay in the whitelist-only hrisGroup.
const hrisSelfServiceItems: NavItem[] = [
  { label: 'My Leave',    icon: Calendar,  href: '/hris/leave' },
  { label: 'My Payslips', icon: Wallet,    href: '/hris/payslips' },
  { label: 'My Profile',  icon: UsersIcon, href: '/hris/profile' },
  // Moved out of the Overview top list (CFO 2026-07-21) — staff loans is a
  // self-service HRIS surface (own-data only; route already whitelisted in
  // hris/layout.tsx SELF_SERVICE_ROUTES).
  { label: 'Staff Loans', icon: Banknote,  href: '/hris/staff-loans' },
  // Leave Encashment is self-service too — any employee applies to cash out
  // their own leave (CFO 2026-07-21). Own-data on the apply path; the register
  // + approvals are backend-gated to CFO/HR/Finance.
  { label: 'Leave Encashment', icon: Banknote, href: '/hris/leave-encashment' },
  // My Daily Brief — the workforce brief is emailed to every employee and the
  // shortfall-justification page is own-data only, so it belongs in self-service
  // (CFO 2026-07-23; staff hit the "HRIS is restricted" wall without it).
  { label: 'My Daily Brief', icon: Clock, href: '/hris/my-brief' },
  // Request a Letter — own-data self-service (employment/salary confirmation etc.);
  // route already whitelisted in hris/layout.tsx SELF_SERVICE_ROUTES. Was reachable
  // by direct URL only, missing from this menu (bug 1b9d6052, Oprah 2026-07-25).
  { label: 'Request a Letter', icon: FileText, href: '/hris/letters' },
  // Incentives — every line manager submits their team's incentives here, but
  // the only menu entry lived in the whitelist-only hrisGroup above, so a
  // manager who is not on the HRIS whitelist had NO way to reach the page
  // (Unami / Sechele 2026-07-30). Route is already in hris/layout.tsx
  // SELF_SERVICE_ROUTES and the backend gates submit to managers and above.
  { label: 'Incentives', icon: Coins, href: '/hris/incentives' },
  // Monthly Feedback — every line manager owes their team a monthly note, but
  // the only menu entry lived in the whitelist-only hrisGroup, so a manager who
  // is not one of the five had NO way to reach the page (Bharath, CFO
  // 2026-08-07). Route is in hris/layout.tsx TEAM_ROUTES and the backend scopes
  // it to the caller's own reports.
  { label: 'Monthly Feedback', icon: ClipboardCheck, href: '/hris/monthly-feedback' },
]

// Help & support cluster — pinned at the bottom of the old sidebar, now the
// tail section of the System module so every user keeps the same links.
const helpItems: NavItem[] = [
  // User Manual — single canonical how-to (CFO directive 2026-06-08).
  // Lives at /help. Everyone has read access (no role gate).
  { label: 'User Manual',     icon: BookOpen,       href: '/help' },
  // Report a System Bug (CFO directive 2026-06-10) — staff bug channel
  // that emails excoboard@ so people stop emailing the CFO directly.
  { label: 'Report a Bug',    icon: Bug,            href: '/report-bug' },
  // Bug Reports status board — role-aware: users see their own + status,
  // triagers see all + can move status (emails the reporter).
  { label: 'Bug Reports',     icon: ClipboardCheck, href: '/bug-reports' },
  // 10 Commandments — culture easter egg
  { label: '10 Commandments', icon: Sparkles,       href: '/commandments' },
]

// ─── Two-tier derivation (redesign pack 02, 2026-06-13) ─────────────────────
// The flat groups above stay the single source of truth. The icon rail +
// contextual panel are DERIVED from them — nothing is duplicated, so a route
// added to a group automatically appears in the panel.

interface NavSection {
  title: string
  items: NavItem[]
}

interface NavModule {
  key: string
  label: string
  /** Short name printed under the icon on the rail. Defaults to `label`.
      CFO 2026-08-06: the rail used to be icons only — "even I do not know where
      the features are, I have to keep my mouse over those icons". */
  short?: string
  icon: LucideIcon
  sections: NavSection[]
}

/** Split a group's children into sections at its header:true separators. */
function sectionize(children: NavItem[], fallbackTitle: string): NavSection[] {
  const sections: NavSection[] = []
  let current: NavSection = { title: fallbackTitle, items: [] }
  for (const item of children) {
    if (item.header) {
      if (current.items.length > 0) sections.push(current)
      current = { title: item.label, items: [] }
    } else {
      current.items.push(item)
    }
  }
  if (current.items.length > 0) sections.push(current)
  return sections
}

/** With-alpha helper so the active-item wash always follows the theme accent. */
function withAlpha(hex: string, alpha: number): string {
  const m = /^#?([0-9a-f]{6})$/i.exec(hex.trim())
  if (!m) return hex
  const n = parseInt(m[1], 16)
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`
}

// ─── Props ───────────────────────────────────────────────────────────────────

interface SidebarProps {
  collapsed: boolean
  onToggle: () => void
}

/** Rail width + expanded width — (dashboard)/layout.tsx margins must match. */
// Wide enough for a two-line name under the icon (CFO 2026-08-06).
export const SIDEBAR_RAIL_W = 96
export const SIDEBAR_FULL_W = 356

// ─── Component ───────────────────────────────────────────────────────────────

export function Sidebar({ collapsed, onToggle }: SidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const { theme, themeKey } = useTheme()
  const { selected: selectedCompany, selectedId: selectedCompanyId } = useCompany()
  // On unknown, hide. While the company list is still resolving `selected` is
  // null, which would otherwise read as the group view and show the links.
  const planVisible = !isCompanyResolving(selectedCompanyId, selectedCompany)
    && isAdiplPlanVisible(selectedCompany?.code)

  const [mobileOpen, setMobileOpen] = useState(false)
  const [username, setUsername] = useState('')
  const [me, setMe] = useState<UserProfile | null>(null)
  // Module the user explicitly clicked on the rail. Null = follow the route.
  const [pinnedModule, setPinnedModule] = useState<string | null>(null)
  const [userMenuOpen, setUserMenuOpen] = useState(false)
  const userMenuRef = useRef<HTMLDivElement>(null)
  const canAccessSalvage = useSalvageAccess()
  // HRIS module is restricted to a CFO whitelist (Prathap, Arun, Kago,
  // Pako, Unami) plus superuser / admins — CFO directive 2026-05-18.
  const canAccessHris = useHrisAccess()
  // Self-service tier — every employee (incl. subsidiaries like ADRisk) gets
  // their own leave / payslips / profile even off the whitelist (CFO directive
  // 2026-06-16, bug aec2f3ce).
  const canSelfServeHris = useHrisSelfService()
  // Data Protection module — DPO + C-suite + HR + Finance Mgr, server-gated
  // (CFO directive 2026-07-20: its own folder, like HRIS).
  const [canAccessDpa, setCanAccessDpa] = useState<boolean | undefined>(undefined)
  useEffect(() => {
    apiFetch<{ allowed: boolean }>('/dpa-dashboard/access/')
      .then(r => setCanAccessDpa(!!r.allowed)).catch(() => setCanAccessDpa(false))
  }, [])
  // AML / Compliance overview — AML officer + Compliance & Risk + C-suite / HR /
  // Finance, server-gated (CFO directive 2026-07-24). Shown atop the Compliance
  // module only to those allowed; the page itself is server-gated too.
  const [canAccessCompliance, setCanAccessCompliance] = useState<boolean | undefined>(undefined)
  useEffect(() => {
    apiFetch<{ allowed: boolean }>('/compliance-dashboard/access/')
      .then(r => setCanAccessCompliance(!!r.allowed)).catch(() => setCanAccessCompliance(false))
  }, [])
  // Security Posture — group C-suite only (CEO / COO / CFO), server-gated
  // (CFO directive 2026-08-06). Sits in the Compliance module beside AML.
  const [canAccessSecurity, setCanAccessSecurity] = useState<boolean | undefined>(undefined)
  useEffect(() => {
    apiFetch<{ allowed: boolean }>('/security-dashboard/access/')
      .then(r => setCanAccessSecurity(!!r.allowed)).catch(() => setCanAccessSecurity(false))
  }, [])
  // UniCoin Instant Insurance portal — its OWN top-level module for the portal
  // managers (CFO 2026-07-27: "under unicoin, out of ADIC"), not buried in the
  // Accounting list. Same manager probe as the portal itself; non-managers never
  // see it. Probe loading → hidden (no flash).
  const [canManageUnicoin, setCanManageUnicoin] = useState<boolean | undefined>(undefined)
  useEffect(() => {
    apiFetch<{ is_manager: boolean }>('/agent-portal/cycles/access/')
      .then(r => setCanManageUnicoin(!!r.is_manager)).catch(() => setCanManageUnicoin(false))
  }, [])
  // Audience Feedback — confidential to the speaker alone (CFO 2026-08-03).
  // Server-gated with no admin bypass; hidden here for everyone else so the
  // module's existence isn't advertised. Probe loading → hidden (no flash).
  const [canReadSpeakerFeedback, setCanReadSpeakerFeedback] = useState<boolean | undefined>(undefined)
  useEffect(() => {
    apiFetch<{ allowed: boolean }>('/speaker-feedback/access/')
      .then(r => setCanReadSpeakerFeedback(!!r.allowed))
      .catch(() => setCanReadSpeakerFeedback(false))
  }, [])

  // The CFO's build log is his alone (CFO 2026-09-09). Same treatment as the
  // speaker feedback above: probe, and while the answer is unknown keep it
  // hidden, so the item never flashes on somebody else's menu. Hiding is not
  // the control — the API and the page are both gated — it just stops the
  // screen's existence being advertised to everyone.
  const [isTheCfo, setIsTheCfo] = useState<boolean | undefined>(undefined)
  const [canSeeForgiveness, setCanSeeForgiveness] = useState<boolean | undefined>(undefined)
  useEffect(() => {
    apiFetch<{ is_the_cfo: boolean; can_see_forgiveness: boolean }>('/cfo/whoami/')
      .then(r => { setIsTheCfo(!!r.is_the_cfo); setCanSeeForgiveness(!!r.can_see_forgiveness) })
      .catch(() => { setIsTheCfo(false); setCanSeeForgiveness(false) })
  }, [])

  useEffect(() => {
    const stored = localStorage.getItem('alpha_user')
    if (stored) setUsername(stored)
    getMe().then(setMe).catch(() => setMe(null))
  }, [])

  // CFO directive 2026-06-25 ("stop the menu jumping"): navigating closes the
  // mobile drawer + user menu but KEEPS the module the user opened — no
  // auto-jump. The panel still auto-follows the route until the user pins one
  // (pinnedModule stays null), then stays where they put it.
  useEffect(() => {
    setMobileOpen(false)
    setUserMenuOpen(false)
  }, [pathname])

  // Close the user-chip menu on outside click.
  useEffect(() => {
    function onDocClick(e: MouseEvent) {
      if (userMenuRef.current && !userMenuRef.current.contains(e.target as Node)) {
        setUserMenuOpen(false)
      }
    }
    if (userMenuOpen) {
      document.addEventListener('mousedown', onDocClick)
      return () => document.removeEventListener('mousedown', onDocClick)
    }
  }, [userMenuOpen])

  const isExp = !collapsed || mobileOpen

  function isActive(href: string): boolean {
    // Sub-header items use href='#' as a placeholder — never an active route.
    if (!href || href === '#') return false
    // Strip query params for comparison
    const base = href.split('?')[0]
    if (base === '/') return pathname === '/'
    return pathname === base || pathname.startsWith(base + '/')
  }

  // ─── Modules (derived, RBAC-gated exactly like the old flat sidebar) ──────

  const modules: NavModule[] = useMemo(() => {
    const mods: NavModule[] = []

    mods.push({
      key: 'overview',
      label: 'Overview',
      short: 'Overview',
      icon: LayoutDashboard,
      // Split the top list into its header:true sections (Overview / My Work /
      // Spend & Payments / Support) — same treatment as the Accounting group,
      // so the sub-headers render as titles, not dead rows (CFO 2026-08-22).
      sections: sectionize(topItems.filter(i => {
        if (!i.href.startsWith('/cfo/')) return true
        if (i.href === '/cfo/forgiveness') return isTheCfo === true || canSeeForgiveness === true
        return isTheCfo === true
      }), 'Overview'),
    })

    // Project Nexus — rewards / wellness / Nexus, one programme, its own module
    // (CFO directive 2026-07-02). Ungated, as these items were on the flat nav.
    mods.push({
      key: 'nexus',
      label: 'Project Nexus',
      short: 'Nexus',
      icon: Compass,
      sections: [{ title: 'Project Nexus', items: nexusItems }],
    })

    // Commissions — its own top-level module, NOT under Finance/Payables
    // (CFO directive 2026-07-17). Sales agents don't have finance access but
    // must reach their own commission, so this is ungated: every signed-in
    // user sees it. A non-agent just sees the "not linked to an agent" note.
    mods.push({
      key: 'commissions',
      label: 'Commissions',
      short: 'Commissions',
      icon: Coins,
      sections: [{ title: 'Commissions', items: [
        { label: 'Commissions', icon: Coins, href: '/commissions' },
        // Broker Commission register (Rose Mokgware / CFO 2026-09-08). The page
        // gates itself on the finance roster; a sales agent who lands here sees
        // the refusal, same as the rest of the module.
        { label: 'Broker Commission', icon: Building2, href: '/commissions/brokers' },
      ] }],
    })

    // Alpha Rooms — boardroom booking, its own top-level module so any signed-in
    // staff member can find and book a room without finance access (CFO 2026-08-12).
    mods.push({
      key: 'rooms',
      label: 'Alpha Rooms',
      short: 'Rooms',
      icon: CalendarClock,
      sections: [{ title: 'Alpha Rooms', items: [
        { label: 'Book a room', icon: CalendarClock, href: '/rooms' },
      ] }],
    })

    // UniCoin — Instant Insurance agent commissions, its own module for portal
    // managers (CFO 2026-07-27). Gated on the manager probe so only the portal
    // managers see it; everyone else never does.
    //
    // HIDDEN 2026-09-01 (CFO, bug bc371a49): the CFO does not need the UniCoin >
    // Agent Commissions nav item right now, so the module is suppressed from the
    // rail. The /unicoin page is untouched and still reachable by URL — this only
    // removes the sidebar entry. Restore by removing the `false &&` guard.
    if (false && canManageUnicoin === true) {
      mods.push({
        key: 'unicoin',
        label: 'UniCoin',
        short: 'UniCoin',
        icon: Users,
        sections: [{ title: 'Instant Insurance', items: [
          { label: 'Agent Commissions', icon: Users, href: '/unicoin' },
        ] }],
      })
    }

    // Accounting & Control — the Accounting group's own sub-headers become
    // panel sections; Period Management appends for FM+ (same gate as before).
    // The 5-Year Plan pages belong to AD Insurtech. Under any other single
    // entity they are hidden rather than shown with irrelevant content.
    const acctChildren = (groups[0].children || []).filter(
      (i) => planVisible || !(ADIPL_ONLY_HREFS as readonly string[]).includes(i.href))
    const acctSections = sectionize(acctChildren, 'Ledger')
    if (me?.can_manage_periods || me?.can_administer_users) {
      acctSections.push({ title: 'Period Management', items: periodMgmtGroup.children || [] })
    }
    mods.push({ key: 'accounting', label: 'Accounting & Control', short: 'Accounting', icon: BookOpen, sections: acctSections })

    // People — HRIS, whitelist gated (CFO directive 2026-05-18). Sits right
    // after Accounting to keep the CFO's position-5 ordering intent.
    if (canAccessHris === true) {
      mods.push({ key: 'people', label: 'People (HRIS)', short: 'People', icon: UsersIcon, sections: sectionize(hrisGroup.children || [], 'HRIS') })
    }
    // Self-service module (own leave / payslips / profile). Every employee with
    // the view_self capability gets it — INCLUDING HRIS-whitelist / HR / admin
    // users, who are also employees with their own leave & payslips. Previously
    // an `else if` here hid My Profile / My Leave / My Payslips from anyone on
    // the admin tier (bug 5ae38c73, Oprah Mogomotsi finance_manager 2026-07-22).
    if (canSelfServeHris === true) {
      mods.push({ key: 'myhr', label: 'My HR', icon: UsersIcon, sections: [{ title: 'Self-Service', items: hrisSelfServiceItems }] })
    }

    // Data Protection — its own folder for the DPO (+ C-suite / HR / Finance
    // Mgr), server-gated. All the DPA registers in one place (CFO 2026-07-20).
    if (canAccessDpa === true) {
      mods.push({ key: 'dpa', label: 'Data Protection', short: 'Data Protection', icon: ShieldCheck, sections: [
        { title: 'Data Protection', items: [
          { label: 'Dashboard',         icon: ShieldCheck,    href: '/data-protection' },
          { label: 'Monthly Checklist', icon: ClipboardCheck, href: '/data-protection#checklist' },
          { label: 'Breach Register',   icon: Shield,         href: '/data-protection#breaches' },
          { label: 'Data Requests',     icon: Inbox,          href: '/data-protection#dsr' },
          { label: 'DPIA',              icon: ClipboardCheck, href: '/data-protection#dpia' },
          { label: 'ROPA (register)',   icon: FileText,       href: '/data-protection#ropa' },
          { label: 'Privacy Notices',   icon: FileText,       href: '/data-protection#notices' },
          { label: 'Audit Scorecard',   icon: BarChart3,      href: '/data-protection#scorecard' },
        ] },
      ] })
    }

    // Operations — Banking / Payables / Claims / Procurement / Health Care
    // (+ Salvage when gated in). Group labels become section headers.
    const opsSections: NavSection[] = []
    for (const g of groups.slice(1)) {
      if (g.label === 'Compliance') continue
      opsSections.push(...sectionize(g.children || [], g.label))
    }
    if (canAccessSalvage) {
      opsSections.push({ title: 'Salvage Yard', items: salvageGroup.children || [] })
    }
    mods.push({ key: 'operations', label: 'Operations', icon: Landmark, sections: opsSections })
    // Records Register — its own tab, NOT under Fixed Assets (CFO 2026-08-06:
    // "do not put this under the fixed asset register, keep a separate tab").
    // Paper files must never sit in the register that feeds asset reporting.
    mods.push({ key: 'records', label: 'Records Register', short: 'Records', icon: Archive, sections: [
      { title: 'Records Register', items: [
        { label: 'Records Register', icon: Archive, href: '/records' },
      ] },
    ] })

    const complianceGroup = groups.find(g => g.label === 'Compliance')
    if (complianceGroup) {
      const complianceSections: NavSection[] = []
      // AML officer overview sits at the top for those allowed (CFO 2026-07-24).
      if (canAccessCompliance === true) {
        complianceSections.push({ title: 'AML / Compliance', items: [
          { label: 'Compliance Overview', icon: ClipboardCheck, href: '/compliance/overview' },
        ] })
      }
      // Security Posture — CEO / COO / CFO only.
      if (canAccessSecurity === true) {
        complianceSections.push({ title: 'Security', items: [
          { label: 'Security Posture', icon: Shield, href: '/compliance/security' },
        ] })
      }
      complianceSections.push(...sectionize(complianceGroup.children || [], 'Compliance'))
      mods.push({ key: 'compliance', label: 'Compliance', icon: ShieldCheck, sections: complianceSections })
    }

    // Internal Audit — visible only to CEO / COO / CFO / board + the audit function.
    if (me?.can_view_internal_audit) {
      mods.push({ key: 'internal-audit', label: 'Internal Audit', short: 'Internal Audit', icon: ShieldCheck, sections: sectionize(internalAuditGroup.children || [], 'Internal Audit') })
    }

    // Audience Feedback — the speaker's confidential pre-session responses
    // (CFO 2026-08-03). Only the listed reader sees this; not even admins.
    if (canReadSpeakerFeedback) {
      mods.push({
        key: 'speaker-feedback',
        label: 'Confidential',
        short: 'Feedback',
        icon: Lock,
        sections: [{ title: 'Confidential', items: [
          { label: 'Audience Feedback', icon: Lock, href: '/speaker-feedback' },
        ] }],
      })
    }

    // System — admin Settings (admin-gated, unchanged) + the help cluster
    // every user always had at the bottom of the old sidebar.
    const sysSections: NavSection[] = []
    if (me?.can_administer_users) {
      sysSections.push(...sectionize(adminGroup.children || [], 'Settings'))
    }
    sysSections.push({ title: 'Help & Support', items: helpItems })
    mods.push({ key: 'system', label: 'System', icon: Settings, sections: sysSections })

    return mods
    // planVisible gates the AD Insurtech plan links inside this memo, so it MUST
    // be a dependency. Without it the nav was built once on the first paint —
    // before the company context resolves, when selectedId and selected are both
    // null, which reads as the "All companies" group view and shows the links.
    // The page guard then correctly refused to render plan content under ADIC
    // while the sidebar kept offering the links for the rest of the session, and
    // switching TO AD Insurtech never revealed them either.
    // Bug 4c339e6b, Ontlametse Mogomotsi 2026-08-06.
  }, [isTheCfo, canSeeForgiveness, me, canAccessHris, canSelfServeHris, canAccessSalvage, canAccessDpa, canAccessCompliance,
      canAccessSecurity, canReadSpeakerFeedback, planVisible])

  const routeModuleKey = useMemo(() => {
    for (const m of modules) {
      for (const s of m.sections) {
        if (s.items.some(it => isActive(it.href))) return m.key
      }
    }
    return null
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [modules, pathname])

  const activeKey = pinnedModule ?? routeModuleKey ?? 'overview'
  const activeModule = modules.find(m => m.key === activeKey) || modules[0]

  // BUG 30f69c69 (Oprah 2026-06-26): two sidebar items highlighted at once on
  // nested routes. isActive() prefix-matches, so on /banking/realpay/... BOTH
  // "Bank Reconciliation" (/banking) and "RealPay" (/banking/realpay) lit up.
  // Fix: only the SINGLE most-specific (longest) matching href is active.
  const deepestActiveHref = useMemo(() => {
    const hrefs: string[] = []
    const walk = (items: NavItem[]) => items.forEach(it => {
      if (it.href && it.href !== '#' && !it.header) hrefs.push(it.href.split('?')[0])
    })
    modules.forEach(m => m.sections.forEach(s => walk(s.items)))
    walk(hrisSelfServiceItems); walk(helpItems); walk(topItems)
    let best = ''
    for (const h of hrefs) {
      const matches = h === '/' ? pathname === '/' : (pathname === h || pathname.startsWith(h + '/'))
      if (matches && h.length > best.length) best = h
    }
    return best
  }, [modules, pathname])

  // BUG 13c0b4b0 (Oprah 2026-06-26): the sub-sections inside a module (Banks,
  // Collections, Petty Cash, …) all rendered expanded at once — a very long,
  // hard-to-scan panel. Accordion them: one section open at a time, the section
  // holding the current page auto-opens, the rest collapse behind a ▸.
  const [openSection, setOpenSection] = useState<string | null>(null)
  const activeSectionTitle = useMemo(() => {
    for (const s of activeModule.sections) {
      if (s.items.some(it => it.href && it.href !== '#' && it.href.split('?')[0] === deepestActiveHref)) {
        return s.title
      }
    }
    return activeModule.sections[0]?.title ?? null
  }, [activeModule, deepestActiveHref])
  // Reset the manual toggle when the module changes so the new module's active
  // section opens (a title from the old module would otherwise leave all closed).
  useEffect(() => { setOpenSection(null) }, [activeKey])

  function onRailClick(key: string) {
    // CFO directive 2026-06-25 — click the already-open module again to COLLAPSE
    // the panel (click-to-toggle), instead of it only ever opening.
    if (key === activeKey && !collapsed && !mobileOpen) {
      onToggle()
      return
    }
    setPinnedModule(key)
    // Bug bc371a49 (CFO 2026-09-01): a single-item module (Commissions, Alpha
    // Rooms, …) must navigate straight to its page on a rail click. Before this
    // the rail only pinned the module and opened a one-row panel, so clicking
    // "Commissions" looked dead — the highlight moved but the route never
    // changed and the content stayed on whatever page you were on.
    const mod = modules.find(m => m.key === key)
    const navItems = mod
      ? mod.sections.flatMap(s => s.items).filter(it => it.href && it.href !== '#' && !it.external)
      : []
    if (navItems.length === 1 && pathname.split('?')[0] !== navItems[0].href.split('?')[0]) {
      router.push(navItems[0].href)
    }
    // Collapsed rail: choosing a module re-opens the panel so the links are
    // actually reachable (the rail alone only carries module-level icons).
    if (collapsed && !mobileOpen) onToggle()
  }

  async function handleLogout() {
    // Local cleanup first so /login can't auto-route us back to /dashboard
    // before the MSAL redirect fires. removeToken() drops the alpha_token
    // sentinel + the me/companies caches; alpha_user is the display name.
    removeToken()
    localStorage.removeItem('alpha_user')
    localStorage.removeItem('alpha_company_id')

    // SSO logout: dynamically import so the MSAL bundle isn't pulled into
    // every page that renders the sidebar. signOut() calls logoutRedirect
    // when SSO is configured (ends the Microsoft session too) and falls
    // back to a hard nav to /login?signedout=1 otherwise. Without this
    // step the cached MSAL account survives, /login auto-routes to /,
    // and the user appears stuck on the dashboard after clicking Logout.
    try {
      const { signOut } = await import('@/auth/msal')
      await signOut()
    } catch {
      router.push('/login?signedout=1')
    }
  }

  function handleNav() {
    setMobileOpen(false)
  }

  // BUG-013/020 (Oprah 2026-06-05): the footer showed empty username -> "Admin"
  // while Tasks/ARIA showed the real signed-in user. Resolve the real name from
  // the /me profile (full_name -> username) so it's consistent everywhere.
  // 2026-07-25: the fallback below used to be the literal word "Admin", so an
  // ordinary finance-manager account was labelled Admin whenever /me hadn't
  // loaded. Never fall back to something that reads like a role or a rank.
  const realName = (me as any)?.full_name || me?.username || username || ''
  const displayName = realName || 'Signed in'
  const initials = realName ? realName.slice(0, 2).toUpperCase() : '··'

  const accentSoft = withAlpha(theme.orange, 0.14)

  // ─── Sub-renderers ─────────────────────────────────────────────────────────

  function renderItem(item: NavItem) {
    // Active = the single most-specific matching route (BUG 30f69c69), not every
    // prefix. Falls back to isActive for the '#' placeholder guard.
    const active = item.href !== '#' && item.href.split('?')[0] === deepestActiveHref

    const Icon = item.icon
    const className = cn(
      'flex items-center gap-2.5 h-9 rounded-lg px-3 transition-colors duration-150 group',
      active ? 'text-white' : 'text-white/70 hover:bg-white/[0.04] hover:text-white',
    )
    const style = {
      borderLeft: `3px solid ${active ? theme.orange : 'transparent'}`,
      background: active ? accentSoft : undefined,
    }
    const inner = (
      <>
        <Icon
          className="flex-shrink-0 w-[18px] h-[18px]"
          style={active ? { color: theme.orange } : undefined}
          strokeWidth={1.5}
        />
        <span
          className="text-sm font-medium truncate"
          style={active ? { color: theme.orange } : undefined}
        >
          {item.label}
        </span>
      </>
    )
    // External items (e.g. /claims-po — the Claims PO app served same-origin
    // behind omni's Caddy, not a Next route) must be a full-page anchor; a
    // Next <Link> would client-route and 404.
    if (item.external) {
      return (
        <a key={item.href + item.label} href={item.href} onClick={handleNav}
           title={'Opens ' + item.label}
           className={className} style={style}>
          {inner}
        </a>
      )
    }
    return (
      <Link key={item.href + item.label} href={item.href} onClick={handleNav}
            className={className} style={style}>
        {inner}
      </Link>
    )
  }

  function renderSection(section: NavSection) {
    // Accordion only when the module has more than one section. A lone section
    // (e.g. Overview) stays always-open — collapsing the only nav helps no one.
    const accordion = activeModule.sections.length > 1
    if (!accordion) {
      return (
        <div key={section.title}>
          <div className="px-3 pt-4 pb-1.5 text-[10.5px] uppercase tracking-[0.18em] font-semibold text-white/35 select-none">
            {section.title}
          </div>
          <div className="space-y-0.5">
            {section.items.map(item => renderItem(item))}
          </div>
        </div>
      )
    }
    const isOpen = (openSection ?? activeSectionTitle) === section.title
    return (
      <div key={section.title}>
        <button
          type="button"
          onClick={() => setOpenSection(isOpen ? null : section.title)}
          className="w-full flex items-center justify-between px-3 pt-4 pb-1.5 text-[10.5px] uppercase tracking-[0.18em] font-semibold text-white/35 hover:text-white/60 transition-colors select-none"
        >
          <span>{section.title}</span>
          {isOpen
            ? <ChevronDown className="w-3 h-3 flex-shrink-0" />
            : <ChevronRight className="w-3 h-3 flex-shrink-0" />}
        </button>
        {isOpen && (
          <div className="space-y-0.5">
            {section.items.map(item => renderItem(item))}
          </div>
        )}
      </div>
    )
  }

  // ─── Render ────────────────────────────────────────────────────────────────

  return (
    <>
      {/* Mobile hamburger */}
      <button
        className="fixed left-4 z-50 md:hidden p-2 rounded-lg text-white"
        // `top` clears the iOS status-bar / notch safe area. In an installed
        // (Add to Home Screen) PWA with viewport-fit=cover, env(safe-area-inset-top)
        // is ~47px, and the old fixed top-4 (16px) put this button UNDER the status
        // bar, where iOS eats the tap — so the menu was unopenable and the app stuck
        // on the dashboard (reported from a home-screen install, 2026-08-12). In
        // Safari / on desktop the inset is 0, so this stays at 1rem — no change there.
        style={{ background: theme.sidebar, top: 'calc(env(safe-area-inset-top, 0px) + 1rem)' }}
        onClick={() => setMobileOpen(!mobileOpen)}
        aria-label="Toggle menu"
      >
        {mobileOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
      </button>

      {/* Mobile overlay */}
      {mobileOpen && (
        <div
          className="fixed inset-0 bg-black/50 z-30 md:hidden"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar — icon rail + contextual panel (redesign pack 02) */}
      <aside
        data-omni-sidebar
        className={cn(
          'fixed left-0 top-0 h-full z-40 flex-row',
          'hidden md:flex',
          mobileOpen && '!flex',
        )}
        style={{
          background: theme.sidebar,
          width: mobileOpen ? SIDEBAR_FULL_W : collapsed ? SIDEBAR_RAIL_W : SIDEBAR_FULL_W,
          transition: 'width 0.2s ease',
        }}
      >
        {/* ── Icon rail ───────────────────────────────────────────────── */}
        <div
          className="flex flex-col items-center flex-shrink-0 h-full"
          style={{
            width: SIDEBAR_RAIL_W,
            background: 'rgba(0,0,0,0.28)',
            borderRight: '1px solid rgba(255,255,255,0.06)',
          }}
        >
          {/* Brand mark — the REAL Alpha Direct logo, as-is. Full-colour on the
              light (professional) rail; the official white version on the dark
              rails so it reads on navy. Replaces the lone orange swoosh that
              looked like a broken fragment. Shown on the rail only when the
              sidebar is COLLAPSED — when expanded, the panel header carries the
              logo, so it never appears twice (CFO 2026-08-17). */}
          {!isExp && (
            <Link href="/dashboard" onClick={handleNav} className="py-4 flex-shrink-0 flex justify-center w-full" title="omni — Dashboard">
              <Image
                src={themeKey === 'professional' ? '/brand/logo-full-color.png' : '/brand/logo-monotone-white.png'}
                alt="Alpha Direct"
                width={200}
                height={99}
                className="w-14 h-auto object-contain"
                priority
              />
            </Link>
          )}

          {/* Module tiles */}
          <div className="flex-1 w-full flex flex-col items-center gap-1.5 py-2 overflow-y-auto overflow-x-hidden">
            {modules.map(m => {
              const Icon = m.icon
              const moduleActive = m.key === activeKey
              return (
                <button
                  key={m.key}
                  onClick={() => onRailClick(m.key)}
                  title={m.label}
                  aria-label={m.label}
                  aria-pressed={moduleActive}
                  data-omni-active={moduleActive ? '' : undefined}
                  className={cn(
                    'w-[84px] rounded-xl flex flex-col items-center justify-start gap-1 flex-shrink-0',
                    'px-1 pt-2 pb-1.5 transition-all duration-150',
                    moduleActive ? 'text-white' : 'text-white/60 hover:text-white hover:bg-white/[0.06]',
                  )}
                  style={moduleActive ? {
                    background: theme.orange,
                    boxShadow: `0 0 0 1px ${withAlpha(theme.orange, 0.35)}, 0 8px 22px -8px ${withAlpha(theme.orange, 0.65)}`,
                  } : undefined}
                >
                  <Icon className="w-5 h-5 flex-shrink-0" strokeWidth={1.6} />
                  <span
                    className="w-full text-center leading-[1.15] font-semibold"
                    style={{ fontSize: 9.5, letterSpacing: '0.01em', hyphens: 'auto' }}
                  >
                    {m.short || m.label}
                  </span>
                </button>
              )
            })}
          </div>

          {/* Collapsed-rail user affordances — when the contextual panel (which
              holds the user chip + Logout) is hidden, keep the avatar and a
              Logout control reachable on the rail itself. Without this, a
              collapsed sidebar has no path to log out (parity with the old
              always-rendered bottom section). */}
          {!isExp && (
            <div className="flex flex-col items-center gap-1.5 mb-1.5 flex-shrink-0">
              <div className="relative" title={`${displayName} — ${me?.title || 'Alpha Direct'}`}>
                <div
                  className="w-9 h-9 rounded-full flex items-center justify-center"
                  style={{ background: accentSoft, border: `1px solid ${withAlpha(theme.orange, 0.35)}` }}
                >
                  <span className="text-xs font-bold" style={{ color: theme.orange }}>{initials}</span>
                </div>
                <span
                  className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full"
                  style={{ background: '#34D399', border: `2px solid ${theme.sidebar}` }}
                  aria-hidden="true"
                />
              </div>
              <button
                onClick={handleLogout}
                className="w-11 h-9 rounded-lg flex items-center justify-center text-white/40 hover:text-red-400 hover:bg-white/[0.06] transition-colors"
                aria-label="Logout"
                title="Logout"
              >
                <LogOut className="w-4 h-4" strokeWidth={1.5} />
              </button>
            </div>
          )}

          {/* Collapse chevron — desktop only */}
          <button
            onClick={onToggle}
            className="hidden md:flex w-11 h-10 mb-3 rounded-lg items-center justify-center text-white/35 hover:text-white/70 hover:bg-white/[0.06] transition-colors flex-shrink-0"
            aria-label={collapsed ? 'Expand sidebar' : 'Collapse sidebar'}
            title={collapsed ? 'Expand' : 'Collapse'}
          >
            {collapsed ? <ChevronRight className="w-4 h-4" /> : <ChevronLeft className="w-4 h-4" />}
          </button>
        </div>

        {/* ── Contextual panel ────────────────────────────────────────── */}
        {isExp && (
          <div
            className="flex flex-col flex-1 min-w-0 h-full"
            style={{ background: 'linear-gradient(180deg, rgba(255,255,255,0.035) 0%, rgba(255,255,255,0.01) 100%)' }}
          >
            {/* Lockup + active module eyebrow */}
            <div
              className="px-5 pt-4 pb-3 flex-shrink-0"
              style={{ borderBottom: '1px solid rgba(255,255,255,0.07)' }}
            >
              {/* The real Alpha Direct logo, as-is, on every theme: full-colour
                  on the light (professional) sidebar, the official white version
                  on the dark sidebars (default / fun / heavenly) so it reads on
                  navy. Replaces the old "OMNI" text (CFO 2026-08-17). */}
              <Link href="/dashboard" onClick={handleNav} title="omni — Dashboard" className="inline-block">
                <Image
                  src={themeKey === 'professional' ? '/brand/logo-full-color.png' : '/brand/logo-monotone-white.png'}
                  alt="Alpha Direct"
                  width={210}
                  height={104}
                  priority
                  className="h-[108px] w-auto object-contain object-left"
                />
              </Link>
              <p className="mt-1.5 text-[10px] uppercase tracking-[0.22em] font-semibold" style={{ color: theme.orange }}>
                {activeModule.label}
              </p>
            </div>

            {/* Sections */}
            <nav aria-label="Main navigation" className="flex-1 px-2.5 pb-3 overflow-y-auto overflow-x-hidden">
              {/* CFO directive 2026-06-25 — a visible search that fires the
                  existing global command palette (CommandPalette.tsx listens
                  for 'omni:cmdk'); type to jump to any of the ~194 pages. */}
              <button
                onClick={() => window.dispatchEvent(new Event('omni:cmdk'))}
                className="mt-3 mb-1.5 flex items-center gap-2 h-9 rounded-lg px-3 w-full text-left text-white/60 hover:text-white hover:bg-white/[0.06] transition-colors border border-white/10"
                title="Search — jump to any page"
              >
                <Search className="w-4 h-4 flex-shrink-0" strokeWidth={1.5} />
                <span className="text-sm">Search… jump to any page</span>
                <span className="ml-auto text-[10px] text-white/40 border border-white/15 rounded px-1.5 py-0.5">⌘K</span>
              </button>
              {activeModule.sections.map(section => renderSection(section))}
            </nav>

            {/* User chip — pinned bottom (replaces the old mid-sidebar block) */}
            <div
              ref={userMenuRef}
              className="relative flex-shrink-0 p-2.5"
              style={{ borderTop: '1px solid rgba(255,255,255,0.07)' }}
            >
              {userMenuOpen && (
                <div
                  className="absolute left-2.5 right-2.5 bottom-[64px] rounded-xl overflow-hidden py-1"
                  style={{
                    background: theme.sidebar,
                    border: '1px solid rgba(255,255,255,0.12)',
                    boxShadow: '0 18px 40px -12px rgba(0,0,0,0.6)',
                    zIndex: 50,
                  }}
                >
                  <Link
                    href="/help"
                    onClick={() => { setUserMenuOpen(false); handleNav() }}
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-white/80 hover:bg-white/[0.06] hover:text-white transition-colors"
                  >
                    <BookOpen className="w-4 h-4" strokeWidth={1.5} />
                    <span>User Manual</span>
                  </Link>
                  <button
                    onClick={handleLogout}
                    className="w-full flex items-center gap-2.5 px-3 py-2 text-sm text-white/80 hover:bg-white/[0.06] hover:text-red-400 transition-colors"
                  >
                    <LogOut className="w-4 h-4" strokeWidth={1.5} />
                    <span>Logout</span>
                  </button>
                </div>
              )}
              <button
                onClick={() => setUserMenuOpen(o => !o)}
                className="w-full flex items-center gap-2.5 rounded-xl px-2.5 py-2 hover:bg-white/[0.05] transition-colors text-left"
                aria-haspopup="menu"
                aria-expanded={userMenuOpen}
              >
                <div className="relative flex-shrink-0">
                  <div
                    className="w-9 h-9 rounded-full flex items-center justify-center"
                    style={{ background: accentSoft, border: `1px solid ${withAlpha(theme.orange, 0.35)}` }}
                  >
                    <span className="text-xs font-bold" style={{ color: theme.orange }}>{initials}</span>
                  </div>
                  <span
                    className="absolute -bottom-0.5 -right-0.5 w-2.5 h-2.5 rounded-full"
                    style={{ background: '#34D399', border: `2px solid ${theme.sidebar}` }}
                    aria-hidden="true"
                  />
                </div>
                <div className="min-w-0 flex-1">
                  <p className="text-sm font-medium text-white truncate leading-tight">{displayName}</p>
                  <p className="text-[11px] text-white/40 truncate">{me?.title || 'Alpha Direct'}</p>
                </div>
                <ChevronDown
                  className={cn('w-4 h-4 text-white/35 flex-shrink-0 transition-transform', userMenuOpen && 'rotate-180')}
                />
              </button>
            </div>
          </div>
        )}
      </aside>
    </>
  )
}
