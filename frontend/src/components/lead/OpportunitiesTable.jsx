import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ArrowSquareOut,
  BookmarkSimple,
  ClockCounterClockwise,
  Sparkle,
  Trash,
} from "@phosphor-icons/react";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Badge } from "../ui/badge";
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from "../ui/alert-dialog";
import { toast } from "sonner";
import { opportunitiesApi } from "../../lib/api";
import { MatchBadge } from "./MatchBadge";

const STATUS_COLORS = {
  New: "bg-neutral-100 text-neutral-700 border-neutral-300",
  Applied: "bg-blue-50 text-[#002FA7] border-[#002FA7]",
  Rejected: "bg-red-50 text-[#CC0000] border-[#CC0000]",
  Interview: "bg-amber-50 text-amber-800 border-amber-500",
};

const formatDate = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
};

const normalizeUrl = (u) => (!u ? null : u.startsWith("http") ? u : `https://${u}`);

export const OpportunitiesTable = ({
  opportunities,
  loading,
  meta,
  matchSummary = {},
  hasResume = false,
  onChanged,
  onGenerateEmail,
  onShowHistory,
}) => {
  const [pendingDelete, setPendingDelete] = useState(null);
  const [busy, setBusy] = useState({});

  const setOppBusy = (id, key, value) =>
    setBusy((b) => ({ ...b, [`${id}-${key}`]: value }));

  const handleStatus = async (opp, newStatus) => {
    setOppBusy(opp.id, "status", true);
    try {
      await opportunitiesApi.updateStatus(opp.id, newStatus);
      toast.success(`Marked as ${newStatus}`);
      onChanged?.();
    } catch {
      toast.error("Failed to update status");
    } finally {
      setOppBusy(opp.id, "status", false);
    }
  };

  const handleSaveToLeads = async (opp) => {
    setOppBusy(opp.id, "save", true);
    try {
      const res = await opportunitiesApi.saveToLeads(opp.id);
      toast.success(res.message || "Saved to Leads");
      onChanged?.();
    } catch {
      toast.error("Failed to save to Leads");
    } finally {
      setOppBusy(opp.id, "save", false);
    }
  };

  const handleDelete = async () => {
    if (!pendingDelete) return;
    setOppBusy(pendingDelete.id, "delete", true);
    try {
      await opportunitiesApi.remove(pendingDelete.id);
      toast.success(`Removed "${pendingDelete.role} @ ${pendingDelete.company_name}"`);
      onChanged?.();
    } catch {
      toast.error("Failed to delete");
    } finally {
      setOppBusy(pendingDelete.id, "delete", false);
      setPendingDelete(null);
    }
  };

  if (loading) {
    return (
      <div
        className="border border-neutral-200 bg-white py-20 text-center"
        data-testid="opportunities-loading"
      >
        <p className="font-mono text-xs uppercase tracking-[0.25em] text-neutral-500">
          Loading opportunities…
        </p>
      </div>
    );
  }

  if (!opportunities || opportunities.length === 0) {
    return (
      <div
        className="border border-neutral-200 bg-white py-20 text-center"
        data-testid="opportunities-empty"
      >
        <p className="font-mono text-xs uppercase tracking-[0.25em] text-neutral-500 mb-3">
          No opportunities
        </p>
        <h3 className="font-heading text-2xl font-bold tracking-tight text-neutral-900 mb-2">
          Start discovering roles
        </h3>
        <p className="text-sm text-neutral-500 max-w-sm mx-auto">
          Use &quot;Add Opportunity&quot; to capture a role, or &quot;Load Sample Data&quot; to populate demo opportunities.
        </p>
      </div>
    );
  }

  return (
    <>
      <div
        className="border border-neutral-200 bg-white overflow-x-auto"
        data-testid="opportunities-table-wrapper"
      >
        <table className="w-full min-w-[1100px]" data-testid="opportunities-table">
          <thead>
            <tr className="border-b border-neutral-200 bg-neutral-50">
              {[
                "Role / Company",
                "Match",
                "Type",
                "Location",
                "Skills",
                "Status",
                "Source",
                "Found",
                "Actions",
              ].map((h) => (
                <th
                  key={h}
                  className="text-left font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500 font-bold px-4 py-3"
                >
                  {h}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            <AnimatePresence initial={false}>
              {opportunities.map((opp, idx) => {
                const apply = normalizeUrl(opp.apply_link);
                return (
                  <motion.tr
                    key={opp.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.18, delay: Math.min(idx, 8) * 0.03 }}
                    className="border-b border-neutral-200 last:border-b-0 hover:bg-neutral-50 align-top"
                    data-testid={`opportunity-row-${opp.id}`}
                  >
                    <td className="px-4 py-4">
                      <div className="font-semibold text-neutral-900" data-testid={`opp-role-${opp.id}`}>
                        {opp.role}
                      </div>
                      <div className="text-sm text-neutral-500">
                        {opp.company_name}
                      </div>
                      {apply && (
                        <a
                          href={apply}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="mt-1 inline-flex items-center gap-1 text-xs text-[#002FA7] hover:underline"
                          data-testid={`opp-apply-${opp.id}`}
                        >
                          Apply <ArrowSquareOut size={10} weight="bold" />
                        </a>
                      )}
                    </td>
                    <td className="px-4 py-4">
                      <MatchBadge
                        opportunityId={opp.id}
                        hasResume={hasResume}
                        summary={matchSummary[opp.id]}
                      />
                    </td>
                    <td className="px-4 py-4 text-xs">
                      <div className="font-semibold text-neutral-700">
                        {opp.employment_type}
                      </div>
                      <div className="text-neutral-500">{opp.work_mode || "—"}</div>
                    </td>
                    <td className="px-4 py-4 text-sm text-neutral-700">
                      {opp.location || "—"}
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex flex-wrap gap-1 max-w-[220px]">
                        {(opp.skills || []).slice(0, 4).map((s) => (
                          <Badge
                            key={s}
                            variant="outline"
                            className="rounded-none border-neutral-300 text-[10px] font-mono py-0 px-1.5 h-5"
                          >
                            {s}
                          </Badge>
                        ))}
                        {opp.skills && opp.skills.length > 4 && (
                          <span className="text-[10px] text-neutral-500 font-mono">
                            +{opp.skills.length - 4}
                          </span>
                        )}
                      </div>
                    </td>
                    <td className="px-4 py-4">
                      <Select
                        value={opp.status}
                        onValueChange={(v) => handleStatus(opp, v)}
                      >
                        <SelectTrigger
                          className={`rounded-none h-8 text-xs font-semibold border w-[120px] ${STATUS_COLORS[opp.status] || ""}`}
                          data-testid={`opp-status-trigger-${opp.id}`}
                        >
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="rounded-none">
                          {(meta?.statuses || ["New", "Applied", "Rejected", "Interview"]).map(
                            (s) => (
                              <SelectItem
                                key={s}
                                value={s}
                                data-testid={`opp-status-option-${opp.id}-${s}`}
                              >
                                {s}
                              </SelectItem>
                            ),
                          )}
                        </SelectContent>
                      </Select>
                    </td>
                    <td className="px-4 py-4 text-xs text-neutral-500 font-mono">
                      {opp.source || "—"}
                    </td>
                    <td className="px-4 py-4 text-xs text-neutral-500 font-mono whitespace-nowrap">
                      {formatDate(opp.date_found)}
                    </td>
                    <td className="px-4 py-4">
                      <div className="flex items-center gap-1">
                        <button
                          onClick={() => onGenerateEmail?.(opp)}
                          title="Generate outreach email"
                          className="inline-flex items-center justify-center h-8 px-2 border border-neutral-300 hover:border-[#002FA7] hover:text-[#002FA7] transition-colors duration-150 gap-1.5 text-xs font-semibold"
                          data-testid={`opp-generate-email-btn-${opp.id}`}
                        >
                          <Sparkle size={12} weight="fill" />
                          Email
                        </button>
                        <button
                          onClick={() => onShowHistory?.(opp)}
                          title="View outreach history"
                          className="inline-flex items-center justify-center h-8 w-8 border border-transparent text-neutral-500 hover:text-neutral-900 hover:border-neutral-400 transition-colors duration-150"
                          data-testid={`opp-history-btn-${opp.id}`}
                        >
                          <ClockCounterClockwise size={14} weight="bold" />
                        </button>
                        <button
                          onClick={() => handleSaveToLeads(opp)}
                          disabled={busy[`${opp.id}-save`]}
                          title="Save to Leads"
                          className="inline-flex items-center justify-center h-8 w-8 border border-transparent text-neutral-500 hover:text-neutral-900 hover:border-neutral-400 transition-colors duration-150"
                          data-testid={`opp-save-to-leads-btn-${opp.id}`}
                        >
                          <BookmarkSimple size={14} weight="bold" />
                        </button>
                        <button
                          onClick={() => setPendingDelete(opp)}
                          title="Delete"
                          className="inline-flex items-center justify-center h-8 w-8 border border-transparent text-neutral-400 hover:text-[#E60000] hover:border-[#E60000] transition-colors duration-150"
                          data-testid={`opp-delete-btn-${opp.id}`}
                        >
                          <Trash size={14} weight="bold" />
                        </button>
                      </div>
                    </td>
                  </motion.tr>
                );
              })}
            </AnimatePresence>
          </tbody>
        </table>
      </div>

      <AlertDialog
        open={!!pendingDelete}
        onOpenChange={(o) => !o && setPendingDelete(null)}
      >
        <AlertDialogContent
          className="rounded-none border border-neutral-900"
          data-testid="opp-delete-confirm-dialog"
        >
          <AlertDialogHeader>
            <AlertDialogTitle className="font-heading tracking-tight">
              Delete this opportunity?
            </AlertDialogTitle>
            <AlertDialogDescription>
              {pendingDelete && (
                <>
                  <span className="font-semibold text-neutral-900">
                    {pendingDelete.role}
                  </span>{" "}
                  at {pendingDelete.company_name} will be removed.
                </>
              )}
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              data-testid="opp-cancel-delete-btn"
              className="rounded-none border-neutral-300"
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              data-testid="opp-confirm-delete-btn"
              onClick={handleDelete}
              className="rounded-none bg-[#E60000] hover:bg-[#CC0000] text-white"
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};
