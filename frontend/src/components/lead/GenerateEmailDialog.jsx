import React, { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from "../ui/dialog";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { Label } from "../ui/label";
import { toast } from "sonner";
import { Copy, EnvelopeOpen, PencilSimple, Sparkle, X } from "@phosphor-icons/react";
import { outreachApi } from "../../lib/api";

const inputClass =
  "rounded-none border-neutral-300 focus-visible:ring-1 focus-visible:ring-[#002FA7] focus-visible:ring-offset-0 h-10 text-sm";
const textareaClass =
  "rounded-none border-neutral-300 focus-visible:ring-1 focus-visible:ring-[#002FA7] focus-visible:ring-offset-0 text-sm";

const Step = ({ active, children }) => (
  <div className={active ? "" : "hidden"}>{children}</div>
);

export const GenerateEmailDialog = ({ opportunity, open, onClose }) => {
  const [phase, setPhase] = useState("form"); // form | loading | result
  const [sender, setSender] = useState({
    sender_name: "",
    sender_role: "",
    sender_pitch: "",
    tone: "warm and professional",
  });
  const [result, setResult] = useState({ subject: "", body: "", to: "" });
  const [editable, setEditable] = useState(false);

  const reset = () => {
    setPhase("form");
    setResult({ subject: "", body: "", to: "" });
    setEditable(false);
  };

  const handleClose = (o) => {
    if (!o) {
      onClose?.();
      // delay reset so the closing animation isn't janky
      setTimeout(reset, 200);
    }
  };

  const submit = async () => {
    if (!opportunity?.id) return;
    setPhase("loading");
    try {
      const res = await outreachApi.generate({
        opportunity_id: opportunity.id,
        sender_name: sender.sender_name.trim() || undefined,
        sender_role: sender.sender_role.trim() || undefined,
        sender_pitch: sender.sender_pitch.trim() || undefined,
        tone: sender.tone || undefined,
      });
      setResult({
        subject: res.subject || "",
        body: res.body || "",
        to: res.to || opportunity.contact_email || "",
      });
      setPhase("result");
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(typeof detail === "string" ? detail : "Failed to generate email");
      setPhase("form");
    }
  };

  const copy = async () => {
    const text = `Subject: ${result.subject}\n\n${result.body}`;
    try {
      await navigator.clipboard.writeText(text);
      toast.success("Email copied to clipboard");
    } catch {
      toast.error("Copy failed");
    }
  };

  const mailto = () => {
    const to = result.to || "";
    const url = `mailto:${encodeURIComponent(to)}?subject=${encodeURIComponent(
      result.subject,
    )}&body=${encodeURIComponent(result.body)}`;
    window.location.href = url;
  };

  return (
    <Dialog open={open} onOpenChange={handleClose}>
      <DialogContent
        className="rounded-none border border-neutral-900 bg-white sm:max-w-2xl p-0 max-h-[90vh] overflow-y-auto"
        data-testid="generate-email-dialog"
      >
        <DialogHeader className="border-b border-neutral-200 px-6 py-5">
          <DialogTitle className="font-heading text-xl font-bold tracking-tight flex items-center gap-2">
            <Sparkle size={18} weight="fill" className="text-[#002FA7]" />
            Generate Outreach Email
          </DialogTitle>
          <DialogDescription className="text-sm text-neutral-500">
            {opportunity
              ? `For "${opportunity.role}" at ${opportunity.company_name}`
              : ""}
          </DialogDescription>
        </DialogHeader>

        <Step active={phase === "form"}>
          <div className="px-6 py-6 space-y-5">
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Your Name
              </Label>
              <Input
                value={sender.sender_name}
                onChange={(e) => setSender({ ...sender, sender_name: e.target.value })}
                placeholder="Alex Park"
                data-testid="outreach-name-input"
                className={inputClass}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Your Background / Current Role
              </Label>
              <Input
                value={sender.sender_role}
                onChange={(e) => setSender({ ...sender, sender_role: e.target.value })}
                placeholder="Final-year CS student · open-source contributor"
                data-testid="outreach-role-input"
                className={inputClass}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Highlights / Pitch
              </Label>
              <Textarea
                value={sender.sender_pitch}
                onChange={(e) => setSender({ ...sender, sender_pitch: e.target.value })}
                placeholder="Built 3 production automation pipelines in Python; shipped an analytics dashboard used by 200 users."
                data-testid="outreach-pitch-input"
                rows={4}
                className={textareaClass}
              />
            </div>
          </div>

          <DialogFooter className="border-t border-neutral-200 px-6 py-4 gap-2">
            <Button
              variant="outline"
              onClick={() => handleClose(false)}
              data-testid="outreach-cancel-btn"
              className="rounded-none border-neutral-300 h-10 px-4"
            >
              Cancel
            </Button>
            <Button
              onClick={submit}
              data-testid="outreach-generate-btn"
              className="rounded-none bg-neutral-900 hover:bg-neutral-700 text-white h-10 px-5 font-semibold gap-2"
            >
              <Sparkle size={14} weight="fill" />
              Generate
            </Button>
          </DialogFooter>
        </Step>

        <Step active={phase === "loading"}>
          <div
            className="px-6 py-16 flex flex-col items-center justify-center gap-3"
            data-testid="outreach-loading"
          >
            <div className="h-10 w-10 border-2 border-neutral-200 border-t-[#002FA7] animate-spin rounded-full" />
            <p className="font-mono text-[10px] uppercase tracking-[0.25em] text-neutral-500">
              Claude is drafting your email…
            </p>
          </div>
        </Step>

        <Step active={phase === "result"}>
          <div className="px-6 py-6 space-y-4">
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                To
              </Label>
              <Input
                value={result.to}
                onChange={(e) => setResult({ ...result, to: e.target.value })}
                placeholder="contact@company.com"
                data-testid="outreach-result-to"
                className={inputClass}
                readOnly={!editable}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Subject
              </Label>
              <Input
                value={result.subject}
                onChange={(e) => setResult({ ...result, subject: e.target.value })}
                data-testid="outreach-result-subject"
                className={inputClass}
                readOnly={!editable}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Body
              </Label>
              <Textarea
                value={result.body}
                onChange={(e) => setResult({ ...result, body: e.target.value })}
                rows={12}
                data-testid="outreach-result-body"
                className={`${textareaClass} font-mono`}
                readOnly={!editable}
              />
            </div>
          </div>

          <DialogFooter className="border-t border-neutral-200 px-6 py-4 gap-2 flex-wrap">
            <Button
              variant="ghost"
              onClick={() => setPhase("form")}
              data-testid="outreach-back-btn"
              className="rounded-none h-10 px-4 hover:bg-neutral-100 mr-auto"
            >
              ← Back
            </Button>
            <Button
              variant="outline"
              onClick={() => setEditable((v) => !v)}
              data-testid="outreach-edit-btn"
              className="rounded-none border-neutral-300 h-10 px-4 gap-2"
            >
              {editable ? (
                <>
                  <X size={14} weight="bold" /> Done
                </>
              ) : (
                <>
                  <PencilSimple size={14} weight="bold" /> Edit
                </>
              )}
            </Button>
            <Button
              variant="outline"
              onClick={copy}
              data-testid="outreach-copy-btn"
              className="rounded-none border-neutral-300 h-10 px-4 gap-2"
            >
              <Copy size={14} weight="bold" /> Copy
            </Button>
            <Button
              onClick={mailto}
              data-testid="outreach-mailto-btn"
              className="rounded-none bg-neutral-900 hover:bg-neutral-700 text-white h-10 px-4 gap-2 font-semibold"
            >
              <EnvelopeOpen size={14} weight="bold" /> Open in Mail
            </Button>
          </DialogFooter>
        </Step>
      </DialogContent>
    </Dialog>
  );
};
