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
import { Button } from "../ui/button";
import { Input } from "../ui/input";
import { Label } from "../ui/label";
import { toast } from "sonner";
import { companiesApi } from "../../lib/api";

export const AddCompanyDialog = ({ onCreated }) => {
  const [open, setOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [form, setForm] = useState({ company_name: "", website: "", email: "" });

  const reset = () => setForm({ company_name: "", website: "", email: "" });

  const submit = async (e) => {
    e.preventDefault();
    if (!form.company_name.trim()) {
      toast.error("Company name is required");
      return;
    }
    setSubmitting(true);
    try {
      const payload = {
        company_name: form.company_name.trim(),
        website: form.website.trim() || null,
        email: form.email.trim() || null,
      };
      const created = await companiesApi.create(payload);
      toast.success(`Added "${created.company_name}"`);
      reset();
      setOpen(false);
      onCreated?.();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      toast.error(
        typeof detail === "string"
          ? detail
          : Array.isArray(detail)
            ? detail[0]?.msg || "Failed to add company"
            : "Failed to add company",
      );
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button
          data-testid="add-company-btn"
          className="rounded-none bg-neutral-900 text-white hover:bg-neutral-700 transition-colors duration-150 h-10 px-5 font-semibold gap-2"
        >
          <Plus size={16} weight="bold" />
          Add Lead
        </Button>
      </DialogTrigger>
      <DialogContent
        className="rounded-none border border-neutral-900 bg-white sm:max-w-md p-0"
        data-testid="add-company-dialog"
      >
        <form onSubmit={submit}>
          <DialogHeader className="border-b border-neutral-200 px-6 py-5">
            <DialogTitle className="font-heading text-xl font-bold tracking-tight">
              New Lead
            </DialogTitle>
            <DialogDescription className="text-sm text-neutral-500">
              Add a startup to your pipeline.
            </DialogDescription>
          </DialogHeader>

          <div className="px-6 py-6 space-y-5">
            <div className="space-y-2">
              <Label htmlFor="company_name" className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Company Name *
              </Label>
              <Input
                id="company_name"
                data-testid="input-company-name"
                value={form.company_name}
                onChange={(e) => setForm({ ...form, company_name: e.target.value })}
                placeholder="Acme Robotics"
                className="rounded-none border-neutral-300 focus-visible:ring-1 focus-visible:ring-[#002FA7] focus-visible:ring-offset-0 h-10"
                autoFocus
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="website" className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Website
              </Label>
              <Input
                id="website"
                data-testid="input-website"
                value={form.website}
                onChange={(e) => setForm({ ...form, website: e.target.value })}
                placeholder="https://acme.com"
                className="rounded-none border-neutral-300 focus-visible:ring-1 focus-visible:ring-[#002FA7] focus-visible:ring-offset-0 h-10"
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="email" className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Email
              </Label>
              <Input
                id="email"
                data-testid="input-email"
                type="email"
                value={form.email}
                onChange={(e) => setForm({ ...form, email: e.target.value })}
                placeholder="founder@acme.com"
                className="rounded-none border-neutral-300 focus-visible:ring-1 focus-visible:ring-[#002FA7] focus-visible:ring-offset-0 h-10"
              />
            </div>
          </div>

          <DialogFooter className="border-t border-neutral-200 px-6 py-4 gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => setOpen(false)}
              data-testid="cancel-add-btn"
              className="rounded-none border-neutral-300 hover:bg-neutral-100 h-10 px-4"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={submitting}
              data-testid="submit-add-btn"
              className="rounded-none bg-neutral-900 text-white hover:bg-neutral-700 h-10 px-5 font-semibold"
            >
              {submitting ? "Saving…" : "Save Lead"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
