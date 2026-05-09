'use client'
import React, { useState } from 'react'
import AppShell from '@/components/layout/AppShell'
import { diagnosticsApi } from '@/lib/api'
import { useRouter } from 'next/navigation'
import { Info } from 'lucide-react'

const PAYMENT_METHODS = ['Visa','Mastercard','Amex','Apple Pay','Google Pay','PayPal','Klarna','iDEAL','SEPA','Bancontact','Sofort','BACS','ACH']

export default function ManualEntryPage() {
  const router = useRouter()
  const [submitting, setSubmitting] = useState(false)
  const [selectedMethods, setSelectedMethods] = useState<string[]>(['Visa','Mastercard'])
  const [form, setForm] = useState({
    company_name:'',website:'',vertical:'retail',tier:'core',
    monthly_volume:'',monthly_transactions:'',avg_order_value:'',cross_border_pct:'',psps_used:'',regions:'',
    auth_rate:'',decline_rate:'',soft_decline_pct:'',hard_decline_pct:'',top_decline_reasons:'',
    chargeback_rate:'',refund_rate:'',retry_enabled:'',retry_notes:'',
    checkout_currencies:'',settlement_currencies:'',
    pricing_model:'',mdr:'',fx_fee_spread:'',scheme_fee_visibility:'',acquiring_setup:'',routing_setup:'',additional_context:'',
  })

  const set = (k: string) => (e: React.ChangeEvent<HTMLInputElement|HTMLSelectElement|HTMLTextAreaElement>) =>
    setForm(p => ({ ...p, [k]: e.target.value }))

  const toggleMethod = (m: string) =>
    setSelectedMethods(prev => prev.includes(m) ? prev.filter(x => x !== m) : [...prev, m])

  const handleSubmit = async () => {
    if (!form.company_name || !form.monthly_volume) { alert('Company name and monthly volume are required.'); return }
    setSubmitting(true)
    try {
      const p = {
        company_name: form.company_name, website: form.website||null, vertical: form.vertical, tier: form.tier,
        monthly_volume: form.monthly_volume ? parseFloat(form.monthly_volume.replace(/,/g,'')) : null,
        monthly_transactions: form.monthly_transactions ? parseInt(form.monthly_transactions.replace(/,/g,'')) : null,
        avg_order_value: form.avg_order_value ? parseFloat(form.avg_order_value) : null,
        cross_border_pct: form.cross_border_pct ? parseFloat(form.cross_border_pct) : null,
        psps_used: form.psps_used ? form.psps_used.split(',').map(s=>s.trim()).filter(Boolean) : [],
        regions: form.regions||null,
        auth_rate: form.auth_rate ? parseFloat(form.auth_rate) : null,
        decline_rate: form.decline_rate ? parseFloat(form.decline_rate) : null,
        soft_decline_pct: form.soft_decline_pct ? parseFloat(form.soft_decline_pct) : null,
        hard_decline_pct: form.hard_decline_pct ? parseFloat(form.hard_decline_pct) : null,
        top_decline_reasons: form.top_decline_reasons ? form.top_decline_reasons.split(',').map(s=>s.trim()).filter(Boolean) : [],
        chargeback_rate: form.chargeback_rate ? parseFloat(form.chargeback_rate) : null,
        refund_rate: form.refund_rate ? parseFloat(form.refund_rate) : null,
        payment_methods: selectedMethods,
        retry_enabled: form.retry_enabled==='true' ? true : form.retry_enabled==='false' ? false : null,
        retry_notes: form.retry_notes||null,
        checkout_currencies: form.checkout_currencies ? form.checkout_currencies.split(',').map(s=>s.trim()).filter(Boolean) : [],
        settlement_currencies: form.settlement_currencies ? form.settlement_currencies.split(',').map(s=>s.trim()).filter(Boolean) : [],
        pricing_model: form.pricing_model||null, mdr: form.mdr ? parseFloat(form.mdr) : null,
        fx_fee_spread: form.fx_fee_spread ? parseFloat(form.fx_fee_spread) : null,
        scheme_fee_visibility: form.scheme_fee_visibility||null, acquiring_setup: form.acquiring_setup||null,
        routing_setup: form.routing_setup||null, additional_context: form.additional_context||null,
      }
      const r = await diagnosticsApi.create(p)
      await diagnosticsApi.submit(r.data.id)
      router.push('/dashboard')
    } catch(e:any) { alert(e.response?.data?.detail||'Submission failed') }
    setSubmitting(false)
  }

  const Hdr = ({title,sub,badge}:{title:string;sub:string;badge?:string}) => (
    <div className="flex items-center justify-between mb-4">
      <div><div className="text-[13px] font-medium">{title}</div><div className="text-[11.5px] text-ink/40 mt-0.5">{sub}</div></div>
      {badge && <span className={`tag ${badge==='Required'?'tag-red':badge==='Recommended'?'tag-amber':'tag-purple'}`}>{badge}</span>}
    </div>
  )

  return (
    <AppShell>
      <div className="max-w-5xl">
        <div className="alert-blue mb-5"><Info size={13}/>Enter what you know — every field adds precision. Fields marked * are required.</div>
        <div className="grid grid-cols-2 gap-5">
          <div className="space-y-4">
            <div className="card">
              <Hdr title="Company information" sub="Required for all tiers" badge="Required"/>
              <div className="form-row"><label className="label">Company name *</label><input className="input" value={form.company_name} onChange={set('company_name')} placeholder="e.g. Acme Retail Ltd"/></div>
              <div className="form-grid-2">
                <div className="form-row"><label className="label">Website</label><input className="input" value={form.website} onChange={set('website')} placeholder="acme.com"/></div>
                <div className="form-row"><label className="label">Sector *</label>
                  <select className="input" value={form.vertical} onChange={set('vertical')}>
                    <option value="retail">Retail</option><option value="saas">SaaS / Subscription</option>
                    <option value="travel">Travel</option><option value="marketplace">Marketplace</option>
                    <option value="fintech">Financial Services</option><option value="luxury">Luxury</option>
                  </select>
                </div>
              </div>
              <div className="form-row"><label className="label">Service tier *</label>
                <select className="input" value={form.tier} onChange={set('tier')}>
                  <option value="lite">Lite – Fast entry diagnostic</option>
                  <option value="core">Core – Full diagnostic</option>
                  <option value="enterprise">Enterprise – Precision analysis</option>
                </select>
              </div>
            </div>

            <div className="card">
              <Hdr title="Payment volume" sub="Minimum required" badge="Required"/>
              <div className="form-grid-2">
                <div className="form-row"><label className="label">Monthly volume (£) *</label><input className="input" value={form.monthly_volume} onChange={set('monthly_volume')} placeholder="4,700,000"/></div>
                <div className="form-row"><label className="label">Monthly transactions</label><input className="input" value={form.monthly_transactions} onChange={set('monthly_transactions')} placeholder="82,000"/></div>
              </div>
              <div className="form-grid-2">
                <div className="form-row"><label className="label">Avg. order value (£)</label><input className="input" value={form.avg_order_value} onChange={set('avg_order_value')} placeholder="57.30"/></div>
                <div className="form-row"><label className="label">Cross-border %</label><input className="input" value={form.cross_border_pct} onChange={set('cross_border_pct')} placeholder="34"/></div>
              </div>
              <div className="form-row"><label className="label">PSPs used *</label><input className="input" value={form.psps_used} onChange={set('psps_used')} placeholder="Stripe, Adyen (comma separated)"/></div>
              <div className="form-row"><label className="label">Regions served</label><input className="input" value={form.regions} onChange={set('regions')} placeholder="UK, DE, FR, NL, US"/></div>
            </div>

            <div className="card">
              <Hdr title="Performance metrics" sub="Improves precision significantly" badge="Recommended"/>
              <div className="form-grid-2">
                <div className="form-row"><label className="label">Auth rate (%)</label><input className="input" value={form.auth_rate} onChange={set('auth_rate')} placeholder="86.2"/></div>
                <div className="form-row"><label className="label">Decline rate (%)</label><input className="input" value={form.decline_rate} onChange={set('decline_rate')} placeholder="13.8"/></div>
              </div>
              <div className="form-grid-2">
                <div className="form-row"><label className="label">Soft declines (%)</label><input className="input" value={form.soft_decline_pct} onChange={set('soft_decline_pct')} placeholder="9.2"/></div>
                <div className="form-row"><label className="label">Hard declines (%)</label><input className="input" value={form.hard_decline_pct} onChange={set('hard_decline_pct')} placeholder="4.6"/></div>
              </div>
              <div className="form-grid-2">
                <div className="form-row"><label className="label">Chargeback rate (%)</label><input className="input" value={form.chargeback_rate} onChange={set('chargeback_rate')} placeholder="0.82"/></div>
                <div className="form-row"><label className="label">Refund rate (%)</label><input className="input" value={form.refund_rate} onChange={set('refund_rate')} placeholder="4.1"/></div>
              </div>
              <div className="form-row"><label className="label">Top decline reasons</label><input className="input" value={form.top_decline_reasons} onChange={set('top_decline_reasons')} placeholder="Insufficient funds, Do not honour"/></div>
              <div className="form-row"><label className="label">Retry logic</label>
                <select className="input" value={form.retry_enabled} onChange={set('retry_enabled')}>
                  <option value="">Unknown</option><option value="false">Not configured</option><option value="true">Enabled</option>
                </select>
              </div>
              {form.retry_enabled==='true' && <div className="form-row"><label className="label">Retry notes</label><input className="input" value={form.retry_notes} onChange={set('retry_notes')} placeholder="e.g. Smart retry, 3 attempts, 12hr delay"/></div>}
              <div className="form-row">
                <label className="label">Payment methods</label>
                <div className="grid grid-cols-4 gap-1.5 mt-1">
                  {PAYMENT_METHODS.map(m=>(
                    <button key={m} type="button" onClick={()=>toggleMethod(m)}
                      className={`py-1.5 px-2 rounded text-[11px] border transition-all text-center ${selectedMethods.includes(m)?'border-brand-blue bg-brand-blue-bg text-brand-blue font-medium':'border-black/[0.13] text-ink/60 hover:border-black/20'}`}>
                      {m}
                    </button>
                  ))}
                </div>
              </div>
            </div>
          </div>

          <div className="space-y-4">
            <div className="card">
              <Hdr title="Currency setup" sub="Identifies FX leakage" badge="Recommended"/>
              <div className="form-grid-2">
                <div className="form-row"><label className="label">Checkout currencies</label><input className="input" value={form.checkout_currencies} onChange={set('checkout_currencies')} placeholder="GBP, EUR, USD"/></div>
                <div className="form-row"><label className="label">Settlement currencies</label><input className="input" value={form.settlement_currencies} onChange={set('settlement_currencies')} placeholder="GBP"/></div>
              </div>
            </div>

            <div className="card">
              <Hdr title="Advanced inputs" sub="Enterprise tier — optional for Core" badge="Enterprise"/>
              <div className="form-row"><label className="label">Pricing model</label>
                <select className="input" value={form.pricing_model} onChange={set('pricing_model')}>
                  <option value="">Unknown</option><option value="blended">Blended rate</option>
                  <option value="ic_plus_plus">IC++ (interchange plus plus)</option><option value="subscription">Subscription / flat fee</option>
                </select>
              </div>
              <div className="form-grid-2">
                <div className="form-row"><label className="label">MDR (%)</label><input className="input" value={form.mdr} onChange={set('mdr')} placeholder="1.4"/></div>
                <div className="form-row"><label className="label">FX fee / spread (%)</label><input className="input" value={form.fx_fee_spread} onChange={set('fx_fee_spread')} placeholder="1.8"/></div>
              </div>
              <div className="form-row"><label className="label">Scheme fee visibility</label>
                <select className="input" value={form.scheme_fee_visibility} onChange={set('scheme_fee_visibility')}>
                  <option value="">Unknown</option><option value="none">No visibility</option>
                  <option value="partial">Partial</option><option value="full">Full breakdown</option>
                </select>
              </div>
              <div className="form-row"><label className="label">Acquiring setup</label><input className="input" value={form.acquiring_setup} onChange={set('acquiring_setup')} placeholder="Single UK acquirer via Stripe"/></div>
              <div className="form-row"><label className="label">Routing setup</label><input className="input" value={form.routing_setup} onChange={set('routing_setup')} placeholder="No routing — single PSP"/></div>
            </div>

            <div className="card">
              <div className="text-[13px] font-medium mb-3">Additional context</div>
              <div className="form-row">
                <textarea className="input" rows={4} value={form.additional_context} onChange={set('additional_context')} style={{resize:'none'}}
                  placeholder="e.g. Recent PSP migration, seasonal spikes, known decline issue, upcoming contract renewal, specific regions with problems..."/>
              </div>
            </div>

            <div className="card" style={{background:'#F0EEE9',borderStyle:'dashed'}}>
              <div className="text-[13px] font-medium mb-1">Ready to submit?</div>
              <div className="text-[12px] text-ink/50 mb-4">Your data will be analysed by Claude AI and reviewed by our operator before release to you.</div>
              <div className="flex gap-3">
                <button onClick={()=>router.push('/submit')} className="btn-ghost flex-1 justify-center">Upload files instead</button>
                <button onClick={handleSubmit} disabled={submitting} className="btn-primary flex-1 justify-center">
                  {submitting?'Submitting...':'Submit for analysis →'}
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </AppShell>
  )
}
