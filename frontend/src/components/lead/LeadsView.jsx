import React, { useCallback, useEffect, useMemo, useState } from "react";
import { MagnifyingGlass, DownloadSimple, X } from "@phosphor-icons/react";
import { Input } from "../ui/input";
import { Button } from "../ui/button";
import { toast } from "sonner";
import { companiesApi } from "../../lib/api";
import { AddCompanyDialog } from "./AddCompanyDialog";
import { CompaniesTable } from "./CompaniesTable";
import { StatsBar } from "./StatsBar";

const useDebounced = (value, delay = 250) => {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
};

export const LeadsView = ({ refreshSignal, onStatsChange }) => {
  const [companies, setCompanies] = useState([]);
  const [stats, setStats] = useState({ total: 0, with_email: 0, with_website: 0 });
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const debouncedSearch = useDebounced(search, 250);

  const fetchAll = useCallback(async (q = "") => {
    setLoading(true);
    try {
      const [list, s] = await Promise.all([
        companiesApi.list(q),
        companiesApi.stats(),
      ]);
      setCompanies(list);
      setStats(s);
      onStatsChange?.(s);
    } catch {
      toast.error("Failed to load leads");
    } finally {
      setLoading(false);
    }
  }, [onStatsChange]);

  useEffect(() => {
    fetchAll(debouncedSearch);
  }, [debouncedSearch, fetchAll, refreshSignal]);

  const handleExport = () => {
    if (!companies.length) {
      toast.error("No companies to export");
      return;
    }
    window.location.href = companiesApi.exportUrl();
  };

  const headingCount = useMemo(
    () =>
      debouncedSearch
        ? `${companies.length} match${companies.length === 1 ? "" : "es"}`
        : `${companies.length} lead${companies.length === 1 ? "" : "s"}`,
    [companies.length, debouncedSearch],
  );

  return (
    <section data-testid="leads-view">
      <StatsBar stats={stats} />

      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mt-8 mb-8">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-500 mb-2">
            Pipeline
          </p>
          <h2 className="font-heading text-3xl md:text-4xl font-extrabold tracking-tight">
            Your Leads
          </h2>
          <p className="text-sm text-neutral-500 mt-2" data-testid="results-count">
            {headingCount}
          </p>
        </div>

        <div className="flex items-center gap-2 flex-wrap">
          <div className="relative w-full sm:w-72">
            <MagnifyingGlass
              size={16}
              weight="bold"
              className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400 pointer-events-none"
            />
            <Input
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Search companies…"
              data-testid="company-search-input"
              className="pl-9 pr-9 rounded-none border-neutral-300 focus-visible:ring-1 focus-visible:ring-[#002FA7] focus-visible:ring-offset-0 h-10"
            />
            {search && (
              <button
                onClick={() => setSearch("")}
                aria-label="Clear search"
                data-testid="clear-search-btn"
                className="absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400 hover:text-neutral-900"
              >
                <X size={14} weight="bold" />
              </button>
            )}
          </div>
          <Button
            variant="outline"
            onClick={handleExport}
            data-testid="export-csv-btn"
            className="rounded-none border-neutral-300 hover:bg-neutral-100 h-10 px-4 gap-2 font-semibold"
          >
            <DownloadSimple size={16} weight="bold" />
            Export CSV
          </Button>
          <AddCompanyDialog onCreated={() => fetchAll(debouncedSearch)} />
        </div>
      </div>

      <CompaniesTable
        companies={companies}
        loading={loading}
        search={debouncedSearch}
        onChanged={() => fetchAll(debouncedSearch)}
      />
    </section>
  );
};
