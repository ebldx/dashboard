"use client";

import { FormEvent, useEffect, useState } from "react";
import { Check, History, RotateCcw, Save, ThumbsDown, ThumbsUp, X } from "lucide-react";

type PreferenceField =
  | "working_hours"
  | "study_sessions"
  | "break_preferences"
  | "focus_preferences"
  | "planning_preferences"
  | "task_presentation"
  | "response_detail";
type Feedback = {
  id: string;
  briefing_id: string | null;
  local_date: string | null;
  rating: -1 | 0 | 1;
  comment: string;
  created_at: string;
};
type Candidate = {
  id: string;
  feedback_id: string | null;
  preference_field: PreferenceField;
  candidate_value: string;
  current_value: string;
  status: "pending" | "applied" | "rejected" | "undone";
  auto_applied: boolean;
  decided_at: string | null;
  created_at: string;
  updated_at: string;
};
type HistoryEntry = {
  id: string;
  candidate_id: string;
  preference_field: PreferenceField;
  previous_value: string;
  applied_value: string;
  source: "candidate" | "profile_edit";
  undone_at: string | null;
  created_at: string;
};
type LearningWorkspace = {
  current_preferences: Record<PreferenceField, string>;
  feedback: Feedback[];
  candidates: Candidate[];
  history: HistoryEntry[];
};
type Briefing = { local_date: string };

const PREFERENCE_FIELDS: PreferenceField[] = [
  "working_hours",
  "study_sessions",
  "break_preferences",
  "focus_preferences",
  "planning_preferences",
  "task_presentation",
  "response_detail",
];

function label(value: string) {
  return value.replaceAll("_", " ").replace(/\b\w/g, (letter) => letter.toUpperCase());
}

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, cache: "no-store" });
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body: { detail?: string } = await response.json();
      if (body.detail) message = body.detail;
    } catch {
      // Keep the HTTP status when an error response is not JSON.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

function jsonBody(value: unknown): RequestInit {
  return {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(value),
  };
}

export default function PreferenceWorkspace() {
  const [workspace, setWorkspace] = useState<LearningWorkspace | null>(null);
  const [briefingDate, setBriefingDate] = useState("");
  const [rating, setRating] = useState<-1 | 0 | 1>(0);
  const [comment, setComment] = useState("");
  const [preferenceField, setPreferenceField] = useState<PreferenceField | "">("");
  const [candidateValue, setCandidateValue] = useState("");
  const [explicitlyRequested, setExplicitlyRequested] = useState(false);
  const [drafts, setDrafts] = useState<Record<string, string>>({});
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);

  async function refresh() {
    const data = await request<LearningWorkspace>("/api/preferences/learning");
    setWorkspace(data);
    setDrafts(
      Object.fromEntries(data.candidates.map((candidate) => [
        candidate.id,
        candidate.candidate_value,
      ])),
    );
    return data;
  }

  useEffect(() => {
    const controller = new AbortController();
    Promise.all([
      fetch("/api/preferences/learning", { signal: controller.signal, cache: "no-store" })
        .then(async (response) => {
          if (!response.ok) throw new Error("Preference history could not be loaded.");
          return (await response.json()) as LearningWorkspace;
        }),
      fetch("/api/ai/briefing", { signal: controller.signal, cache: "no-store" })
        .then(async (response) => {
          if (!response.ok) throw new Error("The latest briefing could not be loaded.");
          return (await response.json()) as Briefing;
        }),
    ])
      .then(([data, briefing]) => {
        setWorkspace(data);
        setBriefingDate(briefing.local_date);
        setDrafts(
          Object.fromEntries(data.candidates.map((candidate) => [
            candidate.id,
            candidate.candidate_value,
          ])),
        );
        const existingFeedback = data.feedback.find(
          (item) => item.local_date === briefing.local_date,
        );
        if (existingFeedback) {
          setRating(existingFeedback.rating);
          setComment(existingFeedback.comment);
        }
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(reason instanceof Error ? reason.message : "Preference data unavailable.");
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  async function submitFeedback(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!briefingDate) {
      setError("A daily briefing is required before feedback can be saved.");
      return;
    }
    if ((preferenceField === "") !== (candidateValue.trim() === "")) {
      setError("Choose a preference area and enter the preference together.");
      return;
    }
    if (explicitlyRequested && !candidateValue.trim()) {
      setError("Enter the preference you want to apply.");
      return;
    }
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await request("/api/preferences/feedback", {
        ...jsonBody({
          local_date: briefingDate,
          rating,
          comment,
          preference_field: preferenceField || null,
          candidate_value: candidateValue.trim() || null,
          explicitly_requested: explicitlyRequested,
        }),
      });
      await refresh();
      setExplicitlyRequested(false);
      setNotice(
        explicitlyRequested
          ? "Feedback saved and your explicitly selected preference was applied."
          : candidateValue.trim()
            ? "Feedback saved. Your preference is waiting for review."
            : "Your feedback was saved.",
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Feedback could not be saved.");
    } finally {
      setSaving(false);
    }
  }

  async function updateCandidate(candidateId: string, action: "accept" | "reject" | "edit") {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      if (action === "edit") {
        await request(`/api/preferences/candidates/${candidateId}`, {
          method: "PATCH",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ candidate_value: drafts[candidateId] ?? "" }),
        });
      } else {
        await request(`/api/preferences/candidates/${candidateId}/${action}`, jsonBody({}));
      }
      await refresh();
      setNotice(
        action === "accept"
          ? "Preference applied and added to history."
          : action === "reject"
            ? "Preference candidate dismissed."
            : "Candidate updated.",
      );
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Candidate could not be updated.");
    } finally {
      setSaving(false);
    }
  }

  async function undo(historyId: string) {
    setSaving(true);
    setError(null);
    setNotice(null);
    try {
      await request(`/api/preferences/history/${historyId}/undo`, jsonBody({}));
      await refresh();
      setNotice("Preference restored to its previous value.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Preference could not be undone.");
    } finally {
      setSaving(false);
    }
  }

  const feedbackExists = workspace?.feedback.some(
    (item) => item.local_date === briefingDate,
  );
  const pendingCandidates = workspace?.candidates.filter(
    (candidate) => candidate.status === "pending",
  ) ?? [];

  return (
    <section className="panel preference-panel" id="preferences" aria-labelledby="preferences-title">
      <div className="panel-heading">
        <div>
          <div className="section-kicker">YOUR FEEDBACK STAYS IN YOUR WORKSPACE</div>
          <h2 id="preferences-title">Preferences &amp; learning</h2>
        </div>
        <span className="heading-icon"><History size={18} /></span>
      </div>

      {error && <p className="preference-alert" role="alert">{error}</p>}
      {notice && <p className="preference-notice" role="status">{notice}</p>}

      <form className="feedback-form" onSubmit={submitFeedback}>
        <h3>How useful was today&apos;s briefing?</h3>
        <div className="feedback-rating" role="group" aria-label="Briefing rating">
          <button
            type="button"
            className={rating === 1 ? "feedback-choice selected" : "feedback-choice"}
            aria-pressed={rating === 1}
            onClick={() => setRating(1)}
          >
            <ThumbsUp size={15} /> Helpful
          </button>
          <button
            type="button"
            className={rating === -1 ? "feedback-choice selected" : "feedback-choice"}
            aria-pressed={rating === -1}
            onClick={() => setRating(-1)}
          >
            <ThumbsDown size={15} /> Not helpful
          </button>
          <button
            type="button"
            className={rating === 0 ? "feedback-choice selected" : "feedback-choice"}
            aria-pressed={rating === 0}
            onClick={() => setRating(0)}
          >
            Skip rating
          </button>
        </div>
        <label className="preference-field">
          <span>Optional feedback (stored locally, not sent to Ollama)</span>
          <textarea
            value={comment}
            maxLength={2000}
            rows={2}
            onChange={(event) => setComment(event.target.value)}
          />
        </label>

        <details className="candidate-create">
          <summary>Suggest a preference to remember</summary>
          <div className="candidate-create-fields">
            <label className="preference-field">
              <span>Preference area</span>
              <select
                value={preferenceField}
                onChange={(event) => setPreferenceField(event.target.value as PreferenceField | "")}
              >
                <option value="">Select an area</option>
                {PREFERENCE_FIELDS.map((field) => (
                  <option value={field} key={field}>{label(field)}</option>
                ))}
              </select>
            </label>
            <label className="preference-field">
              <span>Proposed preference</span>
              <textarea
                value={candidateValue}
                maxLength={2000}
                rows={2}
                onChange={(event) => setCandidateValue(event.target.value)}
                placeholder="Write the preference in your own words"
              />
            </label>
            <label className="preference-explicit">
              <input
                type="checkbox"
                checked={explicitlyRequested}
                onChange={(event) => setExplicitlyRequested(event.target.checked)}
              />
              <span>
                I explicitly want this exact preference applied now. This is the only auto-save rule;
                it is recorded in history and can be undone.
              </span>
            </label>
          </div>
        </details>

        <button className="preference-submit" type="submit" disabled={saving || loading}>
          <Save size={14} /> {feedbackExists ? "Update feedback" : "Save feedback"}
        </button>
      </form>

      {loading ? (
        <p className="preference-empty">Loading preference history…</p>
      ) : (
        <>
          <section className="preference-subsection">
            <h3>Current preferences</h3>
            <div className="preference-current-list">
              {PREFERENCE_FIELDS.map((field) => (
                <div className="preference-current" key={field}>
                  <strong>{label(field)}</strong>
                  <span>{workspace?.current_preferences[field] || "Not set"}</span>
                </div>
              ))}
            </div>
          </section>

          <section className="preference-subsection">
            <h3>Review candidates ({pendingCandidates.length})</h3>
            {pendingCandidates.length === 0 ? (
              <p className="preference-empty">No preferences are waiting for review.</p>
            ) : (
              <div className="candidate-list">
                {pendingCandidates.map((candidate) => (
                  <article className="candidate-card" key={candidate.id}>
                    <div className="candidate-card-heading">
                      <strong>{label(candidate.preference_field)}</strong>
                      <span>Current value: {candidate.current_value || "Not set"}</span>
                    </div>
                    <label className="preference-field">
                      <span>Proposed value</span>
                      <textarea
                        rows={2}
                        maxLength={2000}
                        value={drafts[candidate.id] ?? candidate.candidate_value}
                        onChange={(event) => setDrafts({
                          ...drafts,
                          [candidate.id]: event.target.value,
                        })}
                      />
                    </label>
                    <div className="candidate-actions">
                      <button type="button" onClick={() => void updateCandidate(candidate.id, "edit")} disabled={saving}>
                        <Save size={13} /> Save edit
                      </button>
                      <button type="button" onClick={() => void updateCandidate(candidate.id, "accept")} disabled={saving}>
                        <Check size={13} /> Apply
                      </button>
                      <button type="button" onClick={() => void updateCandidate(candidate.id, "reject")} disabled={saving}>
                        <X size={13} /> Dismiss
                      </button>
                    </div>
                  </article>
                ))}
              </div>
            )}
          </section>

          <section className="preference-subsection">
            <h3>Preference history</h3>
            {workspace?.history.length ? (
              <div className="preference-history">
                {workspace.history.map((entry) => (
                  <article className="history-entry" key={entry.id}>
                    <div>
                      <strong>{label(entry.preference_field)}</strong>
                      <small>{entry.source === "candidate" ? "From reviewed candidate" : "Direct profile edit"}</small>
                      <span>{entry.previous_value || "Not set"} → {entry.applied_value}</span>
                      <small>{new Date(entry.created_at).toLocaleString()}</small>
                      {entry.undone_at && <small>Undone {new Date(entry.undone_at).toLocaleString()}</small>}
                    </div>
                    {!entry.undone_at && (
                      <button type="button" onClick={() => void undo(entry.id)} disabled={saving}>
                        <RotateCcw size={13} /> Undo
                      </button>
                    )}
                  </article>
                ))}
              </div>
            ) : (
              <p className="preference-empty">Applied preferences will appear here with an undo option.</p>
            )}
          </section>

          <section className="preference-subsection">
            <h3>Recent feedback</h3>
            {workspace?.feedback.length ? (
              <div className="feedback-history">
                {workspace.feedback.slice(0, 10).map((item) => (
                  <article className="history-entry" key={item.id}>
                    <div>
                      <strong>{item.local_date ?? "General feedback"} · {item.rating === 1 ? "Helpful" : item.rating === -1 ? "Not helpful" : "No rating"}</strong>
                      <span>{item.comment || "No comment provided."}</span>
                    </div>
                  </article>
                ))}
              </div>
            ) : (
              <p className="preference-empty">Your saved feedback will appear here.</p>
            )}
          </section>
        </>
      )}
    </section>
  );
}
