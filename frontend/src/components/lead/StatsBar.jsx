import React from "react";

const Stat = ({ label, value, testId }) => (
  <div className="flex flex-col gap-2 px-6 py-5 border-r border-neutral-200 last:border-r-0 min-w-[180px]">
    <span className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-500">
      {label}
    </span>
    <span
      className="font-heading text-3xl font-extrabold tracking-tight text-neutral-900"
      data-testid={testId}
    >
      {value}
    </span>
  </div>
);

export const StatsBar = ({ stats }) => {
  return (
    <section
      className="border-b border-neutral-200 bg-neutral-50"
      data-testid="stats-bar"
    >
      <div className="mx-auto max-w-7xl px-6 md:px-12">
        <div className="flex flex-wrap divide-y md:divide-y-0">
          <Stat label="Total Leads" value={stats?.total ?? 0} testId="stat-total" />
          <Stat label="With Email" value={stats?.with_email ?? 0} testId="stat-with-email" />
          <Stat label="With Website" value={stats?.with_website ?? 0} testId="stat-with-website" />
        </div>
      </div>
    </section>
  );
};
