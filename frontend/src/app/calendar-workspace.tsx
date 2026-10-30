"use client";

import { FormEvent, useCallback, useEffect, useState } from "react";
import {
  CalendarDays,
  ChevronLeft,
  ChevronRight,
  CircleAlert,
  Clock3,
  RefreshCw,
  Save,
  ShieldCheck,
  Unlink,
} from "lucide-react";

type CalendarStatus = {
  configured: boolean;
  enabled: boolean;
  adapter: string | null;
  display_name: string | null;
  sync_status: string;
  last_sync_attempt_at: string | null;
  last_successful_sync_at: string | null;
  last_sync_error: string | null;
  last_event_count: number;
  last_created_count: number;
  last_updated_count: number;
  last_deleted_count: number;
};

type CalendarEvent = {
  id: string;
  source_id: string;
  source_name: string;
  source_uid: string;
  title: string;
  description: string;
  location: string;
  starts_at: string;
  ends_at: string;
  local_date: string;
  all_day: boolean;
  source_timezone: string;
  status: "confirmed" | "tentative" | "cancelled";
};

async function request<T>(url: string, init?: RequestInit): Promise<T> {
  const response = await fetch(url, { ...init, cache: "no-store" });
  if (!response.ok) {
    let message = `Request failed (${response.status}).`;
    try {
      const body: { detail?: string } = await response.json();
      if (body.detail) message = body.detail;
    } catch {
      // Keep the HTTP status when the server does not return JSON.
    }
    throw new Error(message);
  }
  return response.json() as Promise<T>;
}

function localToday() {
  return new Intl.DateTimeFormat("en-CA", {
    timeZone: "Europe/Oslo",
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  }).format(new Date());
}

function shiftDate(value: string, days: number) {
  const date = new Date(`${value}T12:00:00Z`);
  date.setUTCDate(date.getUTCDate() + days);
  return date.toISOString().slice(0, 10);
}

function displayDate(value: string, options: Intl.DateTimeFormatOptions) {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Oslo",
    ...options,
  }).format(new Date(`${value}T12:00:00Z`));
}

function displayTime(value: string) {
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Oslo",
    hour: "2-digit",
    minute: "2-digit",
  }).format(new Date(value));
}

function displayUpdated(value: string | null) {
  if (!value) return "Never";
  return new Intl.DateTimeFormat("en-GB", {
    timeZone: "Europe/Oslo",
    dateStyle: "medium",
    timeStyle: "short",
  }).format(new Date(value));
}

function weekDays(start: string) {
  return Array.from({ length: 7 }, (_, index) => shiftDate(start, index));
}

export default function CalendarWorkspace() {
  const [status, setStatus] = useState<CalendarStatus | null>(null);
  const [events, setEvents] = useState<CalendarEvent[]>([]);
  const [selectedDate, setSelectedDate] = useState("");
  const [feedUrl, setFeedUrl] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");

  const loadStatus = useCallback(async () => {
    setStatus(await request<CalendarStatus>("/api/calendar/status"));
  }, []);

  const loadEvents = useCallback(async (date: string) => {
    if (!date) return;
    const toDate = shiftDate(date, 6);
    setEvents(
      await request<CalendarEvent[]>(
        `/api/calendar/events?from_date=${date}&to_date=${toDate}`,
      ),
    );
  }, []);

  useEffect(() => {
    let active = true;
    const today = localToday();
    void Promise.all([
      request<CalendarStatus>("/api/calendar/status"),
      request<CalendarEvent[]>(
        `/api/calendar/events?from_date=${today}&to_date=${shiftDate(today, 6)}`,
      ),
    ])
      .then(([sourceStatus, calendarEvents]) => {
        if (!active) return;
        setSelectedDate(today);
        setStatus(sourceStatus);
        setEvents(calendarEvents);
      })
      .catch((cause: unknown) => {
        if (active) {
          setSelectedDate(today);
          setError(cause instanceof Error ? cause.message : "Could not load the calendar.");
        }
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    return () => {
      active = false;
    };
  }, []);

  async function saveSource(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const saved = await request<CalendarStatus>("/api/calendar/source", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feed_url: feedUrl.trim() }),
      });
      setStatus(saved);
      setFeedUrl("");
      await loadEvents(selectedDate);
      setNotice("Calendar subscription saved. Sync it to import events.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not save the subscription.");
    } finally {
      setSaving(false);
    }
  }

  async function disconnectSource() {
    if (!window.confirm("Remove the saved subscription and its imported calendar events?")) {
      return;
    }
    setSaving(true);
    setError("");
    setNotice("");
    try {
      const saved = await request<CalendarStatus>("/api/calendar/source", {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feed_url: "" }),
      });
      setStatus(saved);
      setEvents([]);
      setNotice("Calendar subscription and imported events removed.");
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not remove the subscription.");
    } finally {
      setSaving(false);
    }
  }

  async function synchronize() {
    setSyncing(true);
    setError("");
    setNotice("");
    try {
      const result = await request<{
        status: string;
        created: number;
        updated: number;
        deleted: number;
        event_count: number;
      }>("/api/calendar/sync", { method: "POST" });
      await Promise.all([loadStatus(), loadEvents(selectedDate)]);
      setNotice(
        result.status === "not_modified"
          ? "Calendar is already up to date."
          : `Sync complete: ${result.created} new, ${result.updated} updated, ${result.deleted} removed.`,
      );
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Calendar synchronization failed.";
      try {
        await loadStatus();
        setError(message);
      } catch {
        setError(`${message} Calendar sync status could not be refreshed.`);
      }
    } finally {
      setSyncing(false);
    }
  }

  async function changeDate(date: string) {
    setSelectedDate(date);
    setLoading(true);
    setError("");
    try {
      await loadEvents(date);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Could not load calendar events.");
    } finally {
      setLoading(false);
    }
  }

  const days = selectedDate ? weekDays(selectedDate) : [];
  const eventsByDate = new Map<string, CalendarEvent[]>();
  for (const event of events) {
    const current = eventsByDate.get(event.local_date) ?? [];
    current.push(event);
    eventsByDate.set(event.local_date, current);
  }

  return (
    <section className="calendar-workspace" id="calendar" aria-label="Calendar">
      <div className="personal-intro">
        <div>
          <div className="section-kicker">PHASE 4 · YOUR SCHEDULE</div>
          <h2>See the week ahead</h2>
          <p>Imported calendar events stay separate from your tasks and are shown with their source.</p>
        </div>
        <span className="personal-local-label"><span /> Europe/Oslo</span>
      </div>

      {error && <div className="workspace-message workspace-message-error" role="alert">{error}</div>}
      {notice && <div className="workspace-message workspace-message-success" role="status">{notice}</div>}

      <section className="panel personal-panel calendar-panel">
        <div className="personal-section-heading">
          <div>
            <div className="section-kicker">IMPORTED COMMITMENTS</div>
            <h3>Calendar</h3>
            <p>Connect an authorized Mine studier iCalendar subscription. The URL is encrypted at rest; events are read-only.</p>
          </div>
          <span className={`record-status record-status-${status?.sync_status === "error" ? "cancelled" : status?.sync_status === "success" ? "completed" : "paused"}`}>
            {status?.sync_status === "success" ? "Synced" : status?.sync_status === "error" ? "Sync error" : status?.configured ? "Not synced yet" : "Not connected"}
          </span>
        </div>

        <form className="calendar-source-form" onSubmit={(event) => void saveSource(event)}>
          <label className="personal-field">
            <span>Private iCalendar subscription URL</span>
            <input
              type="password"
              autoComplete="new-password"
              value={feedUrl}
              maxLength={8192}
              required
              placeholder={status?.configured ? "Enter a new URL to replace the saved subscription" : "https://…"}
              onChange={(event) => setFeedUrl(event.target.value)}
            />
          </label>
          <button className="personal-button personal-button-primary" type="submit" disabled={saving || !feedUrl.trim()}>
            <Save size={14} /> {saving ? "Saving…" : "Save subscription"}
          </button>
        </form>

        <div className="calendar-source-status">
          <div className="calendar-source-details">
            <ShieldCheck size={16} />
            <span>
              <strong>{status?.configured ? `${status.display_name} subscription saved` : "No calendar subscription configured"}</strong>
              <small>
                Last successful sync: {displayUpdated(status?.last_successful_sync_at ?? null)}
                {status?.configured ? ` · ${status.last_event_count} events in the sync window` : ""}
              </small>
            </span>
          </div>
          <div className="calendar-source-actions">
            {status?.configured && (
              <>
                <button className="personal-button personal-button-subtle" type="button" onClick={() => void synchronize()} disabled={syncing || saving}>
                  <RefreshCw size={14} className={syncing ? "calendar-spinning" : ""} /> {syncing ? "Syncing…" : "Sync now"}
                </button>
                <button className="personal-button personal-button-subtle" type="button" onClick={() => void disconnectSource()} disabled={saving || syncing}>
                  <Unlink size={14} /> Disconnect
                </button>
              </>
            )}
          </div>
        </div>
        {status?.last_sync_error && (
          <p className="calendar-sync-error"><CircleAlert size={14} /> {status.last_sync_error}</p>
        )}
        {status?.last_successful_sync_at && (
          <p className="calendar-sync-counts">
            Latest sync: {status.last_created_count} added · {status.last_updated_count} updated · {status.last_deleted_count} removed
          </p>
        )}

        <div className="calendar-agenda">
          <div className="calendar-agenda-heading">
            <div>
              <div className="section-kicker">WEEKLY AGENDA</div>
              <h4>{selectedDate ? `${displayDate(selectedDate, { month: "long", year: "numeric" })}` : "Loading dates…"}</h4>
            </div>
            <div className="calendar-date-controls">
              <button type="button" aria-label="Previous week" onClick={() => void changeDate(shiftDate(selectedDate, -7))} disabled={!selectedDate}><ChevronLeft size={16} /></button>
              <input aria-label="Choose week starting date" type="date" value={selectedDate} onChange={(event) => { if (event.target.value) void changeDate(event.target.value); }} />
              <button type="button" aria-label="Next week" onClick={() => void changeDate(shiftDate(selectedDate, 7))} disabled={!selectedDate}><ChevronRight size={16} /></button>
            </div>
          </div>
          {loading && <p className="calendar-loading" role="status">Loading calendar events…</p>}
          {!loading && events.length === 0 && (
            <div className="calendar-empty">
              <CalendarDays size={20} />
              <span>{status?.configured ? "No imported events for this week. Try syncing the calendar." : "Connect and sync a calendar to see events here."}</span>
            </div>
          )}
          <div className="calendar-days">
            {days.map((day) => {
              const dayEvents = eventsByDate.get(day) ?? [];
              return (
                <section className={`calendar-day${day === localToday() ? " calendar-day-today" : ""}`} key={day}>
                  <div className="calendar-day-heading">
                    <strong>{displayDate(day, { weekday: "short", day: "numeric" })}</strong>
                    <span>{dayEvents.length ? `${dayEvents.length} event${dayEvents.length === 1 ? "" : "s"}` : "Clear"}</span>
                  </div>
                  {dayEvents.map((event) => (
                    <article className={`calendar-event calendar-event-${event.status}`} key={event.id}>
                      <div className="calendar-event-time">
                        {event.all_day ? "All day" : `${displayTime(event.starts_at)}–${displayTime(event.ends_at)}`}
                      </div>
                      <div className="calendar-event-main">
                        <h5>{event.title}{event.status === "cancelled" ? " · Cancelled" : event.status === "tentative" ? " · Tentative" : ""}</h5>
                        {event.location && <p>{event.location}</p>}
                        {event.description && <p>{event.description}</p>}
                        <span><Clock3 size={11} /> {event.source_name} · {event.source_timezone}</span>
                      </div>
                    </article>
                  ))}
                </section>
              );
            })}
          </div>
        </div>
      </section>
    </section>
  );
}
