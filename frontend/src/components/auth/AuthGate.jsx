import React from "react";
import { useAuth } from "../../contexts/AuthContext";
import AuthPage from "./AuthPage";

export const AuthGate = ({ children }) => {
  const { user } = useAuth();

  if (user === undefined) {
    return (
      <div
        className="min-h-screen flex items-center justify-center bg-white"
        data-testid="auth-loading"
      >
        <div className="h-10 w-10 border-2 border-neutral-200 border-t-neutral-900 animate-spin rounded-full" />
      </div>
    );
  }

  if (!user) return <AuthPage />;
  return children;
};
