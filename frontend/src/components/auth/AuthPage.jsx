import React, { useState } from "react";
import { Crosshair, EyeSlash, Eye } from "@phosphor-icons/react";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { useAuth } from "../../contexts/AuthContext";

const inputClass =
  "rounded-none border-neutral-300 focus-visible:ring-1 focus-visible:ring-[#002FA7] focus-visible:ring-offset-0 h-11";

const TabButton = ({ active, children, onClick, testId }) => (
  <button
    onClick={onClick}
    data-testid={testId}
    className={`flex-1 py-3 text-sm font-semibold tracking-tight transition-colors duration-150 border-b-2 ${
      active
        ? "border-neutral-900 text-neutral-900"
        : "border-transparent text-neutral-500 hover:text-neutral-900"
    }`}
    type="button"
  >
    {children}
  </button>
);

export default function AuthPage() {
  const [mode, setMode] = useState("login");
  const [showPw, setShowPw] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState(null);
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
  });
  const { login, register } = useAuth();

  const set = (k, v) => setForm({ ...form, [k]: v });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    setSubmitting(true);
    let res;
    if (mode === "login") {
      res = await login(form.email.trim(), form.password);
    } else {
      res = await register({
        full_name: form.full_name.trim(),
        email: form.email.trim(),
        password: form.password,
      });
    }
    setSubmitting(false);
    if (!res.ok) {
      setError(res.error);
    }
  };

  return (
    <div
      className="min-h-screen bg-white flex items-center justify-center p-6"
      data-testid="auth-page"
    >
      <div className="w-full max-w-md">
        <div className="flex items-center gap-3 mb-8 justify-center">
          <div className="h-10 w-10 bg-neutral-900 text-white flex items-center justify-center">
            <Crosshair size={22} weight="bold" />
          </div>
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-500">
              v0.2 · multi-user
            </p>
            <h1 className="font-heading text-xl font-extrabold tracking-tight leading-none">
              Startup Lead Finder
            </h1>
          </div>
        </div>

        <div className="border border-neutral-200">
          <div className="flex border-b border-neutral-200">
            <TabButton
              active={mode === "login"}
              onClick={() => {
                setMode("login");
                setError(null);
              }}
              testId="auth-tab-login"
            >
              Sign In
            </TabButton>
            <TabButton
              active={mode === "register"}
              onClick={() => {
                setMode("register");
                setError(null);
              }}
              testId="auth-tab-register"
            >
              Create Account
            </TabButton>
          </div>

          <form onSubmit={submit} className="p-6 space-y-5">
            {mode === "register" && (
              <div className="space-y-2">
                <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                  Full Name
                </Label>
                <Input
                  data-testid="auth-fullname-input"
                  value={form.full_name}
                  onChange={(e) => set("full_name", e.target.value)}
                  placeholder="Alex Park"
                  className={inputClass}
                  required
                  autoComplete="name"
                />
              </div>
            )}

            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Email
              </Label>
              <Input
                data-testid="auth-email-input"
                type="email"
                value={form.email}
                onChange={(e) => set("email", e.target.value)}
                placeholder="you@example.com"
                className={inputClass}
                required
                autoComplete="email"
                autoFocus
              />
            </div>

            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Password
              </Label>
              <div className="relative">
                <Input
                  data-testid="auth-password-input"
                  type={showPw ? "text" : "password"}
                  value={form.password}
                  onChange={(e) => set("password", e.target.value)}
                  placeholder={mode === "register" ? "Min 8, Aa & a digit" : "Your password"}
                  className={`${inputClass} pr-10`}
                  required
                  autoComplete={mode === "register" ? "new-password" : "current-password"}
                />
                <button
                  type="button"
                  onClick={() => setShowPw((v) => !v)}
                  aria-label={showPw ? "Hide password" : "Show password"}
                  data-testid="auth-toggle-password"
                  className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-900"
                >
                  {showPw ? <EyeSlash size={16} weight="bold" /> : <Eye size={16} weight="bold" />}
                </button>
              </div>
              {mode === "register" && (
                <p className="text-[11px] text-neutral-500 font-mono">
                  At least 8 chars, with uppercase, lowercase, and a number.
                </p>
              )}
            </div>

            {error && (
              <div
                className="border border-[#E60000] bg-red-50 text-[#CC0000] px-3 py-2 text-xs font-mono"
                data-testid="auth-error"
              >
                {error}
              </div>
            )}

            <Button
              type="submit"
              disabled={submitting}
              data-testid="auth-submit-btn"
              className="w-full rounded-none bg-neutral-900 hover:bg-neutral-700 text-white h-11 font-semibold"
            >
              {submitting
                ? mode === "login"
                  ? "Signing in…"
                  : "Creating account…"
                : mode === "login"
                  ? "Sign In"
                  : "Create Account"}
            </Button>
          </form>

          <div className="px-6 pb-6 -mt-2 text-center">
            <p className="text-xs text-neutral-500">
              {mode === "login" ? (
                <>
                  New here?{" "}
                  <button
                    type="button"
                    onClick={() => setMode("register")}
                    data-testid="auth-switch-to-register"
                    className="text-neutral-900 font-semibold hover:underline"
                  >
                    Create an account
                  </button>
                </>
              ) : (
                <>
                  Already have an account?{" "}
                  <button
                    type="button"
                    onClick={() => setMode("login")}
                    data-testid="auth-switch-to-login"
                    className="text-neutral-900 font-semibold hover:underline"
                  >
                    Sign in
                  </button>
                </>
              )}
            </p>
          </div>
        </div>

        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-400 text-center mt-6">
          Demo · demo@leadfinder.app · Demo1234!
        </p>
      </div>
    </div>
  );
}
