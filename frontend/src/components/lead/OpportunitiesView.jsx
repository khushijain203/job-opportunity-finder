import React, { useCallback, useEffect, useMemo, useState } from "react";
import { Database } from "@phosphor-icons/react";
import { Button } from "../ui/button";
import { toast } from "sonner";
import { opportunitiesApi, resumesApi, matchesApi } from "../../lib/api";
import { OpportunityFilters } from "./OpportunityFilters";
import { OpportunitiesTable } from "./OpportunitiesTable";
import { AddOpportunityDialog } from "./AddOpportunityDialog";
import { GenerateEmailDialog } from "./GenerateEmailDialog";
import { EmailHistoryDialog } from "./EmailHistoryDialog";

const useDebounced = (value, delay = 250) => {
  const [v, setV] = useState(value);
  useEffect(() => {
    const t = setTimeout(() => setV(value), delay);
    return () => clearTimeout(t);
  }, [value, delay]);
  return v;
};

const initialFilters = {
  search: "",
  skillsRaw: "",
  role: "",
  location: "",
  employment_type: "",
  work_mode: "",
  status: "",
  freshness: "",
  sort: "newest",
};

export const OpportunitiesView = ({ onLeadsChanged }) => {
  const [meta, setMeta] = useState(null);
  const [filters, setFilters] = useState(initialFilters);
  const debounced = useDebounced(filters, 300);

  const [opps, setOpps] = useState([]);
  const [loading, setLoading] = useState(true);
  const [seeding, setSeeding] = useState(false);
  const [matchSummary, setMatchSummary] = useState({});
  const [hasResume, setHasResume] = useState(false);

  const [emailFor, setEmailFor] = useState(null);
  const [historyFor, setHistoryFor] = useState(null);

  useEffect(() => {
    opportunitiesApi.meta().then(setMeta).catch(() => {});
  }, []);

  const fetchOpps = useCallback(async () => {
    setLoading(true);
    try {
      const skills = debounced.skillsRaw
        .split(",")
        .map((s) => s.trim())
        .filter(Boolean);
      const data = await opportunitiesApi.list({
        search: debounced.search,
        role: debounced.role,
        location: debounced.location,
        employment_type: debounced.employment_type,
        work_mode: debounced.work_mode,
        status: debounced.status,
        freshness: debounced.freshness,
        skills,
        sort: debounced.sort,
      });
      setOpps(data);

      // Check for active resume + batch-compute match scores in one round-trip.
      try {
        const active = await resumesApi.active();
        setHasResume(!!active);
        if (active && data.length > 0) {
          const batch = await matchesApi.batch(data.map((o) => o.id));
          const map = {};
          for (const m of batch) map[m.opportunity_id] = m;
          setMatchSummary(map);
        } else {
          setMatchSummary({});
        }
      } catch {
        setHasResume(false);
        setMatchSummary({});
      }
    } catch {
      toast.error("Failed to load opportunities");
    } finally {
      setLoading(false);
    }
  }, [debounced]);

  useEffect(() => {
    fetchOpps();
  }, [fetchOpps]);

  // Refetch when the resume changes (uploaded / activated / deleted in ProfileDialog).
  useEffect(() => {
    const handler = () => fetchOpps();
    window.addEventListener("resume-changed", handler);
    return () => window.removeEventListener("resume-changed", handler);
  }, [fetchOpps]);

  const handleSeed = async () => {
    setSeeding(true);
    try {
      const res = await opportunitiesApi.seed();
      if (res.inserted > 0) {
        toast.success(`Seeded ${res.inserted} sample opportunities`);
        fetchOpps();
      } else {
        toast.info(res.message || "Nothing to seed");
      }
    } catch {
      toast.error("Seed failed");
    } finally {
      setSeeding(false);
    }
  };

  const handleChanged = useCallback(() => {
    fetchOpps();
    onLeadsChanged?.();
  }, [fetchOpps, onLeadsChanged]);

  const headingNote = useMemo(
    () => `${opps.length} opportunit${opps.length === 1 ? "y" : "ies"} matching your filters`,
    [opps.length],
  );

  return (
    <section data-testid="opportunities-view">
      <div className="flex flex-col md:flex-row md:items-end md:justify-between gap-6 mb-8">
        <div>
          <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-500 mb-2">
            Discovery
          </p>
          <h2 className="font-heading text-3xl md:text-4xl font-extrabold tracking-tight">
            Find Opportunities
          </h2>
          <p className="text-sm text-neutral-500 mt-2" data-testid="opportunities-heading-note">
            {headingNote}
          </p>
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            variant="outline"
            onClick={handleSeed}
            disabled={seeding}
            data-testid="seed-opportunities-btn"
            className="rounded-none border-neutral-300 hover:bg-neutral-100 h-10 px-4 gap-2 font-semibold"
          >
            <Database size={16} weight="bold" />
            {seeding ? "Loading…" : "Load Sample Data"}
          </Button>
          <AddOpportunityDialog meta={meta} onCreated={handleChanged} />
        </div>
      </div>

      <OpportunityFilters
        filters={filters}
        setFilters={setFilters}
        meta={meta}
        resultCount={opps.length}
        onClear={() => setFilters(initialFilters)}
      />

      <OpportunitiesTable
        opportunities={opps}
        loading={loading}
        meta={meta}
        matchSummary={matchSummary}
        hasResume={hasResume}
        onChanged={handleChanged}
        onGenerateEmail={(opp) => setEmailFor(opp)}
        onShowHistory={(opp) => setHistoryFor(opp)}
      />

      <GenerateEmailDialog
        open={!!emailFor}
        opportunity={emailFor}
        onClose={() => setEmailFor(null)}
      />

      <EmailHistoryDialog
        open={!!historyFor}
        opportunity={historyFor}
        onClose={() => setHistoryFor(null)}
      />
    </section>
  );
};
