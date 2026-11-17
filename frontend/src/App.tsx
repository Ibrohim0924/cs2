import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import type { FormEvent, ReactNode } from "react";
import { Link, NavLink, Route, Routes, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  Activity, ArrowDownToLine, ArrowLeft, ArrowRight, Award, Bell, Check, ChevronRight,
  CircleHelp, Clipboard, Coins, Crosshair, ExternalLink, Gift, Home, Layers3, LoaderCircle,
  LogOut, Menu, Shield, Sparkles, Target, Trophy, UserRound, Users, WalletCards, X,
} from "lucide-react";
import { api, clearAdminToken, clearToken, getAdminToken, getToken, setAdminToken, setToken } from "./api";
import type { CaseItem, InventoryItem, TaskItem, User } from "./types";

type Notice = { tone: "success" | "error"; text: string };

function App() {
  const [user, setUser] = useState<User | null>(null);
  const [tokenReady, setTokenReady] = useState(false);
  const [authError, setAuthError] = useState<string | null>(null);
  const [notice, setNotice] = useState<Notice | null>(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();
  const navigate = useNavigate();

  const refreshUser = useCallback(async () => setUser(await api<User>("/me")), []);
  const notify = useCallback((tone: Notice["tone"], text: string) => {
    setNotice({ tone, text });
    window.setTimeout(() => setNotice(null), 4200);
  }, []);

  useEffect(() => {
    let active = true;
    if (location.pathname.startsWith("/admin")) {
      setTokenReady(true);
      return () => { active = false; };
    }
    async function authenticate() {
      try {
        const telegram = window.Telegram?.WebApp;
        if (telegram?.initData) {
          telegram.ready();
          const result = await api<{ access_token: string }>("/auth/telegram", {
            method: "POST", body: JSON.stringify({ init_data: telegram.initData }),
          });
          setToken(result.access_token);
        } else if (!getToken() && import.meta.env.DEV) {
          const result = await api<{ access_token: string }>("/auth/demo", {
            method: "POST", body: JSON.stringify({ username: "demo_player" }),
          });
          setToken(result.access_token);
        } else if (!getToken()) {
          setAuthError("Open this Mini App through Telegram to create a player session.");
        }
        if (getToken()) await refreshUser();
      } catch (error) {
        clearToken();
        if (active) setAuthError(error instanceof Error ? error.message : "Could not connect to the service.");
      } finally {
        if (active) setTokenReady(true);
      }
    }
    void authenticate();
    return () => { active = false; };
  }, [refreshUser]);

  const shellVisible = !location.pathname.startsWith("/admin");
  const handleLogout = () => { clearToken(); setUser(null); setTokenReady(false); navigate("/"); window.location.reload(); };
  const value = useMemo(() => ({ user, refreshUser, notify }), [user, refreshUser, notify]);

  if (!tokenReady) return <LoadingScreen />;
  if (!user && !location.pathname.startsWith("/admin")) {
    return <main className="connection-screen"><div className="brand-mark"><Crosshair size={24} /></div><h1>CS2 OPEN CASE BOT</h1><p>Open the Mini App through Telegram to continue.</p><div className="notice error">{authError ?? "Could not establish a player session. Check that the backend is running."}</div></main>;
  }

  return (
    <AppContext.Provider value={value}>
      <div className="app-shell">
        {shellVisible && <aside className="sidebar">
          <Link className="brand" to="/"><span className="brand-mark"><Crosshair size={21} /></span><span>CS2 <b>OPEN CASE</b><small>COLLECTION PLATFORM</small></span></Link>
          <div className="side-label">MENU</div>
          <nav className="side-nav">
            {primaryLinks.map(([to, label, Icon]) => <NavLink key={to} to={to} end={to === "/"}><Icon size={18}/>{label}</NavLink>)}
          </nav>
          <div className="side-label side-spaced">YOUR ACCOUNT</div>
          <nav className="side-nav">
            {accountLinks.map(([to, label, Icon]) => <NavLink key={to} to={to}><Icon size={18}/>{label}</NavLink>)}
          </nav>
          <div className="sidebar-foot"><span className="online-dot"/> Development catalog <small>Transparent fixed rewards</small></div>
        </aside>}
        <main className="main-area">
          {shellVisible && <header className="topbar">
            <button className="icon-btn mobile-menu" onClick={() => setMenuOpen(!menuOpen)} aria-label="Toggle menu">{menuOpen ? <X/> : <Menu/>}</button>
            <div className="topbar-title">CS2 <span>OPEN CASE BOT</span></div>
            <div className="topbar-actions"><div className="balance-chip"><Coins size={16}/>{user?.crystals ?? 0}<span>CRYSTALS</span></div><button className="icon-btn" onClick={() => notify("success", "You're all caught up.")} aria-label="Notifications"><Bell size={18}/></button><div className="avatar">{user?.avatar_url ? <img src={user.avatar_url} alt=""/> : user?.username.slice(0, 1).toUpperCase()}</div></div>
          </header>}
          {menuOpen && <div className="mobile-menu-panel">{primaryLinks.map(([to, label, Icon]) => <NavLink key={to} to={to} onClick={() => setMenuOpen(false)}><Icon size={18}/>{label}</NavLink>)}{accountLinks.map(([to, label, Icon]) => <NavLink key={to} to={to} onClick={() => setMenuOpen(false)}><Icon size={18}/>{label}</NavLink>)}</div>}
          <Routes>
            <Route path="/" element={<HomePage/>}/>
            <Route path="/cases" element={<CasesPage/>}/>
            <Route path="/cases/:slug" element={<CaseDetailPage/>}/>
            <Route path="/tasks" element={<TasksPage/>}/>
            <Route path="/inventory" element={<InventoryPage/>}/>
            <Route path="/profile" element={<ProfilePage onLogout={handleLogout}/>}/>
            <Route path="/referrals" element={<ReferralsPage/>}/>
            <Route path="/leaderboard" element={<LeaderboardPage/>}/>
            <Route path="/transactions" element={<TransactionsPage/>}/>
            <Route path="/steam" element={<SteamPage/>}/>
            <Route path="/withdrawals" element={<WithdrawalsPage/>}/>
            <Route path="/admin/*" element={<AdminPage/>}/>
            <Route path="*" element={<NotFound/>}/>
          </Routes>
          {shellVisible && <BottomNav/>}
        </main>
        {notice && <div className={`toast ${notice.tone}`}><span>{notice.tone === "success" ? <Check size={17}/> : <CircleHelp size={17}/>}</span>{notice.text}<button onClick={() => setNotice(null)} aria-label="Dismiss"><X size={15}/></button></div>}
      </div>
    </AppContext.Provider>
  );
}

type AppState = { user: User | null; refreshUser: () => Promise<void>; notify: (tone: Notice["tone"], text: string) => void };
const AppContext = createContext<AppState>({ user: null, refreshUser: async () => {}, notify: () => {} });
const useApp = () => useContext(AppContext);

const primaryLinks = [
  ["/", "Home", Home], ["/cases", "Games", Crosshair], ["/inventory", "Inventory", Layers3], ["/tasks", "Tasks", Target],
] as const;
const accountLinks = [
  ["/profile", "Profile", UserRound], ["/referrals", "Referrals", Users], ["/leaderboard", "Leaderboard", Trophy],
  ["/transactions", "Transactions", Activity], ["/steam", "Steam settings", Shield], ["/withdrawals", "Withdrawals", ArrowDownToLine],
] as const;

function LoadingScreen() { return <main className="loading-screen"><LoaderCircle className="spin" size={28}/><span>Preparing your collection...</span></main>; }

function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="page-header"><div><div className="eyebrow">{eyebrow}</div><h1>{title}</h1>{description && <p>{description}</p>}</div>{action}</div>;
}

function SectionTitle({ title, link, to }: { title: string; link?: string; to?: string }) {
  return <div className="section-title"><h2>{title}</h2>{link && to && <Link to={to}>{link}<ArrowRight size={14}/></Link>}</div>;
}

function HomePage() {
  const { user, notify } = useApp();
  const [cases, setCases] = useState<CaseItem[]>([]);
  const [featured, setFeatured] = useState<InventoryItem[]>([]);
  const [activity, setActivity] = useState<{id:number; amount:number;reason:string;created_at:string}[]>([]);
  useEffect(() => {
    void Promise.all([api<CaseItem[]>("/cases"), api<typeof activity>("/transactions"), api<InventoryItem[]>("/inventory")])
      .then(([caseData, transactions, inventory]) => { setCases(caseData); setActivity(transactions.slice(0, 3)); setFeatured(inventory.slice(0, 3)); })
      .catch(error => notify("error", error.message));
  }, [notify]);
  return <div className="page">
    <div className="home-player"><div className="avatar">{user?.avatar_url ? <img src={user.avatar_url} alt=""/> : user?.username.slice(0, 1).toUpperCase()}</div><div><span>WELCOME BACK</span><strong>{user?.first_name || user?.username}</strong></div><span className="level-pill">LVL {user?.level}</span></div>
    <section className="hero-panel">
      <div className="hero-copy"><div className="eyebrow"><span className="online-dot"/> THE COLLECTION STARTS HERE</div><h1>Make every<br/><span>drop count.</span></h1>
        <p>Discover CS2 classics. Every case reward is published and fixed — no paid spins, no guessing.</p>
        <div className="hero-actions"><Link className="button primary" to="/cases">Explore free cases <ArrowRight size={16}/></Link><Link className="button subtle" to="/inventory">View inventory</Link></div>
      </div>
      <div className="hero-art"><div className="hero-orbit orbit-one"/><div className="hero-orbit orbit-two"/><div className="hero-rifle">✦</div><div className="floating-tag"><Sparkles size={14}/> FIXED REWARD</div><div className="hero-caption">YOUR NEXT<br/><strong>FAVORITE</strong></div></div>
      <div className="hero-grid-pattern"/>
    </section>
    <div className="stats-grid">
      <StatCard label="CRYSTAL BALANCE" value={user?.crystals ?? 0} icon={<Coins/>} detail="Earned through verified tasks"/>
      <StatCard label="COLLECTION" value={user?.inventory_count ?? 0} icon={<Layers3/>} detail="Items in your inventory"/>
      <StatCard label="PROFILE LEVEL" value={`LVL ${user?.level ?? 1}`} icon={<Award/>} detail={`${user?.xp ?? 0} XP earned`}/>
      <StatCard label="REFERRALS" value={user?.referral_count ?? 0} icon={<Users/>} detail="Friends invited"/>
    </div>
    {featured.length > 0 && <section className="section"><SectionTitle title="Your latest finds" link="Full inventory" to="/inventory"/><div className="featured-skins">{featured.map(item => <Link className="featured-skin" to="/inventory" key={item.id}><div style={{backgroundImage:`url("${item.image_url}")`}}/><span><small>{item.weapon} · {item.exterior}</small><b>{item.name}</b></span><ChevronRight size={16}/></Link>)}</div></section>}
    <section className="section"><SectionTitle title="Featured cases" link="Browse all" to="/cases"/><div className="case-grid">{cases.slice(0, 3).map((item, index) => <CaseCard key={item.id} item={item} index={index}/>)}</div></section>
    <div className="home-bottom-grid"><section className="section"><SectionTitle title="Recent activity" link="History" to="/transactions"/>{activity.length ? <div className="activity-list">{activity.map(row => <div className="activity-row" key={row.id}><div className="activity-icon"><Coins size={17}/></div><div><b>{row.reason.replaceAll("_", " ")}</b><small>{new Date(row.created_at).toLocaleDateString()}</small></div><strong className={row.amount > 0 ? "positive" : ""}>{row.amount > 0 ? "+" : ""}{row.amount}</strong></div>)}</div> : <EmptyState title="A fresh start" text="Your verified rewards will show up here."/>}</section>
      <section className="promo-card"><div className="promo-icon"><Gift size={21}/></div><span className="eyebrow">YOUR NEXT STEP</span><h2>Build your<br/>collection.</h2><p>Complete a task to earn crystals and explore more of the platform.</p><Link className="button primary" to="/tasks">View tasks <ArrowRight size={16}/></Link></section></div>
  </div>;
}

function StatCard({ label, value, icon, detail }: { label: string; value: ReactNode; icon: ReactNode; detail: string }) {
  return <div className="stat-card"><div className="stat-icon">{icon}</div><span>{label}</span><strong>{value}</strong><small>{detail}</small></div>;
}

function CaseCard({ item, index }: { item: CaseItem; index: number }) {
  return <Link className="case-card" to={`/cases/${item.slug}`}><div className={`case-art art-${index % 3}`} style={{ backgroundImage: `linear-gradient(180deg,transparent 35%,#151a1d 100%),url("${item.image_url}")` }}><span className="case-chip">FREE · FIXED REWARD</span><div className="case-emblem"><Crosshair size={36}/></div></div><div className="case-card-content"><div><h3>{item.name}</h3><p>{item.description}</p></div><span className="round-arrow"><ArrowRight size={16}/></span></div></Link>;
}

function CasesPage() {
  const [items, setItems] = useState<CaseItem[]>([]);
  const { notify } = useApp();
  useEffect(() => { void api<CaseItem[]>("/cases").then(setItems).catch(error => notify("error", error.message)); }, [notify]);
  return <div className="page"><PageHeader eyebrow="THE ARMORY" title="Cases" description="Every case is free and transparent. The featured reward is fixed before you open it."/>
    <div className="notice info"><Shield size={17}/> No paid cases, randomized rewards, or gambling mechanics. Each case lists its exact reward.</div>
    {items.length ? <div className="case-grid cases-page-grid">{items.map((item, index) => <CaseCard item={item} index={index} key={item.id}/>)}</div> : <LoadingCards/>}
  </div>;
}

function CaseDetailPage() {
  const { slug = "" } = useParams();
  const { notify, refreshUser } = useApp();
  const [item, setItem] = useState<CaseItem | null>(null);
  const [opening, setOpening] = useState(false);
  const [result, setResult] = useState<string | null>(null);
  useEffect(() => { void api<CaseItem[]>("/cases").then(all => setItem(all.find(x => x.slug === slug) ?? null)).catch(error => notify("error", error.message)); }, [slug, notify]);
  const open = async () => {
    if (!item) return;
    setOpening(true);
    try { const response = await api<{reward:string}>(`/cases/${item.slug}/open`, { method: "POST" }); setResult(response.reward); await refreshUser(); notify("success", "Your fixed reward was added to inventory."); }
    catch (error) { notify("error", error instanceof Error ? error.message : "Case could not be opened"); }
    finally { setOpening(false); }
  };
  if (!item) return <div className="page"><Link className="back-link" to="/cases"><ArrowLeft size={16}/> Cases</Link><LoadingCards/></div>;
  return <div className="page"><Link className="back-link" to="/cases"><ArrowLeft size={16}/> Back to cases</Link><div className="detail-layout"><div className="detail-art" style={{ backgroundImage: `linear-gradient(0deg,#101416 0%,transparent 80%),url("${item.image_url}")` }}><div className="detail-glow"><Crosshair size={82}/></div><span className="case-chip">FREE · PUBLISHED REWARD</span></div><section className="detail-copy"><div className="eyebrow">ONE CASE · ONE PUBLISHED REWARD</div><h1>{item.name}</h1><p>{item.description}</p>  <div className="fixed-reward"><div className="reward-symbol"><Sparkles/></div><div><small>PREDETERMINED REWARD</small><strong>{item.published_reward_name}</strong><span>This exact published item is granted. No randomization.</span></div></div>
      {result ? <div className="reward-result"><Sparkles size={20}/><div><small>ADDED TO YOUR COLLECTION</small><strong>{result}</strong></div></div> : <button className="button primary full-button" disabled={opening} onClick={() => void open()}>{opening ? <LoaderCircle className="spin"/> : <Crosshair size={18}/>} {opening ? "Opening..." : "Open free case"}</button>}
      <div className="detail-note"><Shield size={15}/> Single opening per account. Delivery is not enabled.</div></section></div></div>;
}

function TasksPage() {
  const [tasks, setTasks] = useState<TaskItem[]>([]);
  const { notify, refreshUser } = useApp();
  const load = useCallback(() => api<TaskItem[]>("/tasks").then(setTasks).catch(error => notify("error", error.message)), [notify]);
  useEffect(() => { void load(); }, [load]);
  const claim = async (slug: string) => {
    try { await api(`/tasks/${slug}/claim`, { method: "POST" }); await load(); await refreshUser(); notify("success", "Verified crystal reward added to your balance."); }
    catch (error) { notify("error", error instanceof Error ? error.message : "Could not claim this reward"); }
  };
  return <div className="page"><PageHeader eyebrow="EARN CRYSTALS" title="Tasks" description="Rewards are verified and granted by the server. Social actions need verification before claiming."/>
    <div className="task-grid">{tasks.map(task => <article className="task-card" key={task.id}><div className="task-icon">{task.task_type === "daily" ? <Sparkles/> : task.task_type === "social" ? <Users/> : <UserRound/>}</div><div className="task-body"><div className="task-type">{task.task_type} task</div><h3>{task.title}</h3><p>{task.description}</p><div className="task-reward"><Coins size={15}/> +{task.reward} crystals</div></div><button className={`button ${task.status === "completed" ? "done-button" : "outline"}`} disabled={task.status === "completed" || task.task_type === "social"} onClick={() => void claim(task.slug)}>{task.status === "completed" ? <><Check size={15}/> Claimed</> : task.task_type === "social" ? "Verification required" : "Claim reward"}</button></article>)}</div>
  </div>;
}

function InventoryPage() {
  const [items, setItems] = useState<InventoryItem[]>([]);
  const { notify } = useApp();
  const load = useCallback(() => api<InventoryItem[]>("/inventory").then(setItems).catch(error => notify("error", error.message)), [notify]);
  useEffect(() => { void load(); }, [load]);
  const request = async (item: InventoryItem) => {
    try {
      await api(`/withdrawals/${item.id}`, { method: "POST" });
      notify("success", "Withdrawal request recorded. Delivery is not enabled.");
      await load();
    } catch (error) {
      notify("error", error instanceof Error ? error.message : "Could not request withdrawal");
    }
  };
  return <div className="page"><PageHeader eyebrow="YOUR COLLECTION" title="Inventory" description="Items you have earned through the transparent case catalog." action={<span className="count-pill">{items.length} ITEMS</span>}/>
    {items.length ? <div className="inventory-grid">{items.map(item => <article className="inventory-card" key={item.id}><div className="inventory-image" style={{ backgroundImage: `url("${item.image_url}")` }}><span className="status-pill">{item.status.replaceAll("_", " ")}</span>{item.development_data && <span className="dev-pill">DEV DATA</span>}</div><div className="inventory-content"><div className="eyebrow">{item.weapon} · {item.exterior}</div><h3>{item.name}</h3><small>Acquired {new Date(item.acquired_at).toLocaleDateString()}</small><button className="button outline full-button" disabled={item.status !== "available"} onClick={() => void request(item)}>{item.status === "available" ? "Request withdrawal" : item.status.replaceAll("_", " ")} <ArrowDownToLine size={15}/></button><Link className="inventory-history-link" to="/withdrawals">View request history <ArrowRight size={13}/></Link></div></article>)}</div> : <EmptyState title="Your inventory is waiting" text="Open a free case to add your first published reward to the collection." action={<Link className="button primary" to="/cases">Explore cases <ArrowRight size={15}/></Link>}/>}
  </div>;
}

function ProfilePage({ onLogout }: { onLogout: () => void }) {
  const { user } = useApp();
  return <div className="page"><PageHeader eyebrow="PLAYER CARD" title="Your profile" description="Your account overview and collection progress."/>
    <div className="profile-layout"><section className="profile-card"><div className="profile-cover"><div className="profile-avatar">{user?.avatar_url ? <img src={user.avatar_url} alt=""/> : user?.username.slice(0, 1).toUpperCase()}</div><span className="level-pill">LEVEL {user?.level}</span></div><div className="profile-info"><h2>{user?.username}</h2><p>Telegram ID · {user?.telegram_id}</p><div className="xp-line"><span>EXPERIENCE</span><b>{user?.xp ?? 0} XP</b></div><div className="progress-track"><div style={{ width: `${Math.min((user?.xp ?? 0) % 100, 100)}%` }}/></div><div className="profile-metrics"><div><b>{user?.crystals}</b><small>Crystals</small></div><div><b>{user?.inventory_count}</b><small>Items</small></div><div><b>{user?.referral_count}</b><small>Referrals</small></div></div><div className="achievement-panel"><h3>Achievements</h3><div>{user?.achievements.map(item => <span className={item.unlocked ? "achievement unlocked" : "achievement"} key={item.slug}><Award size={14}/>{item.title}</span>)}</div></div></div></section>
      <div className="profile-settings"><Link className="settings-row" to="/steam"><span className="settings-icon"><Shield/></span><div><b>Steam settings</b><small>{user?.steam_connected ? "Trade URL connected" : "Add a Steam Trade URL"}</small></div><ChevronRight/></Link><Link className="settings-row" to="/transactions"><span className="settings-icon"><WalletCards/></span><div><b>Transaction history</b><small>Review your crystal activity</small></div><ChevronRight/></Link><Link className="settings-row" to="/referrals"><span className="settings-icon"><Users/></span><div><b>Referral program</b><small>Invite friends to the platform</small></div><ChevronRight/></Link><button className="settings-row logout-row" onClick={onLogout}><span className="settings-icon"><LogOut/></span><div><b>Sign out</b><small>Disconnect this session</small></div><ChevronRight/></button></div>
    </div>
  </div>;
}

function ReferralsPage() {
  const [data, setData] = useState<{code:string;link:string|null;count:number;users:{username:string;created_at:string;status:string}[]}|null>(null);
  const { notify } = useApp();
  useEffect(() => { void api<typeof data>("/referrals").then(setData).catch(error => notify("error", error.message)); }, [notify]);
  const copy = async () => { if (!data?.link) return notify("error", "Telegram bot username is not configured."); await navigator.clipboard.writeText(data.link); notify("success", "Referral link copied."); };
  return <div className="page"><PageHeader eyebrow="GROW TOGETHER" title="Referrals" description="Share your unique Telegram link. Referral rewards remain disabled until server-side fraud checks are configured."/>
    <div className="referral-hero"><div className="referral-pattern"/><div><div className="eyebrow">YOUR UNIQUE INVITE</div><h2>Good games are<br/>better together.</h2><p>Invite friends and see who joins your collection crew.</p></div><div className="referral-link-box"><small>YOUR TELEGRAM DEEP LINK</small><div><code>{data?.link ?? `Referral code: ${data?.code ?? "…"}`}</code><button className="button primary" onClick={() => void copy()}><Clipboard size={16}/> Copy link</button></div></div></div>
    <div className="stats-grid compact-stats"><StatCard label="INVITES" value={data?.count ?? 0} icon={<Users/>} detail="Players joined through your link"/><StatCard label="REFERRAL CODE" value={data?.code ?? "…"} icon={<Gift/>} detail="Unique to your account"/></div>
    <section className="section"><SectionTitle title="Referred players"/>{data?.users.length ? <div className="activity-list">{data.users.map((item, index) => <div className="activity-row" key={`${item.username}-${index}`}><div className="avatar small-avatar">{item.username.slice(0,1).toUpperCase()}</div><div><b>{item.username}</b><small>{new Date(item.created_at).toLocaleDateString()}</small></div><span className="status-pill">{item.status}</span></div>)}</div> : <EmptyState title="No referrals yet" text="Share your invite link to bring a friend along."/>}</section>
  </div>;
}

function LeaderboardPage() {
  const [period, setPeriod] = useState("all-time");
  const [players, setPlayers] = useState<{rank:number;user_id:number;username:string;avatar_url:string|null;level:number;points:number}[]>([]);
  const { notify } = useApp();
  useEffect(() => { void api<typeof players>(`/leaderboard?period=${period}`).then(setPlayers).catch(error => notify("error", error.message)); }, [period, notify]);
  return <div className="page"><PageHeader eyebrow="COMMUNITY RANKINGS" title="Leaderboard" description="Players ranked by experience points."/>
    <div className="tab-switch">{["weekly","monthly","all-time"].map(item => <button className={period === item ? "active" : ""} onClick={() => setPeriod(item)} key={item}>{item.replace("-", " ")}</button>)}</div>
    <div className="leaderboard"><div className="table-heading"><span>RANK</span><span>PLAYER</span><span>LEVEL</span><span>POINTS</span></div>{players.map(player => <div className={`leader-row ${player.rank <= 3 ? `rank-${player.rank}` : ""}`} key={player.user_id}><b className="rank-number">{String(player.rank).padStart(2, "0")}</b><div className="leader-player"><div className="avatar small-avatar">{player.avatar_url ? <img src={player.avatar_url} alt=""/> : player.username.slice(0,1).toUpperCase()}</div><b>{player.username}</b></div><span>LVL {player.level}</span><strong>{player.points.toLocaleString()} XP</strong></div>)}{!players.length && <EmptyState title="The board is open" text="Earn experience to appear in the rankings."/>}</div>
    <div className="notice info"><Trophy size={17}/> Weekly and monthly views currently use all-time XP until period-specific XP tracking is enabled.</div>
  </div>;
}

function TransactionsPage() {
  const [rows, setRows] = useState<{id:number;amount:number;reason:string;created_at:string}[]>([]);
  const { notify } = useApp();
  useEffect(() => { void api<typeof rows>("/transactions").then(setRows).catch(error => notify("error", error.message)); }, [notify]);
  return <div className="page"><PageHeader eyebrow="CRYSTAL LEDGER" title="Transactions" description="A record of server-validated crystal rewards."/>
    {rows.length ? <div className="ledger">{rows.map(row => <div className="ledger-row" key={row.id}><div className="activity-icon"><Coins size={17}/></div><div><b>{row.reason.replaceAll("_", " ")}</b><small>{new Date(row.created_at).toLocaleString()}</small></div><strong className={row.amount > 0 ? "positive" : ""}>{row.amount > 0 ? "+" : ""}{row.amount} crystals</strong></div>)}</div> : <EmptyState title="No transactions yet" text="Verified task rewards will appear here."/>}
  </div>;
}

function SteamPage() {
  const [tradeUrl, setTradeUrl] = useState("");
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);
  const { notify, user } = useApp();
  useEffect(() => {
    void api<{trade_url:string|null}>("/steam")
      .then(result => setTradeUrl(result.trade_url ?? ""))
      .catch(error => notify("error", error.message));
  }, [notify]);
  const submit = async (event: FormEvent) => {
    event.preventDefault(); setBusy(true);
    try { await api("/steam", { method: "PUT", body: JSON.stringify({ trade_url: tradeUrl }) }); setSaved(true); notify("success", "Steam Trade URL saved securely."); }
    catch (error) { notify("error", error instanceof Error ? error.message : "Could not save your Trade URL"); }
    finally { setBusy(false); }
  };
  return <div className="page"><PageHeader eyebrow="ACCOUNT CONNECTION" title="Steam settings" description="Connect a Trade URL for future withdrawal requests. Never share your password or Steam Guard codes."/>
    <div className="settings-layout"><form className="form-card" onSubmit={submit}><div className="form-card-heading"><div className="settings-icon"><Shield/></div><div><h2>Steam Trade URL</h2><p>Only a trade URL is required. We will never ask for login credentials.</p></div></div><label htmlFor="trade-url">Trade URL</label><input id="trade-url" value={tradeUrl} onChange={event => { setTradeUrl(event.target.value); setSaved(false); }} placeholder="https://steamcommunity.com/tradeoffer/new/?partner=…&token=…" required/><small className="input-hint"><ExternalLink size={13}/> Find it under Steam → Inventory → Trade Offers → Who can send me Trade Offers?</small><button className="button primary" disabled={busy}>{busy ? <LoaderCircle className="spin"/> : <Check size={16}/>} {user?.steam_connected || saved ? "Update Trade URL" : "Save Trade URL"}</button>{saved && <div className="inline-success"><Check size={15}/> Trade URL connected</div>}</form>
      <aside className="security-card"><div className="security-icon"><Shield/></div><h3>Keep your account safe</h3><ul><li><Check/> We don't request Steam passwords</li><li><Check/> No Steam Guard codes or cookies</li><li><Check/> URL format is checked on our server</li></ul><div className="notice info">Trade delivery is currently disabled until an authorized supplier is configured.</div></aside></div>
  </div>;
}

function WithdrawalsPage() {
  const [rows, setRows] = useState<{id:number;status:string;created_at:string;skin:string}[]>([]);
  const { notify } = useApp();
  useEffect(() => { void api<typeof rows>("/withdrawals").then(setRows).catch(error => notify("error", error.message)); }, [notify]);
  return <div className="page"><PageHeader eyebrow="DELIVERY STATUS" title="Withdrawals" description="Track requests. No trade is marked delivered without confirmation from a configured provider."/>
    {rows.length ? <div className="ledger">{rows.map(row => <div className="ledger-row" key={row.id}><div className="activity-icon"><ArrowDownToLine size={17}/></div><div><b>{row.skin}</b><small>Request #{row.id} · {new Date(row.created_at).toLocaleDateString()}</small></div><span className="status-pill">{row.status}</span></div>)}</div> : <EmptyState title="No withdrawal requests" text="Your withdrawal history will appear here. Delivery is currently disabled." action={<Link className="button outline" to="/inventory">Open inventory</Link>}/>}
    <div className="notice info"><CircleHelp size={17}/> Delivery is intentionally disabled until an authorized Steam trade provider is configured.</div>
  </div>;
}

function AdminPage() {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [data, setData] = useState<{users:number;cases:number;withdrawals_pending:number;transactions:number}|null>(null);
  const [error, setError] = useState("");
  const [adminToken, setAdminTokenState] = useState(getAdminToken());
  const [rows, setRows] = useState<Record<string, unknown>[]>([]);
  const [form, setForm] = useState<Record<string, string>>({});
  const location = useLocation();
  const section = location.pathname.split("/")[2] ?? "";
  const loadSection = useCallback(async () => {
    if (!adminToken || !section) return;
    try {
      const endpoints: Record<string, string> = {
        withdrawals: "/admin/withdrawals",
        audit: "/admin/audit-logs",
        users: "/admin/users",
        tasks: "/admin/tasks",
        cases: "/admin/cases",
        rewards: "/admin/rewards",
        skins: "/admin/skins",
        inventory: "/admin/inventory",
        referrals: "/admin/referrals",
        transactions: "/admin/transactions",
      };
      const path = endpoints[section] ?? "/admin/overview";
      setRows(await api<Record<string, unknown>[]>(path, {}, adminToken));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load admin records");
    }
  }, [adminToken, section]);
  const login = async (event: FormEvent) => {
    event.preventDefault();
    try {
      const result = await api<{access_token:string}>("/auth/admin", {method:"POST",body:JSON.stringify({username,password})});
      setAdminToken(result.access_token);
      setAdminTokenState(result.access_token);
      setError("");
      setData(await api("/admin/overview", {}, result.access_token));
    }
    catch (err) { setError(err instanceof Error ? err.message : "Unable to sign in"); }
  };
  useEffect(() => {
    if (adminToken) void api<typeof data>("/admin/overview", {}, adminToken).then(setData).catch(err => {
      clearAdminToken();
      setAdminTokenState(null);
      setError(err instanceof Error ? err.message : "Admin session expired");
    });
  }, [adminToken]);
  useEffect(() => { void loadSection(); }, [loadSection]);
  const updateWithdrawal = async (id: number, status: string) => {
    try {
      await api(`/admin/withdrawals/${id}?status=${status}`, { method: "PATCH" }, adminToken);
      await loadSection();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not update request"); }
  };
  const updateUser = async (id: number, active: boolean) => {
    try {
      await api(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify({ is_active: active }) }, adminToken);
      await loadSection();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not update account"); }
  };
  const submitCreate = async (event: FormEvent) => {
    event.preventDefault();
    const payload: Record<string, unknown> = { ...form };
    if (section === "tasks") payload.reward = Number(form.reward);
    if (section === "cases") payload.published_reward_id = Number(form.published_reward_id);
    if (section === "rewards" || section === "skins") {
      payload.float_value = form.float_value ? Number(form.float_value) : null;
    }
    try {
      await api(`/admin/${section}`, { method: "POST", body: JSON.stringify(payload) }, adminToken);
      setForm({});
      await loadSection();
    } catch (err) { setError(err instanceof Error ? err.message : "Could not create catalog entry"); }
  };
  const setField = (key: string, value: string) => setForm(previous => ({ ...previous, [key]: value }));
  const input = (key: string, label: string, placeholder = "", type = "text") => (
    <label key={key}>{label}<input type={type} step={type === "number" ? "any" : undefined} value={form[key] ?? ""} placeholder={placeholder}
      onChange={event => setField(key, event.target.value)} required={key !== "description" && key !== "image_url" && key !== "float_value"}/></label>
  );
  const createFields = section === "tasks" ? <>
    {input("slug", "Slug", "weekly-checkin")}{input("title", "Title", "Complete a challenge")}
    {input("description", "Description")}{input("task_type", "Type (daily, social, referral, profile)", "social")}
    {input("reward", "Crystal reward", "10", "number")}
  </> : section === "rewards" ? <>
    {input("name", "Market name")}{input("weapon", "Weapon")}{input("exterior", "Exterior")}
    {input("description", "Description")}{input("image_url", "Image URL")}{input("float_value", "Float value", "0.12", "number")}
  </> : section === "skins" ? <>
    {input("market_name", "Market name")}{input("weapon", "Weapon")}{input("exterior", "Exterior")}
    {input("image_url", "Image URL")}{input("float_value", "Float value", "0.12", "number")}
  </> : section === "cases" ? <>
    {input("slug", "Slug", "starter-case")}{input("name", "Name")}{input("description", "Description")}
    {input("image_url", "Image URL")}{input("published_reward_id", "Published reward ID", "1", "number")}
  </> : null;
  if (!data) return <div className="admin-login"><Link className="back-link" to="/"><ArrowLeft size={16}/> Main app</Link><form className="form-card" onSubmit={login}><div className="settings-icon"><Shield/></div><div className="eyebrow">RESTRICTED ACCESS</div><h1>Admin sign in</h1><label>Username</label><input value={username} onChange={event => setUsername(event.target.value)} autoComplete="username" required/><label>Password</label><input type="password" value={password} onChange={event => setPassword(event.target.value)} autoComplete="current-password" required/>{error && <div className="notice error">{error}</div>}<button className="button primary full-button">Sign in securely</button><small>Use credentials from server environment configuration.</small></form></div>;
  if (section) return <div className="page admin-page"><PageHeader eyebrow="CONTROL CENTER" title={section === "audit" ? "Audit logs" : section === "withdrawals" ? "Withdrawal requests" : section === "users" ? "User management" : section.replace("-", " ")} action={<button className="button outline" onClick={() => {clearAdminToken();setAdminTokenState(null);setData(null);}}>Sign out</button>}/>{error && <div className="notice error">{error}</div>}{createFields && <form className="form-card admin-create-form" onSubmit={submitCreate}><h2>Create {section.slice(0, -1)}</h2>{createFields}<button className="button primary">Create entry</button></form>}<div className="ledger">{rows.map((row, i) => <div className="ledger-row" key={String(row.id ?? i)}><div className="activity-icon"><Activity size={17}/></div><div><b>{String(row.username ?? row.action ?? row.skin ?? row.name ?? row.market_name ?? row.title ?? `Record ${String(row.id ?? i + 1)}`)}</b><small>{Object.entries(row).filter(([key]) => !["username","action","skin","name","market_name","title"].includes(key)).map(([key,value]) => `${key.replaceAll("_"," ")}: ${String(value)}`).join(" · ")}</small></div>{section === "withdrawals" && row.status === "requested" && <button className="button outline" onClick={() => void updateWithdrawal(Number(row.id), "cancelled")}>Cancel request</button>}{section === "users" && <button className="button outline" onClick={() => void updateUser(Number(row.id), row.is_active !== true)}>{row.is_active === true ? "Suspend" : "Reactivate"}</button>}</div>)}</div><Link className="back-link" to="/admin">← Dashboard</Link></div>;
  return <div className="page admin-page"><PageHeader eyebrow="CONTROL CENTER" title="Admin dashboard" description="Operational overview. User balances are not editable from this dashboard." action={<button className="button outline" onClick={() => {clearAdminToken();setAdminTokenState(null);setData(null);}}>Sign out</button>}/><div className="stats-grid"><StatCard label="REGISTERED USERS" value={data.users} icon={<Users/>} detail="Platform accounts"/><StatCard label="PUBLISHED CASES" value={data.cases} icon={<Crosshair/>} detail="Fixed reward catalog"/><StatCard label="PENDING WITHDRAWALS" value={data.withdrawals_pending} icon={<ArrowDownToLine/>} detail="Awaiting review"/><StatCard label="TRANSACTIONS" value={data.transactions} icon={<WalletCards/>} detail="Wallet ledger entries"/></div><div className="admin-shortcuts">{[["users","User management"],["tasks","Task management"],["cases","Cases"],["rewards","Reward catalog"],["skins","Skin catalog"],["inventory","Inventory"],["referrals","Referrals"],["transactions","Transactions"],["withdrawals","Withdrawals"],["audit","Audit logs"]].map(([path,label]) => <Link className="settings-row" to={`/admin/${path}`} key={path}><span className="settings-icon"><Shield/></span><div><b>{label}</b><small>Review {label.toLowerCase()} records</small></div><ChevronRight/></Link>)}</div></div>;
}

function BottomNav() {
  return <nav className="bottom-nav">{primaryLinks.map(([to, label, Icon]) => <NavLink to={to} end={to === "/"} key={to}><Icon size={20}/><span>{label}</span></NavLink>)}</nav>;
}

function EmptyState({ title, text, action }: { title: string; text: string; action?: ReactNode }) {
  return <div className="empty-state"><div className="empty-icon"><Layers3 size={22}/></div><h3>{title}</h3><p>{text}</p>{action}</div>;
}

function LoadingCards() { return <div className="case-grid">{[1,2,3].map(x => <div className="skeleton-card" key={x}><div/><span/><span/></div>)}</div>; }

function NotFound() { return <div className="page not-found"><div className="empty-icon"><CircleHelp/></div><h1>Page not found</h1><Link className="button primary" to="/">Back home</Link></div>; }

declare global {
  interface Window { Telegram?: { WebApp?: { initData: string; ready: () => void } } }
}

export default App;
