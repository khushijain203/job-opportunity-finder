import React, { useCallback, useEffect, useRef, useState } from "react";
import { FileArrowUp, FilePdf, Sparkle, Trash, Star, StarHalf } from "@phosphor-icons/react";
import { toast } from "sonner";
import { resumesApi, formatApiErrorDetail } from "../../lib/api";

const ACCEPT = ".pdf,.docx,.txt";
const MAX_MB = 6;

const formatSize = (bytes) => {
  if (!bytes && bytes !== 0) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / 1024 / 1024).toFixed(2)} MB`;
};

const formatDate = (iso) => {
  try {
    return new Date(iso).toLocaleString();
  } catch {
    return iso;
  }
};

export const ResumeSection = () => {
  const [resumes, setResumes] = useState([]);
  const [loading, setLoading] = useState(true);
  const [uploading, setUploading] = useState(false);
  const [enrichingId, setEnrichingId] = useState(null);
  const inputRef = useRef(null);
  const [dragOver, setDragOver] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const list = await resumesApi.list();
      setResumes(list);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const doUpload = async (file) => {
    if (!file) return;
    if (file.size > MAX_MB * 1024 * 1024) {
      toast.error(`Max size is ${MAX_MB} MB.`);
      return;
    }
    setUploading(true);
    try {
      const created = await resumesApi.upload(file);
      toast.success(`Uploaded "${created.original_filename}" · ${created.parsed?.skills?.length || 0} skills mined`);
      refresh();
    } catch (err) {
      toast.error(
        formatApiErrorDetail(err?.response?.data?.detail) || "Upload failed",
      );
    } finally {
      setUploading(false);
      if (inputRef.current) inputRef.current.value = "";
    }
  };

  const handleSelect = (e) => doUpload(e.target.files?.[0]);

  const handleDrop = (e) => {
    e.preventDefault();
    setDragOver(false);
    const f = e.dataTransfer?.files?.[0];
    if (f) doUpload(f);
  };

  const activate = async (id) => {
    try {
      await resumesApi.activate(id);
      toast.success("Marked as active resume");
      refresh();
    } catch {
      toast.error("Activation failed");
    }
  };

  const remove = async (id) => {
    try {
      await resumesApi.remove(id);
      toast.success("Resume deleted");
      refresh();
    } catch {
      toast.error("Delete failed");
    }
  };

  const enrich = async (id) => {
    setEnrichingId(id);
    try {
      await resumesApi.enrich(id);
      toast.success("Enhanced with Claude — cached for future scoring");
      refresh();
    } catch (err) {
      toast.error(
        formatApiErrorDetail(err?.response?.data?.detail) || "Enrichment failed",
      );
    } finally {
      setEnrichingId(null);
    }
  };

  return (
    <div className="space-y-3" data-testid="resume-section">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragOver(true);
        }}
        onDragLeave={() => setDragOver(false)}
        onDrop={handleDrop}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        className={`border-2 border-dashed ${dragOver ? "border-[#002FA7] bg-blue-50" : "border-neutral-300 hover:border-neutral-500"} p-6 text-center cursor-pointer transition-colors duration-150`}
        data-testid="resume-dropzone"
      >
        <FileArrowUp size={28} weight="bold" className="mx-auto text-neutral-500" />
        <p className="font-heading text-sm font-semibold text-neutral-900 mt-2">
          {uploading ? "Uploading…" : "Drop your resume here, or click to browse"}
        </p>
        <p className="text-[11px] text-neutral-500 mt-1 font-mono">
          PDF · DOCX · TXT · max {MAX_MB} MB · parsed locally
        </p>
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPT}
          onChange={handleSelect}
          className="hidden"
          data-testid="resume-file-input"
        />
      </div>

      {loading ? (
        <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-500 py-3 text-center">
          Loading resumes…
        </p>
      ) : resumes.length === 0 ? (
        <p
          className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-500 py-2 text-center"
          data-testid="resume-empty"
        >
          No resume uploaded yet.
        </p>
      ) : (
        <ul className="space-y-2" data-testid="resume-list">
          {resumes.map((r) => (
            <li
              key={r.id}
              className={`border ${r.is_active ? "border-[#002FA7]" : "border-neutral-200"} p-3 flex items-start gap-3`}
              data-testid={`resume-item-${r.id}`}
            >
              <FilePdf size={20} weight="bold" className="text-neutral-500 mt-0.5" />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <p className="font-semibold text-sm text-neutral-900 truncate">
                    {r.original_filename}
                  </p>
                  {r.is_active && (
                    <span className="font-mono text-[9px] uppercase tracking-[0.2em] px-1.5 py-0.5 bg-[#002FA7] text-white">
                      Active
                    </span>
                  )}
                  {r.parsed?.ai_enriched_at && (
                    <span className="font-mono text-[9px] uppercase tracking-[0.2em] px-1.5 py-0.5 border border-neutral-300 text-neutral-700">
                      AI Enhanced
                    </span>
                  )}
                </div>
                <p className="font-mono text-[10px] uppercase tracking-[0.2em] text-neutral-500 mt-1">
                  {formatSize(r.size)} · {formatDate(r.uploaded_at)} · {r.parsed?.skills?.length || 0} skills
                </p>
                {(r.parsed?.skills || []).length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1" data-testid={`resume-skills-${r.id}`}>
                    {(r.parsed.skills || []).slice(0, 10).map((s) => (
                      <span
                        key={s}
                        className="font-mono text-[10px] border border-neutral-300 px-1.5 py-0.5"
                      >
                        {s}
                      </span>
                    ))}
                    {r.parsed.skills.length > 10 && (
                      <span className="font-mono text-[10px] text-neutral-500">
                        +{r.parsed.skills.length - 10}
                      </span>
                    )}
                  </div>
                )}
              </div>
              <div className="flex flex-col gap-1.5">
                {!r.is_active && (
                  <button
                    type="button"
                    onClick={() => activate(r.id)}
                    title="Set as active resume"
                    data-testid={`resume-activate-btn-${r.id}`}
                    className="inline-flex items-center gap-1 h-7 px-2 border border-neutral-300 hover:bg-neutral-100 text-[10px] font-semibold"
                  >
                    <Star size={11} weight="bold" /> Set Active
                  </button>
                )}
                <button
                  type="button"
                  onClick={() => enrich(r.id)}
                  disabled={enrichingId === r.id || !!r.parsed?.ai_enriched_at}
                  title={r.parsed?.ai_enriched_at ? "Already AI-enhanced (cached)" : "Enhance with Claude (one call, cached)"}
                  data-testid={`resume-enrich-btn-${r.id}`}
                  className="inline-flex items-center gap-1 h-7 px-2 border border-neutral-300 hover:border-[#002FA7] hover:text-[#002FA7] text-[10px] font-semibold disabled:opacity-50 disabled:hover:border-neutral-300 disabled:hover:text-current"
                >
                  <Sparkle size={11} weight="fill" />
                  {enrichingId === r.id ? "AI…" : r.parsed?.ai_enriched_at ? "Enhanced" : "AI Enhance"}
                </button>
                <button
                  type="button"
                  onClick={() => remove(r.id)}
                  title="Delete resume"
                  data-testid={`resume-delete-btn-${r.id}`}
                  className="inline-flex items-center gap-1 h-7 px-2 border border-transparent text-neutral-400 hover:text-[#E60000] hover:border-[#E60000] text-[10px] font-semibold"
                >
                  <Trash size={11} weight="bold" /> Delete
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}
      <StarHalf className="hidden" />
    </div>
  );
};
