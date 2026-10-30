"use client";

import { useEffect, useState } from "react";
import {
  CalendarRange,
  Lightbulb,
  LoaderCircle,
  RotateCw,
  Sparkles,
} from "lucide-react";

type OllamaStatus = {
  configured: boolean;
  reachable: boolean;
  model_configured: boolean;
  model_available: boolean;
  model_name: string | null;
  status: "not_configured" | "unavailable" | "model_missing" | "ready";
};

type Briefing = {
  local_date: string;
  generation_status: "pending" | "generated";
  content: {
    overview: string;
    priorities: { task_id: string; task_title: string | null; reason: string }[];
    principle_reminders: {
      principle_id: string;
      principle_title: string | null;
      reminder: string;
    }[];
    project_recommendations: {
      project_id: string;
      project_title: string | null;
      reason: string;
    }[];
    focus_advice: string;
  };
  error_message: string | null;
};

type WeeklyReview = {
  week_start: string;
  week_end: string;
  generation_status: "pending" | "generated";
  stats: {
    tasks_created: number;
    tasks_completed: number;
    tasks_with_deadlines: number;
    calendar_events: number;
    scheduled_minutes: number;
    feedback_count: number;
    helpful_feedback_count: number;
    unhelpful_feedback_count: number;
  };
  content: {
    summary: string;
    wins: string[];
    reflection_question: string;
    suggested_focus: string[];
  };
  error_message: string | null;
  attempt_count: number;
  next_retry_at: string | null;
};

async function readJson<T>(response: Response): Promise<T> {
  if (!response.ok) {
    throw new Error("The AI service could not be reached.");
  }
  return response.json() as Promise<T>;
}

export function OllamaStatusCard() {
  const [status, setStatus] = useState<OllamaStatus | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/ai/status", { signal: controller.signal, cache: "no-store" })
      .then((response) => readJson<OllamaStatus>(response))
      .then(setStatus)
      .catch(() => {
        if (!controller.signal.aborted) setFailed(true);
      });
    return () => controller.abort();
  }, []);

  const labels: Record<OllamaStatus["status"], string> = {
    not_configured: "Not connected",
    unavailable: "Unavailable",
    model_missing: "Model not found",
    ready: "Connected",
  };
  const ready = status?.status === "ready";

  return (
    <article className="status-card">
      <div className="status-card-top">
        <span className="status-icon status-icon-peach">
          <Sparkles size={18} />
        </span>
        <span className={`status-tag ${ready ? "status-tag-ready" : "status-tag-outline"}`}>
          {failed ? "Status unavailable" : status ? labels[status.status] : "Checking"}
        </span>
      </div>
      <p className="status-label">Your local AI</p>
      <p className="status-value">
        {failed
          ? "AI status unavailable"
          : status?.model_name ?? "Ollama not configured"}
      </p>
      <p className="status-detail">
        {ready
          ? "Configured model is ready for daily briefings."
          : status?.status === "model_missing"
            ? "Pull the configured model in Ollama to enable briefings."
            : status?.status === "unavailable"
              ? "Check that the API can reach your Ollama service."
              : status?.status === "not_configured"
                ? "Set OLLAMA_BASE_URL and OLLAMA_MODEL on the API."
                : "The dashboard works without AI."}
      </p>
    </article>
  );
}

export function DailyBriefingCard() {
  const [briefing, setBriefing] = useState<Briefing | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function loadBriefing(retry = false) {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        retry ? "/api/ai/briefing/retry" : "/api/ai/briefing",
        { method: retry ? "POST" : "GET", cache: "no-store" },
      );
      setBriefing(await readJson<Briefing>(response));
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "The briefing could not be loaded.");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/ai/briefing", { signal: controller.signal, cache: "no-store" })
      .then((response) => readJson<Briefing>(response))
      .then((result) => {
        if (!controller.signal.aborted) setBriefing(result);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            reason instanceof Error ? reason.message : "The briefing could not be loaded.",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const generated = briefing?.generation_status === "generated";
  return (
    <section className="briefing-card">
      <div className="briefing-top">
        <span className="briefing-icon">
          <Sparkles size={17} />
        </span>
        <span className="briefing-label">DAILY BRIEFING</span>
        <span className="briefing-status">
          {loading ? "LOADING" : generated ? "READY" : "PENDING"}
        </span>
      </div>
      {error ? (
        <p className="briefing-message" role="status">{error}</p>
      ) : briefing ? (
        <>
          <h2>{briefing.content.overview}</h2>
          {briefing.content.priorities.length > 0 && (
            <div className="briefing-list">
              <strong>Suggested priorities</strong>
              {briefing.content.priorities.map((priority) => (
                <div className="briefing-item" key={priority.task_id}>
                  <span>{priority.task_title ?? "Your task"}</span>
                  <small>{priority.reason}</small>
                </div>
              ))}
            </div>
          )}
          {briefing.content.project_recommendations.length > 0 && (
            <div className="briefing-list">
              <strong>Project ideas</strong>
              {briefing.content.project_recommendations.map((recommendation) => (
                <div className="briefing-item" key={recommendation.project_id}>
                  <span>{recommendation.project_title ?? "Your project"}</span>
                  <small>{recommendation.reason}</small>
                </div>
              ))}
            </div>
          )}
          {briefing.content.principle_reminders.map((principle) => (
            <div className="briefing-note" key={principle.principle_id}>
              <Lightbulb size={16} />
              <span>
                <strong>{principle.principle_title}</strong>: {principle.reminder}
              </span>
            </div>
          ))}
          <div className="briefing-divider" />
          <div className="briefing-note">
            <Lightbulb size={16} />
            <span>{briefing.content.focus_advice}</span>
          </div>
          {!generated && briefing.error_message && (
            <p className="briefing-error">{briefing.error_message}</p>
          )}
        </>
      ) : (
        <p className="briefing-message">
          {loading ? "Preparing today's briefing…" : "No briefing is available."}
        </p>
      )}
      {!generated && !loading && (
        <button
          className="briefing-retry"
          type="button"
          onClick={() => void loadBriefing(true)}
        >
          Retry with Ollama
        </button>
      )}
      {generated && (
        <a className="briefing-feedback-link" href="#preferences">
          Share feedback on this briefing
        </a>
      )}
      {loading && (
        <LoaderCircle
          aria-label="Loading briefing"
          className="briefing-loader"
          size={16}
        />
      )}
    </section>
  );
}

function formatReviewDate(value: string): string {
  return new Intl.DateTimeFormat("en", {
    day: "numeric",
    month: "short",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function formatRetryTime(value: string): string {
  return new Intl.DateTimeFormat("en", {
    dateStyle: "medium",
    timeStyle: "short",
    timeZone: "Europe/Oslo",
  }).format(new Date(value));
}

export function WeeklyReviewCard() {
  const [review, setReview] = useState<WeeklyReview | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  async function retryReview(weekStart: string) {
    setLoading(true);
    setError(null);
    try {
      const response = await fetch(
        `/api/ai/weekly-review/retry?week_start=${encodeURIComponent(weekStart)}`,
        { method: "POST", cache: "no-store" },
      );
      setReview(await readJson<WeeklyReview>(response));
    } catch (reason) {
      setError(
        reason instanceof Error ? reason.message : "The weekly review could not be loaded.",
      );
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/ai/weekly-review", {
      signal: controller.signal,
      cache: "no-store",
    })
      .then((response) => readJson<WeeklyReview>(response))
      .then((result) => {
        if (!controller.signal.aborted) setReview(result);
      })
      .catch((reason: unknown) => {
        if (!controller.signal.aborted) {
          setError(
            reason instanceof Error
              ? reason.message
              : "The weekly review could not be loaded.",
          );
        }
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, []);

  const generated = review?.generation_status === "generated";
  return (
    <section className="weekly-review-card" id="weekly-review">
      <div className="weekly-review-top">
        <span className="briefing-icon">
          <CalendarRange size={17} />
        </span>
        <span className="briefing-label">WEEKLY REVIEW</span>
        <span className="briefing-status">
          {loading ? "LOADING" : generated ? "READY" : "PENDING"}
        </span>
      </div>
      {review ? (
        <>
          <p className="weekly-review-range">
            {formatReviewDate(review.week_start)} – {formatReviewDate(review.week_end)}
          </p>
          <h2>{review.content.summary}</h2>
          <div className="weekly-review-stats">
            <div>
              <strong>{review.stats.tasks_completed}</strong>
              <span>tasks done</span>
            </div>
            <div>
              <strong>{review.stats.tasks_created}</strong>
              <span>tasks added</span>
            </div>
            <div>
              <strong>{review.stats.calendar_events}</strong>
              <span>events</span>
            </div>
            <div>
              <strong>{Math.round(review.stats.scheduled_minutes / 60)}h</strong>
              <span>scheduled</span>
            </div>
          </div>
          {review.content.wins.length > 0 && (
            <div className="weekly-review-list">
              <strong>Wins</strong>
              {review.content.wins.map((win) => <p key={win}>{win}</p>)}
            </div>
          )}
          {review.content.suggested_focus.length > 0 && (
            <div className="weekly-review-list">
              <strong>For next week</strong>
              {review.content.suggested_focus.map((focus) => <p key={focus}>{focus}</p>)}
            </div>
          )}
          <p className="weekly-review-question">{review.content.reflection_question}</p>
          {!generated && review.error_message && (
            <p className="briefing-error">{review.error_message}</p>
          )}
          {!generated && review.next_retry_at && (
            <p className="briefing-error">
              Automatic retry after {formatRetryTime(review.next_retry_at)} · attempt{" "}
              {review.attempt_count}
            </p>
          )}
        </>
      ) : (
        <p className="briefing-message">
          {error ?? (loading ? "Preparing your weekly review…" : "No review is available.")}
        </p>
      )}
      {!generated && !loading && review && (
        <button
          className="briefing-retry"
          type="button"
          onClick={() => void retryReview(review.week_start)}
        >
          <RotateCw size={13} />
          Retry with Ollama
        </button>
      )}
      {error && review && <p className="briefing-error" role="status">{error}</p>}
      {loading && (
        <LoaderCircle
          aria-label="Loading weekly review"
          className="briefing-loader"
          size={16}
        />
      )}
    </section>
  );
}
