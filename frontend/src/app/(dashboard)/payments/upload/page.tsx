'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { getToken, getBankAccounts, downloadPaymentTemplate, previewPaymentUpload, bulkUploadPayments } from '@/lib/api'
import type { BankAccount, PaymentUploadPreview, PaymentUploadResult } from '@/lib/api'
import { TopBar } from '@/components/layout/TopBar'
import { Card, CardHeader, CardTitle, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { FormField, Select } from '@/components/ui/input'
import { UploadCloud, Download, AlertCircle, CheckCircle2 } from 'lucide-react'

export default function BulkPaymentUploadPage() {
  const router = useRouter()
  const [banks, setBanks] = useState<BankAccount[]>([])
  const [bankAccount, setBankAccount] = useState('')
  const [text, setText] = useState('')
  const [preview, setPreview] = useState<PaymentUploadPreview | null>(null)
  const [result, setResult] = useState<PaymentUploadResult | null>(null)
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    if (!getToken()) { router.replace('/login'); return }
    getBankAccounts().then((b) => {
      setBanks(b.results)
      if (b.results.length) setBankAccount(b.results[0].id)
    }).catch(() => {})
  }, [router])

  const onFile = (f: File | null) => {
    if (!f) return
    const r = new FileReader()
    r.onload = () => setText(String(r.result || ''))
    r.readAsText(f)
  }

  const analyse = async () => {
    setErr(null); setResult(null); setBusy(true)
    try { setPreview(await previewPaymentUpload(text)) }
    catch (e) { setErr(e instanceof Error ? e.message : 'Could not read the sheet') }
    finally { setBusy(false) }
  }

  const create = async () => {
    if (!bankAccount) { setErr('Pick the paying bank account first.'); return }
    setErr(null); setBusy(true)
    try {
      const res = await bulkUploadPayments(text, bankAccount, true)
      setResult(res); setPreview(null)
    } catch (e) { setErr(e instanceof Error ? e.message : 'Upload failed') }
    finally { setBusy(false) }
  }

  return (
    <div className="flex flex-col min-h-screen">
      <TopBar title="Bulk Payment Upload"
        breadcrumbs={[{ label: 'Payments', href: '/payments' }, { label: 'Bulk Upload' }]} />
      <div className="flex-1 p-6 max-w-3xl mx-auto w-full space-y-5">

        {err && (
          <div className="bg-[#FEF2F2] border border-[#FEE2E2] rounded-xl p-4 flex items-center gap-3">
            <AlertCircle className="w-5 h-5 text-[#DC2626] flex-shrink-0" /><p className="text-[#DC2626] text-sm">{err}</p>
          </div>
        )}

        <Card>
          <CardHeader><CardTitle>Upload a sheet of payments</CardTitle></CardHeader>
          <CardContent className="space-y-4">
            <p className="text-sm text-[#6B7280]">
              Paste rows from your sheet (any column order) or upload a CSV. We map the columns
              for you — <b>vendor, amount, currency, method, reference</b> — and create a <b>draft</b> payment
              for each, then route them through the normal approval (2 FMs + CFO). Nothing is paid here.
            </p>

            <div className="flex flex-wrap gap-3 items-center">
              <Button variant="outline" onClick={() => downloadPaymentTemplate().catch(() => setErr('Template download failed'))}>
                <Download className="w-4 h-4 mr-1" /> Download the template
              </Button>
              <label className="inline-flex items-center gap-2 text-sm cursor-pointer px-3 py-2 rounded-lg border border-[#E5E7EB]">
                <UploadCloud className="w-4 h-4" /> Choose CSV file
                <input type="file" accept=".csv,.tsv,.txt" className="hidden"
                  onChange={(e) => onFile(e.target.files?.[0] || null)} />
              </label>
            </div>

            <FormField label="Paying bank account" required>
              <Select value={bankAccount} onChange={(e) => setBankAccount(e.target.value)}>
                <option value="">Select bank account…</option>
                {banks.map((b) => <option key={b.id} value={b.id}>{b.account_name} — {b.bank_name} ({b.currency})</option>)}
              </Select>
            </FormField>

            <textarea value={text} onChange={(e) => { setText(e.target.value); setPreview(null); setResult(null) }} rows={9}
              placeholder="Paste rows here — e.g. Vendor Name, Amount, Currency, Payment Method, Reference"
              className="w-full font-mono text-xs p-3 rounded-lg border border-[#E5E7EB]" />

            <div className="flex gap-3">
              <Button variant="outline" disabled={busy || !text.trim()} onClick={analyse}>
                {busy ? 'Reading…' : 'Analyse (map columns)'}
              </Button>
              {preview && preview.ok_count > 0 && (
                <Button disabled={busy} onClick={create}>
                  Create {preview.ok_count} draft payment{preview.ok_count === 1 ? '' : 's'}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>

        {preview && (
          <Card>
            <CardHeader><CardTitle>
              Preview — {preview.ok_count} ready, {preview.error_count} need fixing
              <span className="ml-2 text-xs font-normal text-[#9CA3AF]">columns mapped via {preview.via}</span>
            </CardTitle></CardHeader>
            <CardContent className="p-0">
              <table className="w-full text-sm">
                <thead><tr className="text-left text-[#6B7280]">
                  <th className="p-2">Vendor</th><th className="p-2 text-right">Amount</th>
                  <th className="p-2">Method</th><th className="p-2">Status</th>
                </tr></thead>
                <tbody>
                  {preview.rows.map((r, i) => (
                    <tr key={i} className="border-t border-[#F0F0F0]">
                      <td className="p-2">{r.vendor}</td>
                      <td className="p-2 text-right">{r.amount ? `${r.currency} ${r.amount}` : '—'}</td>
                      <td className="p-2">{r.method}</td>
                      <td className="p-2">{r.ok
                        ? <span className="text-[#059669]">ready</span>
                        : <span className="text-[#DC2626]">{r.error}</span>}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </CardContent>
          </Card>
        )}

        {result && (
          <Card>
            <CardHeader><CardTitle className="flex items-center gap-2">
              <CheckCircle2 className="w-5 h-5 text-[#059669]" />
              {result.created_count} draft payment{result.created_count === 1 ? '' : 's'} created
            </CardTitle></CardHeader>
            <CardContent className="space-y-3">
              <p className="text-sm text-[#6B7280]">
                They're now in <b>Payment Approvals</b> awaiting the dual-control (FM + CFO) sign-off. {result.error_count > 0 && `${result.error_count} row(s) were skipped.`}
              </p>
              {result.created.map((c) => (
                <div key={c.id} className="text-sm flex justify-between border-b border-[#F0F0F0] py-1">
                  <span>{c.vendor} <span className="font-mono text-[#CC6C00]">{c.payment_number}</span></span>
                  <span className="font-medium">{c.amount}</span>
                </div>
              ))}
              {result.errors.map((e, i) => (
                <div key={i} className="text-sm text-[#DC2626]">{e.vendor}: {e.error}</div>
              ))}
              <Button variant="outline" onClick={() => router.push('/payments/approvals')}>Go to Payment Approvals</Button>
            </CardContent>
          </Card>
        )}
      </div>
    </div>
  )
}
