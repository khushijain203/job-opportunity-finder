import React, { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Trash, ArrowSquareOut, EnvelopeSimple } from "@phosphor-icons/react";
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
import { companiesApi } from "../../lib/api";

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

const normalizeUrl = (url) => {
  if (!url) return null;
  return url.startsWith("http") ? url : `https://${url}`;
};

export const CompaniesTable = ({ companies, loading, onChanged, search }) => {
  const [pendingDelete, setPendingDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const confirmDelete = async () => {
    if (!pendingDelete) return;
    setDeleting(true);
    try {
      await companiesApi.remove(pendingDelete.id);
      toast.success(`Removed "${pendingDelete.company_name}"`);
      onChanged?.();
    } catch {
      toast.error("Failed to delete");
    } finally {
      setDeleting(false);
      setPendingDelete(null);
    }
  };

  if (loading) {
    return (
      <div
        className="border border-neutral-200 bg-white py-20 text-center"
        data-testid="loading-state"
      >
        <p className="font-mono text-xs uppercase tracking-[0.25em] text-neutral-500">
          Loading leads…
        </p>
      </div>
    );
  }

  if (!companies || companies.length === 0) {
    return (
      <div
        className="border border-neutral-200 bg-white py-24 text-center"
        data-testid="empty-state"
      >
        <p className="font-mono text-xs uppercase tracking-[0.25em] text-neutral-500 mb-3">
          {search ? "No matches" : "No leads yet"}
        </p>
        <h3 className="font-heading text-2xl font-bold tracking-tight text-neutral-900 mb-2">
          {search ? `Nothing matches “${search}”` : "Start building your pipeline"}
        </h3>
        <p className="text-sm text-neutral-500 max-w-sm mx-auto">
          {search
            ? "Try a different search term, or clear the filter to see all leads."
            : "Add your first startup using the “Add Lead” button above."}
        </p>
      </div>
    );
  }

  return (
    <>
      <div
        className="border border-neutral-200 bg-white overflow-x-auto"
        data-testid="companies-table-wrapper"
      >
        <table className="w-full" data-testid="companies-table">
          <thead>
            <tr className="border-b border-neutral-200 bg-neutral-50">
              <th className="text-left font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500 font-bold px-4 py-3">
                Company
              </th>
              <th className="text-left font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500 font-bold px-4 py-3">
                Website
              </th>
              <th className="text-left font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500 font-bold px-4 py-3">
                Email
              </th>
              <th className="text-left font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500 font-bold px-4 py-3">
                Added
              </th>
              <th className="text-right font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500 font-bold px-4 py-3 w-24">
                Actions
              </th>
            </tr>
          </thead>
          <tbody>
            <AnimatePresence initial={false}>
              {companies.map((c, idx) => {
                const websiteHref = normalizeUrl(c.website);
                return (
                  <motion.tr
                    key={c.id}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    exit={{ opacity: 0 }}
                    transition={{ duration: 0.18, delay: Math.min(idx, 8) * 0.03 }}
                    className="border-b border-neutral-200 last:border-b-0 hover:bg-neutral-50 group"
                    data-testid={`company-row-${c.id}`}
                  >
                    <td className="px-4 py-4">
                      <span
                        className="font-semibold text-neutral-900"
                        data-testid={`company-name-${c.id}`}
                      >
                        {c.company_name}
                      </span>
                    </td>
                    <td className="px-4 py-4 text-sm">
                      {websiteHref ? (
                        <a
                          href={websiteHref}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1.5 text-[#002FA7] hover:underline"
                          data-testid={`company-website-${c.id}`}
                        >
                          {c.website}
                          <ArrowSquareOut size={12} weight="bold" />
                        </a>
                      ) : (
                        <span className="text-neutral-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-4 text-sm">
                      {c.email ? (
                        <a
                          href={`mailto:${c.email}`}
                          className="inline-flex items-center gap-1.5 text-neutral-700 hover:text-neutral-900 hover:underline"
                          data-testid={`company-email-${c.id}`}
                        >
                          <EnvelopeSimple size={12} weight="bold" />
                          {c.email}
                        </a>
                      ) : (
                        <span className="text-neutral-400">—</span>
                      )}
                    </td>
                    <td className="px-4 py-4 text-sm text-neutral-500 font-mono">
                      {formatDate(c.created_at)}
                    </td>
                    <td className="px-4 py-4 text-right">
                      <button
                        onClick={() => setPendingDelete(c)}
                        className="inline-flex items-center justify-center h-8 w-8 border border-transparent text-neutral-400 hover:text-[#E60000] hover:border-[#E60000] transition-colors duration-150"
                        aria-label={`Delete ${c.company_name}`}
                        data-testid={`delete-company-btn-${c.id}`}
                      >
                        <Trash size={16} weight="bold" />
                      </button>
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
          data-testid="delete-confirm-dialog"
        >
          <AlertDialogHeader>
            <AlertDialogTitle className="font-heading tracking-tight">
              Delete this lead?
            </AlertDialogTitle>
            <AlertDialogDescription>
              <span className="font-semibold text-neutral-900">
                {pendingDelete?.company_name}
              </span>{" "}
              will be removed from your pipeline. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel
              data-testid="cancel-delete-btn"
              className="rounded-none border-neutral-300"
            >
              Cancel
            </AlertDialogCancel>
            <AlertDialogAction
              data-testid="confirm-delete-btn"
              onClick={confirmDelete}
              disabled={deleting}
              className="rounded-none bg-[#E60000] hover:bg-[#CC0000] text-white"
            >
              {deleting ? "Deleting…" : "Delete"}
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
};
