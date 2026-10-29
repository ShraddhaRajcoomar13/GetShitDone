import { useEffect, useState } from "react";
import { api } from "../api";
import { Goal } from "../types";

export default function Goals() {
  const [goals, setGoals] = useState<Goal[]>([]);
  const [title, setTitle] = useState("");
  const [targetOutcome, setTargetOutcome] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editTitle, setEditTitle] = useState("");
  const [editOutcome, setEditOutcome] = useState("");
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);

  const refresh = async () => setGoals(await api.goals());
  useEffect(() => { refresh(); }, []);

  const add = async () => {
    if (!title.trim()) return;
    const monday = (() => {
      const d = new Date();
      d.setDate(d.getDate() - ((d.getDay() + 6) % 7));
      return d.toISOString().slice(0, 10);
    })();
    await api.createGoal({ title, target_outcome: targetOutcome, week_start: monday });
    setTitle(""); setTargetOutcome("");
    await refresh();
  };

  const startEdit = (g: Goal) => {
    setEditingId(g.id);
    setEditTitle(g.title);
    setEditOutcome(g.target_outcome);
  };

  const saveEdit = async (id: number) => {
    await api.updateGoal(id, { title: editTitle, target_outcome: editOutcome });
    setEditingId(null);
    await refresh();
  };

  const del = async (id: number) => {
    await api.deleteGoal(id);
    setConfirmDelete(null);
    await refresh();
  };

  return (
    <div className="space-y-4 max-w-3xl">
      <h1 className="text-3xl">Weekly Goals</h1>

      <div className="card space-y-2">
        <input className="input" placeholder="Goal title"
          value={title} onChange={(e) => setTitle(e.target.value)} />
        <input className="input" placeholder="Desired outcome (optional)"
          value={targetOutcome} onChange={(e) => setTargetOutcome(e.target.value)} />
        <button className="btn-primary" onClick={add}>Add goal</button>
      </div>

      <div className="space-y-2">
        {goals.length === 0 && <div className="text-neutral-500">No goals yet. Add one above.</div>}
        {goals.map((g) => (
          <div key={g.id} className="card">
            {editingId === g.id ? (
              <div className="space-y-2">
                <input className="input" value={editTitle}
                  onChange={(e) => setEditTitle(e.target.value)} />
                <input className="input" placeholder="Desired outcome (optional)"
                  value={editOutcome} onChange={(e) => setEditOutcome(e.target.value)} />
                <div className="flex gap-2 justify-end">
                  <button className="btn-ghost text-xs" onClick={() => setEditingId(null)}>Cancel</button>
                  <button className="btn-primary text-xs" onClick={() => saveEdit(g.id)}>Save</button>
                </div>
              </div>
            ) : (
              <div className="flex justify-between items-start gap-2">
                <div className="min-w-0">
                  <div className="font-medium">#{g.id} {g.title}</div>
                  {g.target_outcome && (
                    <div className="text-sm text-neutral-500">{g.target_outcome}</div>
                  )}
                  <div className="text-xs text-neutral-500 mt-1">
                    Week of {g.week_start} · priority {g.priority} · {g.status}
                  </div>
                  <div className="text-xs mt-2 text-neutral-500">
                    Tip: ask the agent “break down goal {g.id} into: …” to generate subtasks.
                  </div>
                </div>
                <div className="flex flex-col gap-1 shrink-0">
                  {confirmDelete === g.id ? (
                    <div className="flex gap-1">
                      <button className="text-xs text-red-600 font-medium" onClick={() => del(g.id)}>Delete</button>
                      <button className="text-xs text-neutral-500" onClick={() => setConfirmDelete(null)}>Cancel</button>
                    </div>
                  ) : (
                    <div className="flex gap-1">
                      <button className="btn-ghost text-xs" onClick={() => startEdit(g)}>Edit</button>
                      <button className="btn-ghost text-xs text-red-600" onClick={() => setConfirmDelete(g.id)}>×</button>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}