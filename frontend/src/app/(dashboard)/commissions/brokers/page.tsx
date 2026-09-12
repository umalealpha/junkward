'use client'

/**
 * /commissions/brokers — the Broker Commission register.
 *
 * Replaces "Broker Commission - <Month>.xlsm": 28 broker tabs, each with a
 * RealPay transaction report VLOOKUP'd in by hand (Rose Mokgware, 2026-09-08).
 *
 * Two panes. Left: every broker with their live commercial + domestic book.
 * Right: the picked broker's clients, each carrying the LIVE collection status
 * from RealPay — Successful / Failed / Error — which is the whole point of the
 * exercise. Rows can be added and uploaded; only rows a person added can be
 * deleted, because a Graphite row is the book's record, not ours to hide.
 *
 * Brokers write COMMERCIAL and DOMESTIC business only, never Instant (CFO).
 */

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  getToken, listBrokers, getBroker, syncBrokers,
  addBrokerPolicy, deleteBrokerPolicy, uploadBrokerWorkbook, absorbBroker,
} from '@/lib/api'
import type { BrokerListResp, BrokerDetailResp, BrokerRow, BrokerClientRow } from '@/lib/api'
import { TopBar } from '@/components/layout/TopBar'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { ModalPortal } from '@/components/ui/ModalPortal'
import {
  Users, Search, RefreshCw, Upload, Plus, Trash2, AlertTriangle,
  CheckCircle2, XCircle, Clock, HelpCircle, Building2, X, FileSpreadsheet,
} from 'lucide-react'

const NAVY = '#0D1B2A'
const ORANGE = '#F4A623'
const SERIF = '"Book Antiqua", "Palatino Linotype", Palatino, Georgia, serif'

/** One colour per collection outcome, used for the pill AND the tally chips so
 *  the eye learns the mapping once. */
const STATUS_TONE: Record<string, { bg: string; fg: string; icon: typeof CheckCircle2 }> = {
  Successful:            { bg: '#DCFCE7', fg: '#166534', icon: CheckCircle2 },
  Failed:                { bg: '#FEE2E2', fg: '#991B1B', icon: XCircle },
  Error:                 { bg: '#FFEDD5', fg: '#9A3412', icon: AlertTriangle },
  Processing:            { bg: '#DBEAFE', fg: '#1E40AF', icon: Clock },
  Retry:                 { bg: '#DBEAFE', fg: '#1E40AF', icon: RefreshCw },
  Scheduled:             { bg: '#F1F5F9', fg: '#475569', icon: Clock },
  Cancelled:             { bg: '#F1F5F9', fg: '#475569', icon: XCircle },
  Unknown:               { bg: '#FEF9C3', fg: '#854D0E', icon: HelpCircle },
  'No debit in this period': { bg: '#F8FAFC', fg: '#64748B', icon: HelpCircle },
  'No outcome received': { bg: '#FEF9C3', fg: '#854D0E', icon: AlertTriangle },
}
function tone(label: string) {
  return STATUS_TONE[label] || STATUS_TONE['No debit in this period']
}

function money(v: number | undefined | null): string {
  if (v == null || !isFinite(v)) return '—'
  return v.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
}

export default function BrokerCommissionPage() {
  const router = useRouter()
  const [list, setList] = useState<BrokerListResp | null>(null)
  const [picked, setPicked] = useState<string | null>(null)
  const [detail, setDetail] = useState<BrokerDetailResp | null>(null)
  const [q, setQ] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [note, setNote] = useState<string | null>(null)
  const [showAdd, setShowAdd] = useState(false)
  const [showUpload, setShowUpload] = useState(false)
  const [activeOnly, setActiveOnly] = useState(false)
  // A broker sheet pays on ONE month's collections — that is what Finance's
  // "Current Status" column means. Default to this month so the screen opens on
  // something that reconciles, never an all-history mix.
  const [period, setPeriod] = useState(() => {
    const d = new Date()
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}`
  })

  const loadList = useCallback(async () => {
    setLoading(true); setError(null)
    try { setList(await listBrokers()) }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not load the brokers.') }
    finally { setLoading(false) }
  }, [])

  const loadDetail = useCallback(async (id: string, ao: boolean, per: string) => {
    setBusy('detail'); setError(null)
    try { setDetail(await getBroker(id, { activeOnly: ao, period: per })) }
    catch (e) { setError(e instanceof Error ? e.message : 'Could not load that broker.') }
    finally { setBusy(null) }
  }, [])

  useEffect(() => {
    if (!getToken()) { router.replace('/login'); return }
    void loadList()
  }, [loadList, router])

  useEffect(() => { if (picked) void loadDetail(picked, activeOnly, period) },
    [picked, activeOnly, period, loadDetail])

  const brokers = useMemo(() => {
    const rows = list?.brokers || []
    const needle = q.trim().toLowerCase()
    if (!needle) return rows
    return rows.filter(b =>
      b.name.toLowerCase().includes(needle) ||
      b.short_name.toLowerCase().includes(needle) ||
      b.aliases.some(a => a.toLowerCase().includes(needle)))
  }, [list, q])

  async function doSync() {
    setBusy('sync'); setError(null); setNote(null)
    try {
      const r = await syncBrokers()
      setNote(r.configured
        ? `Register refreshed — ${r.created} new broker(s), ${r.aliases} Graphite name(s) linked.`
        : 'Graphite is not reachable from here, so nothing was refreshed.')
      await loadList()
    } catch (e) { setError(e instanceof Error ? e.message : 'The refresh failed.') }
    finally { setBusy(null) }
  }

  async function foldIn(keeperId: string, otherId: string, otherName: string, keepName: string) {
    setBusy('absorb'); setError(null); setNote(null)
    try {
      const r = await absorbBroker(keeperId, otherId)
      setNote(`Folded ${r.absorbed} into ${r.kept} — ${r.aliases_moved} Graphite name(s) `
              + `and ${r.rows_moved} added row(s) moved across.`)
      if (picked === otherId) setPicked(keeperId)
      await loadList()
    } catch (e) {
      setError(e instanceof Error ? e.message : `Could not fold ${otherName} into ${keepName}.`)
    } finally { setBusy(null) }
  }

  async function removeRow(row: BrokerClientRow) {
    if (!picked || !row.id) return
    setBusy(row.policy_number); setError(null)
    try {
      await deleteBrokerPolicy(picked, row.id)
      await loadDetail(picked, activeOnly, period)
      setNote(`Removed ${row.policy_number}.`)
    } catch (e) { setError(e instanceof Error ? e.message : 'Could not remove that row.') }
    finally { setBusy(null) }
  }

  const totals = useMemo(() => {
    const rows = detail?.rows || []
    return {
      collected: rows.reduce((a, r) => a + (r.collected_amount || 0), 0),
      commission: rows.reduce((a, r) => a + (r.commission_payable || 0), 0),
      premium: rows.reduce((a, r) => a + (r.premium || 0), 0),
    }
  }, [detail])

  return (
    <div className="min-h-screen" style={{ background: '#F8F9FB' }}>
      <TopBar title="Broker Commission" />
      <div className="max-w-[1400px] mx-auto px-4 sm:px-6 lg:px-8 py-6">

        {/* Masthead — deliberately editorial, not a stat-tile row. */}
        <div className="flex flex-wrap items-end justify-between gap-4 mb-5">
          <div>
            <h1 className="text-[26px] leading-tight font-bold" style={{ fontFamily: SERIF, color: NAVY }}>
              Broker Commission
            </h1>
            <p className="text-sm mt-1" style={{ color: '#6B7280' }}>
              Every broker and their clients, with the collection result read live from RealPay.
              Commercial and domestic business only.
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="outline" size="sm" onClick={() => setShowUpload(true)}>
              <Upload className="w-4 h-4 mr-1.5" /> Upload workbook
            </Button>
            <Button variant="secondary" size="sm" onClick={doSync} loading={busy === 'sync'} disabled={!!busy}>
              <RefreshCw className="w-4 h-4 mr-1.5" /> Refresh from Graphite
            </Button>
          </div>
        </div>

        {error && (
          <div className="mb-4 rounded-lg px-4 py-3 text-sm flex items-start gap-2"
               style={{ background: '#FEE2E2', color: '#991B1B' }}>
            <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" /> {error}
          </div>
        )}
        {note && (
          <div className="mb-4 rounded-lg px-4 py-3 text-sm flex items-start justify-between gap-2"
               style={{ background: '#DCFCE7', color: '#166534' }}>
            <span className="flex items-start gap-2">
              <CheckCircle2 className="w-4 h-4 mt-0.5 flex-shrink-0" /> {note}
            </span>
            <button onClick={() => setNote(null)} aria-label="Dismiss"><X className="w-4 h-4" /></button>
          </div>
        )}
        {list && !list.graphite_live && (
          <div className="mb-4 rounded-lg px-4 py-3 text-sm flex items-start gap-2"
               style={{ background: '#FEF9C3', color: '#854D0E' }}>
            <AlertTriangle className="w-4 h-4 mt-0.5 flex-shrink-0" />
            Graphite is not reachable, so policy counts and collection results are not shown.
            Nothing here is wrong — it is simply not being read right now.
          </div>
        )}

        <div className="grid grid-cols-1 lg:grid-cols-[340px_1fr] gap-5 items-start">

          {/* ── Broker list ─────────────────────────────────────────────── */}
          <Card className="overflow-hidden">
            <div className="px-3 py-2.5 border-b" style={{ background: NAVY }}>
              <div className="flex items-center gap-2 text-white text-sm font-semibold">
                <Users className="w-4 h-4" style={{ color: ORANGE }} /> Brokers
                {list && <span className="ml-auto text-[11px] font-normal opacity-70">
                  {brokers.length} of {list.brokers.length}
                </span>}
              </div>
            </div>
            <div className="p-2.5 border-b">
              <div className="relative">
                <Search className="w-4 h-4 absolute left-2.5 top-1/2 -translate-y-1/2" style={{ color: '#9CA3AF' }} />
                <input value={q} onChange={e => setQ(e.target.value)} placeholder="Find a broker…"
                       aria-label="Find a broker"
                       className="w-full pl-8 pr-3 py-1.5 text-sm rounded border bg-white" />
              </div>
            </div>
            <div className="max-h-[62vh] overflow-y-auto">
              {loading && <p className="px-3 py-6 text-sm text-center" style={{ color: '#6B7280' }}>Loading…</p>}
              {!loading && brokers.length === 0 && (
                <div className="px-3 py-8 text-center">
                  <Building2 className="w-8 h-8 mx-auto mb-2" style={{ color: '#D1D5DB' }} />
                  <p className="text-sm" style={{ color: '#6B7280' }}>
                    No brokers yet. Press <b>Refresh from Graphite</b> to build the register.
                  </p>
                </div>
              )}
              {brokers.map(b => {
                const on = picked === b.id
                return (
                  <button key={b.id} onClick={() => setPicked(b.id)}
                          className="w-full text-left px-3 py-2.5 border-b transition-colors"
                          style={{ background: on ? ORANGE + '18' : 'transparent',
                                   borderLeft: `3px solid ${on ? ORANGE : 'transparent'}` }}>
                    <div className="flex items-baseline justify-between gap-2">
                      <span className="text-sm font-semibold truncate" style={{ color: NAVY }}>
                        {b.short_name || b.name}
                      </span>
                      <span className="text-[11px] flex-shrink-0" style={{ color: '#6B7280' }}>
                        {b.graphite_policies}
                      </span>
                    </div>
                    <div className="text-[11px] mt-0.5 flex items-center gap-2" style={{ color: '#6B7280' }}>
                      <span>{b.live_policies} live</span>
                      {b.added_rows > 0 && <span style={{ color: ORANGE }}>+{b.added_rows} added</span>}
                      {b.aliases.length > 1 && <span title={b.aliases.join(' · ')}>
                        {b.aliases.length} names merged
                      </span>}
                    </div>
                  </button>
                )
              })}
            </div>
          </Card>

          {/* ── Broker detail ───────────────────────────────────────────── */}
          <div className="min-w-0">
            {!picked && (
              <Card><CardContent className="py-16 text-center">
                <Building2 className="w-10 h-10 mx-auto mb-3" style={{ color: '#D1D5DB' }} />
                <p className="text-sm" style={{ color: '#6B7280' }}>
                  Pick a broker to see their clients and which debits went through.
                </p>
              </CardContent></Card>
            )}

            {picked && detail && (
              <>
                <Card className="mb-4">
                  <CardContent className="py-4">
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0">
                        <h2 className="text-lg font-bold truncate" style={{ fontFamily: SERIF, color: NAVY }}>
                          {detail.broker.name}
                        </h2>
                        {detail.broker.aliases.length > 1 && (
                          <p className="text-[11px] mt-0.5" style={{ color: '#6B7280' }}>
                            Graphite files this broker under {detail.broker.aliases.length} names:{' '}
                            {detail.broker.aliases.join(' · ')}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-2 flex-shrink-0">
                        <label className="flex items-center gap-1.5 text-xs" style={{ color: '#6B7280' }}>
                          Month
                          <input type="month" value={period} aria-label="Commission month"
                                 onChange={e => setPeriod(e.target.value)}
                                 className="border rounded px-2 py-1 text-xs" />
                        </label>
                        <label className="flex items-center gap-1.5 text-xs" style={{ color: '#6B7280' }}>
                          <input type="checkbox" checked={activeOnly}
                                 onChange={e => setActiveOnly(e.target.checked)} />
                          Live policies only
                        </label>
                        <Button size="sm" variant="primary" onClick={() => setShowAdd(true)}>
                          <Plus className="w-4 h-4 mr-1" /> Add policy
                        </Button>
                      </div>
                    </div>

                    {/* Money strip — three figures, sized by importance. */}
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mt-4">
                      {[['Clients', String(detail.count), NAVY],
                        ['Premium', money(totals.premium), NAVY],
                        ['Collected', money(totals.collected), '#166534'],
                        ['Commission payable', money(totals.commission), ORANGE],
                      ].map(([label, val, col]) => (
                        <div key={label} className="rounded-lg px-3 py-2" style={{ background: '#F8F9FB' }}>
                          <div className="text-[10px] uppercase tracking-wider" style={{ color: '#6B7280' }}>{label}</div>
                          <div className="text-base font-bold tabular-nums truncate" style={{ color: col as string }}>{val}</div>
                        </div>
                      ))}
                    </div>

                    {/* Outcome tally — the answer to "who succeeded, who failed". */}
                    <div className="flex flex-wrap gap-1.5 mt-3">
                      {Object.entries(detail.tally).sort((a, b) => b[1] - a[1]).map(([label, n]) => {
                        const t = tone(label); const Icon = t.icon
                        return (
                          <span key={label} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold"
                                style={{ background: t.bg, color: t.fg }}>
                            <Icon className="w-3 h-3" /> {label} · {n}
                          </span>
                        )
                      })}
                    </div>

                    {!detail.status_live && (
                      <p className="text-[11px] mt-3 rounded px-2 py-1.5"
                         style={{ background: '#FEF9C3', color: '#854D0E' }}>
                        Collection results could not be read just now, so every row shows as unknown.
                        That is not the same as “nothing was collected”.
                      </p>
                    )}
                  </CardContent>
                </Card>

                <Card className="overflow-hidden">
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr style={{ background: '#F3F4F6' }}>
                          {['Policy', 'Insured', 'Premium', 'Collected', 'Result', 'Last attempt', ''].map(h => (
                            <th key={h} className="text-left px-3 py-2 text-[11px] uppercase tracking-wider font-semibold"
                                style={{ color: '#6B7280' }}>{h}</th>
                          ))}
                        </tr>
                      </thead>
                      <tbody>
                        {busy === 'detail' && (
                          <tr><td colSpan={7} className="px-3 py-8 text-center text-sm" style={{ color: '#6B7280' }}>Loading…</td></tr>
                        )}
                        {busy !== 'detail' && detail.rows.length === 0 && (
                          <tr><td colSpan={7} className="px-3 py-10 text-center text-sm" style={{ color: '#6B7280' }}>
                            No clients on this broker yet. Add one, or upload their sheet.
                          </td></tr>
                        )}
                        {detail.rows.map(r => {
                          const t = tone(r.status_label); const Icon = t.icon
                          return (
                            <tr key={r.policy_number} className="border-t hover:bg-[#FAFAFA]">
                              <td className="px-3 py-2 font-mono text-[12px] whitespace-nowrap" style={{ color: NAVY }}>
                                {r.policy_number}
                                {r.policy_active === false && (
                                  <span className="ml-1.5 text-[10px] px-1 rounded"
                                        style={{ background: '#F1F5F9', color: '#64748B' }}>not live</span>
                                )}
                              </td>
                              <td className="px-3 py-2 max-w-[220px] truncate" title={r.insured_name}>{r.insured_name || '—'}</td>
                              <td className="px-3 py-2 tabular-nums whitespace-nowrap">{money(r.premium)}</td>
                              <td className="px-3 py-2 tabular-nums whitespace-nowrap"
                                  style={{ color: r.collected_amount > 0 ? '#166534' : '#9CA3AF' }}>
                                {money(r.collected_amount)}
                              </td>
                              <td className="px-3 py-2 whitespace-nowrap">
                                <span className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-semibold"
                                      style={{ background: t.bg, color: t.fg }}
                                      title={r.status_reason || undefined}>
                                  <Icon className="w-3 h-3" /> {r.status_label}
                                </span>
                              </td>
                              <td className="px-3 py-2 text-[12px] whitespace-nowrap" style={{ color: '#6B7280' }}>
                                {r.last_attempt || '—'}
                              </td>
                              <td className="px-3 py-2 text-right">
                                {r.id ? (
                                  <button onClick={() => removeRow(r)} disabled={busy === r.policy_number}
                                          aria-label={`Remove ${r.policy_number}`}
                                          className="p-1 rounded hover:bg-red-50 disabled:opacity-40"
                                          title="Remove this row (added in Omni)">
                                    <Trash2 className="w-4 h-4" style={{ color: '#991B1B' }} />
                                  </button>
                                ) : (
                                  <span className="text-[10px]" style={{ color: '#D1D5DB' }} title="Comes from Graphite">
                                    Graphite
                                  </span>
                                )}
                              </td>
                            </tr>
                          )
                        })}
                      </tbody>
                    </table>
                  </div>
                </Card>
              </>
            )}
          </div>
        </div>

        {/* Near-duplicate brokers. Automatic merging handles trading names and
            branches; these last few need someone who knows the book, because an
            over-merge silently pays two brokers as one. */}
        {list && list.possible_duplicates.length > 0 && (
          <Card className="mt-5">
            <CardContent className="py-4">
              <h3 className="text-sm font-semibold mb-1" style={{ color: NAVY }}>
                Possibly the same broker twice
              </h3>
              <p className="text-[12px] mb-3" style={{ color: '#6B7280' }}>
                Graphite files these under names close enough to be one firm — but not
                close enough for Omni to decide on its own. Fold them together only if
                you know they are the same broker.
              </p>
              <div className="space-y-2">
                {list.possible_duplicates.map(d => (
                  <div key={d.a.id + d.b.id}
                       className="flex flex-wrap items-center gap-2 rounded px-3 py-2"
                       style={{ background: '#FEF3C7' }}>
                    <span className="text-[12px] font-medium" style={{ color: '#92400E' }}>
                      {d.a.name}
                    </span>
                    <span className="text-[12px]" style={{ color: '#92400E' }}>and</span>
                    <span className="text-[12px] font-medium" style={{ color: '#92400E' }}>
                      {d.b.name}
                    </span>
                    <div className="ml-auto flex gap-1.5">
                      <Button size="sm" variant="outline" disabled={!!busy}
                              onClick={() => void foldIn(d.a.id, d.b.id, d.b.name, d.a.name)}>
                        Keep {d.a.name.slice(0, 18)}
                      </Button>
                      <Button size="sm" variant="outline" disabled={!!busy}
                              onClick={() => void foldIn(d.b.id, d.a.id, d.a.name, d.b.name)}>
                        Keep {d.b.name.slice(0, 18)}
                      </Button>
                    </div>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Agencies writing broker business that no broker owns — Rose's
            "which brokers need tabs created?", answered from the data. */}
        {list && list.unclaimed_agencies.length > 0 && (
          <Card className="mt-5">
            <CardContent className="py-4">
              <h3 className="text-sm font-semibold mb-1" style={{ color: NAVY }}>
                Writing business, but not on the register yet
              </h3>
              <p className="text-[12px] mb-3" style={{ color: '#6B7280' }}>
                These agencies have commercial or domestic policies but no broker record.
                Press <b>Refresh from Graphite</b> to add them.
              </p>
              <div className="flex flex-wrap gap-2">
                {list.unclaimed_agencies.map(a => (
                  <span key={a.agency} className="px-2 py-1 rounded text-[12px]"
                        style={{ background: '#FEF3C7', color: '#92400E' }}>
                    {a.agency} · {a.policies}
                  </span>
                ))}
              </div>
            </CardContent>
          </Card>
        )}
      </div>

      {showAdd && picked && (
        <AddPolicyModal brokerId={picked} onClose={() => setShowAdd(false)}
                        onSaved={async () => { setShowAdd(false); await loadDetail(picked, activeOnly, period) }} />
      )}
      {showUpload && (
        <UploadModal onClose={() => setShowUpload(false)}
                     onDone={async () => { await loadList(); if (picked) await loadDetail(picked, activeOnly, period) }} />
      )}
    </div>
  )
}

/* ── Add a policy ────────────────────────────────────────────────────────── */
function AddPolicyModal({ brokerId, onClose, onSaved }:
                        { brokerId: string; onClose: () => void; onSaved: () => void }) {
  const [f, setF] = useState({ policy_number: '', insured_name: '', premium: '',
                               commission_payable: '', vat: '', period_label: '' })
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const set = (k: string, v: string) => setF(p => ({ ...p, [k]: v }))

  async function save() {
    if (!f.policy_number.trim()) { setErr('A policy number is required.'); return }
    setBusy(true); setErr(null)
    try { await addBrokerPolicy(brokerId, f); onSaved() }
    catch (e) { setErr(e instanceof Error ? e.message : 'Could not save that row.') }
    finally { setBusy(false) }
  }

  return (
    <ModalPortal>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4"
           style={{ background: 'rgba(13,27,42,.55)' }} onClick={onClose}>
        <div className="bg-white rounded-xl w-full max-w-lg shadow-2xl" onClick={e => e.stopPropagation()}>
          <div className="px-5 py-3 rounded-t-xl flex items-center justify-between" style={{ background: NAVY }}>
            <h3 className="text-white font-semibold text-sm">Add a policy to this broker</h3>
            <button onClick={onClose} aria-label="Close"><X className="w-4 h-4 text-white" /></button>
          </div>
          <div className="p-5 space-y-3">
            {err && <p className="text-sm rounded px-3 py-2" style={{ background: '#FEE2E2', color: '#991B1B' }}>{err}</p>}
            {([['policy_number', 'Policy number *', 'DOMG2025123456'],
               ['insured_name', 'Insured name', ''],
               ['period_label', 'Month (YYYY-MM)', '2026-08']] as const).map(([k, label, ph]) => (
              <div key={k}>
                <label className="block text-xs mb-1" style={{ color: '#6B7280' }}>{label}</label>
                <input value={f[k]} placeholder={ph} onChange={e => set(k, e.target.value)}
                       className="w-full px-3 py-1.5 text-sm border rounded" />
              </div>
            ))}
            <div className="grid grid-cols-3 gap-3">
              {([['premium', 'Premium'], ['commission_payable', 'Commission'], ['vat', 'VAT']] as const).map(([k, label]) => (
                <div key={k}>
                  <label className="block text-xs mb-1" style={{ color: '#6B7280' }}>{label}</label>
                  <input value={f[k]} inputMode="decimal" onChange={e => set(k, e.target.value)}
                         className="w-full px-3 py-1.5 text-sm border rounded tabular-nums" />
                </div>
              ))}
            </div>
            <p className="text-[11px]" style={{ color: '#6B7280' }}>
              Omni does not work the commission out for you — enter what Finance has agreed.
            </p>
          </div>
          <div className="px-5 py-3 border-t flex justify-end gap-2">
            <Button variant="outline" size="sm" onClick={onClose}>Cancel</Button>
            <Button variant="primary" size="sm" onClick={save} loading={busy} disabled={busy}>Save</Button>
          </div>
        </div>
      </div>
    </ModalPortal>
  )
}

/* ── Upload the workbook ─────────────────────────────────────────────────── */
function UploadModal({ onClose, onDone }: { onClose: () => void; onDone: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [period, setPeriod] = useState('')
  const [busy, setBusy] = useState(false)
  const [err, setErr] = useState<string | null>(null)
  const [preview, setPreview] = useState<Awaited<ReturnType<typeof uploadBrokerWorkbook>> | null>(null)

  async function run(commit: boolean) {
    if (!file) { setErr('Choose the workbook first.'); return }
    setBusy(true); setErr(null)
    try {
      const r = await uploadBrokerWorkbook(file, { period: period || undefined, preview: !commit })
      setPreview(r)
      if (commit) { await onDone() }
    } catch (e) { setErr(e instanceof Error ? e.message : 'That workbook could not be read.') }
    finally { setBusy(false) }
  }

  return (
    <ModalPortal>
      <div className="fixed inset-0 z-[100] flex items-center justify-center p-4"
           style={{ background: 'rgba(13,27,42,.55)' }} onClick={onClose}>
        <div className="bg-white rounded-xl w-full max-w-2xl shadow-2xl max-h-[88vh] overflow-y-auto"
             onClick={e => e.stopPropagation()}>
          <div className="px-5 py-3 rounded-t-xl flex items-center justify-between sticky top-0" style={{ background: NAVY }}>
            <h3 className="text-white font-semibold text-sm">Upload the broker workbook</h3>
            <button onClick={onClose} aria-label="Close"><X className="w-4 h-4 text-white" /></button>
          </div>
          <div className="p-5 space-y-4">
            <p className="text-[12px]" style={{ color: '#6B7280' }}>
              Every broker tab is read, not just one. Check the preview first — any tab that
              does not match a broker on the register is listed rather than quietly skipped.
            </p>
            {err && <p className="text-sm rounded px-3 py-2" style={{ background: '#FEE2E2', color: '#991B1B' }}>{err}</p>}

            <div className="flex items-center gap-3">
              <input ref={fileRef} type="file" accept=".xlsx,.xlsm,.xlsb,.xls,.ods"
                     aria-label="Broker workbook"
                     onChange={e => { setFile(e.target.files?.[0] || null); setPreview(null) }}
                     className="text-sm" />
            </div>
            <div>
              <label className="block text-xs mb-1" style={{ color: '#6B7280' }}>Month (YYYY-MM, optional)</label>
              <input value={period} onChange={e => setPeriod(e.target.value)} placeholder="2026-08"
                     className="px-3 py-1.5 text-sm border rounded w-40" />
            </div>

            {preview && (
              <div className="space-y-3">
                <div className="rounded-lg px-3 py-2 text-sm"
                     style={{ background: preview.committed ? '#DCFCE7' : '#EFF6FF',
                              color: preview.committed ? '#166534' : '#1E40AF' }}>
                  {preview.committed
                    ? `Imported — ${preview.rows_written} row(s) written across ${preview.matched.length} broker(s).`
                    : `Preview only — nothing saved yet. ${preview.matched.length} tab(s) matched a broker.`}
                </div>
                {preview.matched.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold mb-1" style={{ color: NAVY }}>Matched</h4>
                    <div className="flex flex-wrap gap-1.5">
                      {preview.matched.map(m => (
                        <span key={m.sheet} className="px-2 py-0.5 rounded text-[11px]"
                              style={{ background: '#DCFCE7', color: '#166534' }}>
                          {m.sheet} → {m.broker} · {m.rows}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {preview.unmatched.length > 0 && (
                  <div>
                    <h4 className="text-xs font-semibold mb-1" style={{ color: '#92400E' }}>
                      Tabs with no matching broker — nothing was imported for these
                    </h4>
                    <div className="flex flex-wrap gap-1.5">
                      {preview.unmatched.map(m => (
                        <span key={m.sheet} className="px-2 py-0.5 rounded text-[11px]"
                              style={{ background: '#FEF3C7', color: '#92400E' }}>
                          {m.sheet} · {m.rows} row(s)
                        </span>
                      ))}
                    </div>
                  </div>
                )}
                {preview.sheets_without_a_table.length > 0 && (
                  <p className="text-[11px]" style={{ color: '#6B7280' }}>
                    Skipped (no policy table): {preview.sheets_without_a_table.join(', ')}
                  </p>
                )}
              </div>
            )}
          </div>
          <div className="px-5 py-3 border-t flex justify-end gap-2 sticky bottom-0 bg-white">
            <Button variant="outline" size="sm" onClick={onClose}>Close</Button>
            <Button variant="secondary" size="sm" onClick={() => run(false)} loading={busy} disabled={busy || !file}>
              <FileSpreadsheet className="w-4 h-4 mr-1.5" /> Preview
            </Button>
            <Button variant="primary" size="sm" onClick={() => run(true)} loading={busy} disabled={busy || !file}>
              <Upload className="w-4 h-4 mr-1.5" /> Import
            </Button>
          </div>
        </div>
      </div>
    </ModalPortal>
  )
}
