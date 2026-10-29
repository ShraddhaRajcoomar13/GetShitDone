import { useEffect, useState } from "react";
import { api } from "../api";
import { Dashboard, Task } from "../types";
import TaskCard from "../components/TaskCard";
import { buildTree, TaskNode } from "../lib/tree";

export default function Today() {
  const [d, setD] = useState<Dashboard | null>(null);
  const [allTasks, setAllTasks] = useState<Task[]>([]);
  const [newTitle, setNewTitle] = useState("");

  const refresh = async () => {
    setD(await api.dashboard());
    setAllTasks(await api.tasks());
  };
  useEffect(() => { refresh(); }, []);
  if (!d) return <div>Loading…</div>;

  const todayStr = new Date().toISOString().slice(0, 10);

  const active = allTasks.filter(
    (t) => t.status !== "completed" && t.status !== "dropped"
  );
  const completedToday = allTasks.filter(
    (t) => t.status === "completed" && t.scheduled_start?.startsWith(todayStr)
  );

  const scheduledActive = active.filter((t) => t.scheduled_start?.startsWith(todayStr));
  const scheduledRoots = buildTree(scheduledActive);
  // Anything active but not scheduled today → lives in the Unscheduled tray
  const remainingActive = active.filter((t) => !t.scheduled_start?.startsWith(todayStr));

  const quickAdd = async () => {
    if (!newTitle.trim()) return;
    await api.createTask({ title: newTitle.trim(), estimated_minutes: 30 });
    setNewTitle("");
    await refresh();
  };

  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-3xl">Today</h1>

      <div className="card flex gap-2">
        <input className="input flex-1" placeholder="Quick add task…"
          value={newTitle} onChange={(e) => setNewTitle(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && quickAdd()} />
        <button className="btn-primary" onClick={quickAdd}>Add</button>
      </div>

      <div className="card">
        <div className="text-sm text-neutral-500">Agent summary</div>
        <div>{d.agent_summary}</div>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
        <Stat label="Done" value={`${d.completed_today}/${d.planned_today}`} />
        <Stat label="Focus" value={`${d.focus_minutes_today}m`} />
        <Stat label="Overdue" value={d.overdue_count} />
        <Stat label="Water" value={`${d.hydration_ml_today}/${d.hydration_goal_ml}ml`} />
      </div>

      {d.next_task && (
        <div className="card border-accent">
          <div className="text-sm text-neutral-500">Next up</div>
          <div className="text-lg font-medium">{d.next_task.title}</div>
          <div className="text-sm">{d.next_task.smallest_first_action || "Open it and start."}</div>
        </div>
      )}

      <section>
        <div className="text-sm text-neutral-500 mb-2">Scheduled today</div>
        {scheduledRoots.length === 0
          ? <div className="text-sm text-neutral-500 italic">Nothing scheduled for today yet.</div>
          : <TaskTree nodes={scheduledRoots} onChange={refresh} />
        }
      </section>

      {remainingActive.length > 0 && (
        <section>
          <div className="text-sm text-neutral-500 mb-2">
            Unscheduled ({remainingActive.length}) — click ✓ to mark done, or drag into Planner
          </div>
          <TaskTree nodes={buildTree(remainingActive)} onChange={refresh} />
        </section>
      )}

      {completedToday.length > 0 && (
        <section>
          <div className="text-sm text-neutral-500 mb-2">
            Completed today ({completedToday.length}) — click ✓ to reopen
          </div>
          <div className="space-y-2 opacity-70">
            {completedToday.map((t) => (
              <TaskCard key={t.id} task={t} onChange={refresh} />
            ))}
          </div>
        </section>
      )}
    </div>
  );
}

function TaskTree({ nodes, onChange }: { nodes: TaskNode[]; onChange: () => void }) {
  const render = (list: TaskNode[], depth = 0): JSX.Element => (
    <>
      {list.map((n) => (
        <div key={n.task.id} style={{ marginLeft: depth * 20 }}>
          <TaskCard task={n.task} onChange={onChange} />
          {n.children.length > 0 && render(n.children, depth + 1)}
        </div>
      ))}
    </>
  );
  return <div className="space-y-2">{render(nodes)}</div>;
}

function Stat({ label, value }: { label: string; value: any }) {
  return (
    <div className="card">
      <div className="text-xs text-neutral-500">{label}</div>
      <div className="text-xl font-serif">{value}</div>
    </div>
  );
}