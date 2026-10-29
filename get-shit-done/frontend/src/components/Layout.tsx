import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../auth";
import AgentChat from "./AgentChat";

const links = [
  ["/", "Today"], ["/planner", "Planner"], ["/goals", "Goals"],
  ["/focus", "Focus"], ["/ideas", "Ideas"], ["/tracking", "Body"],
  ["/progress", "Progress"], ["/settings", "Settings"],
] as const;

export default function Layout() {
  const { logout, email } = useAuth();
  return (
    <div className="min-h-screen flex">
      <aside className="w-56 shrink-0 border-r border-neutral-200 dark:border-neutral-700 p-4 flex flex-col gap-2">
        <div className="font-serif text-xl mb-4">GET SHIT DONE</div>
        {links.map(([to, label]) => (
          <NavLink
            key={to} to={to} end={to === "/"}
            className={({ isActive }) =>
              `px-3 py-2 rounded-lg ${isActive ? "bg-accent text-white" : "hover:bg-neutral-100 dark:hover:bg-neutral-800"}`
            }
          >{label}</NavLink>
        ))}
        <div className="mt-auto text-xs text-neutral-500">
          <div className="mb-2">{email}</div>
          <button className="btn-ghost text-xs" onClick={logout}>Sign out</button>
        </div>
      </aside>
      <main className="flex-1 p-6 overflow-auto"><Outlet /></main>
      <AgentChat />
    </div>
  );
}