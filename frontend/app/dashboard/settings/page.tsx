"use client";

import { UserRound, Phone, Bell, Shield, Save, CheckCircle2, AlertCircle } from "lucide-react";
import { useState, useEffect, useCallback } from "react";
import { useAuthStore } from "@/store/auth";
import { cn } from "@/lib/utils";
import { api, UserSettings } from "@/lib/api";

// ── Small components ───────────────────────────────────────────────────────────

function Toggle({ enabled, onChange }: { enabled: boolean; onChange: (v: boolean) => void }) {
  return (
    <button
      onClick={() => onChange(!enabled)}
      className={cn(
        "relative shrink-0 rounded-full transition-all duration-200 ease-in-out border w-10 h-5",
        enabled ? "bg-white border-white" : "bg-surface-raised border-border-strong hover:border-text-tertiary"
      )}
    >
      <span className={cn(
        "absolute top-[1px] rounded-full transition-all duration-200 shadow-sm w-4 h-4",
        enabled ? "left-[19px] bg-black" : "left-[1px] bg-text-tertiary"
      )} />
    </button>
  );
}

function Section({
  title, description, icon: Icon, children,
}: {
  title: string; description?: string; icon: React.ElementType; children: React.ReactNode;
}) {
  return (
    <div className="py-8 border-b border-border-subtle last:border-0">
      <div className="flex items-start gap-4 mb-6">
        <div className="w-8 h-8 rounded-lg bg-surface-raised border border-border-subtle flex items-center justify-center shrink-0">
          <Icon className="w-4 h-4 text-text-secondary" />
        </div>
        <div>
          <h2 className="text-base font-semibold text-text-primary">{title}</h2>
          {description && <p className="text-sm text-text-secondary mt-1 max-w-2xl">{description}</p>}
        </div>
      </div>
      <div className="pl-12 space-y-6">{children}</div>
    </div>
  );
}

// ── VIP list component ─────────────────────────────────────────────────────────

function EmailList({
  label, badge, badgeColor, items, onRemove, onAdd,
}: {
  label: string; badge: string; badgeColor: string;
  items: string[]; onRemove: (v: string) => void; onAdd: (v: string) => void;
}) {
  const [input, setInput] = useState("");
  const handleAdd = () => {
    const v = input.trim();
    if (v && !items.includes(v)) { onAdd(v); setInput(""); }
  };
  return (
    <div className="p-4 rounded-xl border border-border-subtle bg-surface">
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-sm font-semibold text-text-primary">{label}</h3>
        <span className={cn("text-[10px] uppercase font-bold tracking-wider px-2 py-0.5 rounded", badgeColor)}>{badge}</span>
      </div>
      <div className="space-y-2 mb-4">
        {items.length === 0 && (
          <p className="text-xs text-text-tertiary italic">No entries yet.</p>
        )}
        {items.map((item) => (
          <div key={item} className="flex items-center justify-between p-2.5 rounded-lg border border-border-subtle bg-surface-raised text-sm">
            <span className="text-text-primary">{item}</span>
            <button onClick={() => onRemove(item)} className="text-text-tertiary hover:text-alert transition-colors">✕</button>
          </div>
        ))}
      </div>
      <div className="relative">
        <input
          type="text" value={input} onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === "Enter" && handleAdd()}
          placeholder="Add email..."
          className="w-full bg-void border border-border-subtle rounded-lg pl-3 pr-10 py-2 text-sm focus:outline-none focus:border-text-tertiary"
        />
        <button onClick={handleAdd} className="absolute right-2 top-1/2 -translate-y-1/2 text-text-secondary hover:text-white text-lg leading-none">+</button>
      </div>
    </div>
  );
}

// ── Main Page ──────────────────────────────────────────────────────────────────

type SaveState = "idle" | "saving" | "success" | "error";

type DeliveryItem = {
  sid: string | null;
  to: string | null;
  from_number: string | null;
  status: string | null;
  error_code: number | null;
  error_message: string | null;
  date_sent: string | null;
};

export default function SettingsPage() {
  const { user } = useAuthStore();

  // Remote state (loaded from API)
  const [whatsappNumber, setWhatsappNumber] = useState("");
  const [notifyOnAll, setNotifyOnAll] = useState(false);
  const [notifyDailyDigest, setNotifyDailyDigest] = useState(true);

  // Local-only VIP lists (stored in localStorage for now — backend extension TBD)
  const [vipList, setVipList] = useState<string[]>(["investor@vc-fund.com", "co-founder@startup.com"]);
  const [blockList, setBlockList] = useState<string[]>(["newsletter@spam.com"]);

  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [waTestState, setWaTestState] = useState<"idle" | "sending" | "sent" | "error">("idle");
  const [waTestMsg, setWaTestMsg] = useState("");
  const [waDeliveries, setWaDeliveries] = useState<DeliveryItem[]>([]);
  const [waDeliveriesLoading, setWaDeliveriesLoading] = useState(false);
  const [waDeliveriesError, setWaDeliveriesError] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [loading, setLoading] = useState(true);

  const fetchDeliveries = useCallback(async () => {
    setWaDeliveriesLoading(true);
    setWaDeliveriesError("");
    try {
      const response = await api.get<{ items: DeliveryItem[] }>("/api/v1/settings/whatsapp/deliveries");
      setWaDeliveries(response.data.items ?? []);
    } catch (err: unknown) {
      const msg =
        typeof err === "object" && err !== null && "response" in err
          ? ((err as { response?: { data?: { detail?: string } } }).response?.data?.detail ?? "Failed to load delivery logs")
          : "Failed to load delivery logs";
      setWaDeliveriesError(msg);
    } finally {
      setWaDeliveriesLoading(false);
    }
  }, []);

  // ── Load settings on mount ──────────────────────────────────────────────────
  useEffect(() => {
    api.get<UserSettings>("/api/v1/settings")
      .then((response) => {
        setWhatsappNumber(response.data.whatsapp_number ?? "");
        setNotifyOnAll(response.data.notify_on_all);
        setNotifyDailyDigest(response.data.notify_daily_digest);
        if (response.data.whatsapp_number) {
          fetchDeliveries();
        }
      })
      .catch(() => { /* Silently use defaults if unauthenticated in dev */ })
      .finally(() => setLoading(false));
  }, [fetchDeliveries]);

  // ── Save handler ────────────────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    setSaveState("saving");
    setErrorMsg("");
    try {
      await api.patch<UserSettings>("/api/v1/settings", {
        whatsapp_number: whatsappNumber || null,
        notify_on_all: notifyOnAll,
        notify_daily_digest: notifyDailyDigest,
      });
      setSaveState("success");
      setTimeout(() => setSaveState("idle"), 2500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save settings";
      setErrorMsg(msg);
      setSaveState("error");
      setTimeout(() => setSaveState("idle"), 3000);
    }
  }, [whatsappNumber, notifyOnAll, notifyDailyDigest]);

  const handleTestWhatsApp = useCallback(async () => {
    setWaTestState("sending");
    setWaTestMsg("");
    try {
      if (!whatsappNumber.trim()) {
        setWaTestState("error");
        setWaTestMsg("Add a WhatsApp number first.");
        return;
      }

      // Persist latest number before sending the test message.
      await api.patch<UserSettings>("/api/v1/settings", {
        whatsapp_number: whatsappNumber.trim(),
      });

      const response = await api.post<{ detail: string }>("/api/v1/settings/whatsapp/test");
      setWaTestState("sent");
      setWaTestMsg(response.data.detail || "Test message sent.");
      await fetchDeliveries();
      setTimeout(() => setWaTestState("idle"), 3000);
    } catch (err: unknown) {
      setWaTestState("error");
      const msg = (() => {
        if (typeof err === "object" && err !== null) {
          // Axios error with a real HTTP response from backend
          if ("response" in err) {
            const e = err as { response?: { status?: number; data?: { detail?: string } }; message?: string };
            const detail = e.response?.data?.detail;
            const status = e.response?.status;
            if (detail) return detail;
            if (status === 502) return "WhatsApp provider not configured. Check your backend .env for WHATSAPP_ACCESS_TOKEN / WHATSAPP_PHONE_NUMBER_ID credentials.";
            if (status) return `Server error (HTTP ${status}). Check backend logs.`;
          }
          // Network-level failure: backend not reachable at all
          if ("code" in err) {
            const code = (err as { code?: string }).code;
            if (code === "ERR_NETWORK" || code === "ECONNREFUSED") {
              return "Cannot reach the backend server. Make sure the backend is running on port 8000.";
            }
          }
          if ("message" in err) {
            const rawMsg = (err as { message?: string }).message ?? "";
            if (rawMsg.toLowerCase().includes("network")) {
              return "Cannot reach the backend server. Make sure the backend is running on port 8000.";
            }
            return rawMsg || "Failed to send test message";
          }
        }
        if (err instanceof Error) return err.message;
        return "Failed to send test message";
      })();
      setWaTestMsg(msg);
    }
  }, [fetchDeliveries, whatsappNumber]);

  // ── Save button visual ──────────────────────────────────────────────────────
  const SaveButton = () => {
    if (saveState === "saving") return (
      <button disabled className="px-4 py-1.5 rounded-lg bg-white text-black text-sm font-semibold flex items-center gap-2 opacity-60">
        <div className="w-3.5 h-3.5 border-2 border-black/30 border-t-black rounded-full animate-spin" />
        Saving...
      </button>
    );
    if (saveState === "success") return (
      <button disabled className="px-4 py-1.5 rounded-lg bg-green-500 text-white text-sm font-semibold flex items-center gap-2">
        <CheckCircle2 className="w-3.5 h-3.5" /> Saved
      </button>
    );
    if (saveState === "error") return (
      <button onClick={handleSave} className="px-4 py-1.5 rounded-lg bg-alert text-white text-sm font-semibold flex items-center gap-2">
        <AlertCircle className="w-3.5 h-3.5" /> Retry
      </button>
    );
    return (
      <button onClick={handleSave} className="px-4 py-1.5 rounded-lg bg-white text-black text-sm font-semibold flex items-center gap-2 hover:bg-gray-200 transition-colors">
        <Save className="w-3.5 h-3.5" /> Save
      </button>
    );
  };

  return (
    <div className="flex flex-col h-full bg-void">
      {/* Header */}
      <header className="h-16 border-b border-border-subtle flex items-center justify-between px-8 shrink-0 sticky top-0 bg-void/80 backdrop-blur-md z-10">
        <h1 className="text-lg font-semibold tracking-tight text-text-primary">Settings</h1>
        <div className="flex items-center gap-3">
          {saveState === "error" && (
            <span className="text-xs text-alert flex items-center gap-1">
              <AlertCircle className="w-3 h-3" /> {errorMsg}
            </span>
          )}
          <SaveButton />
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className={cn("w-full max-w-5xl p-8 pt-6 transition-opacity", loading && "opacity-40 pointer-events-none")}>

          {/* Profile */}
          <Section title="Profile Information" icon={UserRound}>
            <div className="flex items-center gap-6">
              <div className="w-16 h-16 rounded-full bg-surface-raised border border-border-strong flex items-center justify-center text-lg font-medium text-text-secondary shrink-0">
                {user?.display_name?.[0]?.toUpperCase() ?? "U"}
              </div>
              <div className="flex-1 grid grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">Full Name</label>
                  <input type="text" defaultValue={user?.display_name ?? "User"}
                    className="w-full bg-surface border border-border-subtle rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-text-tertiary transition-colors" />
                </div>
                <div>
                  <label className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">Email Address</label>
                  <input type="email" defaultValue={user?.email ?? ""} disabled
                    className="w-full bg-surface-raised border border-border-subtle rounded-lg px-3 py-2 text-sm text-text-tertiary cursor-not-allowed" />
                </div>
              </div>
            </div>
          </Section>

          {/* WhatsApp */}
          <Section title="WhatsApp Delivery" description="The number where your AI sends instant alerts for high-priority emails." icon={Phone}>
            <div className="max-w-md">
              <label className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">WhatsApp Number</label>
              <div className="relative">
                <span className="absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary text-sm">💬</span>
                <input
                  type="text"
                  value={whatsappNumber}
                  onChange={(e) => setWhatsappNumber(e.target.value)}
                  placeholder="+1 234 567 8900"
                  className="w-full bg-surface border border-border-subtle rounded-lg pl-9 pr-3 py-2 text-sm text-text-primary focus:outline-none focus:border-text-tertiary transition-colors"
                />
              </div>
              <p className="text-xs text-text-tertiary mt-2">Include country code. E.g. +91 98765 43210</p>
              <div className="mt-3 flex items-center gap-3">
                <button
                  onClick={handleTestWhatsApp}
                  disabled={waTestState === "sending"}
                  className="px-3 py-1.5 rounded-lg bg-surface-raised border border-border-subtle text-sm text-text-primary hover:bg-surface transition-colors disabled:opacity-60"
                >
                  {waTestState === "sending" ? "Sending..." : "Send Test Message"}
                </button>
                <button
                  onClick={fetchDeliveries}
                  disabled={waDeliveriesLoading}
                  className="px-3 py-1.5 rounded-lg bg-void border border-border-subtle text-xs text-text-secondary hover:text-text-primary transition-colors disabled:opacity-60"
                >
                  {waDeliveriesLoading ? "Refreshing..." : "Refresh Logs"}
                </button>
                {waTestMsg && (
                  <span className={cn(
                    "text-xs",
                    waTestState === "error" ? "text-alert" : "text-success"
                  )}>
                    {waTestMsg}
                  </span>
                )}
              </div>

              <div className="mt-4 rounded-lg border border-border-subtle bg-surface overflow-hidden">
                <div className="px-3 py-2 border-b border-border-subtle text-xs font-semibold text-text-secondary uppercase tracking-wider">
                  Recent Delivery Status
                </div>
                {waDeliveriesError ? (
                  <div className="px-3 py-2 text-xs text-alert">{waDeliveriesError}</div>
                ) : waDeliveries.length === 0 ? (
                  <div className="px-3 py-2 text-xs text-text-tertiary">No WhatsApp message logs yet.</div>
                ) : (
                  <div className="max-h-48 overflow-y-auto">
                    {waDeliveries.map((item, idx) => (
                      <div key={item.sid ?? `${item.date_sent ?? "na"}-${idx}`} className="px-3 py-2 border-b border-border-subtle last:border-0">
                        <div className="flex items-center justify-between gap-2">
                          <span className={cn(
                            "text-xs font-medium uppercase",
                            item.status === "delivered" ? "text-success" : item.status === "failed" ? "text-alert" : "text-text-secondary"
                          )}>
                            {item.status ?? "unknown"}
                          </span>
                          <span className="text-[11px] text-text-tertiary">{item.date_sent ?? "-"}</span>
                        </div>
                        {(item.error_code || item.error_message) && (
                          <p className="text-[11px] text-alert mt-1">
                            {item.error_code ? `Error ${item.error_code}: ` : ""}{item.error_message ?? "Delivery failure"}
                          </p>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </Section>

          {/* Notifications */}
          <Section title="Notification Rules" icon={Bell}>
            <div className="space-y-4">
              <div className="flex items-center justify-between gap-4 p-4 rounded-xl border border-border-subtle bg-surface">
                <div>
                  <p className="font-medium text-sm text-text-primary">Alert me on ALL incoming emails</p>
                  <p className="text-xs text-text-secondary mt-1">Overrides AI scoring. Warning: extremely noisy.</p>
                </div>
                <Toggle enabled={notifyOnAll} onChange={setNotifyOnAll} />
              </div>
              <div className="flex items-center justify-between gap-4 p-4 rounded-xl border border-border-subtle bg-surface">
                <div>
                  <p className="font-medium text-sm text-text-primary">Daily Digest for Low Priority</p>
                  <p className="text-xs text-text-secondary mt-1">Receive one summary WhatsApp message at 6 PM.</p>
                </div>
                <Toggle enabled={notifyDailyDigest} onChange={setNotifyDailyDigest} />
              </div>
            </div>
          </Section>

          {/* VIP & Blocklist */}
          <Section title="VIP Routing & Blocklist" description="Force the AI to always (or never) alert you for specific senders." icon={Shield}>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
              <EmailList
                label="Always Alert (VIP)" badge="Score = 100"
                badgeColor="text-brand-400 bg-brand-500/10"
                items={vipList}
                onRemove={(v) => setVipList((p) => p.filter((x) => x !== v))}
                onAdd={(v) => setVipList((p) => [...p, v])}
              />
              <EmailList
                label="Never Alert (Block)" badge="Score = 0"
                badgeColor="text-text-tertiary bg-surface-raised border border-border-subtle"
                items={blockList}
                onRemove={(v) => setBlockList((p) => p.filter((x) => x !== v))}
                onAdd={(v) => setBlockList((p) => [...p, v])}
              />
            </div>
          </Section>

          {/* Security */}
          <Section title="Data & Security" icon={Shield}>
            <div className="flex items-center justify-between gap-4 p-4 rounded-xl border border-alert/20 bg-alert/5">
              <div>
                <p className="font-medium text-sm text-alert">Delete Account & Data</p>
                <p className="text-xs text-text-secondary mt-1">Permanently remove your account, tokens, and all email metadata.</p>
              </div>
              <button className="px-4 py-2 rounded-lg bg-alert text-white text-xs font-semibold hover:bg-alert/90 transition-colors shrink-0">
                Delete Account
              </button>
            </div>
          </Section>

        </div>
      </div>
    </div>
  );
}
