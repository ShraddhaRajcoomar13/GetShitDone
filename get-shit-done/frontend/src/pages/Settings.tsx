import { useEffect, useState } from "react";
import { api } from "../api";
import { Prefs } from "../types";
import { useTheme } from "../lib/theme";
import { fileToDataUrl } from "../lib/image";

const STYLES: { value: string; label: string; desc: string }[] = [
  { value: "gentle", label: "Gentle", desc: "Warm, reassuring, no shame." },
  { value: "supportive_firm", label: "Supportive but firm", desc: "Kind but direct. Reminds you of commitments." },
  { value: "strict", label: "Strict accountability", desc: "Blunt and direct. Expects an explicit decision." },
  { value: "drill_sergeant", label: "Drill sergeant", desc: "High-energy, commanding, motivational." },
  { value: "analytical", label: "Analytical coach", desc: "Examines patterns and bottlenecks." },
  { value: "custom", label: "Custom", desc: "Define your own tone below." },
];

export default function Settings() {
  const [p, setP] = useState<Prefs | null>(null);
  const [msg, setMsg] = useState("");
  const t = useTheme(); 

  useEffect(() => { (async () => setP(await api.prefs()))(); }, []);

  const save = async (patch: Partial<Prefs>) => {
    if (!p) return;
    const next = await api.updatePrefs(patch);
    setP(next);
    setMsg("Saved.");
    setTimeout(() => setMsg(""), 1200);
  };

  if (!p) return <div>Loading…</div>;

  return (
    <div className="max-w-3xl space-y-4">
      <h1 className="text-3xl">Agent & Settings</h1>

      <div className="card">
        <div className="text-sm text-neutral-500 mb-2">Coaching style</div>
        <div className="grid md:grid-cols-2 gap-2">
          {STYLES.map((s) => (
            <button
              key={s.value}
              onClick={() => save({ coaching_style: s.value } as any)}
              className={`text-left p-3 rounded-lg border ${
                p.coaching_style === s.value
                  ? "border-accent bg-orange-50 dark:bg-neutral-800"
                  : "border-neutral-200 dark:border-neutral-700"
              }`}
            >
              <div className="font-medium">{s.label}</div>
              <div className="text-xs text-neutral-500">{s.desc}</div>
            </button>
          ))}
        </div>
        {p.coaching_style === "custom" && (
          <textarea
            className="input mt-3"
            rows={4}
            placeholder="Describe the tone you want…"
            value={p.custom_instructions}
            onChange={(e) => setP({ ...p, custom_instructions: e.target.value })}
            onBlur={() => save({ custom_instructions: p.custom_instructions })}
          />
        )}
      </div>

      {/* ---- Appearance ---- */}
      <div className="card space-y-4">
        <div className="text-sm text-neutral-500">Theme</div>
        <div className="grid grid-cols-2 md:grid-cols-3 gap-2">
          {Object.entries(t.themes).map(([name, def]: [string, any]) => (
            <button
              key={name}
              onClick={() => t.setName(name)}
              className={`p-3 rounded-lg border-2 text-left ${
                t.theme === name ? "border-accent" : "border-transparent"
              }`}
              style={{ background: `rgb(${def.vars.paper})`, color: `rgb(${def.vars.ink})` }}
            >
              <div className="font-medium">{def.label}</div>
              <div className="text-xs opacity-70">{def.dark ? "Dark" : "Light"}</div>
            </button>
          ))}
        </div>

        <div>
          <div className="text-sm text-neutral-500 mb-2">Accent color</div>
          <div className="flex gap-2 items-center">
            <input
              type="color"
              value={t.accentColor || "#c7703c"}
              onChange={(e) => t.setAccent(e.target.value)}
              className="w-12 h-10 rounded cursor-pointer border border-neutral-300 dark:border-neutral-600"
            />
            <button className="btn-ghost text-xs" onClick={() => t.setAccent("")}>
              Use theme default
            </button>
            {t.accentColor && (
              <span className="text-xs text-neutral-500">{t.accentColor}</span>
            )}
          </div>
        </div>
      </div>

      {/* ---- Background image ---- */}
      <div className="card space-y-3">
        <div className="text-sm text-neutral-500">Background image</div>

        <input
          className="input"
          placeholder="Paste an image URL (https://…)"
          value={t.bgImage.startsWith("data:") ? "" : t.bgImage}
          onChange={(e) => t.setBgImage(e.target.value)}
        />

        <div className="flex items-center gap-2 flex-wrap">
          <label className="btn-ghost text-xs cursor-pointer border border-neutral-300 dark:border-neutral-600">
            Upload image
            <input
              type="file"
              accept="image/*"
              className="hidden"
              onChange={async (e) => {
                const f = e.target.files?.[0];
                if (!f) return;
                try {
                  const dataUrl = await fileToDataUrl(f);
                  t.setBgImage(dataUrl);
                } catch {
                  alert("Could not read that image.");
                }
                (e.target as HTMLInputElement).value = "";
              }}
            />
          </label>
          {t.bgImage && (
            <button className="btn-ghost text-xs" onClick={() => t.setBgImage("")}>
              Remove background
            </button>
          )}
          <span className="text-xs text-neutral-500">
            Uploaded images are resized locally — no server storage.
          </span>
        </div>

        {t.bgImage && (
          <>
            <div className="flex items-center gap-2">
              <span className="text-sm whitespace-nowrap">Visibility</span>
              <input
                type="range"
                min={0}
                max={100}
                value={t.bgOpacity}
                onChange={(e) => t.setBgOpacity(Number(e.target.value))}
                className="flex-1"
              />
              <span className="text-sm w-10 text-right">{t.bgOpacity}%</span>
            </div>
            <div
              className="w-full h-24 rounded-lg border border-neutral-300 dark:border-neutral-600"
              style={{
                backgroundImage: `url("${t.bgImage.replace(/"/g, '\\"')}")`,
                backgroundSize: "cover",
                backgroundPosition: "center",
                opacity: t.bgOpacity / 100,
              }}
            />
          </>
        )}
      </div>

      <div className="card space-y-3">
        <div className="text-sm text-neutral-500">Hours & limits</div>
        <label className="block text-sm">
          Work hours start
          <input className="input mt-1" value={p.work_hours_start}
            onChange={(e) => setP({ ...p, work_hours_start: e.target.value })}
            onBlur={() => save({ work_hours_start: p.work_hours_start })} />
        </label>
        <label className="block text-sm">
          Work hours end
          <input className="input mt-1" value={p.work_hours_end}
            onChange={(e) => setP({ ...p, work_hours_end: e.target.value })}
            onBlur={() => save({ work_hours_end: p.work_hours_end })} />
        </label>
        <label className="block text-sm">
          Daily hydration goal (ml)
          <input type="number" className="input mt-1" value={p.hydration_goal_ml}
            onChange={(e) => setP({ ...p, hydration_goal_ml: Number(e.target.value) })}
            onBlur={() => save({ hydration_goal_ml: p.hydration_goal_ml })} />
        </label>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={p.motivational_prompts}
            onChange={(e) => save({ motivational_prompts: e.target.checked })} />
          Enable motivational prompts
        </label>
      </div>

      <div className="card">
        <div className="text-sm text-neutral-500 mb-2">Autonomy</div>
        <select className="input" value={p.autonomy_level}
          onChange={(e) => save({ autonomy_level: e.target.value })}>
          <option value="read">Read-only: agent can only report, never act</option>
          <option value="confirm">Confirm (recommended): agent asks before acting</option>
          <option value="autonomous">Autonomous: agent acts on routine actions</option>
        </select>
      </div>

      {msg && <div className="text-sm text-green-600">{msg}</div>}
    </div>
  );
}