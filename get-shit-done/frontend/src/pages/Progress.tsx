import { useEffect, useState } from "react";
import { api } from "../api";
import { Dashboard } from "../types";

export default function Progress() {
  const [d, setD] = useState<Dashboard | null>(null);

  useEffect(() => { (async () => setD(await api.dashboard()))(); }, []);
  if (!d) return <div>Loading…</div>;

  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-3xl">Progress</h1>

      <div className="card">
        <div className="text-sm text-neutral-500">This week</div>
        <div className="text-lg">{d.agent_summary}</div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Box label="Done today" value={`${d.completed_today}/${d.planned_today}`} />
        <Box label="Focus minutes" value={d.focus_minutes_today} />
        <Box label="Overdue" value={d.overdue_count} />
        <Box label="Blocked" value={d.blocked_count} />
      </div>

      <div className="card">
        <div className="text-sm text-neutral-500 mb-2">Goal progress</div>
        {d.weekly_goal_progress.length === 0 && <div className="text-neutral-500">No goals this week.</div>}
        <div className="space-y-2">
          {d.weekly_goal_progress.map((g) => (
            <div key={g.goal_id}>
              <div className="flex justify-between text-sm">
                <span>{g.title}</span>
                <span>{g.completed}/{g.total} ({g.progress_pct}%)</span>
              </div>
              <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-2">
                <div className="bg-accent h-2 rounded-full" style={{ width: `${g.progress_pct}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="text-sm text-neutral-500 mb-2">Recent mood & energy (30 days)</div>
        {d.mood_energy.length === 0 && <div className="text-neutral-500">No check-ins yet.</div>}
        <div className="flex gap-2 flex-wrap">
          {d.mood_energy.map((m, i) => (
            <div key={i} className="text-xs px-2 py-1 rounded bg-neutral-100 dark:bg-neutral-700">
              {new Date(m.logged_at).toLocaleDateString([], { month: "short", day: "numeric" })}
              {" · "}M{m.mood ?? "–"}/E{m.energy ?? "–"}
            </div>
          ))}
        </div>
      </div>

      <div className="card text-xs text-neutral-500">
        These summaries describe patterns, not diagnoses. If something feels persistently hard, that's
        information about the plan — not about your worth.
      </div>
    </div>
  );
}

function Box({ label, value }: { label: string; value: any }) {
  return (
    <div className="card">
      <div className="text-xs text-neutral-500">{label}</div>
      <div className="text-xl font-serif">{value}</div>
    </div>
  );
}