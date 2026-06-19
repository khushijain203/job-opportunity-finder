import React, { useState } from "react";
import { Header } from "./Header";
import { LeadsView } from "./LeadsView";
import { OpportunitiesView } from "./OpportunitiesView";

const TABS = [
  { id: "leads", label: "Leads" },
  { id: "opportunities", label: "Find Opportunities" },
];

export default function LeadFinder() {
  const [tab, setTab] = useState("leads");
  // Bumping this signal triggers a re-fetch in LeadsView (e.g. after "Save to Leads")
  const [leadsRefresh, setLeadsRefresh] = useState(0);

  return (
    <div
      className="min-h-screen bg-white text-neutral-900 font-body"
      data-testid="lead-finder-root"
    >
      <Header />

      <nav
        className="border-b border-neutral-200 bg-white"
        data-testid="primary-tabs"
      >
        <div className="mx-auto max-w-7xl px-4 sm:px-6 md:px-12 flex gap-2 overflow-x-auto">
          {TABS.map((t) => {
            const active = tab === t.id;
            return (
              <button
                key={t.id}
                onClick={() => setTab(t.id)}
                data-testid={`tab-${t.id}`}
                className={`relative px-4 py-3 -mb-px text-sm font-semibold tracking-tight transition-colors duration-150 whitespace-nowrap border-b-2 ${
                  active
                    ? "border-neutral-900 text-neutral-900"
                    : "border-transparent text-neutral-500 hover:text-neutral-900"
                }`}
              >
                {t.label}
              </button>
            );
          })}
        </div>
      </nav>

      <main className="mx-auto max-w-7xl px-4 sm:px-6 md:px-12 py-10 md:py-14">
        {tab === "leads" && (
          <LeadsView refreshSignal={leadsRefresh} />
        )}
        {tab === "opportunities" && (
          <OpportunitiesView onLeadsChanged={() => setLeadsRefresh((n) => n + 1)} />
        )}

        <footer className="mt-16 pt-8 border-t border-neutral-200 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3">
          <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-500">
            Startup Lead Finder · MVP
          </p>
          <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-400">
            Next: discovery · enrichment · AI scoring · outreach
          </p>
        </footer>
      </main>
    </div>
  );
}
