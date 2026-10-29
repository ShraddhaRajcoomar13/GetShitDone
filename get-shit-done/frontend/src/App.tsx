import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider, useAuth } from "./auth";
import { ThemeProvider } from "./lib/theme";
import { AgentBusProvider } from "./lib/agentBus";
import Layout from "./components/Layout";
import Login from "./pages/Login";
import Today from "./pages/Today";
import Planner from "./pages/Planner";
import Goals from "./pages/Goals";
import Focus from "./pages/Focus";
import Ideas from "./pages/Ideas";
import Tracking from "./pages/Tracking";
import Progress from "./pages/Progress";
import Settings from "./pages/Settings";

function Protected({ children }: { children: React.ReactNode }) {
  const { email, loading } = useAuth();
  if (loading) return <div className="p-8">Loading…</div>;
  if (!email) return <Navigate to="/login" />;
  return <>{children}</>;
}

export default function App() {
  return (
    <AuthProvider>
      <ThemeProvider>
        <AgentBusProvider>
          <BrowserRouter>
            <Routes>
              <Route path="/login" element={<Login />} />
              <Route element={<Protected><Layout /></Protected>}>
                <Route path="/" element={<Today />} />
                <Route path="/planner" element={<Planner />} />
                <Route path="/goals" element={<Goals />} />
                <Route path="/focus" element={<Focus />} />
                <Route path="/ideas" element={<Ideas />} />
                <Route path="/tracking" element={<Tracking />} />
                <Route path="/progress" element={<Progress />} />
                <Route path="/settings" element={<Settings />} />
              </Route>
            </Routes>
          </BrowserRouter>
        </AgentBusProvider>
      </ThemeProvider>
    </AuthProvider>
  );
}