import { useAgentBus } from "../lib/agentBus";
import { useState } from "react";

export default function AgentChat() {
  const bus = useAgentBus();
  const [msg, setMsg] = useState("");

  const handleSend = async () => {
    const text = msg;
    setMsg("");
    await bus.send(text);
  };

  return (
    <>
      <div className="fixed bottom-4 right-4 z-20">
        <button
          className="btn-primary shadow-lg relative"
          onClick={() => bus.setOpen(!bus.open)}
          aria-label={bus.unseenCount > 0 ? `Agent — ${bus.unseenCount} new check-in` : "Agent"}
        >
          {bus.open ? "×" : "Agent"}
          {!bus.open && bus.unseenCount > 0 && (
            <span className="absolute -top-1 -right-1 bg-red-500 text-white text-[10px] rounded-full w-5 h-5 flex items-center justify-center font-bold">
              {bus.unseenCount}
            </span>
          )}
        </button>
      </div>

      {bus.open && (
        <div className="fixed bottom-16 right-4 w-96 h-[28rem] card flex flex-col z-20">
          <div className="font-serif text-lg mb-2">Accountability Agent</div>

          <div className="flex-1 overflow-auto text-sm space-y-2">
            {bus.checkins.length > 0 && (
              <div className="space-y-2 mb-2">
                {bus.checkins.map((c) => (
                  <div
                    key={`ci-${c.id}`}
                    className="border-l-2 border-accent pl-2 py-1 bg-orange-50/60 dark:bg-neutral-800/40 rounded-r"
                  >
                    <div className="text-[10px] uppercase tracking-wide text-accent font-semibold mb-0.5">
                      Check-in ·{" "}
                      {new Date(c.created_at).toLocaleTimeString([], {
                        hour: "2-digit",
                        minute: "2-digit",
                      })}
                    </div>
                    <div className="text-neutral-700 dark:text-neutral-200 whitespace-pre-wrap">
                      {c.content}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {bus.messages.map((m, i) => (
              <div
                key={i}
                className={
                  m.role === "user"
                    ? "text-right"
                    : m.role === "tool"
                    ? "text-xs text-neutral-500 italic"
                    : ""
                }
              >
                <span
                  className={`inline-block px-2 py-1 rounded whitespace-pre-wrap ${
                    m.role === "user"
                      ? "bg-accent text-white"
                      : m.role === "assistant"
                      ? "bg-neutral-100 dark:bg-neutral-700"
                      : ""
                  }`}
                >
                  {m.content}
                </span>
              </div>
            ))}

            {bus.busy && <div className="text-xs text-neutral-500 italic">Thinking…</div>}
          </div>

          <div className="flex gap-2 mt-2">
            <input
              className="input"
              placeholder="Ask anything, e.g. 'why didn't I do task 3?'"
              value={msg}
              onChange={(e) => setMsg(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSend();
                }
              }}
              disabled={bus.busy}
            />
            <button className="btn-primary" onClick={handleSend} disabled={bus.busy || !msg.trim()}>
              Send
            </button>
          </div>
        </div>
      )}
    </>
  );
}