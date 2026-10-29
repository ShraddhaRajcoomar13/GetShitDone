import { useEffect, useMemo, useState } from "react";
import { api } from "../api";
import { Goal, Task } from "../types";
import { buildTree, TaskNode } from "../lib/tree";
import { useAgentBus } from "../lib/agentBus";
import {
  mondayISO, fmtTime, fmtWeekday,
  hourMinuteFromIso, sastToBackendIso,
} from "../lib/sast";

export default function Planner() {
  const [weekStart, setWeekStart] = useState(mondayISO());
  const [tasks, setTasks] = useState<Task[]>([]);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [msg, setMsg] = useState("");
  const [dragId, setDragId] = useState<number | null>(null);
  const [newTitle, setNewTitle] = useState("");
  const [newMinutes, setNewMinutes] = useState(30);
  const bus = useAgentBus();

  const load = async () => {
    setTasks(await api.tasks());
    try { setGoals(await api.goals()); } catch { setGoals([]); }
  };
  useEffect(() => { load(); }, []);

  const days = useMemo(() => Array.from({ length: 7 }, (_, i) => {
    const d = new Date(weekStart + "T00:00:00Z");
    d.setUTCDate(d.getUTCDate() + i);
    return d.toISOString().slice(0, 10);
  }), [weekStart]);

  const byDay = useMemo(() => {
    const map: Record<string, Task[]> = {};
    for (const key of days) map[key] = [];
    for (const t of tasks) {
      const k = t.scheduled_start?.slice(0, 10);
      if (k && map[k]) map[k].push(t);
    }
    return map;
  }, [tasks, days]);

  const unscheduled = tasks.filter(
    (t) => !t.scheduled_start && t.status !== "dropped"
  );

  const plan = async () => {
    const p = await api.scheduleSuggest(weekStart);
    setMsg(`Suggested ${p.scheduled.length} slots, ${p.unscheduled.length} unscheduled, ${p.conflicts.length} conflicts.`);
    await api.scheduleApply(weekStart);
    await load();
  };

  const quickAdd = async () => {
    if (!newTitle.trim()) return;
    await api.createTask({ title: newTitle.trim(), estimated_minutes: newMinutes });
    setNewTitle("");
    await load();
  };

  const deleteTask = async (id: number) => {
    await api.deleteTask(id);
    await load();
  };

  const toggleTask = async (t: Task) => {
    if (t.status === "completed") {
      await api.updateTask(t.id, { status: "planned" });
      if (t.parent_task_id) {
        try { await api.updateTask(t.parent_task_id, { status: "planned" }); } catch {}
      }
    } else {
      await api.completeTask(t.id);
    }
    await load();
  };

  const checkConflicts = async (taskId: number, newStartIso: string) => {
    const token = localStorage.getItem("gsd_token");
    const r = await fetch(
      `/api/tasks/${taskId}/conflicts?new_start=${encodeURIComponent(newStartIso)}`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    if (!r.ok) return [] as any[];
    return (await r.json()).conflicts as any[];
  };

  const onDrop = async (targetDay: string) => {
    if (dragId == null) return;
    const t = tasks.find((x) => x.id === dragId);
    if (!t) return;

    const { hh, mm } = hourMinuteFromIso(t.scheduled_start);
    const [y, m, d] = targetDay.split("-").map(Number);
    const newStartIso = sastToBackendIso(y, m, d, hh, mm);
    const startDate = new Date(newStartIso + "+02:00");
    const endDate = new Date(startDate.getTime() + t.estimated_minutes * 60_000);
    const newEndIso = endDate.toISOString().replace("Z", "+00:00");

    const conflicts = await checkConflicts(t.id, newStartIso);

    await api.updateTask(t.id, {
      scheduled_start: newStartIso,
      scheduled_end: sastToBackendIso(
        endDate.getFullYear(), endDate.getMonth() + 1, endDate.getDate(),
        endDate.getHours(), endDate.getMinutes(),
      ),
      status: t.status === "completed" ? "completed" : "planned",
    });
    setDragId(null);
    await load();
    setMsg(conflicts.length > 0
      ? `Moved — ${conflicts.length} conflict(s).`
      : `Moved "${t.title}" to ${targetDay}.`);
  };

  const decomposeGoal = async (g: Goal) => {
    bus.setOpen(true);
    await bus.send(`Please break down goal ${g.id} "${g.title}" into 3–4 concrete subtasks with estimates, then schedule them.`);
    await load();
  };

  const renderNodes = (nodes: TaskNode[], depth: number): JSX.Element => (
    <>
      {nodes.map((n) => {
        const done = n.task.status === "completed";
        return (
          <div key={n.task.id} style={{ marginLeft: depth * 10 }}>
            <div className="p-2 rounded bg-neutral-100 dark:bg-neutral-700 text-xs flex items-start gap-1">
              <button
                onMouseDown={(e) => e.stopPropagation()}
                onClick={() => toggleTask(n.task)}
                className={`mt-0.5 w-4 h-4 rounded-full border-2 flex items-center justify-center shrink-0 ${
                  done
                    ? "bg-green-500 border-green-500 text-white"
                    : "border-neutral-400 dark:border-neutral-600 hover:border-accent"
                }`}
                title={done ? "Reopen" : "Mark done"}
              >
                {done && <span className="text-[8px] font-bold leading-none">✓</span>}
              </button>
              <div
                className="flex-1 min-w-0 cursor-move"
                draggable
                onDragStart={() => setDragId(n.task.id)}
                onDragEnd={() => setDragId(null)}
                title={n.task.smallest_first_action || ""}
              >
                <div className={`font-medium truncate ${done ? "line-through text-neutral-500" : ""}`}>
                  {n.task.title}
                </div>
                <div className="text-neutral-500">
                  {fmtTime(n.task.scheduled_start)}
                  {" · "}{n.task.estimated_minutes}m
                </div>
              </div>
              <button
                onMouseDown={(e) => e.stopPropagation()}
                className="text-neutral-400 hover:text-red-500 text-sm leading-none px-1 shrink-0"
                onClick={() => deleteTask(n.task.id)}
                title="Delete"
              >×</button>
            </div>
            {n.children.length > 0 && renderNodes(n.children, depth + 1)}
          </div>
        );
      })}
    </>
  );

  return (
    <div className="space-y-4">
      <h1 className="text-3xl">Weekly Planner</h1>

      {goals.length > 0 && (
        <div className="card">
          <div className="text-sm text-neutral-500 mb-2">Weekly Goals</div>
          <div className="space-y-1">
            {goals.map((g) => (
              <div key={g.id} className="flex justify-between items-center gap-2 text-sm">
                <div className="min-w-0">
                  <span className="font-medium">#{g.id} {g.title}</span>
                  <span className="text-xs text-neutral-500 ml-2">{g.status} · week of {g.week_start}</span>
                </div>
                <button className="btn-ghost text-xs border border-accent text-accent"
                  onClick={() => decomposeGoal(g)}>Decompose in agent →</button>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <div className="text-sm text-neutral-500 mb-2">Quick add task</div>
        <div className="flex gap-2">
          <input className="input flex-1" placeholder="Task title"
            value={newTitle} onChange={(e) => setNewTitle(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && quickAdd()} />
          <input type="number" min={5} step={5} className="input w-24"
            value={newMinutes} onChange={(e) => setNewMinutes(Number(e.target.value))} />
          <button className="btn-primary" onClick={quickAdd}>Add</button>
        </div>
      </div>

      <div className="flex items-center gap-2 flex-wrap">
        <input type="date" className="input w-48"
          value={weekStart} onChange={(e) => setWeekStart(e.target.value)} />
        <button className="btn-primary" onClick={plan}>Auto-schedule</button>
        <button className="btn-ghost" onClick={() => setWeekStart(mondayISO())}>This week</button>
        {msg && <span className="text-sm text-neutral-500">{msg}</span>}
      </div>

      <div className="grid grid-cols-7 gap-3">
        {days.map((key) => {
          const dayTasks = byDay[key] || [];
          const roots = buildTree(dayTasks);
          return (
            <div key={key} className="card min-h-[16rem]"
              onDragOver={(e) => e.preventDefault()}
              onDrop={() => onDrop(key)}>
              <div className="text-xs text-neutral-500">{fmtWeekday(key)}</div>
              <div className="space-y-1 mt-2">
                {renderNodes(roots, 0)}
                {dayTasks.length === 0 && (
                  <div className="text-xs text-neutral-400 italic">Drop tasks here</div>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {unscheduled.length > 0 && (
        <div className="card">
          <div className="text-sm text-neutral-500 mb-2">
            Unscheduled ({unscheduled.length}) — drag into a day, or click ✓ to mark done
          </div>
          <div className="space-y-1">
            {renderNodes(buildTree(unscheduled), 0)}
          </div>
        </div>
      )}
    </div>
  );
}