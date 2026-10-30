"use client";

import { FormEvent, useEffect, useState } from "react";
import { Check, FileText, Plus, Save, Trash2, Upload } from "lucide-react";

type Profile = {
  id: string;
  background: string;
  personal_story: string;
  interests: string[];
  values: string[];
  motivations: string;
  personality: string;
  work_environment: string;
  communication_style: string;
  strengths: string[];
  technical_skills: string[];
  soft_skills: string[];
  development_areas: string[];
  challenges: string[];
  working_hours: string;
  study_sessions: string;
  break_preferences: string;
  focus_preferences: string;
  planning_preferences: string;
  task_presentation: string;
  response_detail: string;
  personal_objectives: string[];
  desired_habits: string[];
  self_improvement: string[];
};

type CareerGoal = {
  id: string;
  title: string;
  description: string;
  importance: number;
  time_horizon: "short_term" | "medium_term" | "long_term" | "unspecified";
  status: "active" | "paused" | "completed" | "archived";
  required_skills: string[];
  created_at: string;
  updated_at: string;
};

type AcademicGoal = {
  id: string;
  title: string;
  description: string;
  programme: string;
  course: string;
  target_date: string | null;
  importance: number;
  status: "active" | "paused" | "completed" | "archived";
  created_at: string;
  updated_at: string;
};

type Principle = {
  id: string;
  title: string;
  description: string;
  category:
    | "productivity"
    | "learning"
    | "wellbeing"
    | "personal_growth"
    | "career"
    | "academic"
    | "projects"
    | "general";
  importance: number;
  contexts: string[];
  frequency: "daily" | "weekly" | "sometimes" | "occasionally";
  reminder: string | null;
  active: boolean;
  created_at: string;
  updated_at: string;
};

type ResumeFact = {
  id: string;
  document_id: string;
  category:
    | "contact"
    | "experience"
    | "education"
    | "skill"
    | "certification"
    | "language"
    | "project"
    | "achievement"
    | "responsibility"
    | "interest"
    | "other";
  value: string;
  verified: boolean;
  created_at: string;
  updated_at: string;
};

type ResumeDocument = {
  id: string;
  original_filename: string;
  media_type: string;
  file_size: number;
  version: number;
  uploaded_at: string;
  extracted_at: string | null;
  extraction_status: string;
  facts: ResumeFact[];
};

type ResumeSummary = Omit<ResumeDocument, "facts"> & {
  fact_count: number;
  verified_fact_count: number;
};

type CareerDraft = Omit<CareerGoal, "id" | "created_at" | "updated_at">;
type AcademicDraft = Omit<AcademicGoal, "id" | "created_at" | "updated_at">;
type PrincipleDraft = Omit<Principle, "id" | "created_at" | "updated_at">;

type WorkspaceData = {
  profile: Profile;
  careerGoals: CareerGoal[];
  academicGoals: AcademicGoal[];
  principles: Principle[];
  resumes: ResumeDocument[];
};

const EMPTY_PROFILE: Profile = {
  id: "default",
  background: "",
  personal_story: "",
  interests: [],
  values: [],
  motivations: "",
  personality: "",
  work_environment: "",
  communication_style: "",
  strengths: [],
  technical_skills: [],
  soft_skills: [],
  development_areas: [],
  challenges: [],
  working_hours: "",
  study_sessions: "",
  break_preferences: "",
  focus_preferences: "",
  planning_preferences: "",
  task_presentation: "",
  response_detail: "",
  personal_objectives: [],
  desired_habits: [],
  self_improvement: [],
};

const EMPTY_CAREER: CareerDraft = {
  title: "",
  description: "",
  importance: 3,
  time_horizon: "unspecified",
  status: "active",
  required_skills: [],
};

const EMPTY_ACADEMIC: AcademicDraft = {
  title: "",
  description: "",
  programme: "",
  course: "",
  target_date: null,
  importance: 3,
  status: "active",
};

const EMPTY_PRINCIPLE: PrincipleDraft = {
  title: "",
  description: "",
  category: "general",
  importance: 3,
  contexts: [],
  frequency: "sometimes",
  reminder: null,
  active: true,
};

const CAREER_HORIZONS: CareerGoal["time_horizon"][] = [
  "unspecified",
  "short_term",
  "medium_term",
  "long_term",
];
const GOAL_STATUSES: CareerGoal["status"][] = [
  "active",
  "paused",
  "completed",
  "archived",
];
const PRINCIPLE_CATEGORIES: Principle["category"][] = [
  "general",
  "productivity",
  "learning",
  "wellbeing",
  "personal_growth",
  "career",
  "academic",
  "projects",
];
const FREQUENCIES: Principle["frequency"][] = [
  "sometimes",
  "daily",
  "weekly",
  "occasionally",
];
const FACT_CATEGORIES: ResumeFact["category"][] = [
  "contact",
  "experience",
  "education",
  "skill",
  "certification",
  "language",
  "project",
  "achievement",
  "responsibility",
  "interest",
  "other",
];

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, cache: "no-store" });
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body: { detail?: string } = await response.json();
      if (body.detail) message = body.detail;
    } catch {
      // Keep the HTTP status message when an error response is not JSON.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

async function requestVoid(url: string, init?: RequestInit): Promise<void> {
  const response = await fetch(url, { ...init, cache: "no-store" });
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body: { detail?: string } = await response.json();
      if (body.detail) message = body.detail;
    } catch {
      // Keep the HTTP status message when an error response is not JSON.
    }
    throw new Error(message);
  }
}

async function fetchWorkspaceData(): Promise<WorkspaceData> {
  const [profile, careerGoals, academicGoals, principles, resumeSummaries] =
    await Promise.all([
      request<Profile>("/api/profile"),
      request<CareerGoal[]>("/api/goals/career"),
      request<AcademicGoal[]>("/api/goals/academic"),
      request<Principle[]>("/api/principles"),
      request<ResumeSummary[]>("/api/resume"),
    ]);
  const resumes = await Promise.all(
    resumeSummaries.map((summary) =>
      request<ResumeDocument>(`/api/resume/${summary.id}`),
    ),
  );
  return { profile, careerGoals, academicGoals, principles, resumes };
}

function jsonBody(value: unknown): RequestInit {
  return {
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(value),
  };
}

function linesToList(value: string): string[] {
  return value
    .split(/\r?\n/)
    .map((item) => item.trim())
    .filter(Boolean);
}

function formatLabel(value: string): string {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

function TextField({
  label,
  value,
  onChange,
  multiline = false,
  rows = 3,
  required = false,
  placeholder,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (value: string) => void;
  multiline?: boolean;
  rows?: number;
  required?: boolean;
  placeholder?: string;
  type?: string;
}) {
  return (
    <label className="personal-field">
      <span>{label}</span>
      {multiline ? (
        <textarea
          value={value}
          onChange={(event) => onChange(event.target.value)}
          rows={rows}
          maxLength={10000}
          placeholder={placeholder}
        />
      ) : (
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          required={required}
          maxLength={1000}
          placeholder={placeholder}
          type={type}
        />
      )}
    </label>
  );
}

function SelectField({
  label,
  value,
  options,
  onChange,
}: {
  label: string;
  value: string;
  options: string[];
  onChange: (value: string) => void;
}) {
  return (
    <label className="personal-field">
      <span>{label}</span>
      <select value={value} onChange={(event) => onChange(event.target.value)}>
        {options.map((option) => (
          <option value={option} key={option}>
            {formatLabel(option)}
          </option>
        ))}
      </select>
    </label>
  );
}

function FieldGroup({
  title,
  description,
  children,
}: {
  title: string;
  description?: string;
  children: React.ReactNode;
}) {
  return (
    <fieldset className="personal-fieldset">
      <legend>{title}</legend>
      {description && <p className="personal-fieldset-copy">{description}</p>}
      <div className="personal-form-grid">{children}</div>
    </fieldset>
  );
}

function CareerGoalForm({
  initial,
  saving,
  onSave,
  onCancel,
}: {
  initial: CareerDraft;
  saving: boolean;
  onSave: (value: CareerDraft) => void;
  onCancel?: () => void;
}) {
  const [draft, setDraft] = useState(initial);
  const set = <K extends keyof CareerDraft>(key: K, value: CareerDraft[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSave(draft);
  }

  return (
    <form className="personal-form" onSubmit={submit}>
      <div className="personal-form-grid">
        <TextField label="Career direction" required value={draft.title} onChange={(value) => set("title", value)} placeholder="e.g. Build a career in data science" />
        <SelectField label="Time horizon" value={draft.time_horizon} options={CAREER_HORIZONS} onChange={(value) => set("time_horizon", value as CareerDraft["time_horizon"])} />
        <TextField label="Why this matters" multiline value={draft.description} onChange={(value) => set("description", value)} />
        <TextField label="Skills you want to develop (one per line)" multiline value={draft.required_skills.join("\n")} onChange={(value) => set("required_skills", linesToList(value))} rows={2} />
        <SelectField label="Status" value={draft.status} options={GOAL_STATUSES} onChange={(value) => set("status", value as CareerDraft["status"])} />
        <label className="personal-field">
          <span>Importance · {draft.importance} of 5</span>
          <input type="range" min="1" max="5" value={draft.importance} onChange={(event) => set("importance", Number(event.target.value))} />
        </label>
      </div>
      <div className="personal-form-actions">
        {onCancel && <button className="personal-button personal-button-subtle" type="button" onClick={onCancel}>Cancel</button>}
        <button className="personal-button personal-button-primary" type="submit" disabled={saving}>
          <Save size={15} /> {saving ? "Saving…" : "Save career goal"}
        </button>
      </div>
    </form>
  );
}

function AcademicGoalForm({
  initial,
  saving,
  onSave,
  onCancel,
}: {
  initial: AcademicDraft;
  saving: boolean;
  onSave: (value: AcademicDraft) => void;
  onCancel?: () => void;
}) {
  const [draft, setDraft] = useState(initial);
  const set = <K extends keyof AcademicDraft>(key: K, value: AcademicDraft[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSave(draft);
  }

  return (
    <form className="personal-form" onSubmit={submit}>
      <div className="personal-form-grid">
        <TextField label="Study goal" required value={draft.title} onChange={(value) => set("title", value)} placeholder="e.g. Complete the statistics course" />
        <TextField label="Programme" value={draft.programme} onChange={(value) => set("programme", value)} />
        <TextField label="Course or subject" value={draft.course} onChange={(value) => set("course", value)} />
        <TextField label="Target date" type="date" value={draft.target_date ?? ""} onChange={(value) => set("target_date", value || null)} />
        <SelectField label="Status" value={draft.status} options={GOAL_STATUSES} onChange={(value) => set("status", value as AcademicDraft["status"])} />
        <label className="personal-field">
          <span>Importance · {draft.importance} of 5</span>
          <input type="range" min="1" max="5" value={draft.importance} onChange={(event) => set("importance", Number(event.target.value))} />
        </label>
        <div className="personal-field-full">
          <TextField label="Notes" multiline value={draft.description} onChange={(value) => set("description", value)} />
        </div>
      </div>
      <div className="personal-form-actions">
        {onCancel && <button className="personal-button personal-button-subtle" type="button" onClick={onCancel}>Cancel</button>}
        <button className="personal-button personal-button-primary" type="submit" disabled={saving}>
          <Save size={15} /> {saving ? "Saving…" : "Save study goal"}
        </button>
      </div>
    </form>
  );
}

function PrincipleForm({
  initial,
  saving,
  onSave,
  onCancel,
}: {
  initial: PrincipleDraft;
  saving: boolean;
  onSave: (value: PrincipleDraft) => void;
  onCancel?: () => void;
}) {
  const [draft, setDraft] = useState(initial);
  const set = <K extends keyof PrincipleDraft>(key: K, value: PrincipleDraft[K]) =>
    setDraft((current) => ({ ...current, [key]: value }));

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    onSave(draft);
  }

  return (
    <form className="personal-form" onSubmit={submit}>
      <div className="personal-form-grid">
        <TextField label="Principle" required value={draft.title} onChange={(value) => set("title", value)} placeholder="e.g. Consistency over perfection" />
        <SelectField label="Category" value={draft.category} options={PRINCIPLE_CATEGORIES} onChange={(value) => set("category", value as PrincipleDraft["category"])} />
        <div className="personal-field-full">
          <TextField label="What does this mean to you?" multiline value={draft.description} onChange={(value) => set("description", value)} />
        </div>
        <TextField label="Contexts (one per line)" multiline value={draft.contexts.join("\n")} onChange={(value) => set("contexts", linesToList(value))} rows={2} />
        <TextField label="Optional reminder" value={draft.reminder ?? ""} onChange={(value) => set("reminder", value || null)} />
        <SelectField label="Frequency" value={draft.frequency} options={FREQUENCIES} onChange={(value) => set("frequency", value as PrincipleDraft["frequency"])} />
        <label className="personal-field">
          <span>Importance · {draft.importance} of 5</span>
          <input type="range" min="1" max="5" value={draft.importance} onChange={(event) => set("importance", Number(event.target.value))} />
        </label>
        <label className="personal-check-field">
          <input type="checkbox" checked={draft.active} onChange={(event) => set("active", event.target.checked)} />
          This principle is active
        </label>
      </div>
      <div className="personal-form-actions">
        {onCancel && <button className="personal-button personal-button-subtle" type="button" onClick={onCancel}>Cancel</button>}
        <button className="personal-button personal-button-primary" type="submit" disabled={saving}>
          <Save size={15} /> {saving ? "Saving…" : "Save principle"}
        </button>
      </div>
    </form>
  );
}

function ResumeFactEditor({
  fact,
  saving,
  onSave,
}: {
  fact: ResumeFact;
  saving: boolean;
  onSave: (fact: ResumeFact, update: Pick<ResumeFact, "category" | "value" | "verified">) => void;
}) {
  const [category, setCategory] = useState(fact.category);
  const [value, setValue] = useState(fact.value);
  const [verified, setVerified] = useState(fact.verified);
  return (
    <form
      className="resume-fact"
      onSubmit={(event) => {
        event.preventDefault();
        onSave(fact, { category, value, verified });
      }}
    >
      <SelectField label="Fact type" value={category} options={FACT_CATEGORIES} onChange={(item) => setCategory(item as ResumeFact["category"])} />
      <label className="personal-field resume-fact-value">
        <span>Extracted information</span>
        <textarea value={value} maxLength={5000} rows={2} onChange={(event) => setValue(event.target.value)} />
      </label>
      <label className="personal-check-field resume-verified">
        <input type="checkbox" checked={verified} onChange={(event) => setVerified(event.target.checked)} />
        I have reviewed this
      </label>
      <button className="personal-button personal-button-subtle" type="submit" disabled={saving}>
        <Check size={14} /> {saving ? "Saving…" : "Save"}
      </button>
    </form>
  );
}

export default function PersonalWorkspace() {
  const [profile, setProfile] = useState(EMPTY_PROFILE);
  const [careerGoals, setCareerGoals] = useState<CareerGoal[]>([]);
  const [academicGoals, setAcademicGoals] = useState<AcademicGoal[]>([]);
  const [principles, setPrinciples] = useState<Principle[]>([]);
  const [resumes, setResumes] = useState<ResumeDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [saving, setSaving] = useState(false);
  const [editingCareer, setEditingCareer] = useState<string | null>(null);
  const [editingAcademic, setEditingAcademic] = useState<string | null>(null);
  const [editingPrinciple, setEditingPrinciple] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    void fetchWorkspaceData()
      .then((data) => {
        if (!active) return;
        setProfile(data.profile);
        setCareerGoals(data.careerGoals);
        setAcademicGoals(data.academicGoals);
        setPrinciples(data.principles);
        setResumes(data.resumes);
      })
      .catch((cause: unknown) => {
        if (active) {
          setError(cause instanceof Error ? cause.message : "Could not load personal information.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function loadWorkspace() {
    setLoading(true);
    setError("");
    try {
      const data = await fetchWorkspaceData();
      setProfile(data.profile);
      setCareerGoals(data.careerGoals);
      setAcademicGoals(data.academicGoals);
      setPrinciples(data.principles);
      setResumes(data.resumes);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load personal information.");
    } finally {
      setLoading(false);
    }
  }

  async function runSave(action: () => Promise<void>, successMessage: string) {
    setSaving(true);
    setError("");
    setNotice("");
    try {
      await action();
      setNotice(successMessage);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "The change could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function saveProfile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    await runSave(async () => {
      const updated = await request<Profile>("/api/profile", {
        method: "PATCH",
        ...jsonBody(profile),
      });
      setProfile(updated);
    }, "Your profile has been saved.");
  }

  async function saveCareer(value: CareerDraft) {
    await runSave(async () => {
      const editing = careerGoals.find((goal) => goal.id === editingCareer);
      const saved = await request<CareerGoal>(
        editing ? `/api/goals/career/${editing.id}` : "/api/goals/career",
        { method: editing ? "PATCH" : "POST", ...jsonBody(value) },
      );
      setCareerGoals((current) =>
        editing
          ? current.map((goal) => (goal.id === saved.id ? saved : goal))
          : [saved, ...current],
      );
      setEditingCareer(null);
    }, "Career goal saved.");
  }

  async function deleteCareer(goal: CareerGoal) {
    if (!window.confirm(`Delete “${goal.title}”?`)) return;
    await runSave(async () => {
      await requestVoid(`/api/goals/career/${goal.id}`, { method: "DELETE" });
      setCareerGoals((current) => current.filter((item) => item.id !== goal.id));
    }, "Career goal deleted.");
  }

  async function saveAcademic(value: AcademicDraft) {
    await runSave(async () => {
      const editing = academicGoals.find((goal) => goal.id === editingAcademic);
      const saved = await request<AcademicGoal>(
        editing ? `/api/goals/academic/${editing.id}` : "/api/goals/academic",
        { method: editing ? "PATCH" : "POST", ...jsonBody(value) },
      );
      setAcademicGoals((current) =>
        editing
          ? current.map((goal) => (goal.id === saved.id ? saved : goal))
          : [saved, ...current],
      );
      setEditingAcademic(null);
    }, "Study goal saved.");
  }

  async function deleteAcademic(goal: AcademicGoal) {
    if (!window.confirm(`Delete “${goal.title}”?`)) return;
    await runSave(async () => {
      await requestVoid(`/api/goals/academic/${goal.id}`, { method: "DELETE" });
      setAcademicGoals((current) => current.filter((item) => item.id !== goal.id));
    }, "Study goal deleted.");
  }

  async function savePrinciple(value: PrincipleDraft) {
    await runSave(async () => {
      const editing = principles.find((item) => item.id === editingPrinciple);
      const saved = await request<Principle>(
        editing ? `/api/principles/${editing.id}` : "/api/principles",
        { method: editing ? "PATCH" : "POST", ...jsonBody(value) },
      );
      setPrinciples((current) =>
        editing
          ? current.map((item) => (item.id === saved.id ? saved : item))
          : [saved, ...current],
      );
      setEditingPrinciple(null);
    }, "Personal principle saved.");
  }

  async function deletePrinciple(principle: Principle) {
    if (!window.confirm(`Delete “${principle.title}”?`)) return;
    await runSave(async () => {
      await requestVoid(`/api/principles/${principle.id}`, { method: "DELETE" });
      setPrinciples((current) => current.filter((item) => item.id !== principle.id));
    }, "Personal principle deleted.");
  }

  async function uploadResume(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = event.currentTarget;
    const file = new FormData(form).get("file");
    if (!(file instanceof File) || file.size === 0) {
      setError("Choose a PDF or DOCX file first.");
      return;
    }
    await runSave(async () => {
      const data = new FormData();
      data.set("file", file);
      const uploaded = await request<ResumeDocument>("/api/resume/upload", {
        method: "POST",
        body: data,
      });
      setResumes((current) => [uploaded, ...current]);
      form.reset();
    }, "CV uploaded. Extracted details are unverified until you review them.");
  }

  async function saveResumeFact(
    fact: ResumeFact,
    update: Pick<ResumeFact, "category" | "value" | "verified">,
  ) {
    await runSave(async () => {
      const saved = await request<ResumeFact>(
        `/api/resume/${fact.document_id}/facts/${fact.id}`,
        { method: "PATCH", ...jsonBody(update) },
      );
      setResumes((current) =>
        current.map((document) =>
          document.id !== fact.document_id
            ? document
            : {
                ...document,
                facts: document.facts.map((item) =>
                  item.id === fact.id ? saved : item,
                ),
              },
        ),
      );
    }, "CV detail updated.");
  }

  async function deleteResume(document: ResumeDocument) {
    if (!window.confirm(`Permanently delete ${document.original_filename} and its extracted details?`)) return;
    await runSave(async () => {
      await requestVoid(`/api/resume/${document.id}`, { method: "DELETE" });
      setResumes((current) => current.filter((item) => item.id !== document.id));
    }, "CV document deleted.");
  }

  function setProfileField<K extends keyof Profile>(key: K, value: Profile[K]) {
    setProfile((current) => ({ ...current, [key]: value }));
  }

  return (
    <section className="personal-workspace" aria-labelledby="personal-title">
      <div className="personal-intro">
        <div>
          <div className="section-kicker">PHASE 2 · PERSONAL INFORMATION</div>
          <h2 id="personal-title">The context behind your goals</h2>
          <p>
            Add and maintain your own information. Profile details are user-written;
            CV extraction stays unverified until you confirm it.
          </p>
        </div>
        <span className="personal-local-label"><span /> Stored on your server</span>
      </div>

      {error && <div className="workspace-message workspace-message-error" role="alert">{error}</div>}
      {notice && <div className="workspace-message workspace-message-success" role="status">{notice}</div>}
      {loading && <div className="workspace-message" role="status">Loading your personal workspace…</div>}

      <section className="panel personal-panel" id="profile">
        <div className="personal-section-heading">
          <div>
            <div className="section-kicker">ABOUT YOU</div>
            <h3>Your profile</h3>
            <p>This is your writing. AI features will not silently change it.</p>
          </div>
        </div>
        <form className="personal-form" onSubmit={saveProfile}>
          <FieldGroup title="About me">
            <TextField label="Background" multiline value={profile.background} onChange={(value) => setProfileField("background", value)} />
            <TextField label="Personal story" multiline value={profile.personal_story} onChange={(value) => setProfileField("personal_story", value)} />
            <TextField label="Interests (one per line)" multiline value={profile.interests.join("\n")} onChange={(value) => setProfileField("interests", linesToList(value))} />
            <TextField label="Values (one per line)" multiline value={profile.values.join("\n")} onChange={(value) => setProfileField("values", linesToList(value))} />
            <TextField label="Motivations" multiline value={profile.motivations} onChange={(value) => setProfileField("motivations", value)} />
            <TextField label="Personality, as you describe it" multiline value={profile.personality} onChange={(value) => setProfileField("personality", value)} />
            <TextField label="Preferred work environment" multiline value={profile.work_environment} onChange={(value) => setProfileField("work_environment", value)} />
            <TextField label="Preferred communication style" multiline value={profile.communication_style} onChange={(value) => setProfileField("communication_style", value)} />
          </FieldGroup>
          <FieldGroup title="Strengths and development">
            <TextField label="Strengths (one per line)" multiline value={profile.strengths.join("\n")} onChange={(value) => setProfileField("strengths", linesToList(value))} />
            <TextField label="Technical skills (one per line)" multiline value={profile.technical_skills.join("\n")} onChange={(value) => setProfileField("technical_skills", linesToList(value))} />
            <TextField label="Soft skills (one per line)" multiline value={profile.soft_skills.join("\n")} onChange={(value) => setProfileField("soft_skills", linesToList(value))} />
            <TextField label="Development areas (one per line)" multiline value={profile.development_areas.join("\n")} onChange={(value) => setProfileField("development_areas", linesToList(value))} />
            <TextField label="Challenges you want to work on (one per line)" multiline value={profile.challenges.join("\n")} onChange={(value) => setProfileField("challenges", linesToList(value))} />
          </FieldGroup>
          <FieldGroup title="Working style">
            <TextField label="Preferred working hours" multiline value={profile.working_hours} onChange={(value) => setProfileField("working_hours", value)} />
            <TextField label="Preferred study sessions" multiline value={profile.study_sessions} onChange={(value) => setProfileField("study_sessions", value)} />
            <TextField label="Break preferences" multiline value={profile.break_preferences} onChange={(value) => setProfileField("break_preferences", value)} />
            <TextField label="Focus preferences" multiline value={profile.focus_preferences} onChange={(value) => setProfileField("focus_preferences", value)} />
            <TextField label="Planning preferences" multiline value={profile.planning_preferences} onChange={(value) => setProfileField("planning_preferences", value)} />
            <TextField label="How tasks should be presented" multiline value={profile.task_presentation} onChange={(value) => setProfileField("task_presentation", value)} />
            <TextField label="Preferred AI response detail" multiline value={profile.response_detail} onChange={(value) => setProfileField("response_detail", value)} />
          </FieldGroup>
          <FieldGroup title="Personal development">
            <TextField label="Personal objectives (one per line)" multiline value={profile.personal_objectives.join("\n")} onChange={(value) => setProfileField("personal_objectives", linesToList(value))} />
            <TextField label="Habits you want to build (one per line)" multiline value={profile.desired_habits.join("\n")} onChange={(value) => setProfileField("desired_habits", linesToList(value))} />
            <TextField label="Things you want to improve (one per line)" multiline value={profile.self_improvement.join("\n")} onChange={(value) => setProfileField("self_improvement", linesToList(value))} />
          </FieldGroup>
          <div className="personal-form-actions">
            <button className="personal-button personal-button-primary" type="submit" disabled={saving || loading}>
              <Save size={15} /> {saving ? "Saving…" : "Save profile"}
            </button>
          </div>
        </form>
      </section>

      <div className="personal-goal-grid">
        <section className="panel personal-panel" id="career">
          <div className="personal-section-heading">
            <div>
              <div className="section-kicker">YOUR PROFESSIONAL DIRECTION</div>
              <h3>Career aspirations</h3>
              <p>Keep several possible paths and the skills you want to build.</p>
            </div>
            <span className="personal-count">{careerGoals.length}</span>
          </div>
          <CareerGoalForm
            key={editingCareer ?? "new-career"}
            initial={careerGoals.find((item) => item.id === editingCareer) ?? EMPTY_CAREER}
            saving={saving}
            onSave={saveCareer}
            onCancel={editingCareer ? () => setEditingCareer(null) : undefined}
          />
          <div className="personal-record-list">
            {careerGoals.map((goal) => (
              <article className="personal-record" key={goal.id}>
                <div className="personal-record-heading">
                  <div><h4>{goal.title}</h4><span>{formatLabel(goal.time_horizon)} · {goal.importance}/5 importance</span></div>
                  <span className={`record-status record-status-${goal.status}`}>{formatLabel(goal.status)}</span>
                </div>
                {goal.description && <p>{goal.description}</p>}
                {goal.required_skills.length > 0 && <div className="record-chips">{goal.required_skills.map((skill) => <span key={skill}>{skill}</span>)}</div>}
                <div className="record-actions">
                  <button type="button" onClick={() => setEditingCareer(goal.id)}>Edit</button>
                  <button type="button" className="record-delete" onClick={() => void deleteCareer(goal)}>Delete</button>
                </div>
              </article>
            ))}
            {!loading && careerGoals.length === 0 && <p className="personal-empty">Your career aspirations will appear here when you add them.</p>}
          </div>
        </section>

        <section className="panel personal-panel" id="academic">
          <div className="personal-section-heading">
            <div>
              <div className="section-kicker">LEARNING AND STUDY</div>
              <h3>Academic goals</h3>
              <p>Track programmes, courses, and the milestones that matter.</p>
            </div>
            <span className="personal-count">{academicGoals.length}</span>
          </div>
          <AcademicGoalForm
            key={editingAcademic ?? "new-academic"}
            initial={academicGoals.find((item) => item.id === editingAcademic) ?? EMPTY_ACADEMIC}
            saving={saving}
            onSave={saveAcademic}
            onCancel={editingAcademic ? () => setEditingAcademic(null) : undefined}
          />
          <div className="personal-record-list">
            {academicGoals.map((goal) => (
              <article className="personal-record" key={goal.id}>
                <div className="personal-record-heading">
                  <div><h4>{goal.title}</h4><span>{[goal.programme, goal.course].filter(Boolean).join(" · ") || "Study goal"}{goal.target_date ? ` · Due ${goal.target_date}` : ""}</span></div>
                  <span className={`record-status record-status-${goal.status}`}>{formatLabel(goal.status)}</span>
                </div>
                {goal.description && <p>{goal.description}</p>}
                <div className="record-actions">
                  <button type="button" onClick={() => setEditingAcademic(goal.id)}>Edit</button>
                  <button type="button" className="record-delete" onClick={() => void deleteAcademic(goal)}>Delete</button>
                </div>
              </article>
            ))}
            {!loading && academicGoals.length === 0 && <p className="personal-empty">Your study goals will appear here when you add them.</p>}
          </div>
        </section>
      </div>

      <section className="panel personal-panel" id="principles">
        <div className="personal-section-heading">
          <div>
            <div className="section-kicker">YOUR OWN ADVICE</div>
            <h3>Personal principles</h3>
            <p>Keep reminders and habits you want your future planning to respect.</p>
          </div>
          <span className="personal-count">{principles.length}</span>
        </div>
        <PrincipleForm
          key={editingPrinciple ?? "new-principle"}
          initial={principles.find((item) => item.id === editingPrinciple) ?? EMPTY_PRINCIPLE}
          saving={saving}
          onSave={savePrinciple}
          onCancel={editingPrinciple ? () => setEditingPrinciple(null) : undefined}
        />
        <div className="personal-principle-grid">
          {principles.map((principle) => (
            <article className={`personal-record principle-record${principle.active ? "" : " principle-inactive"}`} key={principle.id}>
              <div className="personal-record-heading">
                <div><h4>{principle.title}</h4><span>{formatLabel(principle.category)} · {formatLabel(principle.frequency)} · {principle.importance}/5</span></div>
                <span className={`record-status record-status-${principle.active ? "active" : "archived"}`}>{principle.active ? "Active" : "Inactive"}</span>
              </div>
              {principle.description && <p>{principle.description}</p>}
              {principle.reminder && <p className="principle-reminder">Reminder: {principle.reminder}</p>}
              {principle.contexts.length > 0 && <div className="record-chips">{principle.contexts.map((context) => <span key={context}>{context}</span>)}</div>}
              <div className="record-actions">
                <button type="button" onClick={() => setEditingPrinciple(principle.id)}>Edit</button>
                <button type="button" className="record-delete" onClick={() => void deletePrinciple(principle)}>Delete</button>
              </div>
            </article>
          ))}
          {!loading && principles.length === 0 && <p className="personal-empty">Your principles will appear here when you add them.</p>}
        </div>
      </section>

      <section className="panel personal-panel" id="resume">
        <div className="personal-section-heading">
          <div>
            <div className="section-kicker">YOUR PROFESSIONAL HISTORY</div>
            <h3>CV &amp; experience</h3>
            <p>Original documents are kept privately; extracted details are yours to check and correct.</p>
          </div>
          <span className="personal-count">{resumes.length}</span>
        </div>
        <form className="resume-upload" onSubmit={uploadResume}>
          <label className="personal-field resume-file-field">
            <span>Choose a CV document (PDF or DOCX, up to 10 MB)</span>
            <input name="file" type="file" accept=".pdf,.docx,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document" required />
          </label>
          <button className="personal-button personal-button-primary" type="submit" disabled={saving}>
            <Upload size={15} /> {saving ? "Uploading…" : "Upload and extract"}
          </button>
        </form>
        <p className="resume-privacy-note">Extracted details are suggestions from your document, not verified qualifications. Review each fact before treating it as confirmed.</p>
        <div className="resume-document-list">
          {resumes.map((document) => (
            <article className="resume-document" key={document.id}>
              <div className="resume-document-heading">
                <span className="resume-document-icon"><FileText size={19} /></span>
                <div className="resume-document-name">
                  <strong>{document.original_filename}</strong>
                  <span>Version {document.version} · {(document.file_size / (1024 * 1024)).toFixed(2)} MB · {new Date(document.uploaded_at).toLocaleDateString()}</span>
                </div>
                <a className="personal-button personal-button-subtle" href={`/api/resume/${document.id}/download`}>Download original</a>
                <button className="icon-delete-button" type="button" aria-label={`Delete ${document.original_filename}`} onClick={() => void deleteResume(document)}><Trash2 size={15} /></button>
              </div>
              <p className="resume-review-warning">{document.facts.length} extracted details · {document.facts.filter((fact) => fact.verified).length} reviewed. Unreviewed facts are not confirmed.</p>
              {document.facts.map((fact) => (
                <ResumeFactEditor key={fact.id} fact={fact} saving={saving} onSave={saveResumeFact} />
              ))}
              {document.facts.length === 0 && <p className="personal-empty">No text details were extracted. The original document is preserved for review.</p>}
            </article>
          ))}
          {!loading && resumes.length === 0 && <p className="personal-empty">Your CV documents will appear here after upload.</p>}
        </div>
      </section>

      <div className="personal-footer">
        <span><Check size={14} /> Your profile and documents remain user-owned.</span>
        <button type="button" className="personal-button personal-button-subtle" onClick={() => void loadWorkspace()} disabled={loading}>
          <Plus size={14} /> Refresh workspace
        </button>
      </div>
    </section>
  );
}
