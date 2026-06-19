import React from "react";
import { Crosshair } from "@phosphor-icons/react";

export const Header = ({ children }) => {
  return (
    <header
      className="border-b border-neutral-200 bg-white"
      data-testid="app-header"
    >
      <div className="mx-auto max-w-7xl px-6 md:px-12 py-6 flex items-center justify-between gap-6">
        <div className="flex items-center gap-3">
          <div className="h-10 w-10 bg-neutral-900 text-white flex items-center justify-center">
            <Crosshair size={22} weight="bold" />
          </div>
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-500">
              v0.1 · MVP
            </p>
            <h1
              className="font-heading text-xl font-extrabold tracking-tight text-neutral-900 leading-none"
              data-testid="app-title"
            >
              Startup Lead Finder
            </h1>
          </div>
        </div>
        <div className="flex items-center gap-3">{children}</div>
      </div>
    </header>
  );
};
