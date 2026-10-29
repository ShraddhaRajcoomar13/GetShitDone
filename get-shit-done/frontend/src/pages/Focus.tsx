import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import { Task } from "../types";

type Phase = "idle" | "running" | "paused" | "done";

export default function Focus() {
  const [tasks, setTasks] = useState<Task[]>([]);
  const [selected, setSelected] = useState<Task | null>(null);
  const [minutes, setMinutes] = useState(25);
  const [remaining, setRemaining] = useState(0);
  const [phase, setPhase] = useState<Phase>("idle");
  const [sessionId, setSessionId] = useState<number | null>(null);
  const [note, setNote] = useState("");
  const tick = useRef<number | null>(null);

  useEffect(() => {
    (async () => {
      const all = await api.tasks();
      setTasks(all.filter((t) => t.status !== "completed"));
    })();
  }, []);

  useEffect(() => {
    if (phase !== "running") return;
    tick.current = window.setInterval(() => {
      setRemaining((r) => {
        if (r <= 1) {
          window.clearInterval(tick.current!);
          tick.current = null;
          setPhase("done");
          if ("Notification" in window && Notification.permission === "granted") {
            new Notification("Session complete", { body: "Time's up. Report the outcome." });
          }
          return 0;
        }
        return r - 1;
      });
    }, 1000);
    return () => {
      if (tick.current) window.clearInterval(tick.current);
    };
  }, [phase]);

  const requestNotif = async () => {
    if ("Notification" in window && Notification.permission === "default") {
      await Notification.requestPermission();
    }
  };

  const start = async () => {
    if (!selected) return;
    await requestNotif();
    const s = await api.focusStart(selected.id, minutes);
    setSessionId(s.session_id);
    setRemaining(minutes * 60);
    setPhase("running");
  };

  const pause = () => {
    if (tick.current) { window.clearInterval(tick.current); tick.current = null; }
    setPhase("paused");
  };

  const resume = () => setPhase("running");

  const finish = async (completed: boolean) => {
    if (sessionId != null) await api.focusEnd(sessionId, completed, note);
    setPhase("idle");
    setRemaining(0);
    setSessionId(null);
    setNote("");
    setSelected(null);
  };

  const mmss = (s: number) =>
    `${String(Math.floor(s / 60)).padStart(2, "0")}:${String(s % 60).padStart(2, "0")}`;

  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-3xl">Focus Mode</h1>

      {phase === "idle" && (
        <>
          <div className="card">
            <div className="text-sm text-neutral-500 mb-2">Pick a task</div>
            <select
              className="input"
              onChange={(e) => setSelected(tasks.find((t) => t.id === Number(e.target.value)) || null)}
              value={selected?.id ?? ""}
            >
              <option value="">— select —</option>
              {tasks.map((t) => (
                <option key={t.id} value={t.id}>{t.title}</option>
              ))}
            </select>
            <div className="text-sm text-neutral-500 mt-3 mb-2">Session length</div>
            <div className="flex gap-2">
              {[5, 10, 25, 50].map((m) => (
                <button
                  key={m}
                  className={`btn ${minutes === m ? "btn-primary" : "btn-ghost border border-neutral-300 dark:border-neutral-600"}`}
                  onClick={() => setMinutes(m)}
                >{m}m</button>
              ))}
            </div>
            <button className="btn-primary w-full mt-4" disabled={!selected} onClick={start}>
              Start work
            </button>
          </div>
        </>
      )}

      {phase !== "idle" && selected && (
        <div className="card">
          <div className="text-sm text-neutral-500">Working on</div>
          <div className="text-lg font-medium">{selected.title}</div>
          {selected.smallest_first_action && (
            <div className="text-sm mt-1">Smallest first action: {selected.smallest_first_action}</div>
          )}
          <div className="text-6xl font-serif text-center my-6 tabular-nums">
            {mmss(remaining)}
          </div>
          <div className="flex gap-2 justify-center">
            {phase === "running" && <button className="btn-ghost" onClick={pause}>Pause</button>}
            {phase === "paused" && <button className="btn-primary" onClick={resume}>Resume</button>}
            {phase === "done" && (
              <>
                <textarea
                  className="input mb-2"
                  placeholder="Quick reflection (optional)"
                  rows={3}
                  value={note}
                  onChange={(e) => setNote(e.target.value)}
                />
                <button className="btn-primary" onClick={() => finish(true)}>Mark task done</button>
                <button className="btn-ghost" onClick={() => finish(false)}>Not finished</button>
              </>
            )}
          </div>
          {phase === "running" && (
            <div className="text-xs text-neutral-500 mt-4 text-center">
              You don't need to feel motivated. Open it. Five minutes on the clock.
            </div>
          )}
        </div>
      )}
    </div>
  );
}