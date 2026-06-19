import React, { useState } from "react";
import { Plus } from "@phosphor-icons/react";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "../ui/dialog";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "../ui/select";
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Textarea } from "../ui/textarea";
import { Label } from "../ui/label";
import { toast } from "sonner";
import { opportunitiesApi } from "../../lib/api";

const empty = {
  company_name: "",
  role: "",
  location: "",
  employment_type: "Internship",
  work_mode: "Remote",
  skills: "",
  source: "",
  apply_link: "",
  company_website: "",
  contact_email: "",
  description: "",
};

const inputClass =
  "rounded-none border-neutral-300 focus-visible:ring-1 focus-visible:ring-[#002FA7] focus-visible:ring-offset-0 h-10 text-sm";
const textareaClass =
  "rounded-none border-neutral-300 focus-visible:ring-1 focus-visible:ring-[#002FA7] focus-visible:ring-offset-0 text-sm";
const selectClass =
  "rounded-none border-neutral-300 focus:ring-1 focus:ring-[#002FA7] focus:ring-offset-0 h-10 text-sm";

const FieldLabel = ({ children }) => (
  <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
    {children}
  </Label>
);

export const AddOpportunityDialog = ({ meta, onCreated }) => {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState(empty);

  const set = (k, v) => setForm({ ...form, [k]: v });

  const submit = async (e) => {
    e.preventDefault();
    if (!form.company_name.trim() || !form.role.trim()) {
      toast.error("Company name and role are required");
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        company_name: form.company_name.trim(),
        role: form.role.trim(),
        location: form.location.trim() || null,
        employment_type: form.employment_type,
        work_mode: form.work_mode || null,
        skills: form.skills
          .split(",")
          .map((s) => s.trim())
          .filter(Boolean),
        source: form.source.trim() || null,
        apply_link: form.apply_link.trim() || null,
        company_website: form.company_website.trim() || null,
        contact_email: form.contact_email.trim() || null,
        description: form.description.trim() || null,
      };
      await opportunitiesApi.create(payload);
      toast.success(`Added "${payload.role} @ ${payload.company_name}"`);
      setForm(empty);
      setOpen(false);
      onCreated?.();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail[0]?.msg || "Failed to add opportunity"
            : "Failed to add opportunity",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          data-testid="add-opportunity-btn"
          className="rounded-none bg-neutral-900 text-white hover:bg-neutral-700 transition-colors duration-150 h-10 px-5 font-semibold gap-2"
        >
          <Plus size={16} weight="bold" />
          Add Opportunity
        </Button>
      </DialogTrigger>
      <DialogContent
        className="rounded-none border border-neutral-900 bg-white sm:max-w-xl p-0 max-h-[90vh] overflow-y-auto"
        data-testid="add-opportunity-dialog"
      >
        <form onSubmit={submit}>
          <DialogHeader className="border-b border-neutral-200 px-6 py-5">
            <DialogTitle className="font-heading text-xl font-bold tracking-tight">
              New Opportunity
            </DialogTitle>
            <DialogDescription className="text-sm text-neutral-500">
              Capture a role from any source.
            </DialogDescription>
          </DialogHeader>

          <div className="px-6 py-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2 sm:col-span-2">
              <FieldLabel>Company Name *</FieldLabel>
              <Input
                value={form.company_name}
                onChange={(e) => set("company_name", e.target.value)}
                placeholder="Acme Robotics"
                data-testid="opp-input-company"
                className={inputClass}
                autoFocus
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <FieldLabel>Role *</FieldLabel>
              <Input
                value={form.role}
                onChange={(e) => set("role", e.target.value)}
                placeholder="Data Analyst Intern"
                data-testid="opp-input-role"
                className={inputClass}
              />
            </div>
            <div className="space-y-2">
              <FieldLabel>Location</FieldLabel>
              <Input
                value={form.location}
                onChange={(e) => set("location", e.target.value)}
                placeholder="Bengaluru / Remote"
                data-testid="opp-input-location"
                className={inputClass}
              />
            </div>
            <div className="space-y-2">
              <FieldLabel>Source</FieldLabel>
              <Input
                value={form.source}
                onChange={(e) => set("source", e.target.value)}
                placeholder="LinkedIn"
                data-testid="opp-input-source"
                className={inputClass}
              />
            </div>
            <div className="space-y-2">
              <FieldLabel>Type *</FieldLabel>
              <Select value={form.employment_type} onValueChange={(v) => set("employment_type", v)}>
                <SelectTrigger className={selectClass} data-testid="opp-select-type">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-none">
                  {(meta?.employment_types || ["Internship", "Full Time"]).map((t) => (
                    <SelectItem key={t} value={t}>
                      {t}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2">
              <FieldLabel>Work Mode</FieldLabel>
              <Select value={form.work_mode} onValueChange={(v) => set("work_mode", v)}>
                <SelectTrigger className={selectClass} data-testid="opp-select-mode">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="rounded-none">
                  {(meta?.work_modes || ["Remote", "Hybrid", "Onsite"]).map((m) => (
                    <SelectItem key={m} value={m}>
                      {m}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div className="space-y-2 sm:col-span-2">
              <FieldLabel>Skills (comma separated)</FieldLabel>
              <Input
                value={form.skills}
                onChange={(e) => set("skills", e.target.value)}
                placeholder="Python, SQL, Tableau"
                data-testid="opp-input-skills"
                className={inputClass}
              />
            </div>
            <div className="space-y-2">
              <FieldLabel>Apply Link</FieldLabel>
              <Input
                value={form.apply_link}
                onChange={(e) => set("apply_link", e.target.value)}
                placeholder="https://…"
                data-testid="opp-input-apply"
                className={inputClass}
              />
            </div>
            <div className="space-y-2">
              <FieldLabel>Company Website</FieldLabel>
              <Input
                value={form.company_website}
                onChange={(e) => set("company_website", e.target.value)}
                placeholder="https://…"
                data-testid="opp-input-website"
                className={inputClass}
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <FieldLabel>Contact Email</FieldLabel>
              <Input
                type="email"
                value={form.contact_email}
                onChange={(e) => set("contact_email", e.target.value)}
                placeholder="careers@acme.com"
                data-testid="opp-input-email"
                className={inputClass}
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <FieldLabel>Description / Notes</FieldLabel>
              <Textarea
                value={form.description}
                onChange={(e) => set("description", e.target.value)}
                placeholder="Short blurb about the role…"
                data-testid="opp-input-description"
                rows={3}
                className={textareaClass}
              />
            </div>
          </div>

          <DialogFooter className="border-t border-neutral-200 px-6 py-4 gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              data-testid="opp-cancel-btn"
              className="rounded-none border-neutral-300 hover:bg-neutral-100 h-10 px-4"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={submitting}
              data-testid="opp-submit-btn"
              className="rounded-none bg-neutral-900 text-white hover:bg-neutral-700 h-10 px-5 font-semibold"
            >
              {submitting ? "Saving…" : "Save Opportunity"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
