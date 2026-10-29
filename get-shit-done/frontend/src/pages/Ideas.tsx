import { useEffect, useState } from "react";
import { api } from "../api";

interface Idea {
  id: number;
  content: string;
  tags: string;
  status: string;
  created_at: string;
}

export default function Ideas() {
  const [ideas, setIdeas] = useState<Idea[]>([]);
  const [text, setText] = useState("");
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editContent, setEditContent] = useState("");
  const [editTags, setEditTags] = useState("");
  const [confirmDelete, setConfirmDelete] = useState<number | null>(null);

  const refresh = async () => setIdeas(await api.ideas());
  useEffect(() => { refresh(); }, []);

  const capture = async () => {
    if (!text.trim()) return;
    await api.addIdea(text.trim());
    setText("");
    await refresh();
  };

  const convert = async (id: number) => { await api.ideaToTask(id); await refresh(); };
  const archive = async (id: number) => {
    const token = localStorage.getItem("gsd_token");
    await fetch(`/api/ideas/${id}/archive`, {
      method: "POST", headers: { Authorization: `Bearer ${token}` },
    });
    await refresh();
  };
  const del = async (id: number) => {
    await api.deleteIdea(id);
    setConfirmDelete(null);
    await refresh();
  };
  const startEdit = (i: Idea) => {
    setEditingId(i.id);
    setEditContent(i.content);
    setEditTags(i.tags);
  };
  const saveEdit = async (id: number) => {
    await api.updateIdea(id, { content: editContent, tags: editTags });
    setEditingId(null);
    await refresh();
  };

  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-3xl">Ideas Inbox</h1>

      <div className="card flex gap-2">
        <input className="input" placeholder="Capture a thought… (Enter to save)"
          value={text} onChange={(e) => setText(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && capture()} autoFocus />
        <button className="btn-primary" onClick={capture}>Capture</button>
      </div>

      <div className="space-y-2">
        {ideas.length === 0 && <div className="text-neutral-500">Nothing captured yet.</div>}
        {ideas.map((i) => (
          <div key={i.id} className="card">
            {editingId === i.id ? (
              <div className="space-y-2">
                <textarea className="input" rows={2}
                  value={editContent} onChange={(e) => setEditContent(e.target.value)} />
                <input className="input" placeholder="tags (optional)"
                  value={editTags} onChange={(e) => setEditTags(e.target.value)} />
                <div className="flex gap-2 justify-end">
                  <button className="btn-ghost text-xs" onClick={() => setEditingId(null)}>Cancel</button>
                  <button className="btn-primary text-xs" onClick={() => saveEdit(i.id)}>Save</button>
                </div>
              </div>
            ) : (
              <div className="flex justify-between items-start gap-2">
                <div className="min-w-0">
                  <div className={i.status === "archived" ? "line-through text-neutral-500" : ""}>{i.content}</div>
                  <div className="text-xs text-neutral-500 mt-1">
                    {i.status} · {new Date(i.created_at).toLocaleString()}
                    {i.tags && ` · ${i.tags}`}
                  </div>
                </div>
                <div className="flex flex-col items-end gap-1 shrink-0">
                  {confirmDelete === i.id ? (
                    <div className="flex gap-1">
                      <button className="text-xs text-red-600 font-medium" onClick={() => del(i.id)}>Delete</button>
                      <button className="text-xs text-neutral-500" onClick={() => setConfirmDelete(null)}>Cancel</button>
                    </div>
                  ) : (
                    <div className="flex gap-1 flex-wrap justify-end">
                      <button className="btn-ghost text-xs" onClick={() => startEdit(i)}>Edit</button>
                      {i.status === "inbox" && (
                        <>
                          <button className="btn-ghost text-xs" onClick={() => convert(i.id)}>→ Task</button>
                          <button className="btn-ghost text-xs" onClick={() => archive(i.id)}>Archive</button>
                        </>
                      )}
                      <button className="btn-ghost text-xs text-red-600" onClick={() => setConfirmDelete(i.id)}>×</button>
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