'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  getBankAccounts,
  getBankStatements,
  getBankStatement,
  importBankStatement,
  runMatching,
  getPayments,
  matchStatementLine,
  getToken,
} from '@/lib/api'
import type {
  BankAccount,
  BankStatement,
  BankStatementDetail,
  BankStatementLine,
  Payment,
} from '@/lib/api'
import { TopBar } from '@/components/layout/TopBar'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { StatusBadge } from '@/components/ui/badge'
import { Modal, ModalBody, ModalFooter } from '@/components/ui/modal'
import { LoadingTable, LoadingSpinner } from '@/components/ui/loading'
import { FormField, Select } from '@/components/ui/input'
import { formatAmount, formatDate, parseAmount, cn } from '@/lib/utils'
import { useNumberFormat } from '@/contexts/NumberFormatContext'
import {
  Upload,
  Zap,
  Landmark,
  AlertCircle,
  CheckCircle,
  RefreshCw,
  Link2,
} from 'lucide-react'

// ─── Bank Reconciliation Page ─────────────────────────────────────────────────

export default function BankingPage() {
  const router = useRouter()
  const { mode } = useNumberFormat()
  const fmt = (amount: string | number, currency = 'BWP') => formatAmount(amount, currency, mode)

  const [bankAccounts, setBankAccounts] = useState<BankAccount[]>([])
  const [bankAccountsLoading, setBankAccountsLoading] = useState(true)
  const [statements, setStatements] = useState<BankStatement[]>([])
  const [statementsLoading, setStatementsLoading] = useState(false)
  const [selectedStatement, setSelectedStatement] = useState<BankStatementDetail | null>(null)
  const [statementLoading, setStatementLoading] = useState(false)
  const [matching, setMatching] = useState(false)
  const [matchResult, setMatchResult] = useState<{ matched: number; unmatched: number } | null>(null)
  const [showUpload, setShowUpload] = useState(false)
  const [uploadBankAccount, setUploadBankAccount] = useState('')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [showMatchModal, setShowMatchModal] = useState(false)
  const [matchingLine, setMatchingLine] = useState<BankStatementLine | null>(null)
  const [unmatchedPayments, setUnmatchedPayments] = useState<Payment[]>([])
  const [selectedPaymentId, setSelectedPaymentId] = useState('')
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // Date filter over the transaction lines — lets you view only the transactions
  // in a chosen day or date range (Lefika Basotli, 14 Aug 2026). Filters the line
  // table only; the statement totals above stay the whole-statement figures.
  const [lineFrom, setLineFrom] = useState('')
  const [lineTo, setLineTo] = useState('')

  useEffect(() => {
    const token = getToken()
    if (!token) { router.replace('/login'); return }
    loadBankAccounts()
    loadStatements()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Clear the date filter whenever a different statement is opened, so a range
  // from the last statement never silently hides the new one's lines.
  useEffect(() => {
    setLineFrom('')
    setLineTo('')
  }, [selectedStatement?.id])

  // The transaction lines actually shown, after the date filter. transaction_date
  // is an ISO 'YYYY-MM-DD' string, so a plain string compare is a correct date
  // compare, and it matches the value an <input type="date"> gives us.
  const dateFilterOn = !!(lineFrom || lineTo)
  const visibleLines = selectedStatement
    ? selectedStatement.lines.filter((l) =>
        (!lineFrom || l.transaction_date >= lineFrom) &&
        (!lineTo || l.transaction_date <= lineTo))
    : []

  const loadBankAccounts = async () => {
    setBankAccountsLoading(true)
    try {
      const res = await getBankAccounts()
      setBankAccounts(res.results)
      if (res.results.length > 0) setUploadBankAccount(res.results[0].id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load bank accounts')
    } finally { setBankAccountsLoading(false) }
  }

  const loadStatements = async () => {
    setStatementsLoading(true)
    try {
      const res = await getBankStatements({ ordering: '-statement_date', page_size: '20' })
      setStatements(res.results)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load statements')
    } finally { setStatementsLoading(false) }
  }

  const loadStatementDetail = async (id: string) => {
    setStatementLoading(true)
    // RECON-002: clear the previous Auto-Match result text whenever we
    // switch to a different statement. The Lines/Matched/Unmatched
    // chips already refresh; this just stops the post-action banner
    // from carrying over (e.g. "0 matched, 1 unmatched" from the prior
    // statement).
    setMatchResult(null)
    try {
      const detail = await getBankStatement(id)
      setSelectedStatement(detail)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load statement')
    } finally { setStatementLoading(false) }
  }

  const handleRunMatching = async () => {
    if (!selectedStatement) return
    setMatching(true)
    setMatchResult(null)
    try {
      const result = await runMatching(selectedStatement.id)
      setMatchResult(result)
      await loadStatementDetail(selectedStatement.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Matching failed')
    } finally { setMatching(false) }
  }

  const handleUpload = async () => {
    if (!uploadFile || !uploadBankAccount) return
    setUploading(true)
    setUploadError(null)
    try {
      const formData = new FormData()
      formData.append('file', uploadFile)
      // Backend reads 'bank_account_id' — sending 'bank_account' produced the
      // "bank_account_id is required" failure (key mismatch, not the dropdown
      // binding). 2026-06-08.
      formData.append('bank_account_id', uploadBankAccount)
      const result = await importBankStatement(formData)
      setShowUpload(false)
      setUploadFile(null)
      await loadStatements()
      await loadStatementDetail(result.id)
    } catch (err) {
      setUploadError(err instanceof Error ? err.message : 'Upload failed')
    } finally { setUploading(false) }
  }

  const openMatchModal = async (line: BankStatementLine) => {
    setMatchingLine(line)
    setSelectedPaymentId('')
    setShowMatchModal(true)
    try {
      const res = await getPayments({ status: 'confirmed', page_size: '100' })
      setUnmatchedPayments(res.results)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load payments for matching')
    }
  }

  const handleManualMatch = async () => {
    if (!matchingLine || !selectedPaymentId) return
    setSaving(true)
    try {
      await matchStatementLine(matchingLine.id, { payment_id: selectedPaymentId })
      setShowMatchModal(false)
      if (selectedStatement) await loadStatementDetail(selectedStatement.id)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Match failed')
    } finally { setSaving(false) }
  }

  const getMatchStatusColor = (status: string) => {
    switch (status) {
      case 'matched':      return 'bg-[#ECFDF5] text-[#059669] border border-[#A7F3D0]'
      case 'auto_matched': return 'bg-[#EFF6FF] text-[#2563EB] border border-[#BFDBFE]'
      case 'unmatched':    return 'bg-[#FEF2F2] text-[#DC2626] border border-[#FEE2E2]'
      case 'excluded':     return 'bg-[#F3F4F6] text-[#9CA3AF] border border-[#E5E7EB]'
      default:             return 'bg-[#F3F4F6] text-[#9CA3AF] border border-[#E5E7EB]'
    }
  }

  return (
    <div className="flex flex-col min-h-screen">
      <TopBar
        title="Bank Reconciliation"
        breadcrumbs={[{ label: 'Finance' }, { label: 'Bank Reconciliation' }]}
        actions={
          <div className="flex items-center gap-2">
            {/* RECON-004: surface the account picker on the panel header
                beside Upload Statement. ARIA's guidance refers to choosing
                the "Bank Account" here; selecting it pre-fills the upload
                dialog. Same validated dropdown of configured accounts —
                never a free-text account number. */}
            <Select
              aria-label="Bank Account"
              value={uploadBankAccount}
              onChange={(e) => setUploadBankAccount(e.target.value)}
              disabled={bankAccountsLoading || bankAccounts.length === 0}
              className="h-9 w-56 text-sm"
            >
              <option value="">Bank Account…</option>
              {bankAccounts.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.account_name} — {b.bank_name}
                </option>
              ))}
            </Select>
            <Button
              variant="accent"
              size="sm"
              leftIcon={<Upload className="w-3.5 h-3.5" />}
              onClick={() => setShowUpload(true)}
            >
              Upload Statement
            </Button>
          </div>
        }
      />

      <div className="flex-1 p-6 space-y-6">
        {error && (
          <div className="bg-[#FEF2F2] border border-[#FEE2E2] rounded-lg p-3 flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-[#DC2626] flex-shrink-0" />
            <p className="text-[#DC2626] text-sm">{error}</p>
            <button aria-label="Dismiss error" onClick={() => setError(null)} className="ml-auto text-[#9CA3AF] hover:text-[#374151]">×</button>
          </div>
        )}

        {/* Bank Accounts Overview */}
        <Card>
          <CardHeader>
            <CardTitle>Bank Accounts</CardTitle>
          </CardHeader>
          <CardContent className="p-0">
            {bankAccountsLoading ? (
              <LoadingTable rows={3} cols={5} />
            ) : (
              <div className="overflow-x-auto">
                <table className="w-full text-sm border-collapse">
                  <thead className="bg-[#F3F4F6] border-b-2 border-[#E5E7EB]">
                    <tr>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-[#374151] uppercase tracking-wider">Account</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-[#374151] uppercase tracking-wider">Bank</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-[#374151] uppercase tracking-wider hidden md:table-cell">Account Number</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-[#374151] uppercase tracking-wider">Book/GL Balance</th>
                      <th className="px-4 py-3 text-right text-xs font-semibold text-[#374151] uppercase tracking-wider hidden md:table-cell">Statement Balance</th>
                      <th className="px-4 py-3 text-left text-xs font-semibold text-[#374151] uppercase tracking-wider hidden lg:table-cell">Last Reconciled</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-[#E5E7EB] bg-white">
                    {bankAccounts.length === 0 ? (
                      <tr>
                        <td colSpan={5} className="px-4 py-8 text-center text-[#6B7280] text-sm">
                          No bank accounts configured
                        </td>
                      </tr>
                    ) : (
                      bankAccounts.map((account) => (
                        // RECON-003: rows are read-only — no onClick wired —
                        // so drop the hover-bg and the implied cursor
                        // affordance. If we later add row-click filtering of
                        // the Statements panel, restore `hover:bg-[#FFF7ED]
                        // cursor-pointer`.
                        <tr key={account.id} className="table-row-alt cursor-default">
                          <td className="px-4 py-3 text-[#111827] font-medium">
                            <div className="flex items-center gap-2">
                              <Landmark className="w-4 h-4 text-[#9CA3AF]" />
                              {account.account_name}
                            </div>
                          </td>
                          <td className="px-4 py-3 text-[#6B7280] text-xs">
                            {account.bank_name_display || account.bank_name || '—'}
                          </td>
                          <td className="px-4 py-3 text-[#9CA3AF] text-xs font-mono hidden md:table-cell">
                            {account.account_number_display || account.account_number || '—'}
                          </td>
                          <td className="px-4 py-3 text-right font-mono-nums">
                            <span className={parseAmount(account.book_balance || '0') >= 0 ? 'text-[#059669]' : 'text-[#DC2626]'}>
                              {fmt(account.book_balance || '0', account.currency)}
                            </span>
                          </td>
                          <td className="px-4 py-3 text-right font-mono-nums hidden md:table-cell">
                            {account.statement_balance == null
                              ? <span className="text-[#9CA3AF]">—</span>
                              : <span className="text-[#374151]">{fmt(account.statement_balance, account.currency)}</span>}
                            {account.statement_as_of && (
                              <div className="text-[10px] text-[#9CA3AF]">{formatDate(account.statement_as_of)}</div>
                            )}
                          </td>
                          <td className="px-4 py-3 text-[#9CA3AF] text-xs hidden lg:table-cell">
                            {account.last_reconciled_date
                              ? formatDate(account.last_reconciled_date)
                              : <span className="text-[#D97706]">Never reconciled</span>}
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Statements List + Detail */}
        <div className="grid grid-cols-1 xl:grid-cols-3 gap-6">
          {/* Statements list */}
          <Card className="xl:col-span-1">
            <CardHeader className="flex flex-row items-center justify-between">
              <CardTitle>Statements</CardTitle>
              <button aria-label="Refresh statements" onClick={loadStatements} className="text-[#9CA3AF] hover:text-[#374151] transition-colors">
                <RefreshCw className="w-4 h-4" />
              </button>
            </CardHeader>
            <CardContent className="p-0">
              {statementsLoading ? (
                <LoadingTable rows={4} cols={2} />
              ) : statements.length === 0 ? (
                <div className="py-8 text-center">
                  <p className="text-[#6B7280] text-sm">No statements uploaded</p>
                  <Button
                    variant="accent"
                    size="sm"
                    className="mt-3"
                    leftIcon={<Upload className="w-3.5 h-3.5" />}
                    onClick={() => setShowUpload(true)}
                  >
                    Upload First Statement
                  </Button>
                </div>
              ) : (
                <div className="divide-y divide-[#E5E7EB]">
                  {statements.map((stmt) => (
                    <button
                      key={stmt.id}
                      onClick={() => loadStatementDetail(stmt.id)}
                      className={cn(
                        'w-full text-left px-4 py-3 hover:bg-[#F9FAFB] transition-colors',
                        selectedStatement?.id === stmt.id && 'bg-[#FFF7ED] border-l-2 border-[#F07F00]'
                      )}
                    >
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-sm font-medium text-[#111827]">{stmt.statement_number}</span>
                        <StatusBadge status={stmt.status} />
                      </div>
                      <p className="text-xs text-[#6B7280]">{stmt.bank_account_name}</p>
                      <div className="flex items-center justify-between mt-1">
                        <p className="text-xs text-[#9CA3AF]">{formatDate(stmt.statement_date)}</p>
                        <p className="text-xs text-[#9CA3AF]">{stmt.line_count} lines</p>
                      </div>
                    </button>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>

          {/* Statement Detail */}
          <Card className="xl:col-span-2">
            <CardHeader className="flex flex-row items-center justify-between">
              <div>
                <CardTitle>
                  {selectedStatement ? selectedStatement.statement_number : 'Statement Lines'}
                </CardTitle>
                {selectedStatement && (
                  <p className="text-xs text-[#9CA3AF] mt-0.5">
                    {selectedStatement.bank_account_name} — {selectedStatement.bank_name}
                  </p>
                )}
              </div>
              {selectedStatement && (
                <div className="flex items-center gap-2">
                  {matchResult && (
                    <span className="text-xs text-[#6B7280]">
                      ✓ {matchResult.matched} matched, {matchResult.unmatched} unmatched
                    </span>
                  )}
                  <Button
                    variant="secondary"
                    size="sm"
                    leftIcon={matching ? <LoadingSpinner size="sm" /> : <Zap className="w-3.5 h-3.5" />}
                    onClick={handleRunMatching}
                    disabled={matching}
                  >
                    Auto-Match
                  </Button>
                </div>
              )}
            </CardHeader>
            <CardContent className="p-0">
              {!selectedStatement && !statementLoading ? (
                <div className="py-12 text-center">
                  <Landmark className="w-8 h-8 text-[#D1D5DB] mx-auto mb-2" />
                  <p className="text-[#6B7280] text-sm">Select a statement to view lines</p>
                </div>
              ) : statementLoading ? (
                <LoadingTable rows={6} cols={5} />
              ) : selectedStatement && (
                <>
                  {/* Statement summary */}
                  <div className="px-4 py-3 bg-[#F9FAFB] border-b border-[#E5E7EB] flex flex-wrap gap-4">
                    <div>
                      <p className="text-xs text-[#9CA3AF]">Opening</p>
                      <p className="text-sm font-semibold text-[#111827] font-mono-nums">
                        {fmt(selectedStatement.opening_balance)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[#9CA3AF]">Closing</p>
                      <p className="text-sm font-semibold text-[#111827] font-mono-nums">
                        {fmt(selectedStatement.closing_balance)}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[#9CA3AF]">Lines</p>
                      <p className="text-sm font-semibold text-[#111827]">{selectedStatement.line_count}</p>
                    </div>
                    <div>
                      <p className="text-xs text-[#9CA3AF]">Matched</p>
                      <p className="text-sm font-semibold text-[#059669]">
                        {selectedStatement.lines.filter(l => l.match_status === 'matched' || l.match_status === 'auto_matched').length}
                      </p>
                    </div>
                    <div>
                      <p className="text-xs text-[#9CA3AF]">Unmatched</p>
                      <p className="text-sm font-semibold text-[#DC2626]">
                        {selectedStatement.lines.filter(l => l.match_status === 'unmatched').length}
                      </p>
                    </div>
                  </div>

                  {/* Date filter — view only the transactions in a chosen day
                      or range (Lefika Basotli, 14 Aug 2026). */}
                  <div className="px-4 py-2.5 border-b border-[#E5E7EB] flex flex-wrap items-center gap-2">
                    <span className="text-xs font-medium text-[#6B7280]">Filter by date</span>
                    <input
                      type="date"
                      value={lineFrom}
                      onChange={(e) => setLineFrom(e.target.value)}
                      aria-label="From date"
                      className="rounded border border-[#E5E7EB] px-2 py-1 text-xs text-[#374151]"
                    />
                    <span className="text-xs text-[#9CA3AF]">to</span>
                    <input
                      type="date"
                      value={lineTo}
                      onChange={(e) => setLineTo(e.target.value)}
                      aria-label="To date"
                      className="rounded border border-[#E5E7EB] px-2 py-1 text-xs text-[#374151]"
                    />
                    {dateFilterOn && (
                      <>
                        <button
                          onClick={() => { setLineFrom(''); setLineTo('') }}
                          className="text-xs text-[#F07F00] hover:text-[#CC6C00] transition-colors"
                        >
                          Clear
                        </button>
                        <span className="text-xs text-[#9CA3AF] ml-auto">
                          Showing {visibleLines.length} of {selectedStatement.lines.length}
                        </span>
                      </>
                    )}
                  </div>

                  <div className="overflow-x-auto max-h-[480px] overflow-y-auto">
                    <table className="w-full text-sm border-collapse">
                      <thead className="bg-[#F3F4F6] border-b-2 border-[#E5E7EB] sticky top-0">
                        <tr>
                          <th className="px-4 py-2.5 text-left text-xs font-semibold text-[#374151] uppercase tracking-wider">Date</th>
                          <th className="px-4 py-2.5 text-left text-xs font-semibold text-[#374151] uppercase tracking-wider">Description</th>
                          <th className="px-4 py-2.5 text-left text-xs font-semibold text-[#374151] uppercase tracking-wider hidden md:table-cell">Reference</th>
                          <th className="px-4 py-2.5 text-right text-xs font-semibold text-[#374151] uppercase tracking-wider">Amount</th>
                          <th className="px-4 py-2.5 text-left text-xs font-semibold text-[#374151] uppercase tracking-wider">Status</th>
                          <th className="px-4 py-2.5 text-center text-xs font-semibold text-[#374151] uppercase tracking-wider">Action</th>
                        </tr>
                      </thead>
                      <tbody className="divide-y divide-[#E5E7EB] bg-white">
                        {visibleLines.length === 0 ? (
                          <tr>
                            <td colSpan={6} className="px-4 py-8 text-center text-[#6B7280] text-sm">
                              {dateFilterOn && selectedStatement.lines.length > 0
                                ? 'No transactions in this date range'
                                : 'No lines in this statement'}
                            </td>
                          </tr>
                        ) : (
                          visibleLines.map((line) => (
                            <tr key={line.id} className="table-row-alt hover:bg-[#FFF7ED] transition-colors">
                              <td className="px-4 py-2.5 text-[#6B7280] text-xs whitespace-nowrap">
                                {formatDate(line.transaction_date)}
                              </td>
                              <td className="px-4 py-2.5 text-[#374151] max-w-[200px] truncate">
                                {line.description}
                                {line.matched_payment_number && (
                                  <span className="ml-1 text-xs text-[#059669]">
                                    → {line.matched_payment_number}
                                  </span>
                                )}
                                {line.matched_je_number && (
                                  <span className="ml-1 text-xs text-[#2563EB]">
                                    → {line.matched_je_number}
                                  </span>
                                )}
                              </td>
                              <td className="px-4 py-2.5 text-[#9CA3AF] text-xs font-mono hidden md:table-cell">
                                {line.reference || '—'}
                              </td>
                              <td className={cn(
                                'px-4 py-2.5 text-right font-mono-nums text-sm font-medium',
                                parseAmount(line.amount) >= 0 ? 'text-[#059669]' : 'text-[#DC2626]'
                              )}>
                                {fmt(line.amount)}
                              </td>
                              <td className="px-4 py-2.5">
                                <span className={cn(
                                  'inline-flex items-center px-2 py-0.5 text-xs font-medium rounded-full',
                                  getMatchStatusColor(line.match_status)
                                )}>
                                  {line.match_status?.replace(/_/g, ' ')}
                                </span>
                                {line.match_confidence > 0 && line.match_status === 'auto_matched' && (
                                  <span className="ml-1 text-xs text-[#9CA3AF]">
                                    {(line.match_confidence * 100).toFixed(0)}%
                                  </span>
                                )}
                              </td>
                              {/* RECON-001 (critical): the floating ARIA
                                  bubble (z-50, fixed bottom-right) was
                                  swallowing clicks on the Match button on
                                  bottom-of-table rows at narrow viewports
                                  (e.g. 987px with sidebar expanded). Pin
                                  this TD's stacking context above the
                                  ARIA layer with `relative z-[60]` so the
                                  button always receives pointer events,
                                  regardless of viewport width. */}
                              <td className="px-4 py-2.5 text-center relative z-[60]">
                                {line.match_status === 'unmatched' && (
                                  <button
                                    onClick={() => openMatchModal(line)}
                                    className="text-xs text-[#F07F00] hover:text-[#CC6C00] transition-colors flex items-center gap-1 mx-auto relative z-[60]"
                                  >
                                    <Link2 className="w-3 h-3" />
                                    Match
                                  </button>
                                )}
                              </td>
                            </tr>
                          ))
                        )}
                      </tbody>
                    </table>
                  </div>
                </>
              )}
            </CardContent>
          </Card>
        </div>
      </div>

      {/* Upload Modal */}
      <Modal
        open={showUpload}
        onOpenChange={setShowUpload}
        title="Upload Bank Statement"
        description="Upload the bank's CSV or Excel (.xlsx) statement file"
        size="sm"
      >
        <ModalBody className="space-y-4">
          {uploadError && (
            <div className="bg-[#FEF2F2] border border-[#FEE2E2] rounded-lg p-3 flex items-center gap-2">
              <AlertCircle className="w-4 h-4 text-[#DC2626] flex-shrink-0" />
              <p className="text-[#DC2626] text-xs">{uploadError}</p>
            </div>
          )}
          <FormField label="Bank Account" required>
            <Select
              value={uploadBankAccount}
              onChange={(e) => setUploadBankAccount(e.target.value)}
            >
              <option value="">Select bank account...</option>
              {bankAccounts.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.account_name} - {b.bank_name}
                </option>
              ))}
            </Select>
          </FormField>
          <FormField label="Statement File" required>
            <div className="border-2 border-dashed border-[#D1D5DB] rounded-lg p-6 text-center hover:border-[#F07F00] transition-colors">
              <input
                type="file"
                accept=".csv,.txt,.xlsx,.xlsm"
                onChange={(e) => setUploadFile(e.target.files?.[0] || null)}
                className="hidden"
                id="statement-file"
              />
              <label htmlFor="statement-file" className="cursor-pointer">
                {uploadFile ? (
                  <div>
                    <CheckCircle className="w-6 h-6 text-[#059669] mx-auto mb-1" />
                    <p className="text-sm text-[#059669]">{uploadFile.name}</p>
                    <p className="text-xs text-[#9CA3AF] mt-0.5">
                      {(uploadFile.size / 1024).toFixed(1)} KB
                    </p>
                  </div>
                ) : (
                  <div>
                    <Upload className="w-6 h-6 text-[#9CA3AF] mx-auto mb-1" />
                    <p className="text-sm text-[#6B7280]">Click to select file</p>
                    <p className="text-xs text-[#9CA3AF] mt-0.5">CSV or Excel (.xlsx)</p>
                  </div>
                )}
              </label>
            </div>
          </FormField>
        </ModalBody>
        <ModalFooter>
          <Button variant="secondary" size="sm" onClick={() => setShowUpload(false)} disabled={uploading}>
            Cancel
          </Button>
          <Button
            variant="accent"
            size="sm"
            loading={uploading}
            disabled={!uploadFile || !uploadBankAccount}
            onClick={handleUpload}
          >
            Upload
          </Button>
        </ModalFooter>
      </Modal>

      {/* Manual Match Modal */}
      <Modal
        open={showMatchModal}
        onOpenChange={setShowMatchModal}
        title="Match Statement Line"
        description={matchingLine ? `Matching: ${matchingLine.description} (${fmt(matchingLine.amount)})` : ''}
        size="md"
      >
        <ModalBody className="space-y-4">
          <div className="bg-[#F9FAFB] rounded-lg p-3 border border-[#E5E7EB]">
            <p className="text-xs text-[#9CA3AF] uppercase tracking-wider mb-2">Statement Line</p>
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-[#111827]">{matchingLine?.description}</p>
                <p className="text-xs text-[#6B7280] mt-0.5">
                  {matchingLine && formatDate(matchingLine.transaction_date)} · Ref: {matchingLine?.reference || '—'}
                </p>
              </div>
              <p className={cn(
                'font-mono-nums font-bold',
                parseAmount(matchingLine?.amount || '0') >= 0 ? 'text-[#059669]' : 'text-[#DC2626]'
              )}>
                {fmt(matchingLine?.amount || '0')}
              </p>
            </div>
          </div>

          <FormField label="Match to Payment">
            <Select value={selectedPaymentId} onChange={(e) => setSelectedPaymentId(e.target.value)}>
              <option value="">Select payment...</option>
              {unmatchedPayments.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.payment_number} — {p.contact_name} — {fmt(p.amount, p.currency)} ({formatDate(p.payment_date)})
                </option>
              ))}
            </Select>
          </FormField>
        </ModalBody>
        <ModalFooter>
          <Button variant="secondary" size="sm" onClick={() => setShowMatchModal(false)} disabled={saving}>
            Cancel
          </Button>
          <Button
            variant="accent"
            size="sm"
            loading={saving}
            disabled={!selectedPaymentId}
            onClick={handleManualMatch}
          >
            Match
          </Button>
        </ModalFooter>
      </Modal>
    </div>
  )
}
