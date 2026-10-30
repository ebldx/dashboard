"use client";

import { useEffect, useState } from "react";
import { CalendarClock, CircleHelp, Goal, ListChecks } from "lucide-react";

type Planning = {
  local_date: string;
  priorities: {
    task_id: string;
    task_title: string;
    score: number;
    reasons: string[];
    deadline: string | null;
    estimated_duration_minutes: number | null;
  }[];
  project_recommendations: {
    project_id: string;
    project_title: string;
    score: number;
    reasons: string[];
  }[];
  schedule: {
    event_count: number;
    events_truncated: boolean;
    scheduled_minutes: number;
    overlapping_event_count: number;
    calendar_gaps: {
      starts_at: string;
      ends_at: string;
      duration_minutes: number;
    }[];
    events: { title: string; starts_at: string; ends_at: string; duration_minutes: number }[];
  };
};

function formatTime(value: string) {
  return new Intl.DateTimeFormat(undefined, {
    hour: "numeric",
    minute: "2-digit",
    timeZone: "Europe/Oslo",
  }).format(new Date(value));
}

export default function PlanningWorkspace() {
  const [planning, setPlanning] = useState<Planning | null>(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    const controller = new AbortController();
    fetch("/api/ai/planning", { signal: controller.signal, cache: "no-store" })
      .then(async (response) => {
        if (!response.ok) throw new Error("Planning is unavailable.");
        return (await response.json()) as Planning;
      })
      .then(setPlanning)
      .catch(() => {
        if (!controller.signal.aborted) setError(true);
      });
    return () => controller.abort();
  }, []);

  return (
    <section className="panel planning-panel" aria-labelledby="planning-title">
      <div className="panel-heading">
        <div>
          <div className="section-kicker">A CLEARER WAY THROUGH TODAY</div>
          <h2 id="planning-title">Planning intelligence</h2>
        </div>
        <span className="heading-icon"><ListChecks size={19} /></span>
      </div>
      {error ? (
        <p className="planning-empty" role="status">Planning information is unavailable right now.</p>
      ) : !planning ? (
        <p className="planning-empty">Building today&apos;s plan…</p>
      ) : (
        <div className="planning-grid">
          <section className="planning-section">
            <h3><ListChecks size={15} /> Daily priorities</h3>
            {planning.priorities.length ? (
              <ol className="planning-list">
                {planning.priorities.map((item) => (
                  <li key={item.task_id}>
                    <div className="planning-item-heading">
                      <strong>{item.task_title}</strong>
                      <span title="Deterministic priority score">{item.score}/100</span>
                    </div>
                    <p>{item.reasons.join(" · ")}</p>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="planning-empty">No open tasks to prioritize.</p>
            )}
          </section>

          <section className="planning-section">
            <h3><Goal size={15} /> Project recommendations</h3>
            {planning.project_recommendations.length ? (
              <ol className="planning-list">
                {planning.project_recommendations.map((item) => (
                  <li key={item.project_id}>
                    <div className="planning-item-heading">
                      <strong>{item.project_title}</strong>
                      <span title="Deterministic recommendation score">{item.score}/100</span>
                    </div>
                    <p>{item.reasons.join(" · ")}</p>
                  </li>
                ))}
              </ol>
            ) : (
              <p className="planning-empty">No active projects to recommend.</p>
            )}
          </section>

          <section className="planning-section planning-schedule">
            <h3><CalendarClock size={15} /> Today&apos;s calendar</h3>
            <p className="planning-summary">
              {planning.schedule.events_truncated ? "At least " : ""}
              {planning.schedule.event_count} event{planning.schedule.event_count === 1 ? "" : "s"}
              {planning.schedule.events_truncated ? " shown" : ""}
              {" · "}{Math.floor(planning.schedule.scheduled_minutes / 60)}h{" "}
              {planning.schedule.scheduled_minutes % 60}m scheduled
              {planning.schedule.overlapping_event_count > 0
                ? ` · ${planning.schedule.overlapping_event_count} overlapping event(s)`
                : ""}
            </p>
            {planning.schedule.events.length > 0 && (
              <ul className="planning-events">
                {planning.schedule.events.map((event, index) => (
                  <li key={`${event.starts_at}-${index}`}>
                    <time>{formatTime(event.starts_at)}–{formatTime(event.ends_at)}</time>
                    <span>{event.title}</span>
                  </li>
                ))}
              </ul>
            )}
            {planning.schedule.event_count > 0 &&
              planning.schedule.calendar_gaps
                .filter((gap) => gap.duration_minutes >= 30)
                .slice(0, 4)
                .map((gap) => (
                  <p className="planning-gap" key={`${gap.starts_at}-${gap.ends_at}`}>
                    Calendar gap: {formatTime(gap.starts_at)}–{formatTime(gap.ends_at)}
                    {" · "}
                    {Math.floor(gap.duration_minutes / 60)}h {gap.duration_minutes % 60}m
                  </p>
                ))}
            <div className="planning-gap-note">
              <CircleHelp size={14} />
              <span>
                Calendar gaps are not confirmed availability. Check your plans before scheduling work.
              </span>
            </div>
          </section>
        </div>
      )}
      <div className="planning-explanation">
        Priorities use task urgency, deadlines, progress, and active-goal links. Scores explain ordering,
        not guaranteed effort or available time.
      </div>
    </section>
  );
}
