'use client'

/**
 * /compliance/iso/risks — ISO 27005 Risk Register.
 *
 * Rows: ref / title / threat-vuln / L × I = score / treatment / owner / status.
 * Click a row → edit panel. Heatmap (L vs I) up top.
 */

import { useCallback, useEffect, useMemo, useState } from 'react'
import { TopBar } from '@/components/layout/TopBar'
import { Card, CardContent } from '@/components/ui/card'
import { apiFetch } from '@/lib/api'
import { AlertTriangle, Plus, X } from 'lucide-react'

interface Risk {
  id: string
  ref: string
  title: string
  description: string
  asset: string
  threat: string
  vulnerability: string
  likelihood: number
  impact: number
  score: number
  residual_likelihood: number | null
  residual_impact: number | null
  residual_score: number | null
  treatment: 'reduce' | 'transfer' | 'avoid' | 'accept'
  treatment_label: string
  treatment_plan: string
  owner: string
  status: 'open' | 'mitigated' | 'closed'
  status_label: string
  control_clauses: string[]
  created_at: string
  reviewed_at: string | null
}

const TREATMENT_TONE: Record<Risk['treatment'], string> = {
  reduce:   'bg-sky-100 text-sky-800',
  transfer: 'bg-violet-100 text-violet-800',
  avoid:    'bg-amber-100 text-amber-800',
  accept:   'bg-slate-200 text-slate-800',
}

function scoreColour(s: number): string {
  if (s >= 20) return '#D72638'
  if (s >= 12) return '#F4A623'
  if (s >= 6)  return '#FFD166'
  return '#0F8B6C'
}

export default function RiskRegisterPage() {
  const [rows, setRows] = useState<Risk[]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)
  const [editing, setEditing] = useState<Risk | null>(null)
  const [creating, setCreating] = useState(false)

  const load = useCallback(async () => {
    setLoading(true); setErr(null)
    try {
      const res = await apiFetch<any>('/iso/risks/?page_size=200')
      const list: Risk[] = Array.isArray(res) ? res : (res?.results ?? [])
      setRows(list)
    } catch (e: any) { setErr(e?.message || 'Load failed') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { void load() }, [load])

  const save = async (r: Partial<Risk> & { id?: string }) => {
    const isNew = !r.id
    const path = isNew ? '/iso/risks/' : `/iso/risks/${r.id}/`
    await apiFetch(path, {
      method: isNew ? 'POST' : 'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(r),
    })
    setEditing(null); setCreating(false)
    await load()
  }

  const del = async (id: string) => {
    if (!confirm('Delete this risk?')) return
    await apiFetch(`/iso/risks/${id}/`, { method: 'DELETE' })
    setEditing(null)
    await load()
  }

  const heatmap = useMemo(() => {
    const cells: Record<string, Risk[]> = {}
    for (const r of rows) {
      const k = `${r.likelihood}-${r.impact}`
      cells[k] = cells[k] || []
      cells[k].push(r)
    }
    return cells
  }, [rows])

  return (
    <div className="min-h-screen bg-slate-50">
      <TopBar />
      <main className="mx-auto max-w-7xl px-6 py-8">
        <div className="mb-6 flex items-start justify-between">
          <div>
            <div className="flex items-center gap-3">
              <AlertTriangle size={28} style={{ color: '#0D1B2A' }} />
              <h1 className="text-2xl font-serif font-semibold" style={{ color: '#0D1B2A' }}>
                Risk Register
              </h1>
            </div>
            <p className="mt-1 text-sm text-slate-600">
              ISO/IEC 27005 risk rows — threats, vulnerabilities, likelihood × impact, treatment.
              Score 1–5 each axis (5 = highest).
            </p>
          </div>
          <button onClick={() => { setCreating(true); setEditing({} as Risk) }}
            className="flex items-center gap-2 rounded-md px-3 py-2 text-sm text-white"
            style={{ background: '#F4A623' }}>
            <Plus size={14} /> New Risk
          </button>
        </div>

        {/* Heatmap */}
        <Card className="mb-6 border border-slate-200">
          <CardContent className="py-5">
            <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">
              Heatmap — Likelihood × Impact
            </div>
            <div className="grid grid-cols-[40px_repeat(5,1fr)] gap-1 text-xs">
              <div></div>
              {[1,2,3,4,5].map((i) => <div key={i} className="text-center text-slate-500">I={i}</div>)}
              {[5,4,3,2,1].map((l) => (
                <>
                  <div key={`L${l}`} className="text-right text-slate-500">L={l}</div>
                  {[1,2,3,4,5].map((i) => {
                    const list = heatmap[`${l}-${i}`] || []
                    const s = l * i
                    return (
                      <div key={`${l}-${i}`} className="rounded p-2 text-center font-mono text-xs"
                           style={{ background: scoreColour(s) + '33', color: scoreColour(s), borderColor: scoreColour(s) }}>
                        <div className="font-semibold">{s}</div>
                        <div className="text-[10px]">{list.length} risk(s)</div>
                      </div>
                    )
                  })}
                </>
              ))}
            </div>
          </CardContent>
        </Card>

        {err && (
          <div className="mb-4 rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800">
            {err}
          </div>
        )}

        {/* Table */}
        <div className="overflow-x-auto rounded-md border border-slate-200 bg-white">
          <table className="min-w-full text-sm">
            <thead className="bg-slate-100 text-left text-xs uppercase tracking-wide text-slate-600">
              <tr>
                <th className="px-3 py-2">Ref</th>
                <th className="px-3 py-2">Title / Threat</th>
                <th className="px-3 py-2">Asset</th>
                <th className="px-3 py-2 text-center">L × I</th>
                <th className="px-3 py-2 text-center">Score</th>
                <th className="px-3 py-2">Treatment</th>
                <th className="px-3 py-2">Owner</th>
                <th className="px-3 py-2">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {loading ? (
                <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-500">Loading…</td></tr>
              ) : rows.length === 0 ? (
                <tr><td colSpan={8} className="px-3 py-8 text-center text-slate-500">
                  No risks logged. Click <strong>New Risk</strong> to add one.
                </td></tr>
              ) : rows.map((r) => (
                <tr key={r.id} onClick={() => setEditing(r)}
                    className="cursor-pointer hover:bg-slate-50">
                  <td className="px-3 py-2 font-mono text-xs">{r.ref}</td>
                  <td className="px-3 py-2">
                    <div className="font-medium" style={{ color: '#0D1B2A' }}>{r.title}</div>
                    <div className="text-xs text-slate-500">{r.threat}</div>
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-600">{r.asset}</td>
                  <td className="px-3 py-2 text-center font-mono text-xs">{r.likelihood} × {r.impact}</td>
                  <td className="px-3 py-2 text-center">
                    <span className="inline-block rounded px-2 py-0.5 font-mono text-xs font-semibold"
                          style={{ background: scoreColour(r.score), color: '#fff' }}>
                      {r.score}
                    </span>
                  </td>
                  <td className="px-3 py-2">
                    <span className={`inline-block rounded px-2 py-0.5 text-[11px] ${TREATMENT_TONE[r.treatment]}`}>
                      {r.treatment_label}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs text-slate-600">{r.owner}</td>
                  <td className="px-3 py-2 text-xs">{r.status_label}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {editing && (
          <RiskEditor risk={editing} isNew={creating}
            onSave={save} onDelete={del} onClose={() => { setEditing(null); setCreating(false) }} />
        )}
      </main>
    </div>
  )
}

function RiskEditor({
  risk, isNew, onSave, onDelete, onClose,
}: {
  risk: Risk
  isNew: boolean
  onSave: (r: Partial<Risk> & { id?: string }) => void | Promise<void>
  onDelete: (id: string) => void | Promise<void>
  onClose: () => void
}) {
  const [r, setR] = useState<Risk>(() => {
    const defaults: Risk = {
      id: '', ref: '', title: '', description: '', asset: '', threat: '', vulnerability: '',
      likelihood: 3, impact: 3, score: 9,
      residual_likelihood: null, residual_impact: null, residual_score: null,
      treatment: 'reduce', treatment_label: '', treatment_plan: '',
      owner: '', status: 'open', status_label: '',
      control_clauses: [], created_at: '', reviewed_at: null,
    }
    return { ...defaults, ...risk }
  })

  const set = <K extends keyof Risk>(k: K, v: Risk[K]) => setR((p) => ({ ...p, [k]: v }))

  return (
    <div className="fixed inset-0 z-40 flex items-end bg-slate-900/50 sm:items-center sm:justify-center">
      <div className="w-full max-w-2xl rounded-t-lg bg-white p-6 shadow-xl sm:rounded-lg">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="font-serif text-xl font-semibold" style={{ color: '#0D1B2A' }}>
            {isNew ? 'New Risk' : `Edit ${r.ref}`}
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-700">
            <X size={20} />
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3 text-sm">
          <Field label="Reference" full={isNew}>
            <input value={r.ref} onChange={(e) => set('ref', e.target.value)}
              placeholder="R-001"
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
          </Field>
          <Field label="Title" full>
            <input value={r.title} onChange={(e) => set('title', e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
          </Field>
          <Field label="Asset">
            <input value={r.asset} onChange={(e) => set('asset', e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
          </Field>
          <Field label="Owner">
            <input value={r.owner} onChange={(e) => set('owner', e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
          </Field>
          <Field label="Threat" full>
            <input value={r.threat} onChange={(e) => set('threat', e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
          </Field>
          <Field label="Vulnerability" full>
            <input value={r.vulnerability} onChange={(e) => set('vulnerability', e.target.value)}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
          </Field>
          <Field label="Likelihood (1-5)">
            <input type="number" min={1} max={5} value={r.likelihood}
              onChange={(e) => set('likelihood', Number(e.target.value))}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
          </Field>
          <Field label="Impact (1-5)">
            <input type="number" min={1} max={5} value={r.impact}
              onChange={(e) => set('impact', Number(e.target.value))}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
          </Field>
          <Field label="Treatment">
            <select value={r.treatment} onChange={(e) => set('treatment', e.target.value as Risk['treatment'])}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm">
              <option value="reduce">Reduce — implement controls</option>
              <option value="transfer">Transfer — insure / outsource</option>
              <option value="avoid">Avoid — stop the activity</option>
              <option value="accept">Accept — sign off the residual</option>
            </select>
          </Field>
          <Field label="Status">
            <select value={r.status} onChange={(e) => set('status', e.target.value as Risk['status'])}
              className="w-full rounded border border-slate-300 px-3 py-2 text-sm">
              <option value="open">Open</option>
              <option value="mitigated">Mitigated</option>
              <option value="closed">Closed</option>
            </select>
          </Field>
          <Field label="Treatment plan" full>
            <textarea value={r.treatment_plan} onChange={(e) => set('treatment_plan', e.target.value)}
              rows={3} className="w-full rounded border border-slate-300 px-3 py-2 text-sm" />
          </Field>
        </div>

        <div className="mt-6 flex justify-between">
          <div>
            {!isNew && (
              <button onClick={() => onDelete(r.id)}
                className="rounded border border-red-200 px-3 py-2 text-sm text-red-700 hover:bg-red-50">
                Delete
              </button>
            )}
          </div>
          <div className="flex gap-2">
            <button onClick={onClose}
              className="rounded border border-slate-300 px-3 py-2 text-sm">
              Cancel
            </button>
            <button onClick={() => onSave(r)}
              className="rounded px-3 py-2 text-sm text-white"
              style={{ background: '#0D1B2A' }}>
              Save
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}

function Field({ label, full, children }: { label: string; full?: boolean; children: React.ReactNode }) {
  return (
    <div className={full ? 'col-span-2' : ''}>
      <label className="mb-1 block text-xs uppercase tracking-wide text-slate-500">{label}</label>
      {children}
    </div>
  )
}
