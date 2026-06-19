import React, { useState } from "react";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "../ui/popover";
import { Button } from "../ui/button";
import { Sparkle, Question } from "@phosphor-icons/react";
import { matchesApi, formatApiErrorDetail } from "../../lib/api";
import { toast } from "sonner";

const colorFor = (score) => {
  if (score == null) return "border-neutral-300 text-neutral-500 bg-white";
  if (score >= 0.7) return "border-emerald-600 text-emerald-700 bg-emerald-50";
  if (score >= 0.45) return "border-amber-500 text-amber-700 bg-amber-50";
  if (score >= 0.2) return "border-neutral-400 text-neutral-700 bg-neutral-50";
  return "border-red-400 text-red-700 bg-red-50";
};

const Section = ({ label, value, children }) => (
  <div className="space-y-1">
    <div className="flex items-center justify-between">
      <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500">
        {label}
      </span>
      {value != null && (
        <span className="font-mono text-[10px] text-neutral-700">
          {Math.round(value * 100)}%
        </span>
      )}
    </div>
    {children}
  </div>
);

export const MatchBadge = ({ opportunityId, summary, hasResume, fullDetails }) => {
  const [open, setOpen] = useState(false);
  const [detail, setDetail] = useState(fullDetails || null);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [showTfidf, setShowTfidf] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [ai, setAi] = useState(null);

  if (!hasResume) {
    return (
      <span
        data-testid={`match-badge-no-resume-${opportunityId}`}
        className="inline-flex items-center justify-center h-7 px-2 border border-dashed border-neutral-300 text-neutral-400 text-[10px] font-mono"
        title="Upload a resume to see match scores"
      >
        —
      </span>
    );
  }

  const score = summary?.overall_score ?? null;
  const percent = score == null ? "—" : Math.round(score * 100);

  const loadDetail = async () => {
    if (detail) return;
    setLoadingDetail(true);
    try {
      const d = await matchesApi.forOpportunity(opportunityId, { tfidf: false });
      setDetail(d);
      setAi(d?.ai_score != null ? { score: d.ai_score, summary: d.ai_summary } : null);
    } catch {
      toast.error("Failed to load match details");
    } finally {
      setLoadingDetail(false);
    }
  };

  const loadTfidf = async () => {
    setShowTfidf(true);
    try {
      const d = await matchesApi.forOpportunity(opportunityId, { tfidf: true });
      setDetail(d);
    } catch {
      toast.error("Failed to compute TF-IDF");
    }
  };

  const requestAi = async () => {
    setAiBusy(true);
    try {
      const d = await matchesApi.aiFor(opportunityId);
      setDetail(d);
      setAi({ score: d.ai_score, summary: d.ai_summary });
      toast.success("AI insight cached");
    } catch (err) {
      toast.error(
        formatApiErrorDetail(err?.response?.data?.detail) || "AI analysis failed",
      );
    } finally {
      setAiBusy(false);
    }
  };

  const bd = detail?.breakdown;

  return (
    <Popover
      open={open}
      onOpenChange={(o) => {
        setOpen(o);
        if (o) loadDetail();
      }}
    >
      <PopoverTrigger asChild>
        <button
          type="button"
          data-testid={`match-badge-${opportunityId}`}
          className={`inline-flex items-center gap-1 h-7 px-2 border text-[11px] font-mono font-bold tabular-nums ${colorFor(score)}`}
          title="Click for match details"
        >
          {percent}{score == null ? "" : "%"}
          <Question size={11} weight="bold" className="opacity-60" />
        </button>
      </PopoverTrigger>
      <PopoverContent
        align="end"
        className="rounded-none w-[360px] p-0 border border-neutral-900"
        data-testid={`match-details-${opportunityId}`}
      >
        <div className="border-b border-neutral-200 px-4 py-3 flex items-center justify-between">
          <div>
            <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-500">
              Match score
            </p>
            <p className="font-heading text-2xl font-extrabold tracking-tight" data-testid={`match-overall-${opportunityId}`}>
              {percent}%
            </p>
          </div>
          {ai?.score != null && (
            <div className="text-right">
              <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-500">
                AI Score
              </p>
              <p className="font-heading text-2xl font-extrabold tracking-tight text-[#002FA7]" data-testid={`match-ai-score-${opportunityId}`}>
                {Math.round(ai.score)}
              </p>
            </div>
          )}
        </div>
        {loadingDetail && !bd ? (
          <p className="px-4 py-6 text-center font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-500">
            Loading…
          </p>
        ) : bd ? (
          <div className="px-4 py-4 space-y-4">
            <Section label="Skills" value={bd.skill_score}>
              {bd.matched_skills?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1" data-testid={`match-matched-${opportunityId}`}>
                  {bd.matched_skills.map((s) => (
                    <span
                      key={s}
                      className="font-mono text-[10px] border border-emerald-500 text-emerald-700 px-1.5 py-0.5"
                    >
                      ✓ {s}
                    </span>
                  ))}
                </div>
              )}
              {bd.missing_skills?.length > 0 && (
                <div className="flex flex-wrap gap-1 mt-1" data-testid={`match-missing-${opportunityId}`}>
                  {bd.missing_skills.map((s) => (
                    <span
                      key={s}
                      className="font-mono text-[10px] border border-red-400 text-red-600 px-1.5 py-0.5"
                    >
                      ✗ {s}
                    </span>
                  ))}
                </div>
              )}
              {bd.matched_skills?.length === 0 && bd.missing_skills?.length === 0 && (
                <p className="text-[11px] text-neutral-500">No skill data on this opportunity.</p>
              )}
            </Section>

            <Section label="Role Relevance" value={bd.role_relevance}>
              <p className="text-[11px] text-neutral-600" data-testid={`match-role-exp-${opportunityId}`}>
                {bd.role_explanation || "—"}
              </p>
            </Section>

            <Section label="Experience" value={bd.experience_relevance}>
              <p className="text-[11px] text-neutral-600" data-testid={`match-exp-exp-${opportunityId}`}>
                {bd.experience_explanation || "—"}
              </p>
            </Section>

            <Section label="Location" value={bd.location_relevance}>
              <p className="text-[11px] text-neutral-600" data-testid={`match-loc-exp-${opportunityId}`}>
                {bd.location_explanation || "—"}
              </p>
            </Section>

            <div className="border-t border-neutral-200 pt-3 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500">
                  Advanced (TF-IDF)
                </span>
                {showTfidf && detail?.tfidf_score != null ? (
                  <span className="font-mono text-[10px] text-neutral-700" data-testid={`match-tfidf-${opportunityId}`}>
                    {(detail.tfidf_score * 100).toFixed(0)}%
                  </span>
                ) : (
                  <button
                    type="button"
                    onClick={loadTfidf}
                    data-testid={`match-tfidf-btn-${opportunityId}`}
                    className="font-mono text-[10px] underline text-neutral-700 hover:text-neutral-900"
                  >
                    Compute
                  </button>
                )}
              </div>

              {ai?.summary ? (
                <div className="border border-neutral-200 p-2 bg-neutral-50">
                  <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500 mb-1">
                    AI Insight (cached)
                  </p>
                  <p className="text-[11px] text-neutral-700" data-testid={`match-ai-summary-${opportunityId}`}>
                    {ai.summary}
                  </p>
                </div>
              ) : (
                <Button
                  type="button"
                  onClick={requestAi}
                  disabled={aiBusy}
                  data-testid={`match-ai-btn-${opportunityId}`}
                  className="w-full rounded-none bg-neutral-900 hover:bg-neutral-700 text-white h-8 text-[11px] font-semibold gap-1.5"
                >
                  <Sparkle size={12} weight="fill" />
                  {aiBusy ? "Asking Claude…" : "Get AI Insight (cached)"}
                </Button>
              )}
            </div>
          </div>
        ) : (
          <p className="px-4 py-6 text-center text-[11px] text-neutral-500">
            No details available.
          </p>
        )}
      </PopoverContent>
    </Popover>
  );
};
