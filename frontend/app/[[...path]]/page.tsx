"use client";
import {
  useState,
  useEffect,
  useCallback,
  type FormEvent,
  type ReactNode,
} from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import { Suspense } from "react";
import {
  ArrowUpRight,
  ArrowRight,
  Check,
  ChevronRight,
  Command,
  Users,
  LayoutDashboard,
  Upload,
  SlidersHorizontal,
  Layers,
  History,
  LogOut,
  Clock,
  ShieldCheck,
  GitBranch,
  Mail,
  Plus,
  Search,
  AlertCircle,
  Code2,
  Target,
  Zap,
  CheckCircle2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
type Data = Record<string, any>;
async function api(path: string, method = "GET", body?: unknown) {
  const r = await fetch("/api" + path, {
    method,
    credentials: "same-origin",
    signal: AbortSignal.timeout(15000),
    headers:
      body instanceof FormData
        ? {}
        : body
          ? { "Content-Type": "application/json" }
          : {},
    body:
      body instanceof FormData ? body : body ? JSON.stringify(body) : undefined,
  });
  const data = await r.json().catch(() => ({
    detail: "Service is unavailable. Check the backend connection.",
  }));
  if (!r.ok)
    throw new Error(
      typeof data.detail === "string"
        ? data.detail
        : "Check your input and try again.",
    );
  return data;
}
const nav = [
  ["/admin", "Overview", LayoutDashboard],
  ["/admin/luma", "Luma imports", Upload],
  ["/admin/participants", "Participants", Users],
  ["/admin/matching", "Matching window", SlidersHorizontal],
  ["/admin/teams", "Team proposals", Layers],
  ["/admin/audit", "Activity log", History],
] as const;
function Brand() {
  return (
    <Link href="/" className="brand">
      <span className="brand-icon">
        <Command size={21} />
      </span>
      hackamatch<span className="brand-dot">.</span>
    </Link>
  );
}
function Tag({
  children,
  tone = "purple",
}: {
  children: ReactNode;
  tone?: string;
}) {
  return <span className={"tag " + tone}>{children}</span>;
}
function Empty({ title, children }: { title: string; children?: ReactNode }) {
  return (
    <div className="empty">
      <GitBranch size={28} />
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
function Countdown({ window: w }: { window: Data | null }) {
  const [n, setN] = useState(Date.now());
  const [offset, setOffset] = useState(0);
  useEffect(() => {
    if (w?.server_time) setOffset(Date.parse(w.server_time) - Date.now());
  }, [w?.server_time]);
  useEffect(() => {
    const t = setInterval(() => setN(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  if (!w) return <span>Window not opened</span>;
  const secs = Math.max(
    0,
    Math.floor((Date.parse(w.closes) - n - offset) / 1000),
  );
  return (
    <span className="countdown">
      {String(Math.floor(secs / 3600)).padStart(2, "0")}
      <b>:</b>
      {String(Math.floor(secs / 60) % 60).padStart(2, "0")}
      <b>:</b>
      {String(secs % 60).padStart(2, "0")}
    </span>
  );
}
function Shell() {
  const path = usePathname();
  const params = useSearchParams();
  const [me, setMe] = useState<Data | null>(null);
  const [ready, setReady] = useState(false);
  const [status, setStatus] = useState<Data | null>(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const load = useCallback(async () => {
    const [u, s] = await Promise.allSettled([
      api("/auth/me"),
      api("/public/status"),
    ]);
    if (u.status === "fulfilled") setMe(u.value);
    else setMe(null);
    if (s.status === "fulfilled") setStatus(s.value);
    else
      setError(
        "Registration service is unavailable. Check the API connection and try again.",
      );
    setReady(true);
  }, []);
  useEffect(() => {
    load();
    const interval = setInterval(load, 15000);
    return () => clearInterval(interval);
  }, [load, path]);
  useEffect(() => {
    setError("");
    setNotice("");
  }, [path]);
  async function action(fn: () => Promise<unknown>, message: string) {
    setError("");
    setNotice("");
    try {
      await fn();
      setNotice(message);
      await load();
      return true;
    } catch (e) {
      setError((e as Error).message);
      return false;
    }
  }
  const admin = path.startsWith("/admin");
  const auth = path === "/login" || path === "/signup";
  if (path === "/") return <Landing status={status} />;
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <div className="workspace">
          <span className="workspace-avatar">HM</span>
          <div>
            <strong>HackAMatch 2026</strong>
            <small>Data Mavericks × NSDC</small>
          </div>
        </div>
        <div className="nav-label">
          {admin ? "ORGANIZER WORKSPACE" : "YOUR HACKATHON"}
        </div>
        <nav>
          {(admin
            ? nav
            : ([
                ["/dashboard", "My profile", LayoutDashboard],
                ["/waiting-room", "Waiting room", Clock],
                ["/team", "My team", Users],
              ] as const)
          ).map(([href, label, Icon]) => (
            <Link
              key={href}
              href={href}
              className={path === href ? "active" : ""}
            >
              <Icon size={18} />
              {label}
              {path === href && <span className="nav-pip" />}
            </Link>
          ))}
        </nav>
        <div className="side-bottom">
          <div className="side-help">
            <ShieldCheck size={18} />
            <strong>Built around your strengths</strong>
            <p>
              Your Luma responses help us find your team. No second
              questionnaire.
            </p>
          </div>
          {me?.role === "organizer" && (
            <Link href={admin ? "/dashboard" : "/admin"} className="switch">
              Switch to {admin ? "participant" : "organizer"} view{" "}
              <ArrowUpRight size={14} />
            </Link>
          )}
          {me && (
            <button
              className="account"
              onClick={() =>
                action(() => api("/auth/logout", "POST"), "Logged out")
              }
            >
              <span className="avatar">{me.email[0].toUpperCase()}</span>
              <span>
                <strong>
                  {me.role === "organizer" ? "Organizer" : "Participant"}
                </strong>
                <small>{me.email}</small>
              </span>
              <LogOut size={16} />
            </button>
          )}
        </div>
      </aside>
      <main className="main">
        <header className="topbar">
          <span>
            Workspace <ChevronRight size={14} />{" "}
            {auth
              ? "Account"
              : admin
                ? "Organizer console"
                : "Participant dashboard"}
          </span>
          <Tag tone="neutral">Data Mavericks × NSDC</Tag>
        </header>
        <div className="page">
          {error && (
            <div role="alert" className="alert error">
              <AlertCircle size={17} />
              {error}
            </div>
          )}
          {notice && (
            <div role="status" className="alert success">
              <CheckCircle2 size={17} />
              {notice}
            </div>
          )}
          {auth ? (
            <Auth
              signup={path === "/signup"}
              verifyToken={params.get("verify")}
              action={action}
              reload={load}
              emailEnabled={status?.email_enabled}
            />
          ) : !ready ? (
            <Empty title="Loading your workspace…" />
          ) : !me ? (
            <Empty title="Your workspace is one login away">
              <Link href="/login" className="text-link">
                Log in to continue →
              </Link>
            </Empty>
          ) : admin && me.role !== "organizer" ? (
            <Empty title="Organizer access required">
              This workspace is restricted to event organizers.
            </Empty>
          ) : admin ? (
            <Admin path={path} action={action} />
          ) : (
            <Participant path={path} me={me} action={action} />
          )}
        </div>
      </main>
    </div>
  );
}
function Landing({ status }: { status: Data | null }) {
  return (
    <div className="landing">
      <header>
        <Brand />
        <nav>
          <a href="#how">How it works</a>
          <Link href="/login">Log in</Link>
          <Button asChild size="sm">
            <Link href="/signup">
              Find my team <ArrowUpRight size={15} />
            </Link>
          </Button>
        </nav>
      </header>
      <main>
        <div className="hero-eyebrow">
          <span /> DATA MAVERICKS × NSDC PRESENT
        </div>
        <div className="hero-grid">
          <section>
            <h1>
              Great ideas.
              <br />
              Better <span>together.</span>
            </h1>
            <p className="hero-text">
              You bring the spark. We find your people.
              <br />
              Meet two teammates whose skills complement yours, and turn a
              hackathon idea into something real.
            </p>
            <div className="hero-actions">
              <Button asChild>
                <Link href="/signup">
                  Find my team <ArrowRight size={18} />
                </Link>
              </Button>
              <a href="#how" className="secondary-link">
                See how it works <ArrowUpRight size={15} />
              </a>
            </div>
            <div className="hero-proof">
              <span>
                <ShieldCheck size={16} /> Luma verified
              </span>
              <span>
                <Users size={16} /> Exactly 3 per team
              </span>
              <span>
                <Code2 size={16} /> Built to build
              </span>
            </div>
          </section>
          <div className="team-art">
            <div className="orb" />
            <div className="art-grid" />
            <div className="art-label">
              <span className="green-dot" /> YOUR NEXT GREAT TEAM
            </div>
            <div className="member-card card-one">
              <span className="art-avatar violet">
                <Code2 />
              </span>
              <div>
                <small>THE BUILDER</small>
                <strong>Turning ideas into code</strong>
                <span>
                  Backend <i /> Architecture
                </span>
              </div>
              <CheckCircle2 size={17} />
            </div>
            <div className="member-card card-two">
              <span className="art-avatar blue">
                <Layers />
              </span>
              <div>
                <small>THE DESIGNER</small>
                <strong>Making every detail count</strong>
                <span>
                  UI/UX <i /> Frontend
                </span>
              </div>
              <CheckCircle2 size={17} />
            </div>
            <div className="member-card card-three">
              <span className="art-avatar amber">
                <Zap />
              </span>
              <div>
                <small>THE CATALYST</small>
                <strong>Connecting the dots</strong>
                <span>
                  Research <i /> Storytelling
                </span>
              </div>
              <CheckCircle2 size={17} />
            </div>
            <div className="art-footer">
              <GitBranch size={15} /> Different strengths. One shared direction.
            </div>
          </div>
        </div>
        <div className="window-strip">
          <div>
            <Clock size={20} />
            <div>
              <small>REGISTRATION WINDOW</small>
              <strong>{status?.window?.name || "Your team starts here"}</strong>
            </div>
          </div>
          <div>
            <Tag tone={status?.window?.status === "open" ? "green" : "neutral"}>
              {status?.window?.status || "Awaiting organizer"}
            </Tag>
            <Countdown window={status?.window} />
          </div>
        </div>
        <section id="how" className="how">
          <div>
            <span className="eyebrow">LESS SEARCHING. MORE BUILDING.</span>
            <h2>Three steps. Your next team.</h2>
          </div>
          <div className="steps">
            {[
              [
                ShieldCheck,
                "01",
                "Verify your spot",
                "Sign in and verify the email you used on Luma. Your existing responses come with you.",
              ],
              [
                GitBranch,
                "02",
                "Join the matching pool",
                "We consider complementary skills, shared goals and how you like to work.",
              ],
              [
                Users,
                "03",
                "Meet your people",
                "After organizer review, discover your three-person team and start building.",
              ],
            ].map(([Icon, num, title, text]) => {
              const I = Icon as typeof Users;
              return (
                <article key={String(num)}>
                  <span className="step-number">{String(num)}</span>
                  <I size={23} />
                  <h3>{String(title)}</h3>
                  <p>{String(text)}</p>
                </article>
              );
            })}
          </div>
        </section>
      </main>
      <footer>
        <Brand />
        <span>Made for the moments that start something.</span>
        <span>HackAMatch / 2026</span>
      </footer>
    </div>
  );
}
type Action = (fn: () => Promise<unknown>, message: string) => Promise<boolean>;
function Auth({
  signup,
  verifyToken,
  action,
  reload,
  emailEnabled,
}: {
  signup: boolean;
  verifyToken: string | null;
  action: Action;
  reload: () => Promise<void>;
  emailEnabled?: boolean;
}) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  async function submit(e: FormEvent) {
    e.preventDefault();
    setBusy(true);
    const ok = await action(
      () =>
        api(signup ? "/auth/signup" : "/auth/login", "POST", {
          email,
          password,
        }),
      signup
        ? "Check your email for your verification link."
        : "You are logged in.",
    );
    if (ok && !signup) {
      await reload();
      window.location.assign("/dashboard");
    }
    setBusy(false);
  }
  return (
    <div className="auth-wrap">
      <div className="auth-icon">
        <Command size={28} />
      </div>
      <span className="eyebrow">YOUR NEXT COLLABORATION STARTS HERE</span>
      <h1>{signup ? "Find your people." : "Welcome back."}</h1>
      <p>Use the same email you registered with on Luma.</p>
      {verifyToken ? (
        <div className="panel">
          <h3>Verify your email</h3>
          <p>Confirm this link to connect your Luma registration.</p>
          <Button
            onClick={() =>
              action(
                () => api("/auth/verify", "POST", { token: verifyToken }),
                "Email verified. Log in below.",
              )
            }
          >
            Verify email ownership <Check size={17} />
          </Button>
        </div>
      ) : null}
      <form onSubmit={submit} className="panel auth-form">
        <label>
          Email address
          <input
            type="email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            placeholder="you@college.edu"
            required
            autoComplete="email"
          />
        </label>
        <label>
          Password
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            minLength={10}
            maxLength={128}
            required
            placeholder="At least 10 characters"
            autoComplete={signup ? "new-password" : "current-password"}
          />
        </label>
        <Button disabled={busy} type="submit">
          {busy ? "Please wait…" : signup ? "Create my account" : "Log in"}
          <ArrowRight size={16} />
        </Button>
        {!signup && (
          <Button
            type="button"
            variant="ghost"
            onClick={() =>
              action(
                () => api("/auth/resend", "POST", { email }),
                "If this address needs verification, a new email has been queued.",
              )
            }
          >
            Resend verification email
          </Button>
        )}
      </form>
      {emailEnabled === false && (
        <div className="alert">
          <Mail size={17} /> Email delivery is disabled. An organizer must
          configure SMTP before new participants can verify ownership.
        </div>
      )}
      <p>
        {signup ? "Already registered?" : "New to HackAMatch?"}{" "}
        <Link className="text-link" href={signup ? "/login" : "/signup"}>
          {signup ? "Log in" : "Create an account"}
        </Link>
      </p>
      <small className="muted">
        Your questionnaire is already on Luma. We won’t ask for it again.
      </small>
    </div>
  );
}
function Heading({
  eyebrow,
  title,
  description,
  children,
}: {
  eyebrow: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className="page-heading">
      <div>
        <span className="eyebrow">{eyebrow}</span>
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {children}
    </div>
  );
}
function Metric({
  label,
  value,
  detail,
  icon: Icon,
}: {
  label: string;
  value: ReactNode;
  detail: string;
  icon: typeof Users;
}) {
  return (
    <div className="metric">
      <div>
        <span>{label}</span>
        <Icon size={17} />
      </div>
      <strong>{value}</strong>
      <small>{detail}</small>
    </div>
  );
}
function TeamCard({ team }: { team: Data }) {
  return (
    <article className="panel team-card">
      <div className="panel-heading">
        <h3>{team.name}</h3>
        <Tag tone={team.status === "published" ? "green" : "purple"}>
          {team.status}
        </Tag>
      </div>
      {team.members.map((m: Data, i: number) => (
        <div className="team-person" key={m.id}>
          <span className={"avatar avatar-" + i}>
            {m.name
              .split(" ")
              .slice(0, 2)
              .map((s: string) => s[0])
              .join("")}
          </span>
          <div>
            <strong>{m.name}</strong>
            <div className="chips">
              {m.skills.map((s: string) => (
                <span key={s}>{s}</span>
              ))}
            </div>
            <small className="muted">
              {m.schedule.join(" · ") || "Schedule unknown"}
            </small>
          </div>
        </div>
      ))}
      <details>
        <summary>
          Why this team? <span>{team.score.toFixed(1)} / 100</span>
        </summary>
        <div className="score-list">
          {Object.entries(team.breakdown.components).map(([k, v]) => (
            <div key={k}>
              <span>{k}</span>
              <strong>
                {v == null ? "Unknown" : Number(v).toFixed(0) + "%"}
              </strong>
            </div>
          ))}
        </div>
        <p>{team.breakdown.explanation}</p>
      </details>
    </article>
  );
}
function Participant({
  path,
  me,
  action,
}: {
  path: string;
  me: Data;
  action: Action;
}) {
  const [profile, setProfile] = useState<Data | null>(null),
    [reg, setReg] = useState<Data | null>(null),
    [team, setTeam] = useState<Data | null>(null),
    [error, setError] = useState("");
  const refresh = useCallback(async () => {
    try {
      const [p, r, t] = await Promise.all([
        api("/participant/profile"),
        api("/participant/registration"),
        api("/participant/team"),
      ]);
      setProfile(p);
      setReg(r);
      setTeam(t);
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, []);
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 10000);
    return () => clearInterval(t);
  }, [refresh]);
  if (error) return <div className="alert error">{error}</div>;
  if (!profile || !reg) return <Empty title="Loading your profile…" />;
  const p = profile.profile,
    w = reg.window;
  if (path === "/team")
    return (
      <>
        <Heading
          eyebrow="BUILD SOMETHING TOGETHER"
          title="Your team."
          description="Three people. Complementary strengths. One shared starting point."
        />
        {team?.team ? (
          <>
            <TeamCard team={team.team} />
            <div className="panel">
              <h3>What’s next?</h3>
              <p>
                Introduce yourselves, choose a project direction together and
                agree on a working schedule. Follow the organizers’ instructions
                for the hackathon round.
              </p>
            </div>
          </>
        ) : (
          <Empty
            title={
              team?.status === "waitlisted"
                ? "You’re on the waitlist"
                : "Your team is still taking shape"
            }
          >
            {team?.status === "waitlisted"
              ? "You weren’t placed into a complete team of three. Organizers can review the waitlist and open another window."
              : "Teams appear here after the matching window closes and organizers publish the results."}
            <p>
              <Link href="/waiting-room" className="text-link">
                View matching status →
              </Link>
            </p>
          </Empty>
        )}
      </>
    );
  if (path === "/waiting-room")
    return (
      <>
        <Heading
          eyebrow="YOUR PLACE IN THE POOL"
          title="Good things take three."
          description="You can leave this page. Matching happens on the server after the deadline."
        />
        <div className="waiting panel">
          <span className="waiting-icon">
            <GitBranch size={40} />
          </span>
          <Tag tone={reg.joined ? "green" : "neutral"}>
            {reg.joined ? reg.state : "Not in the pool yet"}
          </Tag>
          <h2>{w?.name || "Waiting for the organizer"}</h2>
          <Countdown window={w} />
          <p>
            {w?.status === "published"
              ? "Teams have been published."
              : w?.status === "review"
                ? "Organizers are reviewing proposed teams."
                : "After the window closes, we’ll match skills, goals and working preferences."}
          </p>
          {w?.status === "published" ? (
            <Button asChild>
              <Link href="/team">
                Meet my team <ArrowRight size={17} />
              </Link>
            </Button>
          ) : (
            !reg.joined && (
              <Button
                disabled={!profile.eligible || w?.status !== "open"}
                onClick={async () => {
                  if (
                    await action(
                      () => api("/participant/join", "POST"),
                      "You have joined the pool.",
                    )
                  )
                    refresh();
                }}
              >
                Join the matching pool
              </Button>
            )
          )}
        </div>
      </>
    );
  return (
    <>
      <Heading
        eyebrow="PARTICIPANT WORKSPACE"
        title={
          profile.name
            ? `Hey, ${profile.name.split(" ")[0]}.`
            : "Your next team starts here."
        }
        description="Your Luma responses are ready to do the introductions."
      />
      <div className="metrics three">
        <Metric
          icon={ShieldCheck}
          label="Luma registration"
          value={profile.state.replaceAll("_", " ")}
          detail={
            me.verified
              ? "Email ownership verified"
              : "Verify your email to continue"
          }
        />
        <Metric
          icon={CheckCircle2}
          label="Profile completeness"
          value={p ? `${p.completeness}%` : "—"}
          detail="Based on existing questionnaire responses"
        />
        <Metric
          icon={Clock}
          label="Time to matching"
          value={<Countdown window={w} />}
          detail={w?.status || "Organizer has not opened a window"}
        />
      </div>
      <div className="panel eligibility">
        <div>
          <Tag tone={profile.eligible ? "green" : "amber"}>
            {profile.eligible ? "Eligible to match" : "Action needed"}
          </Tag>
          <h2>
            {reg.joined
              ? "You’re in the pool."
              : profile.eligible
                ? "Your place in the pool is ready."
                : "Let’s get you ready."}
          </h2>
          <p>
            {profile.reasons.length
              ? profile.reasons.join(" · ")
              : "Your approved registration and imported profile meet the current matching policy."}
          </p>
        </div>
        <Button
          disabled={!profile.eligible || reg.joined || w?.status !== "open"}
          onClick={async () => {
            if (
              await action(
                () => api("/participant/join", "POST"),
                "You have joined the matching pool.",
              )
            )
              refresh();
          }}
        >
          {reg.joined ? (
            <>
              <Check size={17} /> Joined the pool
            </>
          ) : (
            <>
              Join the pool <ArrowRight size={17} />
            </>
          )}
        </Button>
      </div>
      <div className="panel">
        <div className="panel-heading">
          <div>
            <h2>Your imported profile</h2>
            <p>Collected on Luma. No extra form required.</p>
          </div>
          <Tag tone="neutral">Offline: {p?.availability || "unknown"}</Tag>
        </div>
        {profile.responses ? (
          <div className="response-grid">
            {Object.entries(profile.responses).map(([k, v]) => (
              <div key={k}>
                <small>{k.replaceAll("_", " ")}</small>
                <p>{String(v || "Not answered — unknown")}</p>
              </div>
            ))}
          </div>
        ) : (
          <Empty title="Registration not linked yet">
            Verify your email or ask an organizer to review your registration.
          </Empty>
        )}
      </div>
    </>
  );
}
function Admin({ path, action }: { path: string; action: Action }) {
  const [overview, setOverview] = useState<Data | null>(null),
    [imports, setImports] = useState<Data[]>([]),
    [people, setPeople] = useState<Data[]>([]),
    [teams, setTeams] = useState<Data[]>([]),
    [audit, setAudit] = useState<Data[]>([]),
    [unassigned, setUnassigned] = useState<Data[]>([]),
    [error, setError] = useState("");
  const [q, setQ] = useState(""),
    [filter, setFilter] = useState(""),
    [offset, setOffset] = useState(0),
    [selected, setSelected] = useState<Data | null>(null),
    [preview, setPreview] = useState<Data | null>(null),
    [dry, setDry] = useState<Data | null>(null),
    [busy, setBusy] = useState(false);
  const refresh = useCallback(async () => {
    try {
      const o = await api("/admin/overview");
      setOverview(o);
      if (path === "/admin/luma")
        setImports(await api("/admin/luma/imports?offset=" + offset));
      if (path === "/admin/participants")
        setPeople(
          await api(
            `/admin/participants?q=${encodeURIComponent(q)}&status=${filter}&offset=${offset}`,
          ),
        );
      if (path === "/admin/teams") {
        setTeams(await api("/admin/teams?offset=" + offset));
        setUnassigned(await api("/admin/unassigned?offset=" + offset));
      }
      if (path === "/admin/audit")
        setAudit(await api("/admin/audit?offset=" + offset));
      setError("");
    } catch (e) {
      setError((e as Error).message);
    }
  }, [path, q, filter, offset]);
  useEffect(() => {
    setOffset(0);
    setSelected(null);
  }, [path]);
  useEffect(() => {
    refresh();
    const t = setInterval(refresh, 15000);
    return () => clearInterval(t);
  }, [refresh]);
  async function act(fn: () => Promise<unknown>, message: string) {
    setBusy(true);
    const ok = await action(fn, message);
    if (ok) await refresh();
    setBusy(false);
    return ok;
  }
  if (error)
    return (
      <div className="alert error">
        {error}
        <Button variant="outline" onClick={refresh}>
          Retry
        </Button>
      </div>
    );
  if (!overview) return <Empty title="Loading organizer workspace…" />;
  const o = overview,
    w = o.window;
  const pagination = (
    <div className="pagination">
      <Button
        variant="outline"
        size="sm"
        disabled={offset === 0}
        onClick={() => setOffset(Math.max(0, offset - 30))}
      >
        Previous
      </Button>
      <span>
        Records {offset + 1}–{offset + 30}
      </span>
      <Button
        variant="outline"
        size="sm"
        onClick={() => setOffset(offset + 30)}
      >
        Next
      </Button>
    </div>
  );
  const reason = () =>
    window.prompt("Reason for this change (at least 5 characters):");
  if (path === "/admin/luma")
    return (
      <>
        <Heading
          eyebrow="REGISTRATION SOURCE"
          title="Luma imports."
          description="Bring registrations and existing questionnaire responses into one private workspace."
        />
        <div className="panel upload-panel">
          <span className="upload-icon">
            <Upload size={27} />
          </span>
          <h2>Your registrations, connected.</h2>
          <p>
            Upload your latest Luma CSV or XLSX export. Review the mappings
            before importing.
          </p>
          <label className="file-picker">
            Choose export file <ArrowUpRight size={15} />
            <input
              type="file"
              accept=".csv,.xlsx"
              disabled={busy}
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                setBusy(true);
                const data = new FormData();
                data.append("file", f);
                const ok = await action(async () => {
                  const result = await api(
                    "/admin/luma/import?preview=true",
                    "POST",
                    data,
                  );
                  setPreview({ ...result, file: f });
                }, "Preview ready. Review before confirming.");
                setBusy(false);
                if (!ok) setPreview(null);
              }}
            />
          </label>
          <small className="muted">
            CSV or XLSX · Up to 5 MB · Organizer access only
          </small>
        </div>
        {preview && (
          <div className="panel">
            <div className="panel-heading">
              <h2>Import preview</h2>
              <Tag>{preview.accepted} valid records</Tag>
            </div>
            <div className="metrics three">
              <Metric
                icon={CheckCircle2}
                label="Approved"
                value={preview.approved}
                detail="Luma approval status"
              />
              <Metric
                icon={AlertCircle}
                label="Needs review"
                value={
                  preview.rejected.length +
                  preview.duplicates.length +
                  preview.ambiguous_emails
                }
                detail="Rejected rows, duplicate IDs or emails"
              />
              <Metric
                icon={Clock}
                label="Availability unknown"
                value={preview.unknown_availability}
                detail="Blank responses stay unknown"
              />
            </div>
            <details>
              <summary>Exact column mappings</summary>
              <div className="mapping-list">
                {Object.entries(preview.mapping).map(([k, v]) => (
                  <div key={k}>
                    <code>{k}</code>
                    <span>{String(v)}</span>
                  </div>
                ))}
              </div>
            </details>
            {preview.rejected.length > 0 && (
              <pre>{JSON.stringify(preview.rejected, null, 2)}</pre>
            )}
            <div className="alert">
              This full export replaces the active attendee set. Registrations
              absent from it become inactive. Original responses are preserved;
              organizer overrides remain.
            </div>
            <Button
              disabled={busy}
              onClick={() =>
                act(async () => {
                  const d = new FormData();
                  d.append("file", preview.file);
                  await api("/admin/luma/import", "POST", d);
                  setPreview(null);
                }, "Luma dataset imported.")
              }
            >
              Confirm import <Check size={16} />
            </Button>
          </div>
        )}
        <div className="panel">
          <div className="panel-heading">
            <h2>Import history</h2>
            <span className="muted">Idempotent by file fingerprint</span>
          </div>
          {imports.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Version / file</th>
                    <th>Imported</th>
                    <th>Accepted</th>
                    <th>Approved</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {imports.map((i) => (
                    <tr key={i.id}>
                      <td>
                        <strong>v{i.id}</strong>
                        <small>{i.filename}</small>
                      </td>
                      <td>{new Date(i.created_at).toLocaleString()}</td>
                      <td>{i.accepted}</td>
                      <td>{i.approved}</td>
                      <td>
                        <Tag tone={i.active ? "green" : "neutral"}>
                          {i.active ? "Active" : "Archived"}
                        </Tag>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <Empty title="No imports yet">
              Choose a Luma export to get started.
            </Empty>
          )}
          {pagination}
        </div>
      </>
    );
  if (path === "/admin/participants")
    return (
      <>
        <Heading
          eyebrow="THE PEOPLE BEHIND THE IDEAS"
          title="Participants."
          description="Review registration, profile completeness and any eligibility issues."
        />
        <div className="toolbar">
          <label className="search">
            <Search size={17} />
            <input
              aria-label="Search by email"
              placeholder="Search by email address…"
              value={q}
              onChange={(e) => {
                setQ(e.target.value);
                setOffset(0);
              }}
            />
          </label>
          <select
            aria-label="Approval filter"
            value={filter}
            onChange={(e) => {
              setFilter(e.target.value);
              setOffset(0);
            }}
          >
            <option value="">All registrations</option>
            <option value="approved">Approved</option>
            <option value="declined">Declined</option>
          </select>
        </div>
        <div className="panel table-panel">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Participant</th>
                  <th>Skills</th>
                  <th>Profile</th>
                  <th>Offline</th>
                  <th>Eligibility</th>
                  <th />
                </tr>
              </thead>
              <tbody>
                {people.map((p) => (
                  <tr key={p.id}>
                    <td>
                      <strong>{p.name}</strong>
                      <small>{p.email}</small>
                    </td>
                    <td>
                      <div className="chips">
                        {p.profile.skills.map((s: string) => (
                          <span key={s}>{s}</span>
                        ))}
                      </div>
                    </td>
                    <td>
                      <div className="mini-progress">
                        <i style={{ width: p.profile.completeness + "%" }} />
                      </div>
                      <small>{p.profile.completeness}% complete</small>
                    </td>
                    <td>
                      <Tag
                        tone={
                          p.profile.availability === "yes" ? "green" : "amber"
                        }
                      >
                        {p.profile.availability}
                      </Tag>
                    </td>
                    <td>
                      <Tag tone={p.eligibility.eligible ? "green" : "neutral"}>
                        {p.eligibility.eligible
                          ? "Eligible"
                          : p.eligibility.state.replaceAll("_", " ")}
                      </Tag>
                    </td>
                    <td>
                      <button
                        className="text-link"
                        onClick={() => setSelected(p)}
                      >
                        Review <ArrowUpRight size={13} />
                      </button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!people.length && (
              <Empty title="No matching registrations">
                Import a Luma export or adjust your search.
              </Empty>
            )}
          </div>
          {pagination}
        </div>
        {selected && (
          <div className="modal-backdrop">
            <div className="modal panel">
              <div className="panel-heading">
                <h2>{selected.name}</h2>
                <Button variant="ghost" onClick={() => setSelected(null)}>
                  Close
                </Button>
              </div>
              <p>{selected.email}</p>
              <div className="alert">
                {selected.eligibility.reasons.join(" · ") ||
                  "Meets the current eligibility policy."}
              </div>
              <div className="response-grid">
                {Object.entries(selected.responses).map(([k, v]) => (
                  <div key={k}>
                    <small>{k}</small>
                    <p>{String(v || "Unknown")}</p>
                  </div>
                ))}
              </div>
              {selected.user_id ? (
                <div className="row-actions">
                  {[
                    ["Confirm offline", "yes"],
                    ["Unavailable offline", "no"],
                    ["Reset to unknown", "unknown"],
                  ].map(([label, v]) => (
                    <Button
                      key={v}
                      variant="outline"
                      size="sm"
                      onClick={() => {
                        const r = reason();
                        if (r)
                          act(
                            () =>
                              api(
                                "/admin/participants/" + selected.user_id,
                                "PATCH",
                                { availability: v, reason: r },
                              ),
                            "Availability updated.",
                          );
                      }}
                    >
                      {label}
                    </Button>
                  ))}
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const r = reason();
                      if (r)
                        act(
                          () =>
                            api(
                              "/admin/participants/" + selected.user_id,
                              "PATCH",
                              { excluded: true, reason: r },
                            ),
                          "Participant excluded.",
                        );
                    }}
                  >
                    Exclude
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={() => {
                      const r = reason();
                      if (r)
                        act(
                          () =>
                            api(
                              "/admin/participants/" + selected.user_id,
                              "PATCH",
                              { excluded: false, reason: r },
                            ),
                          "Participant reinstated.",
                        );
                    }}
                  >
                    Reinstate
                  </Button>
                </div>
              ) : (
                <p>
                  Participant needs to create an account before account-level
                  overrides are available.
                </p>
              )}
            </div>
          </div>
        )}
      </>
    );
  if (path === "/admin/matching")
    return (
      <>
        <Heading
          eyebrow="THE MATCHING ENGINE"
          title="A window for possibility."
          description="Set the deadline and eligibility policy. The server handles the rest."
        />
        <WindowForm current={w} busy={busy} action={act} />
        {w && (
          <div className="panel">
            <div className="panel-heading">
              <div>
                <h2>{w.name}</h2>
                <p>
                  Closes {new Date(w.closes).toLocaleString()} · Backend clock
                </p>
              </div>
              <Tag>{w.status}</Tag>
            </div>
            <div className="window-timer">
              <Countdown window={w} />
            </div>
            <div className="row-actions">
              <Button
                disabled={busy || !["open", "scheduled"].includes(w.status)}
                variant="outline"
                onClick={() =>
                  act(
                    async () =>
                      setDry(
                        await api(
                          `/admin/matching-windows/${w.id}/preview`,
                          "POST",
                        ),
                      ),
                    "Dry run ready. No teams were saved.",
                  )
                }
              >
                Preview allocation
              </Button>
              <Button
                disabled={
                  busy || !["closing", "failed", "review"].includes(w.status)
                }
                onClick={() =>
                  act(
                    () => api(`/admin/matching-windows/${w.id}/start`, "POST"),
                    "Proposals are ready for review.",
                  )
                }
              >
                Run / retry matching
              </Button>
              <Button
                disabled={busy || !["review", "failed"].includes(w.status)}
                variant="outline"
                onClick={() => {
                  const r = reason();
                  if (r)
                    act(
                      () =>
                        api(`/admin/matching-windows/${w.id}/reopen`, "POST", {
                          reason: r,
                        }),
                      "Window reopened for two hours.",
                    );
                }}
              >
                Reopen window
              </Button>
              <Button
                disabled={
                  busy || w.status === "published" || w.status === "cancelled"
                }
                variant="ghost"
                onClick={() => {
                  const r = reason();
                  if (r)
                    act(
                      () =>
                        api(`/admin/matching-windows/${w.id}/cancel`, "POST", {
                          reason: r,
                        }),
                      "Window cancelled.",
                    );
                }}
              >
                Cancel window
              </Button>
            </div>
            <p className="muted">
              Dry runs are previews. The final pool freezes at the deadline.
              Reopening discards unpublished proposals.
            </p>
          </div>
        )}
        {dry && (
          <div className="panel">
            <h2>Dry-run result</h2>
            <p>
              {dry.eligible} eligible participants · {dry.result.teams.length}{" "}
              complete teams · {dry.result.unassigned.length} waitlisted ·{" "}
              {dry.result.runtime_ms} ms
            </p>
            <details>
              <summary>Allocation and score breakdown</summary>
              <pre>{JSON.stringify(dry.result, null, 2)}</pre>
            </details>
          </div>
        )}
        <MappingEditor action={act} />
      </>
    );
  if (path === "/admin/teams")
    return (
      <>
        <Heading
          eyebrow="REVIEW BEFORE THE REVEAL"
          title="Team proposals."
          description="Review the full allocation, keep leftovers visible, and publish when ready."
        >
          <div className="row-actions">
            <Button
              variant="outline"
              disabled={busy || w?.status !== "review"}
              onClick={() => {
                const r = reason();
                if (r)
                  act(
                    () =>
                      api(
                        `/admin/matching-windows/${w.id}/regenerate`,
                        "POST",
                        { reason: r },
                      ),
                    "New proposals generated from the same frozen pool.",
                  );
              }}
            >
              Regenerate
            </Button>
            <Button
              disabled={busy || w?.status !== "review"}
              onClick={() =>
                act(
                  () => api(`/admin/matching-windows/${w.id}/publish`, "POST"),
                  "Teams published. Participants can now see their teammates.",
                )
              }
            >
              <Check size={16} /> Publish teams
            </Button>
          </div>
        </Heading>
        {teams.length ? (
          <div className="team-grid">
            {teams.map((t) => (
              <div key={t.id}>
                <TeamCard team={t} />
                {w?.status === "review" && (
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => {
                      const outgoing = window.prompt(
                        "Outgoing account ID (shown in the allocation details below):",
                      );
                      const incoming = window.prompt(
                        "Incoming frozen-pool account ID:",
                      );
                      const r = reason();
                      if (outgoing && incoming && r)
                        act(
                          () =>
                            api(`/admin/teams/${t.id}/reassign`, "POST", {
                              outgoing_user_id: Number(outgoing),
                              incoming_user_id: Number(incoming),
                              reason: r,
                            }),
                          "Allocation updated.",
                        );
                    }}
                  >
                    Reassign / swap participant
                  </Button>
                )}
                <details className="admin-ids">
                  <summary>Account IDs for reassignment</summary>
                  {t.members.map((m: Data) => (
                    <p key={m.id}>
                      {m.name}: {m.id}
                    </p>
                  ))}
                </details>
              </div>
            ))}
          </div>
        ) : (
          <Empty title="The next great teams are on their way">
            Teams appear after matching runs. Open a registration window to
            begin.
          </Empty>
        )}
        {pagination}
        <div className="panel">
          <div className="panel-heading">
            <h2>Unassigned & ineligible</h2>
            <Tag tone="amber">{o.waitlisted} waitlisted</Tag>
          </div>
          {unassigned.length ? (
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Account ID</th>
                    <th>Pool status</th>
                    <th>Reason</th>
                  </tr>
                </thead>
                <tbody>
                  {unassigned.map((u) => (
                    <tr key={u.user_id}>
                      <td>{u.user_id}</td>
                      <td>{u.state}</td>
                      <td>
                        {u.eligibility?.reasons?.join(" · ") ||
                          "Waiting for a complete team of three"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : (
            <p className="muted">No unresolved registrations in this window.</p>
          )}
        </div>
        {w?.status === "published" && (
          <div className="row-actions">
            <Button asChild variant="outline">
              <a href={"/api/admin/export?format=csv&window_id=" + w.id}>
                Export CSV <ArrowUpRight size={15} />
              </a>
            </Button>
            <Button asChild variant="outline">
              <a href={"/api/admin/export?format=xlsx&window_id=" + w.id}>
                Export XLSX <ArrowUpRight size={15} />
              </a>
            </Button>
            <Button asChild>
              <Link href="/admin/matching">
                Open another window <Plus size={16} />
              </Link>
            </Button>
          </div>
        )}
      </>
    );
  if (path === "/admin/audit")
    return (
      <>
        <Heading
          eyebrow="EVERY CHANGE HAS A STORY"
          title="Activity log."
          description="Administrative changes, matching runs and publication actions, with reasons."
        />
        <div className="panel table-panel">
          <div className="table-wrap">
            <table>
              <thead>
                <tr>
                  <th>Action</th>
                  <th>Target</th>
                  <th>Actor</th>
                  <th>Reason / details</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                {audit.map((a) => (
                  <tr key={a.id}>
                    <td>
                      <strong>{a.action}</strong>
                    </td>
                    <td>{a.target}</td>
                    <td>{a.actor || "Scheduler / operator"}</td>
                    <td>{a.reason || JSON.stringify(a.details)}</td>
                    <td>{new Date(a.created_at).toLocaleString()}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            {!audit.length && (
              <Empty title="A fresh start">
                Actions will appear here as you set up the event.
              </Empty>
            )}
          </div>
          {pagination}
        </div>
      </>
    );
  return (
    <>
      <Heading
        eyebrow="ORGANIZER WORKSPACE / HACKAMATCH 2026"
        title="Bring the right people together."
        description="One place to turn registrations into teams that are ready to build."
      >
        <Button asChild>
          <Link href="/admin/luma">
            <Upload size={16} /> Import Luma CSV
          </Link>
        </Button>
      </Heading>
      <div className="metrics">
        <Metric
          label="Imported registrations"
          value={o.total}
          icon={Users}
          detail="From the active Luma dataset"
        />
        <Metric
          label="Approved on Luma"
          value={o.approved}
          icon={ShieldCheck}
          detail={`${o.declined} declined registrations`}
        />
        <Metric
          label="Verified accounts"
          value={o.verified}
          icon={CheckCircle2}
          detail={`${o.eligible} currently eligible to match`}
        />
        <Metric
          label="Needs availability review"
          value={o.unknown_availability}
          icon={AlertCircle}
          detail="Unknown does not mean unavailable"
        />
      </div>
      <div className="overview-grid">
        <section className="panel window-panel">
          <div className="panel-heading">
            <div className="icon-heading">
              <span className="icon-box">
                <Clock size={19} />
              </span>
              <h2>Matching window</h2>
            </div>
            <Tag tone={w?.status === "open" ? "green" : "neutral"}>
              {w?.status || "Not opened"}
            </Tag>
          </div>
          <span className="muted">
            {w?.name || "Let’s make room for great teams."}
          </span>
          <div className="window-timer">
            <Countdown window={w} />
          </div>
          <p>
            {w
              ? "Time remaining until the pool freezes. Matching runs automatically."
              : "Open a two-hour registration window when you are ready for participants to join."}
          </p>
          <div className="panel-footer">
            <span>
              <span className="green-dot" /> Job:{" "}
              {o.job?.status || "Not scheduled"}
            </span>
            <Link href="/admin/matching" className="text-link">
              Manage window <ArrowUpRight size={14} />
            </Link>
          </div>
        </section>
        <section className="panel pipeline">
          <div className="panel-heading">
            <h2>From registration to team</h2>
            <GitBranch size={18} />
          </div>
          {[
            ["Luma registrations", o.total, "Import participant responses"],
            ["Verified accounts", o.verified, "Email ownership confirmed"],
            [
              "Eligible participants",
              o.eligible,
              "Current window policy applied",
            ],
            [
              "Published teams",
              o.published_teams,
              "Reviewed and ready to build",
            ],
          ].map(([label, n, desc], i) => (
            <div className="pipeline-step" key={String(label)}>
              <span
                className={"pipeline-index " + (Number(n) > 0 ? "done" : "")}
              >
                {Number(n) > 0 ? <Check size={13} /> : i + 1}
              </span>
              <div>
                <strong>{label}</strong>
                <small>{desc}</small>
              </div>
              <b>{n}</b>
            </div>
          ))}
        </section>
      </div>
      <div className="section-heading">
        <h2>Your next moves</h2>
        <span className="muted">A clear path to the first team reveal</span>
      </div>
      <div className="next-grid">
        {[
          [
            Upload,
            "Import registrations",
            "Use your latest Luma export. Responses come with it.",
            "/admin/luma",
            "Manage imports",
          ],
          [
            Users,
            "Review the pool",
            "Resolve incomplete profiles and offline availability.",
            "/admin/participants",
            "Review participants",
          ],
          [
            Layers,
            "Review the teams",
            "See proposed matches before making them visible.",
            "/admin/teams",
            "View proposals",
          ],
        ].map(([Icon, title, text, href, label]) => {
          const I = Icon as typeof Users;
          return (
            <div className="panel next-card" key={String(title)}>
              <I size={21} />
              <h3>{String(title)}</h3>
              <p>{String(text)}</p>
              <Link className="text-link" href={String(href)}>
                {String(label)} <ArrowUpRight size={14} />
              </Link>
            </div>
          );
        })}
      </div>
      {!o.email_enabled && (
        <div className="alert">
          <Mail size={17} /> Email delivery is disabled. Configure SMTP before
          accepting real participant signups.
        </div>
      )}
      <div className="footnote">
        <ShieldCheck size={15} /> Participant data is private. Teams are visible
        only after organizer publication.
      </div>
    </>
  );
}
const initialWeights = {
  skills: 35,
  roles: 20,
  goals: 15,
  experience: 10,
  schedule: 10,
  style: 5,
  interests: 5,
};
function WindowForm({
  current,
  busy,
  action,
}: {
  current: Data | null;
  busy: boolean;
  action: Action;
}) {
  const [name, setName] = useState("HackAMatch · Main round"),
    [duration, setDuration] = useState("7200"),
    [openAt, setOpenAt] = useState(""),
    [offline, setOffline] = useState(false),
    [weights, setWeights] = useState<Data>(initialWeights),
    [required, setRequired] = useState("skills, goals, schedule");
  useEffect(() => {
    if (current) {
      setName(current.name);
      setOffline(current.policy.require_offline);
      setWeights(current.config.weights);
      setRequired(current.policy.required_fields.join(", "));
    }
  }, [current?.id]);
  const edit = current && ["open", "scheduled"].includes(current.status),
    canCreate = !current || ["published", "cancelled"].includes(current.status);
  async function submit(e: FormEvent) {
    e.preventDefault();
    const policy = {
        require_offline: offline,
        required_fields: required
          .split(",")
          .map((x) => x.trim())
          .filter(Boolean),
      },
      config = { seed: 42, weights };
    if (edit) {
      const r = window.prompt(
        "Reason for changing the current policy (5+ characters):",
      );
      if (r)
        action(
          () =>
            api(`/admin/matching-windows/${current.id}`, "PATCH", {
              policy,
              config,
              reason: r,
            }),
          "Window configuration saved.",
        );
    } else
      action(
        () =>
          api("/admin/matching-windows", "POST", {
            name,
            duration_seconds: Number(duration),
            opens: openAt ? new Date(openAt).toISOString() : null,
            policy,
            config,
          }),
        "Registration window opened.",
      );
  }
  return (
    <form className="panel window-form" onSubmit={submit}>
      <div className="panel-heading">
        <h2>{edit ? "Window configuration" : "Open a matching window"}</h2>
        <Tag tone="neutral">3 participants / team</Tag>
      </div>
      <div className="form-grid">
        <label>
          Window name
          <input
            value={name}
            onChange={(e) => setName(e.target.value)}
            required
            minLength={2}
            disabled={!!edit}
          />
        </label>
        <label>
          Duration
          <select
            value={duration}
            onChange={(e) => setDuration(e.target.value)}
            disabled={!!edit}
          >
            <option value="7200">2 hours · production default</option>
            <option value="60">1 minute · development only</option>
            <option value="10">10 seconds · development test</option>
          </select>
        </label>
      </div>
      {!edit && (
        <label>
          Opening time (optional; leave blank to open now)
          <input
            type="datetime-local"
            value={openAt}
            onChange={(e) => setOpenAt(e.target.value)}
          />
        </label>
      )}
      <label className="checkbox">
        <input
          type="checkbox"
          checked={offline}
          onChange={(e) => setOffline(e.target.checked)}
        />
        <span>
          Require confirmed offline availability
          <small>
            Unknown and negative responses are excluded until organizers resolve
            them.
          </small>
        </span>
      </label>
      <label>
        Required normalized fields
        <input value={required} onChange={(e) => setRequired(e.target.value)} />
      </label>
      <h3>
        Matching weights <span className="muted"> / total must equal 100%</span>
      </h3>
      <div className="weights">
        {Object.entries(weights).map(([k, v]) => (
          <label key={k}>
            {k}
            <div>
              <input
                type="number"
                min={0}
                max={100}
                value={v}
                onChange={(e) =>
                  setWeights({ ...weights, [k]: Number(e.target.value) })
                }
              />
              <span>%</span>
            </div>
          </label>
        ))}
      </div>
      <p className="muted">
        Initial heuristic weights. Missing signals are omitted and the available
        weights are normalized.
      </p>
      <Button type="submit" disabled={busy || (!edit && !canCreate)}>
        {edit ? "Save configuration" : "Open registration window"}
        <ArrowRight size={16} />
      </Button>
    </form>
  );
}
function MappingEditor({ action }: { action: Action }) {
  const [value, setValue] = useState("");
  const [loaded, setLoaded] = useState(false);
  return (
    <details className="panel">
      <summary
        onClick={() => {
          if (!loaded)
            api("/admin/skill-mappings").then((v) => {
              setValue(JSON.stringify(v, null, 2));
              setLoaded(true);
            });
        }}
      >
        Skill keyword mappings
      </summary>
      <p className="muted">
        Edit the keywords within each category. Saving re-normalizes imported
        profiles; frozen allocations keep their snapshot.
      </p>
      <textarea
        aria-label="Skill mappings JSON"
        rows={14}
        value={value}
        onChange={(e) => setValue(e.target.value)}
      />
      <Button
        variant="outline"
        disabled={!loaded}
        onClick={() => {
          const r = window.prompt(
            "Reason for changing keyword mappings (5+ characters):",
          );
          if (r)
            action(
              async () =>
                api("/admin/skill-mappings", "PUT", {
                  mappings: JSON.parse(value),
                  reason: r,
                }),
              "Skill mappings saved.",
            );
        }}
      >
        Save mappings
      </Button>
    </details>
  );
}
export default function Page() {
  return (
    <Suspense fallback={<div className="empty">Loading HackAMatch…</div>}>
      <Shell />
    </Suspense>
  );
}
