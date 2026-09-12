'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useParams } from 'next/navigation'
import {
  ArrowLeft, AlertCircle, Tag, Hash, Car, MapPin, Package, Building2,
} from 'lucide-react'
import { TopBar } from '@/components/layout/TopBar'
import { useTheme } from '@/contexts/ThemeContext'
import { apiFetch } from '@/lib/api'

interface SalvageImage {
  id: string
  image: string
  caption: string
  ordering: number
}

interface SalvageItemDetail {
  id: string
  item_code: string
  claim_number: string
  policy_number: string
  part_name: string
  part_description: string
  quantity: number
  category_name?: string | null
  vehicle_brand_name?: string | null
  vehicle_model_name?: string | null
  vehicle_year?: number | null
  vehicle_colour: string
  vin_number: string
  condition: string
  status: string
  asking_price: string
  reserve_price: string
  location: string
  company_code?: string | null
  created_by?: string | null
  posted_at?: string | null
  images: SalvageImage[]
}

export default function SalvageItemDetailPage() {
  const { theme } = useTheme()
  const params = useParams<{ id: string }>()
  const id = params?.id
  const [item, setItem] = useState<SalvageItemDetail | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!id) return
    apiFetch<SalvageItemDetail>(`/salvage-items/${id}/`)
      .then(setItem)
      .catch(e => setError(e instanceof Error ? e.message : 'Failed to load'))
      .finally(() => setLoading(false))
  }, [id])

  return (
    <div className="min-h-screen" style={{ background: theme.bg }}>
      <TopBar title="Salvage · Item" />

      <div className="p-4 lg:p-6 max-w-[1200px] mx-auto space-y-5">
        <Link href="/salvage/inventory"
              className="inline-flex items-center gap-1.5 text-xs font-semibold"
              style={{ color: theme.orange }}>
          <ArrowLeft className="w-3.5 h-3.5" /> Back to inventory
        </Link>

        {loading && (
          <div className="rounded-xl p-6 text-sm" style={{
            background: theme.card, border: `1px solid ${theme.cardBdr}`, color: theme.t3,
          }}>Loading…</div>
        )}

        {error && (
          <div className="rounded-md p-3 flex items-start gap-2"
               style={{ background: theme.erB, border: `1px solid ${theme.er}30` }}>
            <AlertCircle className="w-4 h-4 mt-0.5" style={{ color: theme.er }} />
            <div>
              <p className="text-sm font-semibold" style={{ color: theme.er }}>
                Couldn&apos;t load this item
              </p>
              <p className="text-xs mt-0.5" style={{ color: theme.er, opacity: 0.7 }}>{error}</p>
            </div>
          </div>
        )}

        {item && (
          <>
            {/* Header card */}
            <div className="rounded-2xl p-6 lg:p-8 relative overflow-hidden"
                 style={{ background: theme.card, border: `1px solid ${theme.cardBdr}`, boxShadow: theme.cardSh }}>
              <div className="absolute -top-24 -right-20 w-80 h-80 rounded-full pointer-events-none"
                   style={{
                     background: `radial-gradient(circle at 30% 30%, rgba(240,127,0,0.10) 0%, transparent 60%)`,
                     filter: 'blur(30px)',
                   }} />
              <div className="relative">
                <div className="flex items-center gap-2 mb-2">
                  <span className="font-mono text-xs px-2 py-0.5 rounded"
                        style={{ background: theme.g100, color: theme.t2 }}>
                    {item.item_code}
                  </span>
                  <StatusPill theme={theme} status={item.status} />
                  <span className="text-[10px] uppercase tracking-wider font-semibold px-2 py-0.5 rounded-full"
                        style={{ background: theme.g100, color: theme.t2 }}>
                    {item.condition}
                  </span>
                </div>
                <h1 className="font-display-tight text-3xl lg:text-4xl font-bold mb-2"
                    style={{ color: theme.navy }}>
                  {item.part_name}
                </h1>
                {item.part_description && (
                  <p className="font-display text-sm italic max-w-2xl" style={{ color: theme.t2 }}>
                    {item.part_description}
                  </p>
                )}

                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mt-6 pt-6 border-t"
                     style={{ borderColor: theme.cardBdr }}>
                  <Price label="Asking" theme={theme} value={item.asking_price} accent />
                  <Price label="Reserve" theme={theme} value={item.reserve_price} />
                  <div>
                    <div className="text-[10px] uppercase tracking-wider font-semibold mb-1"
                         style={{ color: theme.t3 }}>Quantity</div>
                    <div className="font-display-tight text-2xl font-bold tabular-nums"
                         style={{ color: theme.navy }}>{item.quantity}</div>
                  </div>
                  <div>
                    <div className="text-[10px] uppercase tracking-wider font-semibold mb-1"
                         style={{ color: theme.t3 }}>Location</div>
                    <div className="font-display-tight text-base font-bold truncate"
                         style={{ color: theme.navy }}>
                      {item.location || '—'}
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Detail grid */}
            <div className="grid lg:grid-cols-2 gap-4">
              <DetailCard theme={theme} icon={Car} title="Vehicle">
                <Row theme={theme} label="Brand"  value={item.vehicle_brand_name || '—'} />
                <Row theme={theme} label="Model"  value={item.vehicle_model_name || '—'} />
                <Row theme={theme} label="Year"   value={item.vehicle_year?.toString() || '—'} />
                <Row theme={theme} label="Colour" value={item.vehicle_colour || '—'} />
                <Row theme={theme} label="VIN"    value={item.vin_number || '—'} mono />
              </DetailCard>

              <DetailCard theme={theme} icon={Tag} title="Classification">
                <Row theme={theme} label="Category" value={item.category_name || '—'} />
                <Row theme={theme} label="Status"   value={item.status.replaceAll('_', ' ')} />
                <Row theme={theme} label="Condition" value={item.condition} />
                <Row theme={theme} label="Company"  value={item.company_code || '—'} />
                <Row theme={theme} label="Posted"   value={item.posted_at ? new Date(item.posted_at).toLocaleDateString('en-BW') : '—'} />
              </DetailCard>

              <DetailCard theme={theme} icon={Hash} title="Claim Reference">
                <Row theme={theme} label="Claim number"  value={item.claim_number  || '—'} mono />
                <Row theme={theme} label="Policy number" value={item.policy_number || '—'} mono />
              </DetailCard>

              <DetailCard theme={theme} icon={Package} title="Stock">
                <Row theme={theme} label="Item code" value={item.item_code} mono />
                <Row theme={theme} label="Quantity"  value={String(item.quantity)} />
                <Row theme={theme} label="Location"  value={item.location || '—'} />
              </DetailCard>
            </div>

            {/* Images */}
            {item.images && item.images.length > 0 && (
              <div className="rounded-xl p-5"
                   style={{ background: theme.card, border: `1px solid ${theme.cardBdr}`, boxShadow: theme.cardSh }}>
                <h3 className="font-display text-lg font-bold mb-4" style={{ color: theme.navy }}>
                  Photos
                </h3>
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
                  {item.images.map(img => (
                    <a key={img.id} href={img.image} target="_blank" rel="noopener"
                       className="block rounded-lg overflow-hidden border"
                       style={{ borderColor: theme.cardBdr }}>
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={img.image} alt={img.caption || 'salvage'}
                           className="w-full h-32 object-cover" />
                      {img.caption && (
                        <div className="px-2 py-1 text-[11px]" style={{ color: theme.t2 }}>
                          {img.caption}
                        </div>
                      )}
                    </a>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  )
}

function Price({
  theme, label, value, accent,
}: { theme: any; label: string; value: string; accent?: boolean }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-wider font-semibold mb-1"
           style={{ color: theme.t3 }}>{label}</div>
      <div className="font-display-tight text-2xl font-bold tabular-nums"
           style={{ color: accent ? theme.orange : theme.navy }}>
        BWP {Number(value || 0).toLocaleString('en-BW')}
      </div>
    </div>
  )
}

function DetailCard({
  theme, icon: Icon, title, children,
}: { theme: any; icon: any; title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-xl p-5"
         style={{ background: theme.card, border: `1px solid ${theme.cardBdr}`, boxShadow: theme.cardSh }}>
      <div className="flex items-center gap-2 mb-3">
        <Icon className="w-4 h-4" style={{ color: theme.orange }} strokeWidth={2} />
        <h3 className="font-display text-base font-bold" style={{ color: theme.navy }}>
          {title}
        </h3>
      </div>
      <div className="space-y-2 text-sm">
        {children}
      </div>
    </div>
  )
}

function Row({
  theme, label, value, mono,
}: { theme: any; label: string; value: string; mono?: boolean }) {
  return (
    <div className="flex items-baseline justify-between gap-3">
      <span className="text-xs" style={{ color: theme.t3 }}>{label}</span>
      <span className={mono ? 'font-mono text-xs' : 'text-sm'}
            style={{ color: theme.text }}>
        {value}
      </span>
    </div>
  )
}

function StatusPill({ theme, status }: { theme: any; status: string }) {
  const map: Record<string, { bg: string; fg: string }> = {
    available: { bg: '#ECFDF5', fg: '#059669' },
    reserved:  { bg: '#FFFBEB', fg: '#D97706' },
    sold:      { bg: '#F5F3FF', fg: '#7C3AED' },
    on_hold:   { bg: theme.g100, fg: theme.t2 },
    scrapped:  { bg: '#FEF2F2', fg: '#DC2626' },
  }
  const c = map[status] || { bg: theme.g100, fg: theme.t2 }
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold uppercase tracking-wider"
          style={{ background: c.bg, color: c.fg }}>
      {status.replaceAll('_', ' ')}
    </span>
  )
}
