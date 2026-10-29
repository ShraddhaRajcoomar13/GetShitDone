import { useState } from "react";
import { Task } from "../types";
import { useAgentBus } from "../lib/agentBus";

const CATEGORIES: { key: string; label: string; hint: string }[] = [
  { key: "avoidance",   label: "I've been avoiding it",   hint: "It feels uncomfortable, boring, or scary." },
  { key: "too_big",     label: "It's too big",            hint: "I don't know where to start." },
  { key: "unclear",     label: "I'm not sure what to do", hint: "The first step isn't obvious." },
  { key: "low_energy",  label: "I'm low on energy",       hint: "Tired, foggy, or burnt out." },
  { key: "health",      label: "I'm unwell",              hint: "Sick, in pain, or exhausted." },
  { key: "external",    label: "Something came up",       hint: "Interruptions, other people, chaos." },
  { key: "other",       label: "Other",                   hint: "Something else." },
];

export default function BlockerModal({ task, onClose }: { task: Task; onClose: () => void }) {
  const bus = useAgentBus();
  const [category, setCategory] = useState<string>("");
  const [details, setDetails] = useState("");
  const [sending, setSending] = useState(false);

  const submit = async () => {
    if (!category) return;
    const cat = CATEGORIES.find((c) => c.key === category)!;
    const message =
      `I didn't do task #${task.id} "${task.title}". ` +
      `Reason: ${cat.label}${details ? `. ${details}` : ""}. ` +
      `Help me figure out what to do next.`;
    setSending(true);
    onClose();
    bus.setOpen(true);
    await bus.send(message);
    setSending(false);
  };

  return (
    <div
      className="fixed inset-0 z-30 bg-black/40 flex items-center justify-center p-4"
      onClick={(e) => e.target === e.currentTarget && onClose()}
    >
      <div className="card w-full max-w-md space-y-3">
        <div>
          <div className="text-sm text-neutral-500">Why didn't this happen?</div>
          <div className="font-medium">{task.title}</div>
        </div>

        <div className="grid grid-cols-1 gap-1.5">
          {CATEGORIES.map((c) => (
            <button
              key={c.key}
              onClick={() => setCategory(c.key)}
              className={`text-left p-2 rounded-lg border text-sm ${
                category === c.key
                  ? "border-accent bg-orange-50 dark:bg-neutral-800"
                  : "border-neutral-200 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-800"
              }`}
            >
              <div className="font-medium">{c.label}</div>
              <div className="text-xs text-neutral-500">{c.hint}</div>
            </button>
          ))}
        </div>

        <textarea
          className="input"
          rows={2}
          placeholder="Add detail (optional) — what specifically got in the way?"
          value={details}
          onChange={(e) => setDetails(e.target.value)}
        />

        <div className="flex gap-2 justify-end">
          <button className="btn-ghost" onClick={onClose} disabled={sending}>Cancel</button>
          <button className="btn-primary" onClick={submit} disabled={!category || sending}>
            {sending ? "Sending…" : "Ask agent for help"}
          </button>
        </div>
      </div>
    </div>
  );
}