import {
  ArrowDownRight,
  BookOpen,
  BriefcaseBusiness,
  CalendarDays,
  Check,
  CircleHelp,
  Clock3,
  Compass,
  FolderKanban,
  Goal,
  Heart,
  LayoutDashboard,
  Lightbulb,
  ListTodo,
  Settings2,
  Sparkles,
  UserRound,
} from "lucide-react";
import PersonalWorkspace from "./personal-workspace";
import WorkManagement from "./work-management";
import CalendarWorkspace from "./calendar-workspace";
import {
  DailyBriefingCard,
  OllamaStatusCard,
  WeeklyReviewCard,
} from "./ai-workspace";
import PlanningWorkspace from "./planning-workspace";
import PreferenceWorkspace from "./preference-workspace";

const navigation = [
  { label: "Today", icon: LayoutDashboard, active: true, href: "#today" },
  { label: "My direction", icon: Compass, href: "#career" },
  { label: "Projects", icon: FolderKanban, href: "#projects" },
  { label: "Academic", icon: BookOpen, href: "#academic" },
  { label: "Calendar", icon: CalendarDays, href: "#calendar" },
  { label: "Tasks", icon: ListTodo, href: "#tasks" },
  { label: "My profile", icon: UserRound, href: "#profile" },
  { label: "CV & experience", icon: BriefcaseBusiness, href: "#resume" },
  { label: "Principles", icon: Lightbulb, href: "#principles" },
  { label: "AI preferences", icon: Sparkles, href: "#preferences" },
  { label: "History & reviews", icon: Clock3, href: "#weekly-review" },
];

const setupItems = [
  { label: "Personal profile and goals", detail: "Write and maintain your own context", available: true },
  { label: "Career and study goals", detail: "Track the directions you want to grow", available: true },
  { label: "Projects and tasks", detail: "Track milestones and concrete next actions", available: true },
  { label: "Calendar integration", detail: "Import authorized iCalendar events", available: true },
];

export default function Home() {
  return (
    <div className="app-shell" id="today">
      <aside className="sidebar">
        <a className="brand" href="#today" aria-label="Personal space home">
          <span className="brand-mark">
            <Sparkles size={19} strokeWidth={2.2} />
          </span>
          <span className="brand-copy">
            <strong>daymark</strong>
            <span>PERSONAL SPACE</span>
          </span>
        </a>

        <div className="workspace-label">WORKSPACE</div>
        <nav className="main-nav" aria-label="Main navigation">
          {navigation.map(({ label, icon: Icon, active, href }) =>
            href ? (
              <a
                className={`nav-item${active ? " nav-item-active" : ""}`}
                href={href}
                key={label}
                aria-current={active ? "page" : undefined}
              >
                <Icon size={18} />
                <span>{label}</span>
              </a>
            ) : (
              <span
                className="nav-item nav-item-disabled"
                key={label}
                aria-disabled="true"
                title="Planned for a later development phase"
              >
                <Icon size={18} />
                <span>{label}</span>
              </span>
            ),
          )}
        </nav>

        <div className="sidebar-bottom">
          <div className="sidebar-note">
            <div className="sidebar-note-icon">
              <Heart size={16} />
            </div>
            <p>Built around your life, not the other way around.</p>
          </div>
          <span className="nav-item nav-item-disabled" aria-disabled="true">
            <Settings2 size={18} />
            <span>Settings</span>
          </span>
          <div className="local-profile">
            <div className="avatar">Y</div>
            <div>
              <strong>Your workspace</strong>
              <span>Private · on this server</span>
            </div>
            <CircleHelp className="profile-help" size={16} />
          </div>
        </div>
      </aside>

      <main className="main-area">
        <header className="topbar">
          <div className="breadcrumbs">
            <span>Workspace</span>
            <span className="breadcrumb-divider">/</span>
            <strong>Today</strong>
          </div>
          <div className="topbar-status">
            <span className="status-dot" />
            Your data stays local
          </div>
        </header>

        <div className="dashboard-content">
          <section className="welcome-row">
            <div>
              <div className="eyebrow">
                <span className="eyebrow-line" />
                YOUR PERSONAL COMMAND CENTER
              </div>
              <h1>A little more clarity, every day.</h1>
              <p className="welcome-copy">
                A thoughtful space to connect what needs doing with what
                matters to you.
              </p>
            </div>
            <div className="phase-pill">
              <span className="phase-pill-dot" />
              Phase 8 · Scheduled reviews
            </div>
          </section>

          <section className="status-grid" aria-label="Workspace setup status">
            <article className="status-card">
              <div className="status-card-top">
                <span className="status-icon status-icon-lilac">
                  <CalendarDays size={18} />
                </span>
                <span className="status-tag status-tag-ready">Available</span>
              </div>
              <p className="status-label">Your calendar</p>
              <p className="status-value">Import your schedule</p>
              <p className="status-detail">Connect a private, encrypted iCalendar feed.</p>
            </article>
            <article className="status-card">
              <div className="status-card-top">
                <span className="status-icon status-icon-mint">
                  <ListTodo size={18} />
                </span>
                <span className="status-tag status-tag-ready">Available</span>
              </div>
              <p className="status-label">Your priorities</p>
              <p className="status-value">Projects and next actions</p>
              <p className="status-detail">Plan work around the goals that matter.</p>
            </article>
            <OllamaStatusCard />
          </section>

          <PersonalWorkspace />
          <WorkManagement />
          <CalendarWorkspace />
          <PlanningWorkspace />
          <PreferenceWorkspace />

          <div className="content-grid">
            <div className="primary-column">
              <section className="panel setup-panel">
                <div className="panel-heading">
                  <div>
                    <div className="section-kicker">A GOOD PLACE TO BEGIN</div>
                    <h2>Make this space yours</h2>
                  </div>
                  <span className="heading-icon">
                    <ArrowDownRight size={19} />
                  </span>
                </div>
                <p className="panel-intro">
                  Your dashboard will become more useful as you add the
                  information you want it to work with.
                </p>
                <div className="setup-list">
                  {setupItems.map((item, index) => (
                    <div className="setup-item" key={item.label}>
                      <span className="setup-number">0{index + 1}</span>
                      <span className="setup-copy">
                        <strong>{item.label}</strong>
                        <span>{item.detail}</span>
                      </span>
                      <span className={`setup-state${item.available ? " setup-state-ready" : ""}`}>
                        {item.available ? "Available" : "Planned"}
                      </span>
                    </div>
                  ))}
                </div>
                <div className="panel-footer">
                  <span>
                    Your information stays on your own server.
                  </span>
                  <span className="privacy-check">
                    <Check size={14} />
                  </span>
                </div>
              </section>

            </div>

            <aside className="secondary-column">
              <DailyBriefingCard />
              <WeeklyReviewCard />

              <section className="panel focus-panel">
                <div className="panel-heading panel-heading-compact">
                  <div>
                    <div className="section-kicker">KEEP YOUR NORTH STAR</div>
                    <h2>What matters to you</h2>
                  </div>
                  <span className="heading-icon heading-icon-small">
                    <Goal size={17} />
                  </span>
                </div>
                <p className="focus-copy">
                  Your ambitions and personal principles will guide future
                  planning. They remain yours to write and edit.
                </p>
                <div className="focus-placeholder">
                  <Compass size={17} />
                  <span>Your direction is yours to define.</span>
                </div>
              </section>

              <div className="privacy-card">
                <span className="privacy-shield">
                  <Heart size={16} />
                </span>
                <div>
                  <strong>Private by design</strong>
                  <p>Your data is kept on your self-hosted server.</p>
                </div>
              </div>
            </aside>
          </div>

          <footer className="page-footer">
            <span>DAYMARK <span className="footer-separator">·</span> YOUR OWN PACE</span>
            <span>Phase 8 <span className="footer-separator">·</span> Scheduled reviews</span>
          </footer>
        </div>
      </main>
    </div>
  );
}
