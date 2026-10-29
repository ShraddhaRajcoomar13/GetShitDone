import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../auth";

export default function Login() {
  const { login, register } = useAuth();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState("");

  const submit = async (isReg: boolean) => {
    try {
      if (isReg) await register(email, password);
      else await login(email, password);
      nav("/");
    } catch (e: any) { setErr(e.message); }
  };

  return (
    <div className="min-h-screen flex items-center justify-center">
      <div className="card w-96">
        <h1 className="text-2xl mb-4">GET SHIT DONE</h1>
        <input className="input mb-2" placeholder="email" value={email} onChange={(e) => setEmail(e.target.value)} />
        <input className="input mb-4" type="password" placeholder="password" value={password} onChange={(e) => setPassword(e.target.value)} />
        {err && <div className="text-red-500 text-sm mb-2">{err}</div>}
        <div className="flex gap-2">
          <button className="btn-primary flex-1" onClick={() => submit(false)}>Sign in</button>
          <button className="btn-ghost flex-1" onClick={() => submit(true)}>Register</button>
        </div>
      </div>
    </div>
  );
}