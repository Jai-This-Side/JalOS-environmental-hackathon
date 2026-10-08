import { FormEvent, useCallback, useEffect, useState } from 'react'
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Activity, Bell, ChevronDown, CircleHelp, Droplets, Gauge, LayoutDashboard, Menu, Radio, Settings2, ShieldAlert, Waves, Zap } from 'lucide-react'

const API = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'
const apiOrigin = API.startsWith('http') ? new URL(API).origin : window.location.origin
const apiProtocol = API.startsWith('http') ? new URL(API).protocol : window.location.protocol
const WS = import.meta.env.VITE_WEBSOCKET_URL || `${apiProtocol === 'https:' ? 'wss:' : 'ws:'}//${new URL(apiOrigin).host}/ws/societies/demo`
type WaterStatus = { society: string; synthetic_prototype_data: boolean; observed_at: string; inventory_litres: number; capacity_litres: number; critical_reserve_litres: number; next_tanker_quantity_litres: number; level_percent: number; pump_state: string; demand_litres_per_day: number; scenario: string; tanker_eta_hours: number; runway: { hours_to_critical: number; hours_to_empty: number; risk: string }; recommendations: string[] }
type Complaint = { id: number; category: string; title: string; description: string; status: string; location?: string | null; created_at: string; photo_url?: string | null }
type AlertItem = { id: number; type: string; level: string; message: string; created_at: string; read: boolean }
type Tanker = { id: number; scheduled_arrival: string; actual_arrival: string | null; expected_quantity_litres: number; actual_quantity_litres: number | null; status: string; note: string }
type MaintenanceEvent = { id: number; event_type: string; title: string; description: string; start_time: string; end_time: string; affected_towers: string[]; severity: string; status: string }
type Anomaly = { flat_id: string; tower: string; severity: string; score: number; reason: string; possible_cause: string; detected_at: string; review: { status: string; comment: string; updated_at: string } | null }
type Tank = { id: number; name: string; capacity_litres: number; critical_reserve_litres: number; reading: { observed_at: string; water_level_litres: number; level_percent: number; inflow_litres_per_minute: number; outflow_litres_per_minute: number; pump_state: boolean } | null }
type Forecast = { model: string; model_version: string; dataset_version: string; horizons: Record<string, number> }
type TowerSummary = { id: number; name: string; flat_count: number }
type FlatUsage = { flat_id: number; flat_number: string; today_litres: number; seven_day_average_litres: number | null; thirty_day_average_litres: number | null; household_baseline_litres_per_day: number; recommended_range_litres_per_day: number[]; anomaly_score: number | null; anomaly_status: string }
type TowerUsage = { tower_id: number; tower: string; today_litres: number; flats: FlatUsage[] }
const fmt = (n: number) => new Intl.NumberFormat('en-IN').format(n)
const duration = (hours: number) => `${Math.floor(hours)}h ${Math.round((hours % 1) * 60)}m`
const todayLabel = new Intl.DateTimeFormat(undefined, { weekday: 'long', day: 'numeric', month: 'long' }).format(new Date())
const chartTime = (value: string) => new Intl.DateTimeFormat(undefined, { hour: '2-digit', minute: '2-digit' }).format(new Date(value))
const toLocalDateTimeInput = (date: Date) => new Date(date.getTime() - date.getTimezoneOffset() * 60000).toISOString().slice(0, 16)

function ComplaintPhoto({ url, token }: { url: string; token: string }) {
  const [imageUrl, setImageUrl] = useState<string | null>(null)
  useEffect(() => {
    let active = true
    let objectUrl: string | undefined
    setImageUrl(null)
    void fetch(url, { headers: { Authorization: `Bearer ${token}` } })
      .then(response => { if (!response.ok) throw new Error('Photo unavailable'); return response.blob() })
      .then(blob => { const url = URL.createObjectURL(blob); if (active) { objectUrl = url; setImageUrl(url) } else URL.revokeObjectURL(url) })
      .catch(() => { if (active) setImageUrl(null) })
    return () => { active = false; if (objectUrl) URL.revokeObjectURL(objectUrl) }
  }, [url, token])
  return imageUrl ? <a href={imageUrl} target="_blank" rel="noreferrer" aria-label="Open complaint photo"><img src={imageUrl} alt="Resident complaint attachment" style={{ width: 72, height: 52, objectFit: 'cover', borderRadius: 7, border: '1px solid #e7edeb' }}/></a> : null
}

export default function App() {
  const [data, setData] = useState<WaterStatus | null>(null)
  const [connected, setConnected] = useState(false)
  const [busy, setBusy] = useState(false)
  const [message, setMessage] = useState('')
  const [multiplier, setMultiplier] = useState(1.2)
  const [delay, setDelay] = useState(8)
  const [scenarioQuantity, setScenarioQuantity] = useState(12000)
  const [scenarioPumpAvailable, setScenarioPumpAvailable] = useState(true)
  const [scenarioConservation, setScenarioConservation] = useState(0)
  const [simulation, setSimulation] = useState<{ scenario: WaterStatus['runway']; baseline: WaterStatus['runway']; recommendations: string[] } | null>(null)
  const [history, setHistory] = useState<{ t: string; demand: number }[]>([])
  const [anomalies, setAnomalies] = useState<Anomaly[]>([])
  const [complaints, setComplaints] = useState<Complaint[]>([])
  const [alerts, setAlerts] = useState<AlertItem[]>([])
  const [tankers, setTankers] = useState<Tanker[]>([])
  const [maintenance, setMaintenance] = useState<MaintenanceEvent[]>([])
  const [tanks, setTanks] = useState<Tank[]>([])
  const [forecast, setForecast] = useState<Forecast | null>(null)
  const [towers, setTowers] = useState<TowerSummary[]>([])
  const [selectedTowerId, setSelectedTowerId] = useState('')
  const [towerUsage, setTowerUsage] = useState<TowerUsage | null>(null)
  const [flatUsage, setFlatUsage] = useState<FlatUsage | null>(null)
  const [health, setHealth] = useState<Record<string, string>>({})
  const [showMaintenanceForm, setShowMaintenanceForm] = useState(false)
  const [maintenanceType, setMaintenanceType] = useState('TANK_CLEANING')
  const [maintenanceTitle, setMaintenanceTitle] = useState('')
  const [maintenanceDescription, setMaintenanceDescription] = useState('')
  const [maintenanceSeverity, setMaintenanceSeverity] = useState('INFO')
  const [maintenanceStart, setMaintenanceStart] = useState(() => { const date = new Date(); date.setDate(date.getDate() + 1); date.setHours(10, 0, 0, 0); return toLocalDateTimeInput(date) })
  const [maintenanceEnd, setMaintenanceEnd] = useState(() => { const date = new Date(); date.setDate(date.getDate() + 1); date.setHours(12, 0, 0, 0); return toLocalDateTimeInput(date) })
  const [maintenanceTower, setMaintenanceTower] = useState('')
  const [showTankerForm, setShowTankerForm] = useState(false)
  const [tankerEta, setTankerEta] = useState(12)
  const [tankerQuantity, setTankerQuantity] = useState(12000)
  const [tankerNote, setTankerNote] = useState('')
  const [token, setToken] = useState(() => sessionStorage.getItem('jalos_admin_token') ?? '')
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [activeSection, setActiveSection] = useState('dashboard')
  const [sidebarOpen, setSidebarOpen] = useState(false)
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')

  const refresh = useCallback(async () => {
    if (!token) return
    try {
      const headers = { Authorization: `Bearer ${token}` }
      const [res, chartRes, anomalyRes, complaintRes, alertRes, tankerRes, maintenanceRes, tankRes, forecastRes, towerRes, healthRes, meRes] = await Promise.all([fetch(`${API}/water/status`, { headers }), fetch(`${API}/consumption/society`), fetch(`${API}/anomalies`, { headers }), fetch(`${API}/complaints`, { headers }), fetch(`${API}/alerts`, { headers }), fetch(`${API}/tankers`, { headers }), fetch(`${API}/maintenance`, { headers }), fetch(`${API}/tanks`, { headers }), fetch(`${API}/forecasts`, { headers }), fetch(`${API}/towers`, { headers }), fetch(`${API}/health/components`), fetch(`${API}/auth/me`, { headers })]);
      if ([res, chartRes, anomalyRes, complaintRes, alertRes, tankerRes, maintenanceRes, tankRes, forecastRes, towerRes, healthRes, meRes].some(response => !response.ok)) throw new Error('API unavailable');
      const towerRows: TowerSummary[] = await towerRes.json()
      const admin = await meRes.json()
      setData(await res.json()); setHistory((await chartRes.json()).series); setAnomalies(await anomalyRes.json()); setComplaints(await complaintRes.json()); setAlerts(await alertRes.json()); setTankers(await tankerRes.json()); setMaintenance(await maintenanceRes.json()); setTanks(await tankRes.json()); setForecast(await forecastRes.json()); setTowers(towerRows); setHealth(await healthRes.json()); setSelectedTowerId(current => current || String(towerRows[0]?.id ?? '')); setEmail(admin.email); setMessage('');
    }
    catch { setMessage('Waiting for JalOS API. Start the services with docker compose up --build.') }
  }, [token])

  useEffect(() => {
    if (!token || !selectedTowerId) return
    let active = true
    void fetch(`${API}/consumption/tower/${selectedTowerId}`, { headers: { Authorization: `Bearer ${token}` } })
      .then(response => { if (!response.ok) throw new Error(); return response.json() })
      .then((result: TowerUsage) => { if (active) { setTowerUsage(result); setFlatUsage(null) } })
      .catch(() => { if (active) setTowerUsage(null) })
    return () => { active = false }
  }, [selectedTowerId, token])

  useEffect(() => {
    if (!token) return
    void refresh()
    const poll = window.setInterval(() => void refresh(), 15000)
    let socket: WebSocket | undefined
    let retry: number
    const connect = () => {
      socket = new WebSocket(WS)
      socket.onopen = () => { socket?.send(JSON.stringify({ token })); setConnected(true) }
      socket.onclose = () => { setConnected(false); retry = window.setTimeout(connect, 2500) }
      socket.onerror = () => socket?.close()
      socket.onmessage = (event) => { try { const packet = JSON.parse(event.data); if (packet.data) setData(packet.data) } catch { /* ignore invalid frames */ } }
    }
    connect()
    return () => { window.clearInterval(poll); window.clearTimeout(retry); socket?.close() }
  }, [refresh, token])

  async function signIn(event: FormEvent) {
    event.preventDefault(); setBusy(true); setMessage('')
    try {
      const res = await fetch(`${API}/auth/login`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password }) })
      if (!res.ok) throw new Error('Email or password is incorrect.')
      const result = await res.json()
      if (result.user.role !== 'ADMIN' && result.user.role !== 'SUPER_ADMIN') throw new Error('Use an administrator account for the operations dashboard.')
      sessionStorage.setItem('jalos_admin_token', result.access_token); setToken(result.access_token); setPassword('')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not sign in.') }
    finally { setBusy(false) }
  }

  function signOut() { sessionStorage.removeItem('jalos_admin_token'); setToken(''); setData(null); setHistory([]); setAnomalies([]); setComplaints([]); setAlerts([]); setTankers([]); setMaintenance([]) }

  async function advanceComplaint(complaint: Complaint) {
    const next = complaint.status === 'OPEN' ? 'ACKNOWLEDGED' : complaint.status === 'ACKNOWLEDGED' ? 'IN_PROGRESS' : 'RESOLVED'
    try {
      const res = await fetch(`${API}/complaints/${complaint.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ status: next, comment: `Status changed to ${next.toLowerCase().replaceAll('_', ' ')} by the society admin.` }) })
      if (!res.ok) throw new Error()
      await refresh()
    } catch { setMessage('Could not update this complaint. Please try again.') }
  }

  async function reviewAnomaly(anomaly: Anomaly, status: 'REVIEWED' | 'FALSE_POSITIVE' | 'RESOLVED') {
    try {
      const res = await fetch(`${API}/anomalies/${encodeURIComponent(anomaly.flat_id)}/review`, { method: 'PATCH', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ status }) })
      if (!res.ok) throw new Error()
      setMessage(`${anomaly.flat_id} marked ${status.toLowerCase().replaceAll('_', ' ')}.`)
      await refresh()
    } catch { setMessage('Could not save the anomaly review state.') }
  }

  async function markAlertRead(alertId: number) {
    try {
      const res = await fetch(`${API}/alerts/${alertId}/read`, { method: 'PATCH', headers: { Authorization: `Bearer ${token}` } })
      if (!res.ok) throw new Error()
      await refresh()
    } catch { setMessage('Could not update this alert.') }
  }

  async function showFlatUsage(flatId: number) {
    try {
      const res = await fetch(`${API}/consumption/flat/${flatId}`, { headers: { Authorization: `Bearer ${token}` } })
      if (!res.ok) throw new Error()
      setFlatUsage(await res.json())
    } catch { setMessage('Could not load this flat’s consumption details.') }
  }

  async function changePassword(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    try {
      const res = await fetch(`${API}/auth/password`, { method: 'PATCH', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ current_password: currentPassword, new_password: newPassword }) })
      const result = await res.json()
      if (!res.ok) throw new Error(result.detail ?? 'Could not change password.')
      setCurrentPassword(''); setNewPassword(''); setMessage('Administrator password changed.')
    } catch (error) { setMessage(error instanceof Error ? error.message : 'Could not change password.') }
    finally { setBusy(false) }
  }

  async function scheduleMaintenance(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    try {
      const res = await fetch(`${API}/maintenance`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ event_type: maintenanceType, title: maintenanceTitle, description: maintenanceDescription, start_time: new Date(maintenanceStart).toISOString(), end_time: new Date(maintenanceEnd).toISOString(), affected_towers: maintenanceTower ? [maintenanceTower] : [], severity: maintenanceSeverity }) })
      if (!res.ok) throw new Error('Invalid maintenance window')
      setMaintenanceTitle(''); setMaintenanceDescription(''); setShowMaintenanceForm(false)
      setMessage('Maintenance notice scheduled and resident alerts created.')
      await refresh()
    } catch { setMessage('Could not schedule maintenance. Check that the end time is later than the start time.') }
    finally { setBusy(false) }
  }

  async function updateMaintenance(item: MaintenanceEvent, status: 'CANCELLED' | 'COMPLETED') {
    try {
      const res = await fetch(`${API}/maintenance/${item.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ status }) })
      if (!res.ok) throw new Error()
      await refresh()
      setMessage(`Maintenance marked ${status.toLowerCase()}.`)
    } catch { setMessage('Could not update the maintenance notice.') }
  }

  async function scheduleTanker(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    try {
      const res = await fetch(`${API}/tankers`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ scheduled_eta_hours: tankerEta, expected_quantity_litres: tankerQuantity, note: tankerNote }) })
      if (!res.ok) throw new Error()
      setShowTankerForm(false); setTankerNote('')
      setMessage('Upcoming tanker delivery scheduled; water runway recalculated.')
      await refresh()
    } catch { setMessage('Could not schedule the tanker. Check the ETA and delivery quantity.') }
    finally { setBusy(false) }
  }

  async function updateTanker(item: Tanker, status: 'DELAYED' | 'CANCELLED') {
    try {
      const currentEta = data?.observed_at ? Math.max(0, (new Date(item.scheduled_arrival).getTime() - new Date(data.observed_at).getTime()) / 3600000) : 0
      const res = await fetch(`${API}/tankers/${item.id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ status, ...(status === 'DELAYED' ? { scheduled_eta_hours: currentEta + 8 } : {}) }) })
      if (!res.ok) throw new Error()
      await refresh()
      setMessage(status === 'DELAYED' ? 'Tanker delayed by 8 hours; water runway recalculated.' : 'Tanker delivery cancelled.')
    } catch { setMessage('Could not update the tanker schedule.') }
  }

  async function trigger(name: string) {
    setBusy(true)
    try { const res = await fetch(`${API}/demo/scenarios/${name}`, { method: 'POST', headers: { Authorization: `Bearer ${token}` } }); if (!res.ok) throw new Error(); setData(await res.json()); setMessage(`${name.replaceAll('_', ' ')} applied to demo telemetry.`) }
    catch { setMessage('Could not trigger the demo event. Check that the backend is running.') }
    finally { setBusy(false) }
  }
  async function simulate() {
    setBusy(true)
    try {
      const res = await fetch(`${API}/simulations`, { method: 'POST', headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${token}` }, body: JSON.stringify({ consumption_multiplier: multiplier, tanker_delay_hours: delay, tanker_quantity_litres: scenarioQuantity, pump_available: scenarioPumpAvailable, conservation_percent: scenarioConservation }) })
      if (!res.ok) throw new Error()
      setSimulation(await res.json())
    } catch { setMessage('Simulation unavailable. Check the backend connection.') }
    finally { setBusy(false) }
  }
  const risk = data?.runway.risk ?? '—'
  const navItems = [
    { id: 'dashboard', label: 'Command center', icon: <LayoutDashboard size={17}/> },
    { id: 'water-analytics', label: 'Water analytics', icon: <Waves size={17}/> },
    { id: 'tanks', label: 'Tanks', icon: <Gauge size={17}/> },
    { id: 'consumption', label: 'Consumption', icon: <Activity size={17}/> },
    { id: 'forecasts', label: 'Forecasts', icon: <Activity size={17}/> },
    { id: 'anomalies', label: 'Anomalies', icon: <ShieldAlert size={17}/> },
    { id: 'tankers', label: 'Tankers', icon: <Waves size={17}/> },
    { id: 'simulator', label: 'Shortage simulator', icon: <Zap size={17}/> },
    { id: 'complaints', label: 'Complaints', icon: <CircleHelp size={17}/> },
    { id: 'alerts', label: 'Alerts', icon: <Bell size={17}/> },
    { id: 'maintenance', label: 'Maintenance', icon: <Settings2 size={17}/> },
    { id: 'system-health', label: 'System health', icon: <Radio size={17}/> },
    { id: 'settings', label: 'Settings', icon: <Settings2 size={17}/> },
  ]
  function navigateTo(id: string) {
    setActiveSection(id)
    setSidebarOpen(false)
    document.getElementById(id)?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
  const activeLabel = navItems.find(item => item.id === activeSection)?.label ?? 'Command center'

  if (!token) return <div className="login-shell"><form className="login-card" onSubmit={signIn}><div className="brand login-brand"><div className="brand-mark"><Droplets size={20}/></div><span>jalos<span className="brand-dot">.</span></span></div><div className="eyebrow">ADMINISTRATOR ACCESS</div><h1>Welcome back</h1><p>Sign in to open your society water operations center.</p>{message && <div className="notice login-notice">{message}</div>}<label>Email address<input required type="email" autoComplete="username" value={email} onChange={event => setEmail(event.target.value)}/></label><label>Password<input required type="password" autoComplete="current-password" value={password} onChange={event => setPassword(event.target.value)}/></label><button className="simulate-button" disabled={busy}>{busy ? 'Signing in…' : 'Sign in to JalOS'}</button><small>Demo account credentials are configured in your local `.env` file.</small></form></div>

  return <div className="app-shell">
    <aside className={`sidebar ${sidebarOpen ? 'sidebar-open' : ''}`}>
      <div className="brand"><div className="brand-mark"><Droplets size={20} /></div><span>jalos<span className="brand-dot">.</span></span></div>
      <div className="society-select"><div className="society-avatar">JR</div><div><b>Jal Residency</b><small>Water operations</small></div><ChevronDown size={16} /></div>
      <div className="nav-label">OPERATIONS</div>
      <nav>{navItems.slice(0, 6).map(item => <button key={item.id} className={`nav-item ${activeSection === item.id ? 'active' : ''}`} onClick={() => navigateTo(item.id)}>{item.icon}{item.label}{item.id === 'anomalies' && anomalies.length > 0 && <span className="nav-count">{anomalies.length}</span>}</button>)}</nav>
      <div className="nav-label tools-label">TOOLS</div><nav>{navItems.slice(6).map(item => <button key={item.id} className={`nav-item ${activeSection === item.id ? 'active' : ''}`} onClick={() => navigateTo(item.id)}>{item.icon}{item.label}</button>)}</nav>
      <div className="sidebar-bottom"><div className="user-avatar">JA</div><div><b>JalOS Admin</b><small>Society administrator</small></div><button className="icon-button"><CircleHelp size={17}/></button></div>
    </aside>

    <main className="main-area">
      <header className="topbar"><button className="mobile-menu" aria-label="Open navigation" onClick={() => setSidebarOpen(value => !value)}><Menu /></button><div className="crumb">Operations <span>/</span> <b>{activeLabel}</b></div><div className="top-actions"><div className={`live-chip ${connected ? 'is-live' : ''}`}><i/>{connected ? 'Live connection' : 'Connecting'}</div><button className="icon-button notification" aria-label="Alerts" onClick={() => navigateTo('alerts')}><Bell size={18}/>{alerts.some(item => !item.read) && <i/>}</button><div className="date-label">{todayLabel}</div><button className="sign-out" onClick={signOut}>Sign out</button></div></header>
      <section className="content">
        <div className="page-heading" id="dashboard"><div><div className="eyebrow">WATER OPERATIONS <span>·</span> LIVE OVERVIEW</div><h1>Good morning <span>*</span></h1><p>Your society's water picture, all in one place.</p></div><button className="outline-button" onClick={() => void refresh()}><Radio size={15}/> Refresh status</button></div>
        {message && <div className="notice"><span>{message}</span><button onClick={() => setMessage('')}>Dismiss</button></div>}
        {data?.synthetic_prototype_data && <div className="synthetic-note"><span className="pulse-dot"/> DEMO ENVIRONMENT <span>·</span> Readings are simulated prototype data</div>}

        <div className="metric-grid">
          <article className="metric-card water-card"><div className="metric-top"><span>AVAILABLE WATER</span><span className="metric-icon aqua"><Droplets size={17}/></span></div><div className="metric-value">{data ? `${data.level_percent}%` : '—'}<small>of capacity</small></div><div className="tank-meter"><div style={{ width: `${data?.level_percent ?? 0}%` }}/></div><div className="metric-foot"><b>{data ? fmt(data.inventory_litres) : '—'} L</b> usable inventory <span className="capacity">/ {data ? fmt(data.capacity_litres) : '—'} L</span></div></article>
          <article className="metric-card"><div className="metric-top"><span>TIME TO RESERVE</span><span className="metric-icon lavender"><Gauge size={17}/></span></div><div className="metric-value">{data ? duration(data.runway.hours_to_critical) : '—'}</div><div className="metric-foot"><span className={`risk-pill ${risk.toLowerCase()}`}>{risk} RISK</span><span>Reserve {data ? fmt(data.critical_reserve_litres) : '—'} L</span></div></article>
          <article className="metric-card"><div className="metric-top"><span>DAILY DEMAND</span><span className="metric-icon peach"><Activity size={17}/></span></div><div className="metric-value">{data ? `${(data.demand_litres_per_day / 1000).toFixed(1)}` : '—'}<small>kL / day</small></div><div className="metric-foot"><span className="neutral-pill">Estimated demand</span><span>across 8 towers</span></div></article>
          <article className="metric-card supply-card"><div className="metric-top"><span>NEXT EXPECTED SUPPLY</span><span className="metric-icon mint"><Waves size={17}/></span></div><div className="supply-time">{data ? `In ${duration(data.tanker_eta_hours)}` : '—'}</div><div className="supply-detail"><div className="truck-icon">↗</div><div><b>Municipal tanker · {data ? (data.next_tanker_quantity_litres / 1000).toFixed(0) : '—'} kL</b><small>Scheduled delivery</small></div></div><div className="supply-status"><span/>{data && data.tanker_eta_hours > 18 ? 'Delayed' : 'On schedule'} <span className="status-time">ETA estimate</span></div></article>
          <article className="metric-card"><div className="metric-top"><span>TODAY'S METER USE</span><span className="metric-icon aqua"><Activity size={17}/></span></div><div className="metric-value">{history.length ? history.reduce((sum, point) => sum + point.demand, 0).toFixed(1) : '—'}<small>kL / 24h</small></div><div className="metric-foot">Synthetic virtual-meter aggregate</div></article>
          <article className="metric-card"><div className="metric-top"><span>PREDICTED NEXT 24H</span><span className="metric-icon lavender"><Gauge size={17}/></span></div><div className="metric-value">{forecast ? (forecast.horizons.next_24h_litres / 1000).toFixed(1) : '—'}<small>kL</small></div><div className="metric-foot">{forecast?.model ?? 'Forecast model'}</div></article>
          <article className="metric-card"><div className="metric-top"><span>OPEN ANOMALIES</span><span className="metric-icon peach"><ShieldAlert size={17}/></span></div><div className="metric-value">{anomalies.filter(item => item.review?.status !== 'RESOLVED' && item.review?.status !== 'FALSE_POSITIVE').length}</div><div className="metric-foot">Possible signals for admin review</div></article>
          <article className="metric-card"><div className="metric-top"><span>OPEN COMPLAINTS</span><span className="metric-icon mint"><CircleHelp size={17}/></span></div><div className="metric-value">{complaints.filter(item => item.status !== 'RESOLVED' && item.status !== 'CLOSED').length}</div><div className="metric-foot">Resident-reported service issues</div></article>
        </div>

        <div className="section-row" id="water-analytics"><div><h2>Demand overview</h2><p>Society-wide synthetic meter rollups · last 24 hours</p></div><span className="select-button">Last 24 hours</span></div>
        <div className="chart-card"><div className="chart-summary"><div><span className="chart-label">CONSUMPTION</span><div className="chart-total">{history.length ? (history.reduce((sum, point) => sum + point.demand, 0) / history.length).toFixed(2) : '—'} <small>kL / hour avg.</small></div></div><div className="chart-legend"><span className="legend-now"/> Simulated meter data</div></div><div className="chart-wrap"><ResponsiveContainer width="100%" height="100%"><AreaChart data={history} margin={{ top: 10, right: 8, left: -18, bottom: 0 }}><defs><linearGradient id="demandFill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#18a889" stopOpacity={0.17}/><stop offset="95%" stopColor="#18a889" stopOpacity={0}/></linearGradient></defs><CartesianGrid stroke="#edf1ef" vertical={false}/><XAxis dataKey="t" interval={3} axisLine={false} tickLine={false} tick={{ fill:'#98a6a1',fontSize:11 }} tickFormatter={chartTime} dy={12}/><YAxis axisLine={false} tickLine={false} tick={{ fill:'#98a6a1',fontSize:11 }} tickFormatter={(v) => `${v}kL`}/><Tooltip labelFormatter={(label) => chartTime(String(label))} contentStyle={{border:'1px solid #e7edeb',borderRadius:12,boxShadow:'0 8px 24px #173a3012'}}/><Area type="monotone" dataKey="demand" stroke="#19a98a" strokeWidth={2.5} fill="url(#demandFill)" activeDot={{r:5,fill:'#fff',stroke:'#19a98a',strokeWidth:2}}/></AreaChart></ResponsiveContainer></div></div>

        <section className="panel consumption-panel" id="consumption"><div className="panel-heading"><div><h2>Consumption drilldown</h2><p>Society · tower · flat. Readings and guidance use synthetic virtual meters.</p></div><select aria-label="Choose tower" value={selectedTowerId} onChange={event => setSelectedTowerId(event.target.value)}>{towers.map(tower => <option key={tower.id} value={tower.id}>{tower.name} · {tower.flat_count} flats</option>)}</select></div>{towerUsage ? <><div className="drilldown-summary"><b>{towerUsage.tower}</b><span>{fmt(towerUsage.today_litres)} L today across {towerUsage.flats.length} flats</span></div><div className="table-wrap"><table><thead><tr><th>Flat</th><th>Today</th><th>7-day avg</th><th>30-day avg</th><th>Signal</th><th>Guidance</th></tr></thead><tbody>{towerUsage.flats.map(flat => <tr key={flat.flat_id}><td><button className="flat-link" onClick={() => void showFlatUsage(flat.flat_id)}>{flat.flat_number}</button></td><td>{fmt(flat.today_litres)} L</td><td>{flat.seven_day_average_litres == null ? 'Building history' : `${fmt(flat.seven_day_average_litres)} L`}</td><td>{flat.thirty_day_average_litres == null ? 'Building history' : `${fmt(flat.thirty_day_average_litres)} L`}</td><td><span className={`signal-pill ${flat.anomaly_status.toLowerCase()}`}>{flat.anomaly_score == null ? 'No signal' : `${flat.anomaly_status} · ${flat.anomaly_score.toFixed(2)}`}</span></td><td>{fmt(flat.recommended_range_litres_per_day[0])}–{fmt(flat.recommended_range_litres_per_day[1])} L/day</td></tr>)}</tbody></table></div>{flatUsage && <div className="flat-detail"><b>Flat {flatUsage.flat_number}</b><span>Today {fmt(flatUsage.today_litres)} L</span><span>7-day average {flatUsage.seven_day_average_litres == null ? '—' : `${fmt(flatUsage.seven_day_average_litres)} L/day`}</span><span>30-day average {flatUsage.thirty_day_average_litres == null ? '—' : `${fmt(flatUsage.thirty_day_average_litres)} L/day`}</span><span>Possible anomaly: {flatUsage.anomaly_status}{flatUsage.anomaly_score == null ? '' : ` (${flatUsage.anomaly_score.toFixed(2)})`}</span></div>}</> : <div className="empty-complaints">Loading tower consumption…</div>}</section>

        <section className="panel forecast-panel" id="forecasts"><div className="panel-heading"><div><h2>Demand forecast</h2><p>Trained seasonal ridge model on synthetic data · chronological holdout metrics available in the API.</p></div><span className="demo-tag">{forecast ? `MODEL ${forecast.model_version}` : 'LOADING'}</span></div><div className="forecast-grid">{[['Next hour', 'next_1h_litres'], ['Next 6 hours', 'next_6h_litres'], ['Next 24 hours', 'next_24h_litres'], ['Next 48 hours', 'next_48h_litres']].map(([label, key]) => <div className="forecast-metric" key={key}><small>{label}</small><b>{forecast ? `${fmt(forecast.horizons[key])} L` : '—'}</b></div>)}</div><small className="forecast-footnote">{forecast?.model ?? 'Forecast model'} · {forecast?.dataset_version ?? 'synthetic training data'} · not field validated</small></section>

        <section className="panel tanks-panel" id="tanks"><div className="panel-heading"><div><h2>Tank monitoring</h2><p>Current readings are published from the simulator; pump and flow status are shown per tank.</p></div><span className="demo-tag">{tanks.length} TANKS</span></div><div className="tank-list">{tanks.map(tank => <div className="tank-row" key={tank.id}><div className="tank-row-title"><b>{tank.name}</b><span>{tank.reading ? `${fmt(tank.reading.water_level_litres)} / ${fmt(tank.capacity_litres)} L` : 'Waiting for a reading'}</span></div><div className="tank-meter"><div style={{ width: `${tank.reading?.level_percent ?? 0}%` }}/></div><small>{tank.reading ? `${tank.reading.level_percent}% · Inflow ${tank.reading.inflow_litres_per_minute} L/min · Outflow ${tank.reading.outflow_litres_per_minute} L/min · Pump ${tank.reading.pump_state ? 'on' : 'off'}` : 'No tank telemetry yet'}</small></div>)}</div></section>

        <div className="lower-grid"><section className="panel event-panel"><div className="panel-heading"><div><h2>Demo controls</h2><p>Trigger a scenario and watch the water picture respond.</p></div><span className="demo-tag">SANDBOX</span></div><div className="event-buttons"><button disabled={busy} onClick={() => void trigger('NORMAL_DAY')}><span className="event-mark normal">â—‰</span><span><b>Normal day</b><small>Reset demand pattern</small></span></button><button disabled={busy} onClick={() => void trigger('HIGH_USAGE')}><span className="event-mark high">↗</span><span><b>High usage</b><small>Increase demand 15%</small></span></button><button disabled={busy} onClick={() => void trigger('LEAK_EVENT')}><span className="event-mark leak">âŒ</span><span><b>Possible leak</b><small>Overnight meter anomaly</small></span></button><button disabled={busy} onClick={() => void trigger('TANKER_DELAY')}><span className="event-mark delay">â—·</span><span><b>Tanker delay</b><small>Push arrival by 8 hours</small></span></button><button disabled={busy} onClick={() => void trigger('PUMP_FAILURE')}><span className="event-mark pump">ÏŸ</span><span><b>Pump failure</b><small>Stop new inflow</small></span></button><button disabled={busy} onClick={() => void trigger('SUPPLY_RESTORED')}><span className="event-mark restored">âœ“</span><span><b>Supply restored</b><small>Simulate tanker arrival</small></span></button></div></section>
          <section className="panel simulator-panel" id="simulator"><div className="panel-heading"><div><h2>Shortage simulator</h2><p>Explore a scenario without changing live readings.</p></div><span className="sim-icon"><Zap size={17}/></span></div>
            <label className="slider-label">Consumption change <b>{Math.round((multiplier - 1) * 100) >= 0 ? '+' : ''}{Math.round((multiplier - 1) * 100)}%</b></label><input className="range" type="range" min="0.5" max="2" step="0.05" value={multiplier} onChange={e => setMultiplier(Number(e.target.value))}/><div className="range-labels"><span>−50%</span><span>+100%</span></div>
            <label className="slider-label delay-label">Tanker delay <b>+{delay} hours</b></label><input className="range orange-range" type="range" min="0" max="48" step="2" value={delay} onChange={e => setDelay(Number(e.target.value))}/><div className="range-labels"><span>On time</span><span>+48 hours</span></div>
            <label className="slider-label">Expected tanker quantity <b>{fmt(scenarioQuantity)} L</b></label><input className="range" type="range" min="0" max="40000" step="1000" value={scenarioQuantity} onChange={e => setScenarioQuantity(Number(e.target.value))}/><div className="range-labels"><span>0 L</span><span>40,000 L</span></div>
            <label className="slider-label">Conservation action <b>{scenarioConservation}%</b></label><input className="range" type="range" min="0" max="80" step="5" value={scenarioConservation} onChange={e => setScenarioConservation(Number(e.target.value))}/><div className="range-labels"><span>0%</span><span>80%</span></div>
            <label className="scenario-pump"><input type="checkbox" checked={scenarioPumpAvailable} onChange={e => setScenarioPumpAvailable(e.target.checked)}/> Assume pump is available</label>
            <button className="simulate-button" disabled={busy} onClick={() => void simulate()}><Zap size={15}/> Run scenario</button>{simulation && <div className="simulation-result"><div><span>BASELINE RUNWAY</span><b>{duration(simulation.baseline.hours_to_critical)}</b></div><div><span>SCENARIO RUNWAY</span><b className="scenario-time">{duration(simulation.scenario.hours_to_critical)}</b></div><div className="result-risk">{simulation.scenario.risk} RISK</div><small>Scenario is isolated from current telemetry.</small>{simulation.recommendations.length > 0 && <small className="scenario-recommendation">Recommended: {simulation.recommendations[0]}</small>}</div>}
          </section>
        </div>

        <section className="panel anomaly-panel" id="anomalies"><div className="panel-heading"><div><h2>Possible abnormal consumption</h2><p>Synthetic demo event · review these readings before concluding a leak.</p></div><span className="demo-tag">{anomalies.length} FLATS</span></div>{anomalies.length === 0 ? <div className="empty-complaints">No current anomalies meet the review threshold.</div> : <div className="anomaly-list">{anomalies.map(item => <div className="anomaly-row" key={item.flat_id}><span className="anomaly-dot"/><div className="anomaly-summary"><b>{item.flat_id} · {item.tower}</b><small>{item.severity} · score {item.score.toFixed(2)} · detected {new Date(item.detected_at).toLocaleString()}</small><span>{item.reason}</span><small>{item.possible_cause}{item.review ? ` · ${item.review.status.toLowerCase().replaceAll('_', ' ')}` : ''}</small></div><div className="anomaly-review-actions">{(['REVIEWED', 'FALSE_POSITIVE', 'RESOLVED'] as const).map(status => <button key={status} className={item.review?.status === status ? 'selected' : ''} onClick={() => void reviewAnomaly(item, status)}>{status.replaceAll('_', ' ')}</button>)}</div></div>)}</div>}</section>

        <section className="panel complaints-panel" id="complaints"><div className="panel-heading"><div><h2>Complaint queue</h2><p>Resident-reported water issues · showing the latest four.</p></div><span className="demo-tag">{complaints.filter(item => item.status !== 'RESOLVED' && item.status !== 'CLOSED').length} OPEN</span></div>{complaints.length === 0 ? <div className="empty-complaints">No resident complaints have been submitted.</div> : <div className="complaint-list">{complaints.slice(0, 4).map(item => <div className="complaint-row" key={item.id}><div><b>{item.title}</b><small>{item.location ?? 'Location not set'} · {item.category.replaceAll('_', ' ')} · #{item.id}</small>{item.photo_url && <ComplaintPhoto url={`${API}/complaints/${item.id}/photo`} token={token}/>}</div><span className="complaint-status">{item.status.replaceAll('_', ' ')}</span><button disabled={item.status === 'RESOLVED' || item.status === 'CLOSED'} onClick={() => void advanceComplaint(item)}>{item.status === 'OPEN' ? 'Acknowledge' : item.status === 'ACKNOWLEDGED' ? 'Start work' : 'Resolve'}</button></div>)}</div>}</section>

        <section className="panel alert-center" id="alerts"><div className="panel-heading"><div><h2>Alert center</h2><p>Recent supply, shortage and complaint updates.</p></div><span className="demo-tag">{alerts.filter(item => !item.read).length} UNREAD</span></div>{alerts.length === 0 ? <div className="empty-complaints">No alerts have been recorded.</div> : <div className="alert-list">{alerts.slice(0, 20).map(item => <div className="alert-row" key={item.id}><span className={`alert-level ${item.level.toLowerCase()}`}>{item.level}</span><div><b>{item.message}</b><small>{item.type.replaceAll('_', ' ')} · {new Date(item.created_at).toLocaleString()}</small></div>{item.read ? <span className="read-indicator">Read</span> : <button className="mark-read" onClick={() => void markAlertRead(item.id)}>Mark read</button>}</div>)}</div>}</section>

        <section className="panel tanker-panel" id="tankers">
          <div className="panel-heading"><div><h2>Tanker schedule</h2><p>Delivery quantities and arrival states feed the runway engine.</p></div><button className="outline-button" onClick={() => setShowTankerForm(value => !value)}>{showTankerForm ? 'Close form' : 'Schedule delivery'}</button></div>
          {showTankerForm && <form className="tanker-form" onSubmit={event => void scheduleTanker(event)}>
            <label>ETA from now (hours)<input required type="number" min="0" max="720" step="1" value={tankerEta} onChange={event => setTankerEta(Number(event.target.value))}/></label>
            <label>Expected quantity (litres)<input required type="number" min="1" max="1000000" step="500" value={tankerQuantity} onChange={event => setTankerQuantity(Number(event.target.value))}/></label>
            <label>Delivery note<input maxLength={500} value={tankerNote} onChange={event => setTankerNote(event.target.value)} placeholder="Optional arrival details"/></label>
            <button className="simulate-button" disabled={busy}>Save delivery</button>
          </form>}
          {tankers.length === 0 ? <div className="empty-complaints">No deliveries are scheduled.</div> : <div className="tanker-list">{tankers.slice(0, 6).map(item => <div className="tanker-row" key={item.id}><div className="truck-icon">↗</div><div><b>Delivery #{item.id} · {(item.expected_quantity_litres / 1000).toFixed(1)} kL</b><small>{item.status} · ETA {new Date(item.scheduled_arrival).toLocaleString()}</small></div>{item.actual_quantity_litres != null && <span className="actual-quantity">{(item.actual_quantity_litres / 1000).toFixed(1)} kL received</span>}{(item.status === 'SCHEDULED' || item.status === 'DELAYED') && <div className="tanker-actions"><button onClick={() => void updateTanker(item, 'DELAYED')}>Delay +8h</button><button onClick={() => void updateTanker(item, 'CANCELLED')}>Cancel</button></div>}</div>)}</div>}
        </section>

        <section className="panel maintenance-panel" id="maintenance"><div className="panel-heading"><div><h2>Maintenance schedule</h2><p>Notices are visible to affected residents in the Flutter app.</p></div><button className="outline-button" onClick={() => setShowMaintenanceForm(value => !value)}>{showMaintenanceForm ? 'Close form' : 'Schedule work'}</button></div>
          {showMaintenanceForm && <form className="maintenance-form" onSubmit={event => void scheduleMaintenance(event)}>
            <label>Work type<select value={maintenanceType} onChange={event => setMaintenanceType(event.target.value)}><option value="TANK_CLEANING">Tank cleaning</option><option value="PUMP_MAINTENANCE">Pump maintenance</option><option value="PIPELINE_MAINTENANCE">Pipeline maintenance</option><option value="WATER_SHUTDOWN">Water shutdown</option></select></label>
            <label>Title<input required minLength={3} maxLength={160} value={maintenanceTitle} onChange={event => setMaintenanceTitle(event.target.value)} placeholder="e.g. Overhead tank cleaning"/></label>
            <label>Scope<select value={maintenanceTower} onChange={event => setMaintenanceTower(event.target.value)}><option value="">All towers</option>{'ABCDEFGH'.split('').map(letter => <option key={letter} value={`Tower ${letter}`}>Tower {letter}</option>)}</select></label>
            <label>Severity<select value={maintenanceSeverity} onChange={event => setMaintenanceSeverity(event.target.value)}><option value="INFO">Information</option><option value="LOW">Low</option><option value="MEDIUM">Medium</option><option value="HIGH">High</option><option value="CRITICAL">Critical</option></select></label>
            <label>Starts<input required type="datetime-local" value={maintenanceStart} onChange={event => setMaintenanceStart(event.target.value)}/></label>
            <label>Ends<input required type="datetime-local" value={maintenanceEnd} onChange={event => setMaintenanceEnd(event.target.value)}/></label>
            <label className="maintenance-description">Resident note<input maxLength={2000} value={maintenanceDescription} onChange={event => setMaintenanceDescription(event.target.value)} placeholder="What residents should expect"/></label>
            <button className="simulate-button" disabled={busy}>Publish notice</button>
          </form>}
          {maintenance.length === 0 ? <div className="empty-complaints">No maintenance is scheduled.</div> : <div className="maintenance-list">{maintenance.slice(0, 6).map(item => <div className="maintenance-row" key={item.id}><div><b>{item.title}</b><small>{item.event_type.replaceAll('_', ' ')} · {item.affected_towers.length ? item.affected_towers.join(', ') : 'All towers'} · {new Date(item.start_time).toLocaleString()}</small></div><span className="complaint-status">{item.status}</span>{item.status === 'SCHEDULED' && <div className="maintenance-actions"><button onClick={() => void updateMaintenance(item, 'COMPLETED')}>Complete</button><button onClick={() => void updateMaintenance(item, 'CANCELLED')}>Cancel</button></div>}</div>)}</div>}
        </section>

        <section className="panel system-health-panel" id="system-health"><div className="panel-heading"><div><h2>System health</h2><p>Live component status reported by FastAPI.</p></div><button className="outline-button" onClick={() => void refresh()}>Refresh</button></div><div className="health-grid">{Object.entries(health).map(([component, state]) => <div className="health-item" key={component}><span className={`health-indicator ${state === 'ok' || state === 'running' || state === 'available' || state === 'trained_seasonal_ridge' ? 'healthy' : 'unhealthy'}`}/><b>{component.replaceAll('_', ' ')}</b><span>{state}</span></div>)}</div></section>

        <section className="panel settings-panel" id="settings"><div className="panel-heading"><div><h2>Administrator settings</h2><p>Manage your access and review the active client endpoints.</p></div><span className="demo-tag">SIGNED IN</span></div><div className="settings-endpoints"><div><small>ACCOUNT</small><b>{email}</b></div><div><small>API ENDPOINT</small><b>{API}</b></div><div><small>REAL-TIME ENDPOINT</small><b>{WS}</b></div><div><small>DATA MODE</small><b>Synthetic prototype readings</b></div></div><form className="password-form" onSubmit={event => void changePassword(event)}><h3>Change administrator password</h3><label>Current password<input type="password" autoComplete="current-password" minLength={1} required value={currentPassword} onChange={event => setCurrentPassword(event.target.value)}/></label><label>New password<input type="password" autoComplete="new-password" minLength={12} required value={newPassword} onChange={event => setNewPassword(event.target.value)}/></label><button className="simulate-button" disabled={busy}>Update password</button></form></section>

        <section className="recommendation"><div className="rec-icon"><ShieldAlert size={18}/></div><div><span className="rec-eyebrow">RECOMMENDED NEXT STEP</span><h3>{data?.recommendations[0] ?? 'Connect to the API to view recommendations.'}</h3><p>Based on the current reserve runway and incoming supply schedule.</p></div><button onClick={() => navigateTo('anomalies')}>View risk factors <span>→</span></button></section>
        <footer><span>JalOS <b>·</b> Water Operations</span><span><i/> Systems operational <b>·</b> Synthetic demo data</span></footer>
      </section>
    </main>
  </div>
}
