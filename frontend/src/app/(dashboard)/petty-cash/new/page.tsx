'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  getToken,
  getPettyCashLocations,
  createPettyCashVoucher,
  uploadPettyCashVoucherReceipt,
  type PettyCashLocation,
} from '@/lib/api'
import { TopBar } from '@/components/layout/TopBar'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { AlertTriangle, ArrowLeft, Save, Paperclip, X } from 'lucide-react'
import Link from 'next/link'

// Local calendar date (YYYY-MM-DD). NOT toISOString() — that converts to UTC
// first, so in Botswana (UTC+2) it returns *yesterday* between midnight and
// 02:00, silently backdating the voucher.
function todayISO() {
  const d = new Date()
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`
}

// NaN-safe Pula formatter (a null/empty figure from a new location must show
// "—", never "PNaN").
function fmtP(v: string | number | null | undefined): string {
  if (v === null || v === undefined || v === '') return '—'
  const n = typeof v === 'number' ? v : Number(v)
  if (!isFinite(n)) return '—'
  return n.toLocaleString('en-GB', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function NewPettyCashVoucherPage() {
  const router = useRouter()
  const [locations, setLocations] = useState<PettyCashLocation[]>([])
  const [loadingMeta, setLoadingMeta] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  // Form state. No GL account here: the person raising the voucher does not
  // code it — the petty-cash finance team sets the expense account when they
  // post it (CFO directive 2026-08-10).
  const [locationId, setLocationId] = useState('')
  const [voucherDate, setVoucherDate] = useState(todayISO())
  const [payee, setPayee] = useState('')
  const [amount, setAmount] = useState('')
  const [description, setDescription] = useState('')
  const [receiptReference, setReceiptReference] = useState('')
  const [receiptFiles, setReceiptFiles] = useState<File[]>([])

  useEffect(() => {
    if (!getToken()) { router.replace('/login'); return }
    void (async () => {
      try {
        const locsRes = await getPettyCashLocations()
        const active = locsRes.results.filter((l) => l.is_active)
        setLocations(active)
        // Auto-select only when there is exactly one ACTIVE tin (never silently
        // pin an inactive location the dropdown can't even show).
        if (active.length === 1) setLocationId(active[0].id)
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load setup data')
      } finally {
        setLoadingMeta(false)
      }
    })()
  }, [router])

  const selectedLoc = locations.find((l) => l.id === locationId) || null
  const available = selectedLoc ? Number(selectedLoc.available_for_voucher) : 0
  const amountNum = Number(amount) || 0
  const wouldOverdraw = amountNum > 0 && amountNum > available

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    if (!locationId || !payee || !amount || !description) {
      setError('Please fill in all required fields.')
      return
    }
    if (amountNum <= 0) {
      setError('Amount must be greater than zero.')
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const v = await createPettyCashVoucher({
        location: locationId,
        voucher_date: voucherDate,
        payee: payee.trim(),
        amount: amountNum.toFixed(2),
        description: description.trim(),
        receipt_reference: receiptReference.trim(),
        receipt_attached: receiptFiles.length > 0,
      })
      // Upload the receipts against the freshly-created voucher.
      for (const f of receiptFiles) {
        try {
          await uploadPettyCashVoucherReceipt(v.id, f)
        } catch (upErr) {
          // Voucher saved; a receipt failed — send them to the voucher page to retry there.
          setError(`Voucher saved, but a receipt didn't upload: ${upErr instanceof Error ? upErr.message : 'error'}. Attach it on the next screen.`)
        }
      }
      router.replace(`/petty-cash/${v.id}`)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create voucher')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="flex flex-col min-h-screen">
      <TopBar
        title="New Petty Cash Voucher"
        breadcrumbs={[
          { label: 'Petty Cash', href: '/petty-cash' },
          { label: 'New Voucher' },
        ]}
        actions={
          <Link href="/petty-cash">
            <Button
              variant="outline" size="sm"
              leftIcon={<ArrowLeft className="w-3.5 h-3.5" />}
            >
              Back
            </Button>
          </Link>
        }
      />

      <div className="flex-1 p-6 max-w-3xl">
        {error && (
          <div className="mb-4 bg-[#FEF2F2] border border-[#FEE2E2] rounded-lg p-3 flex items-center gap-2">
            <AlertTriangle className="w-4 h-4 text-[#DC2626]" />
            <p className="text-[#DC2626] text-sm">{error}</p>
          </div>
        )}

        <form onSubmit={handleSubmit}>
          <Card>
            <CardHeader>
              <CardTitle>Voucher details</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-[#374151] mb-1.5">
                    Location *
                  </label>
                  <select
                    value={locationId}
                    onChange={(e) => setLocationId(e.target.value)}
                    disabled={loadingMeta}
                    className="w-full h-10 bg-white border border-[#D1D5DB] rounded-md px-3 text-sm"
                    required
                  >
                    <option value="">Select location…</option>
                    {locations.map((l) => (
                      <option key={l.id} value={l.id}>
                        {l.name} — Available P{fmtP(l.available_for_voucher)}
                      </option>
                    ))}
                  </select>

                  {selectedLoc?.access_notice && (
                    <div className="mt-3 flex items-start gap-2 p-3 rounded-md bg-[#FEF2F2] border-2 border-[#DC2626]">
                      <AlertTriangle className="w-5 h-5 text-[#DC2626] flex-shrink-0 mt-0.5" />
                      <p className="text-sm text-[#991B1B] font-medium leading-relaxed">
                        {selectedLoc.access_notice.text}
                      </p>
                    </div>
                  )}
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#374151] mb-1.5">
                    Voucher date *
                  </label>
                  <input
                    type="date"
                    value={voucherDate}
                    onChange={(e) => setVoucherDate(e.target.value)}
                    className="w-full h-10 bg-white border border-[#D1D5DB] rounded-md px-3 text-sm"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#374151] mb-1.5">
                    Amount (Pula) *
                  </label>
                  <input
                    type="number"
                    step="0.01" min="0.01"
                    value={amount}
                    onChange={(e) => setAmount(e.target.value)}
                    placeholder="e.g. 250.00"
                    className="w-full h-10 bg-white border border-[#D1D5DB] rounded-md px-3 text-sm font-mono tabular-nums"
                    required
                  />
                  {wouldOverdraw && selectedLoc && (
                    <p className="text-[11px] text-[#B91C1C] mt-1">
                      Exceeds available float (P{fmtP(selectedLoc.available_for_voucher)}). Submission will be blocked.
                    </p>
                  )}
                </div>

                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-[#374151] mb-1.5">
                    Payee *
                  </label>
                  <input
                    type="text"
                    value={payee}
                    onChange={(e) => setPayee(e.target.value)}
                    placeholder="Who received the cash"
                    maxLength={200}
                    className="w-full h-10 bg-white border border-[#D1D5DB] rounded-md px-3 text-sm"
                    required
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-[#374151] mb-1.5">
                    Description *
                  </label>
                  <textarea
                    value={description}
                    onChange={(e) => setDescription(e.target.value)}
                    placeholder="Narrative — what was the cash spent on?"
                    rows={3}
                    className="w-full bg-white border border-[#D1D5DB] rounded-md px-3 py-2 text-sm"
                    required
                  />
                </div>

                <div>
                  <label className="block text-xs font-medium text-[#374151] mb-1.5">
                    Receipt reference
                  </label>
                  <input
                    type="text"
                    value={receiptReference}
                    onChange={(e) => setReceiptReference(e.target.value)}
                    placeholder="Till slip or invoice number"
                    maxLength={120}
                    className="w-full h-10 bg-white border border-[#D1D5DB] rounded-md px-3 text-sm"
                  />
                </div>

                <div className="md:col-span-2">
                  <label className="block text-xs font-medium text-[#374151] mb-1.5">
                    Receipt <span className="text-[#9CA3AF]">— attach the slip (photo or PDF)</span>
                  </label>
                  <label className="inline-flex items-center gap-2 text-sm font-medium text-white bg-[#F07F00] hover:bg-[#c96700] rounded-md px-3 py-2 cursor-pointer">
                    <Paperclip className="w-4 h-4" />
                    Attach a receipt
                    <input
                      type="file" accept="image/*,application/pdf" multiple className="hidden"
                      onChange={(e) => {
                        const files = Array.from(e.target.files || [])
                        e.target.value = ''
                        if (files.length) setReceiptFiles((cur) => [...cur, ...files])
                      }}
                    />
                  </label>
                  {receiptFiles.length > 0 && (
                    <div className="mt-2 space-y-1.5">
                      {receiptFiles.map((f, i) => (
                        <div key={i} className="flex items-center justify-between gap-2 text-xs p-2 rounded border border-[#E5E7EB] bg-[#F9FAFB]">
                          <span className="truncate text-[#374151]">{f.name} · {(f.size / 1024).toFixed(0)} KB</span>
                          <button type="button" onClick={() => setReceiptFiles((cur) => cur.filter((_, j) => j !== i))}
                            className="text-[#B91C1C] hover:bg-[#FEF2F2] rounded p-0.5 flex-shrink-0">
                            <X className="w-3.5 h-3.5" />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  <p className="text-[11px] text-[#9CA3AF] mt-1.5">
                    You can also add more receipts after saving, on the voucher page. No more Excel or paper pad.
                  </p>
                </div>
              </div>

              {selectedLoc && (
                <div className="mt-5 p-3 rounded bg-[#F9FAFB] border border-[#E5E7EB]">
                  <p className="text-xs text-[#6B7280]">
                    <strong>{selectedLoc.name}</strong>: cash on hand
                    <span className="font-mono font-semibold text-[#111827]"> P{fmtP(selectedLoc.cash_on_hand)}</span>
                    , available after this voucher
                    <span className="font-mono font-semibold text-[#111827]"> P{fmtP(Math.max(0, available - amountNum))}</span>.
                  </p>
                </div>
              )}
            </CardContent>
          </Card>

          <div className="mt-4 flex justify-end gap-3">
            <Link href="/petty-cash">
              <Button variant="outline" type="button">Cancel</Button>
            </Link>
            <Button
              type="submit"
              disabled={submitting || loadingMeta}
              leftIcon={<Save className="w-4 h-4" />}
            >
              {submitting ? 'Saving…' : 'Save as Draft'}
            </Button>
          </div>
        </form>
      </div>
    </div>
  )
}
