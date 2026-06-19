import React, { useEffect, useState } from "react";
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
import { profileApi, formatApiErrorDetail } from "../../lib/api";
import { ResumeSection } from "./ResumeSection";

const inputClass =
  "rounded-none border-neutral-300 focus-visible:ring-1 focus-visible:ring-[#002FA7] focus-visible:ring-offset-0 h-10 text-sm";
const textareaClass =
  "rounded-none border-neutral-300 focus-visible:ring-1 focus-visible:ring-[#002FA7] focus-visible:ring-offset-0 text-sm";

const csv = (arr) => (arr && arr.length ? arr.join(", ") : "");

export const ProfileDialog = ({ open, onClose }) => {
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState({
    full_name: "",
    skills: "",
    years_experience: "",
    preferred_roles: "",
    preferred_locations: "",
    bio: "",
  });

  useEffect(() => {
    if (!open) return;
    let active = true;
    setLoading(true);
    profileApi
      .get()
      .then((p) => {
        if (!active) return;
        setForm({
          full_name: p.full_name || "",
          skills: csv(p.skills),
          years_experience:
            p.years_experience === null || p.years_experience === undefined
              ? ""
              : String(p.years_experience),
          preferred_roles: csv(p.preferred_roles),
          preferred_locations: csv(p.preferred_locations),
          bio: p.bio || "",
        });
      })
      .catch(() => {})
      .finally(() => active && setLoading(false));
    return () => {
      active = false;
    };
  }, [open]);

  const splitCsv = (s) =>
    s.split(",").map((x) => x.trim()).filter(Boolean);

  const save = async (e) => {
    e.preventDefault();
    setSaving(true);
    try {
      const payload = {
        full_name: form.full_name.trim() || null,
        skills: splitCsv(form.skills),
        years_experience: form.years_experience
          ? Number(form.years_experience)
          : null,
        preferred_roles: splitCsv(form.preferred_roles),
        preferred_locations: splitCsv(form.preferred_locations),
        bio: form.bio.trim() || null,
      };
      await profileApi.update(payload);
      toast.success("Profile saved");
      onClose?.();
    } catch (err) {
      toast.error(
        formatApiErrorDetail(err?.response?.data?.detail) || "Save failed",
      );
    } finally {
      setSaving(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={(o) => !o && onClose?.()}>
      <DialogContent
        className="rounded-none border border-neutral-900 sm:max-w-xl p-0 max-h-[90vh] overflow-y-auto"
        data-testid="profile-dialog"
      >
        <form onSubmit={save}>
          <DialogHeader className="border-b border-neutral-200 px-6 py-5">
            <DialogTitle className="font-heading text-xl font-bold tracking-tight">
              Your Profile
            </DialogTitle>
            <DialogDescription className="text-sm text-neutral-500">
              Used for personalising outreach emails and (soon) resume matching.
            </DialogDescription>
          </DialogHeader>

          <div className="px-6 py-6 grid grid-cols-1 sm:grid-cols-2 gap-4">
            <div className="space-y-2 sm:col-span-2">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Full Name
              </Label>
              <Input
                data-testid="profile-fullname"
                value={form.full_name}
                onChange={(e) => setForm({ ...form, full_name: e.target.value })}
                className={inputClass}
                disabled={loading}
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Skills (comma separated)
              </Label>
              <Input
                data-testid="profile-skills"
                value={form.skills}
                onChange={(e) => setForm({ ...form, skills: e.target.value })}
                placeholder="Python, SQL, Tableau"
                className={inputClass}
                disabled={loading}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Years of Experience
              </Label>
              <Input
                data-testid="profile-years"
                type="number"
                min="0"
                max="80"
                step="0.5"
                value={form.years_experience}
                onChange={(e) => setForm({ ...form, years_experience: e.target.value })}
                className={inputClass}
                disabled={loading}
              />
            </div>
            <div className="space-y-2">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Preferred Roles
              </Label>
              <Input
                data-testid="profile-roles"
                value={form.preferred_roles}
                onChange={(e) => setForm({ ...form, preferred_roles: e.target.value })}
                placeholder="Data Analyst, BA Intern"
                className={inputClass}
                disabled={loading}
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Preferred Locations
              </Label>
              <Input
                data-testid="profile-locations"
                value={form.preferred_locations}
                onChange={(e) => setForm({ ...form, preferred_locations: e.target.value })}
                placeholder="Remote, Bengaluru"
                className={inputClass}
                disabled={loading}
              />
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Short Bio
              </Label>
              <Textarea
                data-testid="profile-bio"
                value={form.bio}
                onChange={(e) => setForm({ ...form, bio: e.target.value })}
                rows={3}
                placeholder="One-sentence pitch about yourself"
                className={textareaClass}
                disabled={loading}
              />
            </div>

            <div className="space-y-3 sm:col-span-2 pt-2 border-t border-neutral-200">
              <Label className="text-xs uppercase tracking-wider text-neutral-600 font-semibold">
                Resume
              </Label>
              <ResumeSection />
            </div>
          </div>

          <DialogFooter className="border-t border-neutral-200 px-6 py-4 gap-2">
            <Button
              type="button"
              variant="outline"
              onClick={() => onClose?.()}
              data-testid="profile-cancel-btn"
              className="rounded-none border-neutral-300 hover:bg-neutral-100 h-10 px-4"
            >
              Cancel
            </Button>
            <Button
              type="submit"
              disabled={saving || loading}
              data-testid="profile-save-btn"
              className="rounded-none bg-neutral-900 text-white hover:bg-neutral-700 h-10 px-5 font-semibold"
            >
              {saving ? "Saving…" : "Save Profile"}
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  );
};
