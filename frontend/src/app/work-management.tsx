"use client";

import { FormEvent, useEffect, useState } from "react";
import {
  ArrowUpRight,
  Circle,
  CircleCheck,
  Clock3,
  FolderKanban,
  Pencil,
  Plus,
  Save,
  Search,
  Trash2,
} from "lucide-react";

type Goal = { id: string; title: string; status: string };
type Milestone = {
  id: string;
  project_id: string;
  title: string;
  description: string;
  target_date: string | null;
  status: "pending" | "completed" | "cancelled";
  completed_at: string | null;
  task_count: number;
  completed_task_count: number;
  created_at: string;
  updated_at: string;
};
type Project = {
  id: string;
  title: string;
  description: string;
  purpose: string;
  category: ProjectCategory;
  status: ProjectStatus;
  importance: number;
  start_date: string | null;
  target_date: string | null;
  estimated_effort_hours: number | null;
  actual_effort_hours: number | null;
  notes: string;
  acquired_skills: string[];
  career_goal_ids: string[];
  academic_goal_ids: string[];
  career_goal_titles: string[];
  academic_goal_titles: string[];
  milestone_count: number;
  completed_milestone_count: number;
  task_count: number;
  completed_task_count: number;
  progress_percent: number;
  created_at: string;
  updated_at: string;
  milestones: Milestone[];
};
type Task = {
  id: string;
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  deadline: string | null;
  estimated_duration_minutes: number | null;
  actual_duration_minutes: number | null;
  category: TaskCategory;
  source: "user";
  project_id: string | null;
  project_title: string | null;
  milestone_id: string | null;
  milestone_title: string | null;
  career_goal_id: string | null;
  career_goal_title: string | null;
  academic_goal_id: string | null;
  academic_goal_title: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
};
type ProjectCategory =
  | "academic"
  | "career_development"
  | "technical"
  | "personal_development"
  | "creative"
  | "other";
type ProjectStatus = "active" | "paused" | "completed" | "archived";
type TaskStatus = "todo" | "in_progress" | "completed" | "cancelled";
type TaskPriority = "low" | "normal" | "high" | "urgent";
type TaskCategory =
  | "academic"
  | "career"
  | "personal"
  | "projects"
  | "administrative"
  | "general";

type ProjectDraft = {
  title: string;
  description: string;
  purpose: string;
  category: ProjectCategory;
  status: ProjectStatus;
  importance: number;
  start_date: string | null;
  target_date: string | null;
  estimated_effort_hours: number | null;
  actual_effort_hours: number | null;
  notes: string;
  acquired_skills: string[];
  career_goal_ids: string[];
  academic_goal_ids: string[];
};
type TaskDraft = {
  title: string;
  description: string;
  status: TaskStatus;
  priority: TaskPriority;
  deadline: string | null;
  estimated_duration_minutes: number | null;
  actual_duration_minutes: number | null;
  category: TaskCategory;
  project_id: string | null;
  milestone_id: string | null;
  career_goal_id: string | null;
  academic_goal_id: string | null;
};

const EMPTY_PROJECT: ProjectDraft = {
  title: "",
  description: "",
  purpose: "",
  category: "other",
  status: "active",
  importance: 3,
  start_date: null,
  target_date: null,
  estimated_effort_hours: null,
  actual_effort_hours: null,
  notes: "",
  acquired_skills: [],
  career_goal_ids: [],
  academic_goal_ids: [],
};
const EMPTY_TASK: TaskDraft = {
  title: "",
  description: "",
  status: "todo",
  priority: "normal",
  deadline: null,
  estimated_duration_minutes: null,
  actual_duration_minutes: null,
  category: "general",
  project_id: null,
  milestone_id: null,
  career_goal_id: null,
  academic_goal_id: null,
};
const PROJECT_CATEGORIES: ProjectCategory[] = [
  "academic",
  "career_development",
  "technical",
  "personal_development",
  "creative",
  "other",
];
const PROJECT_STATUSES: ProjectStatus[] = ["active", "paused", "completed", "archived"];
const TASK_STATUSES: TaskStatus[] = ["todo", "in_progress", "completed", "cancelled"];
const TASK_PRIORITIES: TaskPriority[] = ["low", "normal", "high", "urgent"];
const TASK_CATEGORIES: TaskCategory[] = [
  "academic",
  "career",
  "personal",
  "projects",
  "administrative",
  "general",
];
async function api<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, cache: "no-store" });
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body: { detail?: string } = await response.json();
      if (body.detail) message = body.detail;
    } catch {
      // Preserve the HTTP status when the server does not return JSON.
    }
    throw new Error(message);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

function body(value: unknown): RequestInit {
  return {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(value),
  };
}

function label(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function dateInput(value: string | null) {
  return value ?? "";
}

function FormInput({
  label: caption,
  value,
  onChange,
  type = "text",
  required = false,
  placeholder,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  type?: string;
  required?: boolean;
  placeholder?: string;
}) {
  return (
    <label className="personal-field">
      <span>{caption}</span>
      <input
        type={type}
        value={value}
        required={required}
        maxLength={1000}
        placeholder={placeholder}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function FormText({
  label: caption,
  value,
  onChange,
  rows = 3,
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  rows?: number;
}) {
  return (
    <label className="personal-field">
      <span>{caption}</span>
      <textarea
        value={value}
        rows={rows}
        maxLength={20000}
        onChange={(event) => onChange(event.target.value)}
      />
    </label>
  );
}

function FormSelect({
  label: caption,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: readonly string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="personal-field">
      <span>{caption}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option value={option} key={option}>
            {label(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function GoalChoices({
  title,
  goals,
  selected,
  onChange,
}: {
  title: string;
  goals: Goal[];
  selected: string[];
  onChange: (value: string[]) => void;
}) {
  const choices = goals.filter((goal) => goal.status !== "archived");
  return (
    <fieldset className="work-goal-choices">
      <legend>{title}</legend>
      {choices.length === 0 ? (
        <p>No goals available yet. Add one under Personal information first.</p>
      ) : (
        <div>
          {choices.map((goal) => (
            <label key={goal.id}>
              <input
                type="checkbox"
                checked={selected.includes(goal.id)}
                onChange={(event) =>
                  onChange(
                    event.target.checked
                      ? [...selected, goal.id]
                      : selected.filter((id) => id !== goal.id),
                  )
                }
              />
              {goal.title}
            </label>
          ))}
        </div>
      )}
    </fieldset>
  );
}

function ProjectForm({
  initial,
  careerGoals,
  academicGoals,
  saving,
  onSave,
  onCancel,
}: {
  initial: ProjectDraft;
  careerGoals: Goal[];
  academicGoals: Goal[];
  saving: boolean;
  onSave: (draft: ProjectDraft) => void;
  onCancel?: () => void;
}) {
  const [draft, setDraft] = useState(initial);
  function set<K extends keyof ProjectDraft>(key: K, value: ProjectDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSave(draft);
  }
  return (
    <form className="personal-form work-editor" onSubmit={submit}>
      <div className="personal-form-grid">
        <FormInput label="Project title" required value={draft.title} onChange={(value) => set("title", value)} placeholder="e.g. Build a portfolio application" />
        <FormSelect label="Category" value={draft.category} options={PROJECT_CATEGORIES} onChange={(value) => set("category", value as ProjectCategory)} />
        <FormText label="Description" value={draft.description} onChange={(value) => set("description", value)} />
        <FormText label="Purpose" value={draft.purpose} onChange={(value) => set("purpose", value)} />
        <FormInput label="Start date" type="date" value={dateInput(draft.start_date)} onChange={(value) => set("start_date", value || null)} />
        <FormInput label="Target date" type="date" value={dateInput(draft.target_date)} onChange={(value) => set("target_date", value || null)} />
        <FormInput label="Estimated effort (hours)" type="number" value={draft.estimated_effort_hours?.toString() ?? ""} onChange={(value) => set("estimated_effort_hours", value ? Number(value) : null)} />
        <FormInput label="Actual effort so far (hours)" type="number" value={draft.actual_effort_hours?.toString() ?? ""} onChange={(value) => set("actual_effort_hours", value ? Number(value) : null)} />
        <FormSelect label="Status" value={draft.status} options={PROJECT_STATUSES} onChange={(value) => set("status", value as ProjectStatus)} />
        <label className="personal-field">
          <span>Importance · {draft.importance} of 5</span>
          <input type="range" min="1" max="5" value={draft.importance} onChange={(event) => set("importance", Number(event.target.value))} />
        </label>
        <FormText label="Skills gained (one per line)" value={draft.acquired_skills.join("\n")} onChange={(value) => set("acquired_skills", value.split(/\r?\n/).map((part) => part.trim()).filter(Boolean))} rows={2} />
        <FormText label="Project notes" value={draft.notes} onChange={(value) => set("notes", value)} rows={2} />
      </div>
      <div className="work-goal-grid">
        <GoalChoices title="Career goals this project supports" goals={careerGoals} selected={draft.career_goal_ids} onChange={(value) => set("career_goal_ids", value)} />
        <GoalChoices title="Academic goals this project supports" goals={academicGoals} selected={draft.academic_goal_ids} onChange={(value) => set("academic_goal_ids", value)} />
      </div>
      <div className="personal-form-actions">
        {onCancel && <button className="personal-button personal-button-subtle" type="button" onClick={onCancel}>Cancel</button>}
        <button className="personal-button personal-button-primary" type="submit" disabled={saving}><Save size={14} />{saving ? "Saving…" : "Save project"}</button>
      </div>
    </form>
  );
}

function TaskForm({
  initial,
  projects,
  careerGoals,
  academicGoals,
  saving,
  onSave,
  onCancel,
}: {
  initial: TaskDraft;
  projects: Project[];
  careerGoals: Goal[];
  academicGoals: Goal[];
  saving: boolean;
  onSave: (draft: TaskDraft) => void;
  onCancel?: () => void;
}) {
  const [draft, setDraft] = useState(initial);
  const milestones = projects.find((project) => project.id === draft.project_id)?.milestones ?? [];
  function set<K extends keyof TaskDraft>(key: K, value: TaskDraft[K]) {
    setDraft((current) => ({ ...current, [key]: value }));
  }
  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSave(draft);
  }
  return (
    <form className="personal-form work-editor" onSubmit={submit}>
      <div className="personal-form-grid">
        <FormInput label="Task" required value={draft.title} onChange={(value) => set("title", value)} placeholder="What needs doing?" />
        <FormSelect label="Category" value={draft.category} options={TASK_CATEGORIES} onChange={(value) => set("category", value as TaskCategory)} />
        <FormText label="Description" value={draft.description} onChange={(value) => set("description", value)} rows={2} />
        <FormInput label="Deadline" type="date" value={dateInput(draft.deadline)} onChange={(value) => set("deadline", value || null)} />
        <FormSelect label="Priority" value={draft.priority} options={TASK_PRIORITIES} onChange={(value) => set("priority", value as TaskPriority)} />
        <FormSelect label="Status" value={draft.status} options={TASK_STATUSES} onChange={(value) => set("status", value as TaskStatus)} />
        <FormInput label="Estimated duration (minutes)" type="number" value={draft.estimated_duration_minutes?.toString() ?? ""} onChange={(value) => set("estimated_duration_minutes", value ? Number(value) : null)} />
        <FormInput label="Actual duration (minutes)" type="number" value={draft.actual_duration_minutes?.toString() ?? ""} onChange={(value) => set("actual_duration_minutes", value ? Number(value) : null)} />
        <label className="personal-field">
          <span>Project</span>
          <select value={draft.project_id ?? ""} onChange={(event) => { set("project_id", event.target.value || null); set("milestone_id", null); }}>
            <option value="">No project</option>
            {projects.map((project) => <option key={project.id} value={project.id}>{project.title}</option>)}
          </select>
        </label>
        <label className="personal-field">
          <span>Project milestone</span>
          <select value={draft.milestone_id ?? ""} disabled={!draft.project_id} onChange={(event) => set("milestone_id", event.target.value || null)}>
            <option value="">No milestone</option>
            {milestones.map((milestone) => <option key={milestone.id} value={milestone.id}>{milestone.title}</option>)}
          </select>
        </label>
        <label className="personal-field">
          <span>Career goal</span>
          <select value={draft.career_goal_id ?? ""} onChange={(event) => set("career_goal_id", event.target.value || null)}>
            <option value="">No career goal</option>
            {careerGoals.filter((goal) => goal.status !== "archived").map((goal) => <option key={goal.id} value={goal.id}>{goal.title}</option>)}
          </select>
        </label>
        <label className="personal-field">
          <span>Academic goal</span>
          <select value={draft.academic_goal_id ?? ""} onChange={(event) => set("academic_goal_id", event.target.value || null)}>
            <option value="">No academic goal</option>
            {academicGoals.filter((goal) => goal.status !== "archived").map((goal) => <option key={goal.id} value={goal.id}>{goal.title}</option>)}
          </select>
        </label>
      </div>
      <div className="personal-form-actions">
        {onCancel && <button className="personal-button personal-button-subtle" type="button" onClick={onCancel}>Cancel</button>}
        <button className="personal-button personal-button-primary" type="submit" disabled={saving}><Save size={14} />{saving ? "Saving…" : "Save task"}</button>
      </div>
    </form>
  );
}

export default function WorkManagement() {
  const [projects, setProjects] = useState<Project[]>([]);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [careerGoals, setCareerGoals] = useState<Goal[]>([]);
  const [academicGoals, setAcademicGoals] = useState<Goal[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [editingProject, setEditingProject] = useState<string | null>(null);
  const [editingTask, setEditingTask] = useState<string | null>(null);
  const [projectFormOpen, setProjectFormOpen] = useState(false);
  const [taskFormOpen, setTaskFormOpen] = useState(false);
  const [search, setSearch] = useState("");
  const [taskStatus, setTaskStatus] = useState("");
  const [taskCategory, setTaskCategory] = useState("");

  async function loadTasks() {
    const params = new URLSearchParams();
    if (search.trim()) params.set("search", search.trim());
    if (taskStatus) params.set("status", taskStatus);
    if (taskCategory) params.set("category", taskCategory);
    try {
      setTasks(await api<Task[]>(`/api/tasks?${params.toString()}`));
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load tasks.");
    }
  }

  useEffect(() => {
    let active = true;
    void Promise.all([
      api<Project[]>("/api/projects"),
      api<Goal[]>("/api/goals/career"),
      api<Goal[]>("/api/goals/academic"),
    ])
      .then(async ([projectData, careerData, academicData]) => {
        const [projectList, taskList] = await Promise.all([
          Promise.all(
            projectData.map(async (project) => ({
              ...project,
              milestones: await api<Milestone[]>(`/api/projects/${project.id}/milestones`),
            })),
          ),
          api<Task[]>("/api/tasks"),
        ]);
        if (!active) return;
        setProjects(projectList);
        setTasks(taskList);
        setCareerGoals(careerData);
        setAcademicGoals(academicData);
      })
      .catch((cause: unknown) => {
        if (active) setError(cause instanceof Error ? cause.message : "Could not load projects and tasks.");
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  const filteredTasks = tasks;
  const activeProjects = projects.filter((project) => project.status !== "archived");

  async function run(action: () => Promise<void>, message: string) {
    setSaving(true);
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(message);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The change could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function saveProject(draft: ProjectDraft) {
    await run(async () => {
      const editing = projects.find((project) => project.id === editingProject);
      const saved = await api<Project>(
        editing ? `/api/projects/${editing.id}` : "/api/projects",
        { method: editing ? "PATCH" : "POST", ...body(draft) },
      );
      const milestones = editing?.milestones ?? [];
      setProjects((current) =>
        editing
          ? current.map((project) => project.id === saved.id ? { ...saved, milestones } : project)
          : [{ ...saved, milestones: [] }, ...current],
      );
      setEditingProject(null);
      setProjectFormOpen(false);
    }, "Project saved.");
  }

  async function deleteProject(project: Project) {
    if (!window.confirm(`Delete “${project.title}”? Its tasks will be kept without the project link.`)) return;
    await run(async () => {
      await api<void>(`/api/projects/${project.id}`, { method: "DELETE" });
      setProjects((current) => current.filter((item) => item.id !== project.id));
      setTasks((current) => current.map((task) => task.project_id === project.id ? { ...task, project_id: null, project_title: null, milestone_id: null, milestone_title: null } : task));
    }, "Project deleted. Linked tasks were preserved.");
  }

  async function addMilestone(project: Project) {
    const title = window.prompt("Milestone title");
    if (!title?.trim()) return;
    const target = window.prompt("Optional target date (YYYY-MM-DD)", "");
    await run(async () => {
      const milestone = await api<Milestone>(`/api/projects/${project.id}/milestones`, {
        method: "POST",
        ...body({ title: title.trim(), target_date: target?.trim() || null }),
      });
      setProjects((current) => current.map((item) => item.id === project.id ? { ...item, milestones: [...item.milestones, milestone], milestone_count: item.milestone_count + 1 } : item));
    }, "Milestone added.");
  }

  async function editMilestone(project: Project, milestone: Milestone) {
    const title = window.prompt("Milestone title", milestone.title);
    if (!title?.trim()) return;
    const target = window.prompt("Optional target date (YYYY-MM-DD)", milestone.target_date ?? "");
    if (target === null) return;
    await run(async () => {
      await api<Milestone>(`/api/projects/${project.id}/milestones/${milestone.id}`, {
        method: "PATCH",
        ...body({ title: title.trim(), target_date: target.trim() || null }),
      });
      await reloadProjects();
    }, "Milestone updated.");
  }

  async function toggleMilestone(project: Project, milestone: Milestone) {
    const status = milestone.status === "completed" ? "pending" : "completed";
    await run(async () => {
      const updated = await api<Milestone>(`/api/projects/${project.id}/milestones/${milestone.id}`, { method: "PATCH", ...body({ status }) });
      setProjects((current) => current.map((item) => item.id !== project.id ? item : { ...item, milestones: item.milestones.map((row) => row.id === updated.id ? updated : row), completed_milestone_count: item.completed_milestone_count + (status === "completed" ? 1 : -1) }));
      await reloadProjects();
    }, status === "completed" ? "Milestone marked complete." : "Milestone reopened.");
  }

  async function removeMilestone(project: Project, milestone: Milestone) {
    if (!window.confirm(`Delete milestone “${milestone.title}”? Tasks will be kept without a milestone link.`)) return;
    await run(async () => {
      await api<void>(`/api/projects/${project.id}/milestones/${milestone.id}`, { method: "DELETE" });
      setProjects((current) => current.map((item) => item.id !== project.id ? item : { ...item, milestones: item.milestones.filter((row) => row.id !== milestone.id), milestone_count: Math.max(0, item.milestone_count - 1) }));
      setTasks((current) => current.map((task) => task.milestone_id === milestone.id ? { ...task, milestone_id: null, milestone_title: null } : task));
      await reloadProjects();
    }, "Milestone deleted.");
  }

  async function reloadProjects() {
    const data = await api<Project[]>("/api/projects");
    setProjects(await Promise.all(data.map(async (project) => ({ ...project, milestones: await api<Milestone[]>(`/api/projects/${project.id}/milestones`) }))));
  }

  async function saveTask(draft: TaskDraft) {
    await run(async () => {
      const editing = tasks.find((task) => task.id === editingTask);
      const saved = await api<Task>(
        editing ? `/api/tasks/${editing.id}` : "/api/tasks",
        { method: editing ? "PATCH" : "POST", ...body(draft) },
      );
      setTasks((current) =>
        editing
          ? current.map((task) => task.id === saved.id ? saved : task)
          : [saved, ...current],
      );
      setEditingTask(null);
      setTaskFormOpen(false);
      await reloadProjects();
    }, "Task saved.");
  }

  async function toggleTask(task: Task) {
    const status: TaskStatus = task.status === "completed" ? "todo" : "completed";
    await run(async () => {
      const saved = await api<Task>(`/api/tasks/${task.id}`, { method: "PATCH", ...body({ status }) });
      setTasks((current) => current.map((item) => item.id === saved.id ? saved : item));
      await reloadProjects();
    }, status === "completed" ? "Task completed." : "Task reopened.");
  }

  async function deleteTask(task: Task) {
    if (!window.confirm(`Delete task “${task.title}”?`)) return;
    await run(async () => {
      await api<void>(`/api/tasks/${task.id}`, { method: "DELETE" });
      setTasks((current) => current.filter((item) => item.id !== task.id));
      await reloadProjects();
    }, "Task deleted.");
  }

  async function postponeTask(task: Task) {
    if (!task.deadline) return;
    const deadline = new Date(`${task.deadline}T00:00:00Z`);
    deadline.setUTCDate(deadline.getUTCDate() + 1);
    const nextDate = deadline.toISOString().slice(0, 10);
    await run(async () => {
      const saved = await api<Task>(`/api/tasks/${task.id}`, { method: "PATCH", ...body({ deadline: nextDate }) });
      setTasks((current) => current.map((item) => item.id === saved.id ? saved : item));
    }, "Task moved one day later.");
  }

  return (
    <section className="work-management" aria-label="Projects and tasks">
      <div className="personal-intro">
        <div>
          <div className="section-kicker">PHASE 3 · PROJECTS AND TASKS</div>
          <h2>Turn your direction into progress</h2>
          <p>Organize meaningful projects into milestones and tasks. Progress reflects completed work, not AI estimates.</p>
        </div>
        <span className="personal-local-label"><span /> Your work, your pace</span>
      </div>

      {error && <div className="workspace-message workspace-message-error" role="alert">{error}</div>}
      {notice && <div className="workspace-message workspace-message-success" role="status">{notice}</div>}
      {loading && <div className="workspace-message" role="status">Loading your projects and tasks…</div>}

      <section className="panel personal-panel" id="projects">
        <div className="personal-section-heading">
          <div>
            <div className="section-kicker">MAKE ROOM FOR THE THINGS YOU’RE BUILDING</div>
            <h3>Projects</h3>
            <p>Link projects to career and academic goals. Completion and progress are based on recorded milestones and tasks.</p>
          </div>
          <button className="personal-button personal-button-primary" type="button" onClick={() => { setEditingProject(null); setProjectFormOpen((open) => !open); }}>
            <Plus size={14} /> New project
          </button>
        </div>
        {projectFormOpen && <ProjectForm key={editingProject ?? "new-project"} initial={projects.find((item) => item.id === editingProject) ? projectToDraft(projects.find((item) => item.id === editingProject)!) : EMPTY_PROJECT} careerGoals={careerGoals} academicGoals={academicGoals} saving={saving} onSave={saveProject} onCancel={() => { setProjectFormOpen(false); setEditingProject(null); }} />}
        <div className="work-project-grid">
          {activeProjects.map((project) => {
            const editing = project.id === editingProject;
            return (
              <article className="work-project-card" key={project.id}>
                <div className="work-project-top">
                  <span className="work-project-icon"><FolderKanban size={18} /></span>
                  <span className={`record-status record-status-${project.status}`}>{label(project.status)}</span>
                  <button className="work-icon-button work-delete-button" type="button" aria-label={`Delete ${project.title}`} onClick={() => void deleteProject(project)}><Trash2 size={14} /></button>
                </div>
                <h4>{project.title}</h4>
                <p className="work-project-meta">{label(project.category)} · Importance {project.importance}/5{project.target_date ? ` · Target ${project.target_date}` : ""}</p>
                {project.description && <p className="work-project-description">{project.description}</p>}
                <div className="work-progress-label">
                  <span>Recorded progress</span>
                  <strong>{project.progress_percent}%</strong>
                </div>
                <div className="work-progress-track" role="progressbar" aria-label={`${project.title} progress`} aria-valuenow={project.progress_percent} aria-valuemin={0} aria-valuemax={100}>
                  <span style={{ width: `${project.progress_percent}%` }} />
                </div>
                <p className="work-progress-detail">{project.completed_milestone_count}/{project.milestone_count} milestones · {project.completed_task_count}/{project.task_count} tasks complete</p>
                {(project.career_goal_titles.length > 0 || project.academic_goal_titles.length > 0) && (
                  <div className="record-chips">
                    {[...project.career_goal_titles, ...project.academic_goal_titles].map((goal) => <span key={goal}>{goal}</span>)}
                  </div>
                )}
                <div className="work-milestones">
                  <div className="work-subheading">
                    <strong>Milestones</strong>
                    <button type="button" onClick={() => void addMilestone(project)}><Plus size={13} /> Add</button>
                  </div>
                  {project.milestones.map((milestone) => (
                    <div className="work-milestone" key={milestone.id}>
                      <button className="milestone-check" type="button" aria-label={`${milestone.status === "completed" ? "Reopen" : "Complete"} ${milestone.title}`} onClick={() => void toggleMilestone(project, milestone)}>
                        {milestone.status === "completed" ? <CircleCheck size={16} /> : <Circle size={16} />}
                      </button>
                      <span className={milestone.status === "completed" ? "work-item-completed" : ""}>
                        <strong>{milestone.title}</strong>
                        <small>{milestone.target_date ?? `${milestone.task_count} tasks`}</small>
                      </span>
                      <button className="work-icon-button" type="button" aria-label={`Edit milestone ${milestone.title}`} onClick={() => void editMilestone(project, milestone)}><Pencil size={13} /></button>
                      <button className="work-icon-button" type="button" aria-label={`Delete milestone ${milestone.title}`} onClick={() => void removeMilestone(project, milestone)}><Trash2 size={13} /></button>
                    </div>
                  ))}
                  {project.milestones.length === 0 && <p className="work-empty-inline">No milestones yet.</p>}
                </div>
                <div className="work-project-actions">
                  <button type="button" onClick={() => { setEditingProject(editing ? null : project.id); setProjectFormOpen(!editing); }}>
                    {editing ? "Close editor" : "Edit project"}
                  </button>
                  <a href="#tasks">View tasks <ArrowUpRight size={13} /></a>
                </div>
              </article>
            );
          })}
          {!loading && activeProjects.length === 0 && <p className="personal-empty work-empty-card">No projects yet. Create one to connect goals with milestones and tasks.</p>}
        </div>
      </section>

      <section className="panel personal-panel" id="tasks">
        <div className="personal-section-heading">
          <div>
            <div className="section-kicker">THE NEXT CONCRETE ACTIONS</div>
            <h3>Tasks</h3>
            <p>Tasks are user-created records. AI-created tasks are not enabled in this phase.</p>
          </div>
          <button className="personal-button personal-button-primary" type="button" onClick={() => { setEditingTask(null); setTaskFormOpen((open) => !open); }}>
            <Plus size={14} /> New task
          </button>
        </div>
        {taskFormOpen && <TaskForm key={editingTask ?? "new-task"} initial={taskToDraft(tasks.find((item) => item.id === editingTask))} projects={projects} careerGoals={careerGoals} academicGoals={academicGoals} saving={saving} onSave={saveTask} onCancel={() => { setTaskFormOpen(false); setEditingTask(null); }} />}
        <div className="work-task-filters">
          <label className="work-search">
            <Search size={15} />
            <input aria-label="Search tasks" value={search} placeholder="Search tasks…" onChange={(event) => setSearch(event.target.value)} />
          </label>
          <select aria-label="Filter by status" value={taskStatus} onChange={(event) => setTaskStatus(event.target.value)}>
            <option value="">All statuses</option>
            {TASK_STATUSES.map((item) => <option value={item} key={item}>{label(item)}</option>)}
          </select>
          <select aria-label="Filter by category" value={taskCategory} onChange={(event) => setTaskCategory(event.target.value)}>
            <option value="">All categories</option>
            {TASK_CATEGORIES.map((item) => <option value={item} key={item}>{label(item)}</option>)}
          </select>
          <button type="button" className="personal-button personal-button-subtle" onClick={() => void loadTasks()}>Apply filters</button>
        </div>
        <div className="work-task-list">
          {filteredTasks.map((task) => (
            <article className={`work-task-card${task.status === "completed" ? " work-task-done" : ""}`} key={task.id}>
              <button className="task-complete-button" type="button" aria-label={`${task.status === "completed" ? "Reopen" : "Complete"} ${task.title}`} onClick={() => void toggleTask(task)}>
                {task.status === "completed" ? <CircleCheck size={19} /> : <Circle size={19} />}
              </button>
              <div className="work-task-content">
                <div className="work-task-title-row">
                  <h4>{task.title}</h4>
                  <span className={`task-priority task-priority-${task.priority}`}>{label(task.priority)}</span>
                  <span className={`record-status record-status-${task.status}`}>{label(task.status)}</span>
                </div>
                {task.description && <p>{task.description}</p>}
                <div className="work-task-meta">
                  <span>{label(task.category)}</span>
                  {task.deadline && <span><Clock3 size={12} /> {task.deadline}</span>}
                  {task.estimated_duration_minutes !== null && <span>{task.estimated_duration_minutes} min estimate</span>}
                  {task.project_title && <span>{task.project_title}{task.milestone_title ? ` · ${task.milestone_title}` : ""}</span>}
                  {task.career_goal_title && <span>{task.career_goal_title}</span>}
                  {task.academic_goal_title && <span>{task.academic_goal_title}</span>}
                </div>
                <div className="record-actions">
                  <button type="button" onClick={() => { setEditingTask(task.id); setTaskFormOpen(true); }}>Edit</button>
                  {task.deadline && task.status !== "completed" && <button type="button" onClick={() => void postponeTask(task)}>Postpone one day</button>}
                  <button className="record-delete" type="button" onClick={() => void deleteTask(task)}>Delete</button>
                </div>
              </div>
            </article>
          ))}
          {!loading && filteredTasks.length === 0 && <p className="personal-empty">No tasks match these filters. Add a task to get started.</p>}
        </div>
        <p className="work-task-footnote">{filteredTasks.length} task{filteredTasks.length === 1 ? "" : "s"} shown. Tasks remain separate from calendar events.</p>
      </section>
    </section>
  );
}

function projectToDraft(project: Project): ProjectDraft {
  return {
    title: project.title,
    description: project.description,
    purpose: project.purpose,
    category: project.category,
    status: project.status,
    importance: project.importance,
    start_date: project.start_date,
    target_date: project.target_date,
    estimated_effort_hours: project.estimated_effort_hours,
    actual_effort_hours: project.actual_effort_hours,
    notes: project.notes,
    acquired_skills: project.acquired_skills,
    career_goal_ids: project.career_goal_ids,
    academic_goal_ids: project.academic_goal_ids,
  };
}

function taskToDraft(task: Task | undefined): TaskDraft {
  if (!task) return EMPTY_TASK;
  return {
    title: task.title,
    description: task.description,
    status: task.status,
    priority: task.priority,
    deadline: task.deadline,
    estimated_duration_minutes: task.estimated_duration_minutes,
    actual_duration_minutes: task.actual_duration_minutes,
    category: task.category,
    project_id: task.project_id,
    milestone_id: task.milestone_id,
    career_goal_id: task.career_goal_id,
    academic_goal_id: task.academic_goal_id,
  };
}
