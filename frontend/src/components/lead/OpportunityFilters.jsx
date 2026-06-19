import React from "react";
import { Input } from "../ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Button } from "../ui/button";
import { X } from "@phosphor-icons/react";

const ANY = "__any__";

const selectClass =
  "rounded-none border-neutral-300 focus:ring-1 focus:ring-[#002FA7] focus:ring-offset-0 h-10 text-sm";
const inputClass =
  "rounded-none border-neutral-300 focus-visible:ring-1 focus-visible:ring-[#002FA7] focus-visible:ring-offset-0 h-10 text-sm";

const Field = ({ label, children }) => (
  <div className="flex flex-col gap-1.5 min-w-0">
    <label className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500 font-bold">
      {label}
    </label>
    {children}
  </div>
);

export const OpportunityFilters = ({
  filters,
  setFilters,
  meta,
  onClear,
  resultCount,
}) => {
  const update = (key, value) => setFilters({ ...filters, [key]: value });

  return (
    <div
      className="border border-neutral-200 bg-neutral-50 p-4 md:p-6 mb-6"
      data-testid="opportunity-filters"
    >
      <div className="flex items-center justify-between mb-4 gap-3">
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-500 font-bold">
          Filters
        </p>
        <div className="flex items-center gap-3">
          <span
            className="text-xs text-neutral-500 font-mono"
            data-testid="opportunity-result-count"
          >
            {resultCount} result{resultCount === 1 ? "" : "s"}
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClear}
            data-testid="clear-filters-btn"
            className="rounded-none h-7 text-xs gap-1.5 hover:bg-neutral-200"
          >
            <X size={12} weight="bold" />
            Clear
          </Button>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-3">
        <Field label="Search Company">
          <Input
            placeholder="Acme…"
            value={filters.search}
            onChange={(e) => update("search", e.target.value)}
            data-testid="filter-search-input"
            className={inputClass}
          />
        </Field>

        <Field label="Skills (comma sep.)">
          <Input
            placeholder="Python, SQL"
            value={filters.skillsRaw}
            onChange={(e) => update("skillsRaw", e.target.value)}
            data-testid="filter-skills-input"
            className={inputClass}
          />
        </Field>

        <Field label="Role">
          <Input
            placeholder="Data Analyst"
            value={filters.role}
            onChange={(e) => update("role", e.target.value)}
            data-testid="filter-role-input"
            className={inputClass}
          />
        </Field>

        <Field label="Location">
          <Input
            placeholder="Remote / Pune"
            value={filters.location}
            onChange={(e) => update("location", e.target.value)}
            data-testid="filter-location-input"
            className={inputClass}
          />
        </Field>

        <Field label="Type">
          <Select
            value={filters.employment_type || ANY}
            onValueChange={(v) => update("employment_type", v === ANY ? "" : v)}
          >
            <SelectTrigger className={selectClass} data-testid="filter-type-select">
              <SelectValue placeholder="Any" />
            </SelectTrigger>
            <SelectContent className="rounded-none">
              <SelectItem value={ANY}>Any</SelectItem>
              {(meta?.employment_types || []).map((t) => (
                <SelectItem key={t} value={t} data-testid={`filter-type-${t}`}>
                  {t}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>

        <Field label="Work Mode">
          <Select
            value={filters.work_mode || ANY}
            onValueChange={(v) => update("work_mode", v === ANY ? "" : v)}
          >
            <SelectTrigger className={selectClass} data-testid="filter-mode-select">
              <SelectValue placeholder="Any" />
            </SelectTrigger>
            <SelectContent className="rounded-none">
              <SelectItem value={ANY}>Any</SelectItem>
              {(meta?.work_modes || []).map((m) => (
                <SelectItem key={m} value={m} data-testid={`filter-mode-${m}`}>
                  {m}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>

        <Field label="Status">
          <Select
            value={filters.status || ANY}
            onValueChange={(v) => update("status", v === ANY ? "" : v)}
          >
            <SelectTrigger className={selectClass} data-testid="filter-status-select">
              <SelectValue placeholder="Any" />
            </SelectTrigger>
            <SelectContent className="rounded-none">
              <SelectItem value={ANY}>Any</SelectItem>
              {(meta?.statuses || []).map((s) => (
                <SelectItem key={s} value={s} data-testid={`filter-status-${s}`}>
                  {s}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Field>

        <Field label="Freshness">
          <Select
            value={filters.freshness || ANY}
            onValueChange={(v) => update("freshness", v === ANY ? "" : v)}
          >
            <SelectTrigger className={selectClass} data-testid="filter-freshness-select">
              <SelectValue placeholder="Any time" />
            </SelectTrigger>
            <SelectContent className="rounded-none">
              <SelectItem value={ANY}>Any time</SelectItem>
              <SelectItem value="24h" data-testid="filter-freshness-24h">Last 24 hours</SelectItem>
              <SelectItem value="3d" data-testid="filter-freshness-3d">Last 3 days</SelectItem>
              <SelectItem value="7d" data-testid="filter-freshness-7d">Last 7 days</SelectItem>
              <SelectItem value="30d" data-testid="filter-freshness-30d">Last 30 days</SelectItem>
            </SelectContent>
          </Select>
        </Field>

        <Field label="Sort by">
          <Select
            value={filters.sort}
            onValueChange={(v) => update("sort", v)}
          >
            <SelectTrigger className={selectClass} data-testid="filter-sort-select">
              <SelectValue />
            </SelectTrigger>
            <SelectContent className="rounded-none">
              <SelectItem value="newest">Newest</SelectItem>
              <SelectItem value="oldest">Oldest</SelectItem>
              <SelectItem value="company_az">Company A→Z</SelectItem>
              <SelectItem value="company_za">Company Z→A</SelectItem>
              <SelectItem value="role_az">Role A→Z</SelectItem>
            </SelectContent>
          </Select>
        </Field>
      </div>
    </div>
  );
};
