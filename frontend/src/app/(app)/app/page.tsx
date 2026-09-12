'use client'
import { useEffect, useState } from 'react'
import Link from 'next/link'
import { Banknote, CheckCircle2, ListChecks, CalendarDays, Camera, ChevronRight, Bell, Users, FileText, Zap, Search, Sunrise } from 'lucide-react'
import { afetch } from '../api'
import { enableApprovalPush } from '@/app/(customer)/api'
import { useManagerProbe, type Glance } from '../managerProbe'
import { C, h, serif, headerPad, card, isInAppShell } from '../ui'

interface Stream { key: string; label: string; count: number; href: string }
interface MyApprovals { streams: Stream[]; total: number }
interface MobileHome { first_name: string; approvals: MyApprovals; my_tasks_open: number; capabilities: Record<string, boolean> }

export default function AppHome() {
  const [appr, setAppr] = useState<MyApprovals | null>(null)
  const [tasks, setTasks] = useState<number | null>(null)
  const [isAuthoriser, setIsAuthoriser] = useState(false)
  const [canExpress, setCanExpress] = useState(false)          // CFO/CEO only — Express Pay tile
  const [name, setName] = useState('')
  const [showInstall, setShowInstall] = useState(false)
  const { isManager, glance } = useManagerProbe()

  useEffect(() => {
    // One combined call for greeting + approvals + open tasks (Omni Mobile B).
    // The approvals shape is unchanged, so the badge maths below is untouched.
    afetch<MobileHome>('/mobile/home/').then(h => {
      setAppr(h.approvals)
      setTasks(h.my_tasks_open)
      setName(h.first_name || '')
    }).catch(() => {})
    afetch('/payment-requests/bulk/preview/').then(() => setIsAuthoriser(true)).catch(() => setIsAuthoriser(false))
    afetch<{ allowed: boolean }>('/fnb/express-pay/can/').then(r => setCanExpress(!!r.allowed)).catch(() => setCanExpress(false))
    setShowInstall(!isInAppShell())
  }, [])

  const pay = appr?.streams.find(s => s.key === 'payments')?.count ?? 0
  const payReq = appr?.streams.find(s => s.key === 'payment_requests')?.count ?? 0
  const paymentsBadge = pay + (isAuthoriser ? payReq : 0)
  const approvalsBadge = appr ? Math.max(0, appr.total - pay - payReq) : 0
  const waiting = paymentsBadge + approvalsBadge + (tasks ?? 0)
  const loading = appr === null && tasks === null

  return (
    <main>
      <header style={{ background: C.navy, color: '#fff', padding: headerPad, paddingBottom: 44 }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          {/* The AD mark on its own white chip: the logo's navy and orange need a
              light ground to read, and the mark is never recoloured to suit us. */}
          <span aria-hidden="true" style={{
            width: 40, height: 40, borderRadius: 11, background: '#FFFFFF',
            display: 'grid', placeItems: 'center', flex: '0 0 auto',
          }}>
            <img src="/brand/ad-mark.png" alt="" width={28} height={17} style={{ display: 'block', width: 28, height: 'auto' }} />
          </span>
          <div>
            <h1 style={{ fontFamily: serif, fontSize: 22, fontWeight: 700, lineHeight: 1.05, margin: 0 }}>Alpha Omni</h1>
            <div style={{ opacity: 0.8, fontSize: 13, marginTop: 4 }}>{name ? `Dumela, ${name}` : 'Alpha Direct staff'}</div>
          </div>
        </div>
      </header>

      {/* Bento: one wide hero card, then three small tiles — not a uniform grid. */}
      <section style={{ padding: '0 16px', marginTop: -28, display: 'grid', gap: 12 }}>
        <div className="oa-rise" style={{ ...card, padding: 0, overflow: 'hidden' }}>
          <div style={{ padding: '18px 18px 14px', display: 'flex', alignItems: 'flex-end', gap: 14 }}>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase', color: C.inkSoft, fontWeight: 600 }}>Waiting on you</div>
              <div style={{ fontFamily: serif, fontSize: 56, fontWeight: 700, lineHeight: 1, color: C.head, marginTop: 4 }}>{loading ? '…' : waiting}</div>
            </div>
            <div style={{ fontSize: 13, color: C.inkSoft, maxWidth: 150, paddingBottom: 6 }}>
              {loading ? 'Checking your queues…' : waiting > 0 ? 'Tap a row to action it — it takes seconds.' : 'All caught up. Sharp sharp!'}
            </div>
          </div>
          <div style={{ borderTop: `1px solid ${C.line}` }}>
            {isAuthoriser && paymentsBadge > 0 && <Row href="/app/payments" icon={Banknote} title="Payments to sign" badge={paymentsBadge} accent />}
            <Row href="/app/approve" icon={CheckCircle2} title="Approvals" badge={approvalsBadge || null} />
            <Row href="/app/tasks" icon={ListChecks} title="My tasks" badge={tasks || null} last />
          </div>
        </div>

        {/* Express Pay (CFO 2026-09-04): CFO/CEO only — one payment straight into FNB's
            queue, single authorisation. Omni moves no money; the release is in the FNB app. */}
        {canExpress && (
          <Link href="/app/express-pay" className="oa-press oa-rise oa-rise-2" style={{ ...card, display: 'flex', alignItems: 'center', gap: 14, padding: 16, textDecoration: 'none', color: C.ink, borderLeft: `4px solid ${C.orange}` }}>
            <span style={{ display: 'grid', placeItems: 'center', width: 44, height: 44, borderRadius: 14, background: C.navy }}><Zap size={22} color={C.orange} /></span>
            <span style={{ flex: 1 }}>
              <span style={{ display: 'block', fontFamily: serif, fontWeight: 700, fontSize: 17 }}>Express Pay</span>
              <span style={{ display: 'block', fontSize: 13, color: C.inkSoft }}>Pay anyone now — one payment, straight into FNB for your approval.</span>
            </span>
            <ChevronRight size={18} color={C.inkSoft} />
          </Link>
        )}

        {isManager && <TeamCard glance={glance} />}

        <Link href="/app/snap" className="oa-press" style={{ ...card, display: 'flex', alignItems: 'center', gap: 14, padding: 16, textDecoration: 'none', color: C.ink }}>
          <span style={{ display: 'grid', placeItems: 'center', width: 44, height: 44, borderRadius: 14, background: C.navy }}><Camera size={22} color={C.orange} /></span>
          <span style={{ flex: 1 }}>
            <span style={{ display: 'block', fontFamily: serif, fontWeight: 700, fontSize: 17 }}>Snap anything</span>
            <span style={{ display: 'block', fontSize: 13, color: C.inkSoft }}>Invoice, receipt or quote — Omni sorts it and opens the right form.</span>
          </span>
          <ChevronRight size={18} color={C.inkSoft} />
        </Link>

        {/* Morning brief note (CFO 2026-09-10): 25 words to the CEO or CFO, once a
            morning. Shown to everyone — the screen itself does the gating, so no
            capability probe here and no tile that flickers away after it loads. */}
        <Link href="/app/brief-note" className="oa-press" style={{ ...card, display: 'flex', alignItems: 'center', gap: 14, padding: 16, textDecoration: 'none', color: C.ink }}>
          <span style={{ display: 'grid', placeItems: 'center', width: 44, height: 44, borderRadius: 14, background: C.navy }}><Sunrise size={22} color={C.orange} /></span>
          <span style={{ flex: 1 }}>
            <span style={{ display: 'block', fontFamily: serif, fontWeight: 700, fontSize: 17 }}>Message the CEO or CFO</span>
            <span style={{ display: 'block', fontSize: 13, color: C.inkSoft }}>25 words, once a morning</span>
          </span>
          <ChevronRight size={18} color={C.inkSoft} />
        </Link>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr 1fr', gap: 10 }}>
          <Small href="/app/lookup" icon={Search} label="Look up" delay={2} />
          <Small href="/app/docs" icon={FileText} label="Quotes" delay={2} />
          <Small href="/app/leave" icon={CalendarDays} label="Leave" delay={2} />
          <Small href="/app/receipt" icon={Camera} label="Receipt" delay={2} />
        </div>

        <AlertsCard />
        {showInstall && <InstallCard />}
      </section>
    </main>
  )
}

function Row({ href, icon: Icon, title, badge, accent, last }: { href: string; icon: typeof Banknote; title: string; badge: number | null; accent?: boolean; last?: boolean }) {
  return (
    <Link href={href} className="oa-press" style={{ display: 'flex', alignItems: 'center', gap: 14, padding: '14px 18px', textDecoration: 'none', color: C.ink,
      borderBottom: last ? undefined : `1px solid ${C.line}`, borderLeft: accent ? `4px solid ${C.orange}` : '4px solid transparent' }}>
      <Icon size={20} color={C.head} />
      <span style={{ flex: 1, fontWeight: 600, fontSize: 16 }}>{title}</span>
      {badge ? <span style={{ background: C.orange, color: C.navy, fontWeight: 800, borderRadius: 999, padding: '3px 10px', fontSize: 13 }}>{badge}</span> : null}
      <ChevronRight size={18} color={C.inkSoft} />
    </Link>
  )
}
/** Manager live card (CFO 2026-09-03): one glance — who is in, who is dark, who
 * is on leave, what is overdue — with the dark/overdue people named. Tap → Team. */
const shortName = (full: string) => {
  const p = full.trim().split(/\s+/)
  return p.length > 1 ? `${p[0]} ${p[p.length - 1][0]}.` : p[0]
}
function TeamCard({ glance }: { glance: Glance | null }) {
  const c = glance?.counts
  const dark = (glance?.reports ?? []).filter(r => r.dark_days_7 > 0).map(r => shortName(r.name))
  const late = (glance?.reports ?? []).filter(r => r.overdue_tasks > 0).map(r => shortName(r.name))
  const summary = c ? `${c.in} in · ${c.on_leave} on leave · ${c.dark} dark · ${c.overdue} overdue` : 'Checking your team…'
  return (
    <Link href="/app/team" className="oa-press oa-rise oa-rise-2" aria-label={`Your team today: ${summary}`}
      style={{ ...card, display: 'flex', alignItems: 'center', gap: 14, padding: '14px 16px', textDecoration: 'none', color: C.ink,
               borderLeft: c && (c.dark || c.overdue) ? `4px solid ${C.red}` : `4px solid ${C.green}` }}>
      <span style={{ display: 'grid', placeItems: 'center', width: 40, height: 40, borderRadius: 14, background: C.navy, flexShrink: 0 }}>
        <Users size={20} color={C.orange} />
      </span>
      <span style={{ flex: 1, minWidth: 0 }}>
        <span style={{ display: 'block', fontSize: 12, letterSpacing: '0.08em', textTransform: 'uppercase', color: C.inkSoft, fontWeight: 600 }}>Your team today</span>
        <span style={{ display: 'block', fontWeight: 700, fontSize: 15, marginTop: 2 }}>{summary}</span>
        {(dark.length > 0 || late.length > 0) && (
          <span style={{ display: 'block', fontSize: 12.5, color: C.inkSoft, marginTop: 3, lineHeight: 1.45 }}>
            {dark.length > 0 && <>Dark: <b style={{ color: C.red }}>{dark.join(', ')}</b></>}
            {dark.length > 0 && late.length > 0 && ' · '}
            {late.length > 0 && <>Overdue: <b style={{ color: C.amber }}>{late.join(', ')}</b></>}
          </span>
        )}
      </span>
      <ChevronRight size={18} color={C.inkSoft} />
    </Link>
  )
}

function Small({ href, icon: Icon, label, delay }: { href: string; icon: typeof Banknote; label: string; delay: number }) {
  return (
    <Link href={href} className={`oa-press oa-rise oa-rise-${delay}`}
      style={{ ...card, display: 'grid', placeItems: 'center', gap: 6, padding: '16px 8px', textDecoration: 'none', color: C.ink, fontSize: 13, fontWeight: 600 }}>
      <span style={{ display: 'grid', placeItems: 'center', width: 40, height: 40, borderRadius: 14, background: 'var(--ao-orange-wash, rgba(240,127,0,0.14))' }}>
        <Icon size={20} color={C.head} />
      </span>
      {label}
    </Link>
  )
}

type PushState = 'idle' | 'busy' | 'on' | 'unsupported' | 'denied' | 'unconfigured' | 'error'
const PUSH_MSG: Record<Exclude<PushState, 'idle' | 'busy'>, string> = {
  on: 'Alerts are on. You will hear when something needs you.',
  unsupported: 'This browser cannot show alerts. Install Omni to your Home Screen first.',
  denied: 'Alerts are blocked in your phone settings for this site.',
  unconfigured: 'Alerts are not set up on the server yet.',
  error: 'Could not turn alerts on. Try again later.',
}
/** "Turn on alerts" — shown only when the browser supports Notification and
 * permission is not already granted. Reuses enableApprovalPush() (root /sw.js
 * + the same subscribe endpoint); after Task 7 that call carries the app token. */
function AlertsCard() {
  const [show, setShow] = useState(false)
  const [state, setState] = useState<PushState>('idle')
  useEffect(() => {
    setShow(typeof window !== 'undefined' && 'Notification' in window && Notification.permission !== 'granted')
  }, [])
  if (!show) return null
  const turnOn = async () => {
    setState('busy')
    const r = await enableApprovalPush()
    setState(r in PUSH_MSG ? (r as keyof typeof PUSH_MSG) : 'error')
  }
  return (
    <div className="oa-rise oa-rise-3" style={{ ...card, padding: 16, display: 'flex', alignItems: 'center', gap: 14 }}>
      <span style={{ display: 'grid', placeItems: 'center', width: 40, height: 40, borderRadius: 14, background: C.navy, flexShrink: 0 }}>
        <Bell size={20} color={C.orange} />
      </span>
      <div style={{ flex: 1 }}>
        <div style={h(16)}>Turn on alerts</div>
        <p style={{ color: state === 'denied' || state === 'error' ? C.red : C.inkSoft, fontSize: 13, margin: '4px 0 0' }}>
          {state === 'idle' || state === 'busy' ? 'Hear when something is waiting for you.' : PUSH_MSG[state]}
        </p>
      </div>
      {state !== 'on' && (
        <button onClick={turnOn} disabled={state === 'busy'} className="oa-press"
          style={{ minHeight: 40, padding: '0 14px', borderRadius: 12, border: 0, background: C.orange, color: C.navy, fontWeight: 700, fontSize: 14, whiteSpace: 'nowrap' }}>
          {state === 'busy' ? '…' : '🔔 Turn on'}
        </button>
      )}
    </div>
  )
}

function InstallCard() {
  const ios = typeof navigator !== 'undefined' && /iPhone|iPad/.test(navigator.userAgent)
  const [evt, setEvt] = useState<(Event & { prompt: () => Promise<void> }) | null>(null)
  useEffect(() => {
    const on = (e: Event) => { e.preventDefault(); setEvt(e as Event & { prompt: () => Promise<void> }) }
    window.addEventListener('beforeinstallprompt', on)
    return () => window.removeEventListener('beforeinstallprompt', on)
  }, [])
  return (
    <div className="oa-rise oa-rise-3" style={{ ...card, padding: 16 }}>
      <div style={h(17)}>Put Omni on your Home Screen</div>
      {ios
        ? <p style={{ color: C.inkSoft, fontSize: 14, margin: '6px 0 0' }}>Tap Share <span aria-hidden>⎋</span> then “Add to Home Screen”. Notifications only work from the installed app.</p>
        : evt
          ? <button onClick={() => evt.prompt()} className="oa-press" style={{ marginTop: 10, minHeight: 44, padding: '0 16px', borderRadius: 12, border: 0, background: C.orange, color: C.navy, fontWeight: 700 }}>Install Omni</button>
          : <p style={{ color: C.inkSoft, fontSize: 14, margin: '6px 0 0' }}>In Chrome: menu ⋮ → “Install app”.</p>}
    </div>
  )
}
