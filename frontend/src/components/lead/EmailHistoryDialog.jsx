import React, { useEffect, useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { ClockCounterClockwise, Copy, Trash } from "@phosphor-icons/react";
import { toast } from "sonner";
import { generatedEmailsApi } from "../../lib/api";

const formatDate = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
};

export const EmailHistoryDialog = ({ open, opportunity, onClose }) => {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(null);

  useEffect(() => {
    if (!open || !opportunity?.id) return;
    let active = true;
    setLoading(true);
    generatedEmailsApi
      .list(opportunity.id)
      .then((d) => active && setItems(d))
      .catch(() => active && toast.error("Failed to load history"))
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [open, opportunity]);

  const copy = async (e) => {
    try {
      await navigator.clipboard.writeText(`Subject: ${e.subject}\n\n${e.body}`);
      toast.success("Copied to clipboard");
    } catch {
      toast.error("Copy failed");
    }
  };

  const remove = async (id) => {
    try {
      await generatedEmailsApi.remove(id);
      setItems((arr) => arr.filter((x) => x.id !== id));
      toast.success("Email deleted");
    } catch {
      toast.error("Delete failed");
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose?.()}>
      <DialogContent
        className="rounded-none border border-neutral-900 sm:max-w-2xl p-0 max-h-[90vh] overflow-y-auto"
        data-testid="email-history-dialog"
      >
        <DialogHeader className="border-b border-neutral-200 px-6 py-5">
          <DialogTitle className="font-heading text-xl font-bold tracking-tight flex items-center gap-2">
            <ClockCounterClockwise size={18} weight="bold" />
            Outreach History
          </DialogTitle>
          <DialogDescription className="text-sm text-neutral-500">
            {opportunity ? `${opportunity.role} at ${opportunity.company_name}` : ""}
          </DialogDescription>
        </DialogHeader>

        <div className="px-6 py-6">
          {loading ? (
            <p className="font-mono text-xs uppercase tracking-[0.25em] text-neutral-500 py-12 text-center">
              Loading…
            </p>
          ) : items.length === 0 ? (
            <p
              className="font-mono text-xs uppercase tracking-[0.25em] text-neutral-500 py-12 text-center"
              data-testid="email-history-empty"
            >
              No emails generated yet for this opportunity.
            </p>
          ) : (
            <ul className="space-y-3" data-testid="email-history-list">
              {items.map((e) => {
                const isOpen = expanded === e.id;
                return (
                  <li
                    key={e.id}
                    className="border border-neutral-200"
                    data-testid={`email-history-item-${e.id}`}
                  >
                    <button
                      type="button"
                      onClick={() => setExpanded(isOpen ? null : e.id)}
                      className="w-full text-left px-4 py-3 hover:bg-neutral-50 flex items-center justify-between gap-3"
                    >
                      <div className="min-w-0">
                        <p className="font-semibold text-neutral-900 text-sm truncate">
                          {e.subject}
                        </p>
                        <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500 mt-1">
                          {formatDate(e.created_at)} · to {e.to || "—"}
                        </p>
                      </div>
                      <span className="font-mono text-[10px] text-neutral-400">
                        {isOpen ? "−" : "+"}
                      </span>
                    </button>
                    {isOpen && (
                      <div className="border-t border-neutral-200 px-4 py-3 space-y-3">
                        <pre className="whitespace-pre-wrap font-mono text-xs text-neutral-700">
                          {e.body}
                        </pre>
                        <div className="flex gap-2">
                          <button
                            onClick={() => copy(e)}
                            data-testid={`email-history-copy-${e.id}`}
                            className="inline-flex items-center gap-1.5 h-8 px-3 border border-neutral-300 hover:bg-neutral-100 text-xs font-semibold"
                          >
                            <Copy size={12} weight="bold" /> Copy
                          </button>
                          <button
                            onClick={() => remove(e.id)}
                            data-testid={`email-history-delete-${e.id}`}
                            className="inline-flex items-center gap-1.5 h-8 px-3 border border-neutral-300 text-neutral-500 hover:text-[#E60000] hover:border-[#E60000] text-xs font-semibold"
                          >
                            <Trash size={12} weight="bold" /> Delete
                          </button>
                        </div>
                      </div>
                    )}
                  </li>
                );
              })}
            </ul>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
};
