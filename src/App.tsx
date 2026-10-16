import { useEffect, useMemo, useState } from 'react'
import {
  Activity, AlertCircle, AlertTriangle, Archive, ArrowUpRight, Bot, Check, ChevronDown,
  CircleDot, Clock3, Command, Crosshair, Database, Gauge, History, Layers3, LifeBuoy,
  Menu, Pause, Play, Plus, Radio, RefreshCw, Search, Send, Settings2, ShieldCheck,
  SlidersHorizontal, Sparkles, Target, Users, X, Zap,
} from 'lucide-react'
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'

type Page = 'Command Center' | 'Incident Intelligence' | 'Resource Command' | 'Decision Lab' | 'Audit Center' | 'System Intelligence'
type Severity = 'Critical' | 'High' | 'Medium' | 'Low'
type Incident = { id: string; title: string; zone: string; severity: Severity; status: string; time: string; x: number; y: number; }

const API_BASE = import.meta.env.VITE_API_BASE_URL ?? '/api'
const api = async (path: string, init?: RequestInit) => {
  const response = await fetch(`${API_BASE}${path}`, init)
  if (response.ok) return response.json()
  let detail = `Request failed (${response.status})`
  try { detail = (await response.json()).detail ?? detail } catch { /* non-JSON error */ }
  throw new Error(detail)
}
const normalizeIncident = (item: any): Incident => {
  const rawId = String(item.id ?? item.incident_id ?? 'NEW')
  return {
  id: rawId.startsWith('INC-') ? rawId : `INC-${rawId}`,
  title: item.title ?? 'Simulated incident',
  zone: item.zone ?? `${Number(item.latitude ?? 0).toFixed(2)}, ${Number(item.longitude ?? 0).toFixed(2)}`,
  severity: item.severity >= 5 || item.risk_level === 'critical' ? 'Critical' : item.severity >= 4 || item.risk_level === 'high' ? 'High' : item.severity === 3 || item.risk_level === 'medium' ? 'Medium' : 'Low',
  status: item.status ?? 'Open',
  time: item.created_at ? `${Math.max(0, Math.round((Date.now() - Date.parse(item.created_at)) / 60000))}m ago` : 'just now',
  x: Math.max(8, Math.min(92, ((Number(item.longitude ?? -74) + 74.02) * 260))),
  y: Math.max(8, Math.min(92, ((40.74 - Number(item.latitude ?? 40.72)) * 260))),
  }
}
const nav: { label: Page; icon: typeof Command; hint: string }[] = [
  { label: 'Command Center', icon: Command, hint: 'Live operational picture' },
  { label: 'Incident Intelligence', icon: Crosshair, hint: 'Triage & investigations' },
  { label: 'Resource Command', icon: Users, hint: 'Assets & personnel' },
  { label: 'Decision Lab', icon: Sparkles, hint: 'Scenario planning' },
  { label: 'Audit Center', icon: History, hint: 'Governance & traceability' },
  { label: 'System Intelligence', icon: Gauge, hint: 'Health & telemetry' },
]
const seedIncidents: Incident[] = [
  { id: 'INC-2048', title: 'Multi-vehicle collision', zone: 'North Harbor · A-17', severity: 'Critical', status: 'Responding', time: '02m ago', x: 67, y: 27 },
  { id: 'INC-2047', title: 'Power substation anomaly', zone: 'East Grid · S-04', severity: 'High', status: 'Assessing', time: '08m ago', x: 78, y: 62 },
  { id: 'INC-2046', title: 'Unconfirmed smoke signal', zone: 'West Ridge · W-12', severity: 'Medium', status: 'Investigating', time: '16m ago', x: 29, y: 45 },
  { id: 'INC-2045', title: 'Flood gate sensor alert', zone: 'South Basin · F-02', severity: 'Low', status: 'Monitoring', time: '31m ago', x: 42, y: 74 },
]
const flow = [{ time: '06:00', critical: 2, active: 12 }, { time: '08:00', critical: 4, active: 18 }, { time: '10:00', critical: 3, active: 15 }, { time: '12:00', critical: 6, active: 25 }, { time: '14:00', critical: 4, active: 21 }, { time: '16:00', critical: 5, active: 29 }]
const response = [{ name: 'EMS', value: 84 }, { name: 'Fire', value: 68 }, { name: 'Police', value: 76 }, { name: 'Utility', value: 51 }]

export default function App() {
  const [page, setPage] = useState<Page>('Command Center')
  const [incidents, setIncidents] = useState(seedIncidents)
  const [connected, setConnected] = useState(false)
  const [simulating, setSimulating] = useState(false)
  const [filter, setFilter] = useState<'All' | Severity>('All')
  const [showCreate, setShowCreate] = useState(false)
  const [mobileNav, setMobileNav] = useState(false)
  const [toast, setToast] = useState('')
  const [dataSource, setDataSource] = useState<'loading' | 'live' | 'fallback'>('loading')
  const [loadError, setLoadError] = useState('')

  useEffect(() => {
    api('/incidents').then(data => {
      if (!Array.isArray(data)) throw new Error('Unexpected incident response')
      setIncidents(data.map(normalizeIncident))
      setDataSource('live')
      setLoadError('')
    }).catch(error => {
      setDataSource('fallback')
      setLoadError(error instanceof Error ? error.message : 'The backend could not be reached')
    })
    const configuredWs = import.meta.env.VITE_WS_URL
    const ws = new WebSocket(configuredWs ?? `${location.protocol === 'https:' ? 'wss' : 'ws'}://${location.host}/ws/events`)
    ws.onopen = () => setConnected(true)
    ws.onclose = () => setConnected(false)
    ws.onmessage = event => { try { const item = JSON.parse(event.data); const incident = item.incident ?? item; if (item.type === 'incident.created' && incident.id) setIncidents(current => [normalizeIncident(incident), ...current].slice(0, 12)) } catch { /* demo fallback */ } }
    return () => ws.close()
  }, [])
  useEffect(() => { if (!toast) return; const timer = setTimeout(() => setToast(''), 2600); return () => clearTimeout(timer) }, [toast])
  const filtered = useMemo(() => filter === 'All' ? incidents : incidents.filter(i => i.severity === filter), [filter, incidents])
  const notify = (message: string) => setToast(message)
  const toggleSimulation = async () => {
    const next = !simulating
    try {
      await api(next ? '/simulation/start' : '/simulation/pause', { method: 'POST' })
      setSimulating(next)
      notify(next ? 'Simulation running · synthetic events enabled' : 'Simulation paused')
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Simulation update failed')
    }
  }
  const resetSimulation = async () => {
    try {
      await api('/simulation/reset', { method: 'POST' })
      setSimulating(false)
      setIncidents(seedIncidents)
      setDataSource('fallback')
      setLoadError('Simulation reset uses the local synthetic baseline')
      notify('Simulation reset to baseline')
    } catch (error) {
      notify(error instanceof Error ? error.message : 'Simulation reset failed')
    }
  }
  return <div className="app-shell">
    <aside className={`sidebar ${mobileNav ? 'open' : ''}`}>
      <div className="brand"><div className="brand-mark"><LifeBuoy size={20} /></div><div><strong>RESQ-Z <span>AI</span></strong><small>MISSION CONTROL</small></div></div>
      <div className="workspace-switch"><div className="status-pulse" /> National Response Grid <ChevronDown size={14} /></div>
      <nav aria-label="Primary navigation">{nav.map(({ label, icon: Icon, hint }) => <button key={label} className={page === label ? 'nav-item active' : 'nav-item'} onClick={() => { setPage(label); setMobileNav(false) }}><Icon size={18} /><span>{label}<small>{hint}</small></span>{label === 'Incident Intelligence' && <b className="nav-count">4</b>}</button>)}</nav>
      <div className="sidebar-bottom"><div className="operator"><div className="avatar">AL</div><div><strong>Alex Lee</strong><small>Duty Commander</small></div><Settings2 size={16} /></div><div className="system-status"><span className="online-dot" /> All systems operational</div></div>
    </aside>
    <main className="main-content">
      <header className="topbar"><button className="mobile-menu" onClick={() => setMobileNav(!mobileNav)}><Menu /></button><div className="breadcrumbs">OPERATIONS <span>/</span> <strong>{page.toUpperCase()}</strong></div><div className="top-actions"><div className="connection"><span className={dataSource === 'live' && connected ? 'online-dot' : 'demo-dot'} /> {dataSource === 'loading' ? 'CONNECTING' : dataSource === 'live' && connected ? 'LIVE API' : dataSource === 'fallback' ? 'SYNTHETIC FALLBACK' : 'API ONLY'}</div><button className="icon-btn" title="Search"><Search size={18} /></button><button className="icon-btn" title="Notifications"><AlertCircle size={18} /><i /></button><div className="top-avatar">AL</div></div></header>
      <div className="page-content">{dataSource === 'loading' && <div className="integration-notice" role="status">Connecting to the backend; the baseline incidents shown are synthetic until live data loads.</div>}{loadError && <div className="integration-notice" role="status">Backend unavailable: {loadError}. Showing synthetic demo incidents; actions will not be persisted.</div>}{page === 'Command Center' ? <CommandCenter incidents={filtered} filter={filter} setFilter={setFilter} setShowCreate={setShowCreate} simulating={simulating} toggleSimulation={toggleSimulation} resetSimulation={resetSimulation} notify={notify} /> : <SecondaryPage page={page} incidents={incidents} notify={notify} />}</div>
    </main>
    {showCreate && <CreateIncident onClose={() => setShowCreate(false)} onCreate={async item => { const created = await api('/incidents', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: item.title, description: item.zone, latitude: 40.72, longitude: -74.0, severity: item.severity === 'Critical' ? 5 : item.severity === 'High' ? 4 : item.severity === 'Medium' ? 3 : 1 }) }); const incident = normalizeIncident(created); setIncidents(current => [incident, ...current]); setDataSource('live'); setLoadError(''); setShowCreate(false); notify(`${incident.id} created and queued for triage`) }} />}
    {toast && <div className="toast"><Check size={16} /> {toast}</div>}
  </div>
}

function CommandCenter({ incidents, filter, setFilter, setShowCreate, simulating, toggleSimulation, resetSimulation, notify }: { incidents: Incident[]; filter: 'All' | Severity; setFilter: (f: 'All' | Severity) => void; setShowCreate: (v: boolean) => void; simulating: boolean; toggleSimulation: () => void; resetSimulation: () => void; notify: (s: string) => void }) {
  return <><section className="page-heading"><div><div className="eyebrow"><Radio size={14} /> REAL-TIME OPERATIONS</div><h1>Command Center</h1><p>Unified situational awareness across the response network.</p></div><div className="heading-actions"><button className="btn secondary" onClick={resetSimulation}><RefreshCw size={15} /> Reset</button><button className={`btn ${simulating ? 'danger' : 'primary'}`} onClick={toggleSimulation}>{simulating ? <Pause size={15} /> : <Play size={15} />}{simulating ? 'Pause simulation' : 'Run simulation'}</button></div></section>
    <section className="metric-grid">{[['Active incidents', '12', '+3 today', 'red', AlertTriangle], ['Units deployed', '48', '82% capacity', 'cyan', Users], ['Avg. response time', '08:42', '−12% vs. target', 'green', Clock3], ['Network health', '99.97%', 'All services nominal', 'amber', Activity]].map(([label, value, note, tone, Icon]) => <div className="metric-card" key={label as string}><div className={`metric-icon ${tone}`}><Icon size={18} /></div><div><small>{label as string}</small><strong>{value as string}</strong><span className={String(note).startsWith('−') ? 'positive' : ''}>{note as string}</span></div><ArrowUpRight className="metric-trend" size={16} /></div>)}</section>
    <section className="dashboard-grid"><div className="panel map-panel"><PanelHeader title="Live incident picture" subtitle="NATIONAL GRID · UPDATED JUST NOW" action={<button className="text-btn" onClick={() => notify('Map view centered on active incidents')}>Center view <Target size={14} /></button>} /><div className="incident-map" aria-label="Accessible incident map visualization"><div className="map-grid" /><div className="map-route route-one" /><div className="map-route route-two" />{incidents.map(i => <button key={i.id} className={`map-pin ${i.severity.toLowerCase()}`} style={{ left: `${i.x}%`, top: `${i.y}%` }} title={`${i.id}: ${i.title}`} onClick={() => notify(`${i.id} · ${i.title}`)}><span /><b>{i.id.replace('INC-', '')}</b></button>)}<div className="map-legend"><span><i className="pin-dot critical" /> Critical</span><span><i className="pin-dot high" /> High</span><span><i className="pin-dot medium" /> Medium</span></div><div className="map-scale">NORTH ▲<br /><span>──── 10 km</span></div></div><div className="map-footer"><span><CircleDot size={14} /> {incidents.length} plotted incidents</span><span><Layers3 size={14} /> 3 operational layers</span><button className="text-btn" onClick={() => notify('Opening expanded map layer controls')}><SlidersHorizontal size={14} /> Layers</button></div></div>
      <div className="panel flow-panel"><PanelHeader title="Incident flow" subtitle="LAST 12 HOURS" action={<button className="icon-btn"><MoreIcon /></button>} /><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={flow}><defs><linearGradient id="cyanFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#20d4e6" stopOpacity=".28" /><stop offset="100%" stopColor="#20d4e6" stopOpacity="0" /></linearGradient></defs><CartesianGrid stroke="#1b334b" vertical={false} /><XAxis dataKey="time" stroke="#6c8299" tickLine={false} axisLine={false} /><YAxis stroke="#6c8299" tickLine={false} axisLine={false} width={25} /><Tooltip contentStyle={{ background: '#0f2033', border: '1px solid #284561', borderRadius: 8 }} /><Area type="monotone" dataKey="active" stroke="#20d4e6" fill="url(#cyanFill)" strokeWidth={2} /><Line type="monotone" dataKey="critical" stroke="#ff5964" strokeWidth={2} dot={false} /></AreaChart></ResponsiveContainer></div><div className="chart-key"><span><i className="key cyan" /> Active</span><span><i className="key red" /> Critical</span><strong>29 <small>peak active</small></strong></div></div></section>
    <section className="lower-grid"><div className="panel incidents-panel"><PanelHeader title="Priority queue" subtitle="TRIAGE REQUIRED" action={<div className="filter-row">{(['All', 'Critical', 'High', 'Medium'] as const).map(f => <button key={f} className={filter === f ? 'filter active' : 'filter'} onClick={() => setFilter(f)}>{f}</button>)}<button className="btn small primary" onClick={() => setShowCreate(true)}><Plus size={14} /> New incident</button></div>} /><div className="table-wrap"><table><thead><tr><th>INCIDENT</th><th>ZONE</th><th>SEVERITY</th><th>STATUS</th><th>AGE</th><th /></tr></thead><tbody>{incidents.map(i => <tr key={i.id}><td><strong className="incident-id">{i.id}</strong><span>{i.title}</span></td><td>{i.zone}</td><td><span className={`severity ${i.severity.toLowerCase()}`}><i />{i.severity}</span></td><td><span className="status">{i.status}</span></td><td>{i.time}</td><td><button className="row-action" onClick={() => notify(`Opening intelligence brief for ${i.id}`)}><ArrowUpRight size={16} /></button></td></tr>)}</tbody></table></div></div><div className="panel readiness-panel"><PanelHeader title="Response readiness" subtitle="RESOURCE AVAILABILITY" /><div className="readiness-chart"><ResponsiveContainer width="100%" height="100%"><BarChart data={response} layout="vertical" margin={{ left: 0, right: 20 }}><XAxis type="number" domain={[0, 100]} hide /><YAxis dataKey="name" type="category" stroke="#9bb0c3" axisLine={false} tickLine={false} width={52} /><Bar dataKey="value" fill="#20d4e6" radius={[0, 4, 4, 0]} barSize={9} label={{ position: 'right', fill: '#e8f2f5', fontSize: 11 }} /></BarChart></ResponsiveContainer></div><div className="readiness-foot"><span><i className="online-dot" /> 48 available</span><span><i className="busy-dot" /> 11 engaged</span></div></div></section></>
}

function SecondaryPage({ page, incidents, notify }: { page: Page; incidents: Incident[]; notify: (s: string) => void }) {
  const details: Record<Page, { icon: typeof Command; kicker: string; title: string; description: string }> = {
    'Incident Intelligence': { icon: Crosshair, kicker: 'ANALYSIS WORKBENCH', title: 'Incident Intelligence', description: 'Investigate signals, correlate evidence, and turn live events into actionable briefs.' },
    'Resource Command': { icon: Users, kicker: 'FORCE READINESS', title: 'Resource Command', description: 'Coordinate people, vehicles, equipment, and specialist capabilities across the grid.' },
    'Decision Lab': { icon: Sparkles, kicker: 'SCENARIO PLANNING', title: 'Decision Lab', description: 'Test what-if scenarios and compare response plans before committing resources.' },
    'Audit Center': { icon: History, kicker: 'GOVERNANCE TRAIL', title: 'Audit Center', description: 'Trace every decision, approval, and automated recommendation with confidence.' },
    'System Intelligence': { icon: Gauge, kicker: 'PLATFORM TELEMETRY', title: 'System Intelligence', description: 'Monitor API health, model performance, event throughput, and operational SLOs.' },
    'Command Center': { icon: Command, kicker: '', title: '', description: '' },
  }
  const info = details[page]; const Icon = info.icon
  return <><section className="page-heading"><div><div className="eyebrow"><Icon size={14} /> {info.kicker}</div><h1>{info.title}</h1><p>{info.description}</p></div><button className="btn primary" onClick={() => notify(`${page} refreshed`)}><RefreshCw size={15} /> Refresh data</button></section><div className="placeholder-grid"><div className="panel hero-panel"><div className="hero-icon"><Icon size={26} /></div><h2>Operational workspace ready</h2><p>Connect your FastAPI services to populate this view with live {page.toLowerCase()} data. The shell is designed for keyboard-first, high-signal operations.</p><div className="quick-actions"><button className="btn secondary" onClick={() => notify('Demo action queued')}><Zap size={15} /> Run demo action</button><button className="btn secondary" onClick={() => notify('Export prepared')}><Archive size={15} /> Export view</button></div></div><div className="panel mini-list"><PanelHeader title="Latest signals" subtitle="STREAMING NOW" /><div>{incidents.slice(0, 4).map(i => <button className="signal-row" key={i.id} onClick={() => notify(`${i.id} selected`)}><span className={`signal-icon ${i.severity.toLowerCase()}`}><AlertTriangle size={14} /></span><span><strong>{i.id}</strong><small>{i.title}</small></span><span className="signal-time">{i.time}</span></button>)}</div></div><div className="panel stat-panel"><PanelHeader title="What-if controls" subtitle="SIMULATION PARAMETERS" /><label>Response posture <select><option>Balanced response</option><option>Maximum containment</option><option>Preserve resources</option></select></label><label>Dispatch radius <input type="range" defaultValue="62" /></label><label>Confidence threshold <input type="range" defaultValue="78" /></label><button className="btn primary full" onClick={() => notify('Scenario evaluated with current controls')}><Sparkles size={15} /> Evaluate scenario</button></div></div></>
}

function PanelHeader({ title, subtitle, action }: { title: string; subtitle: string; action?: React.ReactNode }) { return <div className="panel-header"><div><h2>{title}</h2><small>{subtitle}</small></div>{action}</div> }
function MoreIcon() { return <span className="more-icon">•••</span> }
function CreateIncident({ onClose, onCreate }: { onClose: () => void; onCreate: (i: { title: string; zone: string; severity: Severity }) => Promise<void> }) {
  const [title, setTitle] = useState(''); const [zone, setZone] = useState(''); const [severity, setSeverity] = useState<Severity>('High'); const [saving, setSaving] = useState(false); const [error, setError] = useState('')
  const submit = async () => {
    setSaving(true); setError('')
    try { await onCreate({ title: title || 'Manual incident report', zone: zone || 'Unassigned zone', severity }) }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Unable to create incident') }
    finally { setSaving(false) }
  }
  return <div className="modal-backdrop" onMouseDown={onClose}><form className="modal" onSubmit={e => { e.preventDefault(); void submit() }} onMouseDown={e => e.stopPropagation()}><div className="modal-head"><div><div className="eyebrow"><Plus size={14} /> MANUAL INTAKE</div><h2>Create incident</h2></div><button type="button" className="icon-btn" onClick={onClose}><X size={18} /></button></div><label>Incident title<input value={title} onChange={e => setTitle(e.target.value)} placeholder="Describe the event" autoFocus /></label><label>Zone or location<input value={zone} onChange={e => setZone(e.target.value)} placeholder="e.g. North Harbor · A-17" /></label><label>Severity<select value={severity} onChange={e => setSeverity(e.target.value as Severity)}><option>Critical</option><option>High</option><option>Medium</option><option>Low</option></select></label>{error && <div className="form-error" role="alert">{error}</div>}<div className="modal-actions"><button type="button" className="btn secondary" onClick={onClose}>Cancel</button><button className="btn primary" type="submit" disabled={saving}>{saving ? 'Saving…' : <><Send size={15} /> Create incident</>}</button></div></form></div>
}
