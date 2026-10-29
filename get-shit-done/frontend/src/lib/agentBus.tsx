import { createContext, useContext, useEffect, useState } from "react";
import { api } from "../api";

export interface ChatItem {
  role: "user" | "assistant" | "tool";
  content: string;
}

export interface Checkin {
  id: number;
  content: string;
  created_at: string;
}

interface AgentBus {
  messages: ChatItem[];
  checkins: Checkin[];
  busy: boolean;
  open: boolean;
  setOpen: (o: boolean) => void;
  send: (text: string) => Promise<void>;
  unseenCount: number;
}

const Ctx = createContext<AgentBus>(null as any);

export function AgentBusProvider({ children }: { children: React.ReactNode }) {
  const [messages, setMessages] = useState<ChatItem[]>([]);
  const [checkins, setCheckins] = useState<Checkin[]>([]);
  const [seenIds, setSeenIds] = useState<Set<number>>(new Set());
  const [busy, setBusy] = useState(false);
  const [open, setOpen] = useState(false);

  // Poll check-ins
  useEffect(() => {
    const load = async () => {
      const token = localStorage.getItem("gsd_token");
      if (!token) return;
      try {
        const r = await fetch("/api/agent/checkins", {
          headers: { Authorization: `Bearer ${token}` },
        });
        if (r.ok) setCheckins(await r.json());
      } catch {}
    };
    load();
    const t = window.setInterval(load, 60_000);
    return () => window.clearInterval(t);
  }, []);

  // Mark as seen when panel opens
  useEffect(() => {
    if (open && checkins.length > 0) {
      setSeenIds(new Set(checkins.map((c) => c.id)));
    }
  }, [open, checkins]);

  const send = async (text: string) => {
    if (!text.trim() || busy) return;
    setMessages((l) => [...l, { role: "user", content: text }]);
    setBusy(true);
    try {
      const r = await api.chat(text);
      setMessages((l) => [
        ...l,
        { role: "assistant", content: r.reply || "(done)" },
        ...r.tool_calls.map((tc: any) => ({
          role: "tool" as const,
          content: `${tc.name} → ${tc.result}`,
        })),
      ]);
    } catch (e: any) {
      setMessages((l) => [...l, { role: "tool", content: `error: ${e.message}` }]);
    }
    setBusy(false);
  };

  const unseenCount = checkins.filter((c) => !seenIds.has(c.id)).length;

  return (
    <Ctx.Provider value={{ messages, checkins, busy, open, setOpen, send, unseenCount }}>
      {children}
    </Ctx.Provider>
  );
}

export const useAgentBus = () => useContext(Ctx);