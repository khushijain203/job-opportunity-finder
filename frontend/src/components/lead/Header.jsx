import React, { useState } from "react";
import { Crosshair, SignOut, UserCircle } from "@phosphor-icons/react";
import { useAuth } from "../../contexts/AuthContext";
import { ProfileDialog } from "./ProfileDialog";

export const Header = ({ children }) => {
  const { user, logout } = useAuth();
  const [profileOpen, setProfileOpen] = useState(false);

  return (
    <>
      <header
        className="border-b border-neutral-200 bg-white"
        data-testid="app-header"
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 md:px-12 py-5 md:py-6 flex flex-wrap items-center justify-between gap-3 sm:gap-6">
          <div className="flex items-center gap-3 min-w-0">
            <div className="h-9 w-9 sm:h-10 sm:w-10 bg-neutral-900 text-white flex items-center justify-center shrink-0">
              <Crosshair size={20} weight="bold" />
            </div>
            <div className="min-w-0">
              <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-500">
                v0.2 · {user?.is_demo ? "demo account" : "multi-user"}
              </p>
              <h1
                className="font-heading text-lg sm:text-xl font-extrabold tracking-tight text-neutral-900 leading-none truncate"
                data-testid="app-title"
              >
                Startup Lead Finder
              </h1>
            </div>
          </div>
          <div className="flex items-center gap-2 sm:gap-3 flex-wrap justify-end">
            {children}
            {user && (
              <>
                <button
                  type="button"
                  onClick={() => setProfileOpen(true)}
                  data-testid="open-profile-btn"
                  className="inline-flex items-center gap-2 h-10 px-3 border border-neutral-300 hover:bg-neutral-100 transition-colors text-sm font-semibold"
                  title="Edit profile"
                >
                  <UserCircle size={16} weight="bold" />
                  <span className="hidden sm:inline truncate max-w-[160px]" data-testid="header-user-name">
                    {user.full_name || user.email}
                  </span>
                </button>
                <button
                  type="button"
                  onClick={logout}
                  data-testid="logout-btn"
                  className="inline-flex items-center gap-2 h-10 px-3 border border-neutral-300 hover:bg-neutral-100 transition-colors text-sm font-semibold"
                  title="Log out"
                >
                  <SignOut size={16} weight="bold" />
                  <span className="hidden sm:inline">Log out</span>
                </button>
              </>
            )}
          </div>
        </div>
      </header>

      <ProfileDialog open={profileOpen} onClose={() => setProfileOpen(false)} />
    </>
  );
};
