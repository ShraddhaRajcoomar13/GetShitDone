import { useEffect, useState } from "react";
import { api } from "../api";
import { FoodEntry, MoodEntry } from "../types";

export default function Tracking() {
  const [water, setWater] = useState<{ today_ml: number; goal_ml: number } | null>(null);
  const [mood, setMood] = useState(3);
  const [energy, setEnergy] = useState(3);
  const [moods, setMoods] = useState<MoodEntry[]>([]);
  const [foods, setFoods] = useState<FoodEntry[]>([]);
  const [msg, setMsg] = useState("");

  const refresh = async () => {
    setWater(await api.water());
    setMoods(await api.getMoods(30));
    setFoods(await api.foodList());
  };
  useEffect(() => { refresh(); }, []);

  const logMood = async () => {
    await api.logMood(mood, energy);
    setMsg("Logged."); setTimeout(() => setMsg(""), 1500);
    await refresh();
  };
  const addWater = async (ml: number) => {
    const r = await api.logWater(ml);
    setWater((w) => (w ? { ...w, today_ml: r.today_ml } : { today_ml: r.today_ml, goal_ml: 2000 }));
  };

  const pct = water && water.goal_ml > 0 ? Math.min(100, Math.round((water.today_ml / water.goal_ml) * 100)) : 0;

  return (
    <div className="max-w-2xl space-y-4">
      <h1 className="text-3xl">Body & Mind</h1>

      {/* ---- Mood / Energy ---- */}
      <div className="card">
        <div className="text-sm text-neutral-500 mb-2">Log mood & energy</div>
        <div className="grid grid-cols-2 gap-4">
          <label className="text-sm">
            Mood (1–5): <strong>{mood}</strong>
            <input type="range" min={1} max={5} value={mood}
              onChange={(e) => setMood(Number(e.target.value))} className="w-full" />
          </label>
          <label className="text-sm">
            Energy (1–5): <strong>{energy}</strong>
            <input type="range" min={1} max={5} value={energy}
              onChange={(e) => setEnergy(Number(e.target.value))} className="w-full" />
          </label>
        </div>
        <button className="btn-primary mt-3" onClick={logMood}>Log check-in</button>
        {msg && <span className="ml-2 text-sm text-green-600">{msg}</span>}

        <div className="text-sm text-neutral-500 mt-4 mb-2">Recent check-ins</div>
        <MoodList entries={moods} onChange={refresh} />
      </div>

      {/* ---- Water ---- */}
      <div className="card">
        <div className="flex justify-between items-baseline">
          <div className="text-sm text-neutral-500">Hydration</div>
          <div className="text-sm">{water?.today_ml ?? 0} / {water?.goal_ml ?? 0} ml ({pct}%)</div>
        </div>
        <div className="w-full bg-neutral-200 dark:bg-neutral-700 rounded-full h-3 my-2">
          <div className="bg-accent2 h-3 rounded-full" style={{ width: `${pct}%` }} />
        </div>
        <div className="flex gap-2">
          {[250, 500, 750].map((ml) => (
            <button key={ml} className="btn-ghost border border-neutral-300 dark:border-neutral-600"
              onClick={() => addWater(ml)}>+{ml} ml</button>
          ))}
        </div>
      </div>

      {/* ---- Food ---- */}
      <div className="card space-y-2">
        <div className="text-sm text-neutral-500">Food</div>
        <FoodForm onLogged={refresh} />
        <div className="text-sm text-neutral-500 mt-3">Entries</div>
        <FoodList entries={foods} onChange={refresh} />
      </div>
    </div>
  );
}

/* ---------- Mood list (read / update / delete) ---------- */
function MoodList({ entries, onChange }: { entries: MoodEntry[]; onChange: () => void }) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [m, setM] = useState(3);
  const [e, setE] = useState(3);
  const [confirmDel, setConfirmDel] = useState<number | null>(null);

  const startEdit = (row: MoodEntry) => {
    setEditingId(row.id);
    setM(row.mood ?? 3);
    setE(row.energy ?? 3);
  };
  const save = async (id: number) => {
    await api.updateMood(id, { mood: m, energy: e });
    setEditingId(null);
    onChange();
  };
  const del = async (id: number) => {
    await api.deleteMood(id);
    setConfirmDel(null);
    onChange();
  };

  if (entries.length === 0) {
    return <div className="text-xs text-neutral-500 italic">No entries yet.</div>;
  }

  return (
    <ul className="space-y-1">
      {entries.map((row) => (
        <li key={row.id} className="flex justify-between items-center gap-2 text-sm border-b border-neutral-100 dark:border-neutral-700 py-1">
          {editingId === row.id ? (
            <>
              <div className="flex items-center gap-2 flex-1">
                <span className="text-xs text-neutral-500">
                  {new Date(row.logged_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                </span>
                <label className="text-xs">M <input type="number" min={1} max={5} className="input w-14 inline-block"
                  value={m} onChange={(ev) => setM(Number(ev.target.value))} /></label>
                <label className="text-xs">E <input type="number" min={1} max={5} className="input w-14 inline-block"
                  value={e} onChange={(ev) => setE(Number(ev.target.value))} /></label>
              </div>
              <div className="flex gap-1 shrink-0">
                <button className="text-xs text-red-600 font-medium" onClick={() => save(row.id)}>Save</button>
                <button className="text-xs text-neutral-500" onClick={() => setEditingId(null)}>Cancel</button>
              </div>
            </>
          ) : (
            <>
              <div className="flex-1">
                <span className="text-xs text-neutral-500 mr-2">
                  {new Date(row.logged_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                </span>
                M{row.mood ?? "–"}/E{row.energy ?? "–"}
              </div>
              <div className="flex gap-1 shrink-0">
                {confirmDel === row.id ? (
                  <>
                    <button className="text-xs text-red-600 font-medium" onClick={() => del(row.id)}>Delete</button>
                    <button className="text-xs text-neutral-500" onClick={() => setConfirmDel(null)}>Cancel</button>
                  </>
                ) : (
                  <>
                    <button className="btn-ghost text-xs" onClick={() => startEdit(row)}>Edit</button>
                    <button className="btn-ghost text-xs text-red-600" onClick={() => setConfirmDel(row.id)}>×</button>
                  </>
                )}
              </div>
            </>
          )}
        </li>
      ))}
    </ul>
  );
}

/* ---------- Food list (read / update / delete) ---------- */
function FoodList({ entries, onChange }: { entries: FoodEntry[]; onChange: () => void }) {
  const [editingId, setEditingId] = useState<number | null>(null);
  const [desc, setDesc] = useState("");
  const [mt, setMt] = useState("snack");
  const [confirmDel, setConfirmDel] = useState<number | null>(null);

  const startEdit = (row: FoodEntry) => {
    setEditingId(row.id);
    setDesc(row.description);
    setMt(row.meal_type);
  };
  const save = async (id: number) => {
    await api.updateFood(id, { description: desc, meal_type: mt });
    setEditingId(null);
    onChange();
  };
  const del = async (id: number) => {
    await api.deleteFood(id);
    setConfirmDel(null);
    onChange();
  };

  if (entries.length === 0) {
    return <div className="text-xs text-neutral-500 italic">Nothing logged yet.</div>;
  }

  return (
    <ul className="space-y-1">
      {entries.map((row) => (
        <li key={row.id} className="flex justify-between items-center gap-2 text-sm border-b border-neutral-100 dark:border-neutral-700 py-1">
          {editingId === row.id ? (
            <>
              <div className="flex gap-2 flex-1 items-center">
                <span className="text-xs text-neutral-500">
                  {new Date(row.logged_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                </span>
                <select className="input w-28" value={mt} onChange={(e) => setMt(e.target.value)}>
                  <option>breakfast</option><option>lunch</option><option>dinner</option><option>snack</option>
                </select>
                <input className="input flex-1" value={desc} onChange={(e) => setDesc(e.target.value)} />
              </div>
              <div className="flex gap-1 shrink-0">
                <button className="text-xs text-red-600 font-medium" onClick={() => save(row.id)}>Save</button>
                <button className="text-xs text-neutral-500" onClick={() => setEditingId(null)}>Cancel</button>
              </div>
            </>
          ) : (
            <>
              <div className="flex-1 flex gap-2 items-baseline">
                <span className="text-xs text-neutral-500 w-24">
                  {new Date(row.logged_at).toLocaleString([], { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" })}
                </span>
                <span className="text-xs px-1.5 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700">{row.meal_type}</span>
                <span>{row.description}</span>
              </div>
              <div className="flex gap-1 shrink-0">
                {confirmDel === row.id ? (
                  <>
                    <button className="text-xs text-red-600 font-medium" onClick={() => del(row.id)}>Delete</button>
                    <button className="text-xs text-neutral-500" onClick={() => setConfirmDel(null)}>Cancel</button>
                  </>
                ) : (
                  <>
                    <button className="btn-ghost text-xs" onClick={() => startEdit(row)}>Edit</button>
                    <button className="btn-ghost text-xs text-red-600" onClick={() => setConfirmDel(row.id)}>×</button>
                  </>
                )}
              </div>
            </>
          )}
        </li>
      ))}
    </ul>
  );
}

function FoodForm({ onLogged }: { onLogged: () => void }) {
  const [description, setDescription] = useState("");
  const [mealType, setMealType] = useState("snack");

  const save = async () => {
    if (!description.trim()) return;
    await api.logFood(mealType, description);
    setDescription("");
    onLogged();
  };

  return (
    <div className="flex gap-2">
      <select className="input w-32" value={mealType} onChange={(e) => setMealType(e.target.value)}>
        <option>breakfast</option><option>lunch</option><option>dinner</option><option>snack</option>
      </select>
      <input className="input" placeholder="What did you eat?"
        value={description} onChange={(e) => setDescription(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && save()} />
      <button className="btn-primary" onClick={save}>Log</button>
    </div>
  );
}