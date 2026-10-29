import { useState } from "react";
import { Task } from "../types";
import { api } from "../api";
import BlockerModal from "./BlockerModal";

export default function TaskCard({ task, onChange }: { task: Task; onChange: () => void }) {
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [showBlocker, setShowBlocker] = useState(false);
  const [editing, setEditing] = useState(false);
  const [editTitle, setEditTitle] = useState(task.title);
  const [editMin, setEditMin] = useState(task.estimated_minutes);
  const [editOutcome, setEditOutcome] = useState(task.outcome);
  const [editFirst, setEditFirst] = useState(task.smallest_first_action);
  const [busy, setBusy] = useState(false);

  const isDone = task.status === "completed";

  const color =
    isDone                       ? "border-green-400 bg-green-50 dark:bg-green-950" :
    task.status === "overdue"    ? "border-red-400 bg-red-50 dark:bg-red-950" :
    task.status === "postponed"  ? "border-amber-400 bg-amber-50 dark:bg-amber-950" :
    task.status === "blocked"    ? "border-purple-400 bg-purple-50 dark:bg-purple-950" :
    task.status === "active"     ? "border-accent bg-orange-50 dark:bg-neutral-800" :
                                   "border-neutral-200 dark:border-neutral-700";

  const toggleComplete = async () => {
    if (busy) return;
    setBusy(true);
    try {
      if (isDone) {
        await api.updateTask(task.id, { status: "planned" });
        // Reverse Option-B: reopening a subtask reopens its parent
        if (task.parent_task_id) {
          try { await api.updateTask(task.parent_task_id, { status: "planned" }); } catch {}
        }
      } else {
        await api.completeTask(task.id);
      }
      onChange();
    } finally {
      setBusy(false);
    }
  };

  const del = async () => {
    await api.deleteTask(task.id);
    setConfirmDelete(false);
    onChange();
  };

  const saveEdit = async () => {
    await api.updateTask(task.id, {
      title: editTitle,
      estimated_minutes: editMin,
      outcome: editOutcome,
      smallest_first_action: editFirst,
    });
    setEditing(false);
    onChange();
  };

  if (editing) {
    return (
      <div className={`card ${color}`}>
        <div className="space-y-2">
          <input className="input" value={editTitle}
            placeholder="Title" onChange={(e) => setEditTitle(e.target.value)} />
          <div className="flex items-center gap-2">
            <input type="number" min={5} step={5} className="input w-28"
              value={editMin} onChange={(e) => setEditMin(Number(e.target.value))} />
            <span className="text-xs text-neutral-500">minutes</span>
          </div>
          <input className="input" value={editOutcome}
            placeholder="Outcome (what done looks like)" onChange={(e) => setEditOutcome(e.target.value)} />
          <input className="input" value={editFirst}
            placeholder="Smallest first action" onChange={(e) => setEditFirst(e.target.value)} />
          <div className="flex gap-2 justify-end">
            <button className="btn-ghost text-xs" onClick={() => setEditing(false)}>Cancel</button>
            <button className="btn-primary text-xs" onClick={saveEdit}>Save</button>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className={`card ${color}`}>
      {task.subtask_progress && (
        <div className="text-xs text-neutral-500 mb-1">
          subtasks {task.subtask_progress.done}/{task.subtask_progress.total}
          {task.subtask_progress.done === task.subtask_progress.total && " ✓"}
        </div>
      )}
      <div className="flex justify-between items-start gap-2">
        <div className="flex items-start gap-2 min-w-0 flex-1">
          <button
            onClick={toggleComplete}
            disabled={busy}
            className={`mt-0.5 w-5 h-5 rounded-full border-2 flex items-center justify-center shrink-0 transition ${
              isDone
                ? "bg-green-500 border-green-500 text-white"
                : "border-neutral-400 dark:border-neutral-600 hover:border-accent"
            }`}
            aria-label={isDone ? "Mark as not done" : "Mark as done"}
            title={isDone ? "Reopen" : "Mark done"}
          >
            {isDone && <span className="text-[10px] font-bold leading-none">✓</span>}
          </button>

          <div className="min-w-0 flex-1">
            <div className={`font-medium ${isDone ? "line-through text-neutral-500" : ""}`}>
              {task.title}
            </div>
            {task.smallest_first_action && !isDone && (
              <div className="text-sm text-neutral-500">First: {task.smallest_first_action}</div>
            )}
            {task.blocker && (
              <div className="text-xs text-purple-700 dark:text-purple-300 mt-1 italic">
                Blocker: {task.blocker}
              </div>
            )}
            <div className="text-xs mt-1 text-neutral-500">
              {task.scheduled_start
                ? new Date(task.scheduled_start).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })
                : "unscheduled"}
              {" · "}{task.estimated_minutes}m
              {task.postpone_count > 0 && ` · postponed ${task.postpone_count}×`}
            </div>
          </div>
        </div>

        <div className="flex flex-col items-end gap-1 shrink-0">
          {!confirmDelete ? (
            <button
              className="text-neutral-400 hover:text-red-500 text-lg leading-none"
              onClick={() => setConfirmDelete(true)}
              aria-label="Delete task"
              title="Delete"
            >×</button>
          ) : (
            <div className="flex gap-1 items-center">
              <button className="text-xs text-red-600 font-medium" onClick={del}>Delete</button>
              <button className="text-xs text-neutral-500" onClick={() => setConfirmDelete(false)}>Cancel</button>
            </div>
          )}

          <div className="flex flex-wrap gap-1 justify-end">
            {!isDone && (
              <>
                <button className="btn-ghost text-xs"
                  onClick={async () => { await api.startTask(task.id); onChange(); }}>Start</button>
                <button
                  className="btn-ghost text-xs border border-purple-300 dark:border-purple-700 text-purple-700 dark:text-purple-300"
                  onClick={() => setShowBlocker(true)}>Not done</button>
              </>
            )}
            <button className="btn-ghost text-xs" onClick={() => setEditing(true)}>Edit</button>
          </div>
        </div>
      </div>

      {showBlocker && <BlockerModal task={task} onClose={() => setShowBlocker(false)} />}
    </div>
  );
}