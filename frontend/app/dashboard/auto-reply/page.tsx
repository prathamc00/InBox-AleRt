"use client";

import { useState, useEffect, useCallback } from "react";
import { Bot, Shield, Clock, Zap, Info, SlidersHorizontal, CheckCircle2, AlertCircle, Loader2 } from "lucide-react";
import { cn } from "@/lib/utils";
import { api, AutoReplyConfig } from "@/lib/api";

// ── Small components ───────────────────────────────────────────────────────────

function Toggle({
  enabled, onChange,
}: {
  enabled: boolean; onChange: (v: boolean) => void;
}) {
  return (
    <button
      onClick={() => onChange(!enabled)}
      className={cn(
        "relative shrink-0 rounded-full transition-all duration-200 ease-in-out border",
        "w-10 h-5",
        enabled
          ? "bg-white border-white"
          : "bg-surface-raised border-border-strong hover:border-text-tertiary"
      )}
    >
      <span
        className={cn(
          "absolute top-[1px] rounded-full transition-all duration-200 shadow-sm",
          "w-4 h-4",
          enabled ? "left-[19px] bg-black" : "left-[1px] bg-text-tertiary"
        )}
      />
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
      <div className="pl-0 sm:pl-12 space-y-6">{children}</div>
    </div>
  );
}

// ── Defaults ───────────────────────────────────────────────────────────────────

const DEFAULT_CONFIG: AutoReplyConfig = {
  is_enabled: false,
  dry_run: true,
  min_importance_score: 90,
  reply_tone: "professional",
  daily_auto_reply_limit: 50,
  cancel_window_seconds: 60,
  business_hours_only: false,
  business_hours_start: "09:00",
  business_hours_end: "18:00",
  timezone: "UTC",
};

type SaveState = "idle" | "saving" | "success" | "error";

// ── Main Page ──────────────────────────────────────────────────────────────────

export default function AutoReplyPage() {
  const [cfg, setCfg] = useState<AutoReplyConfig>(DEFAULT_CONFIG);
  const [loading, setLoading] = useState(true);
  const [saveState, setSaveState] = useState<SaveState>("idle");
  const [errorMsg, setErrorMsg] = useState("");

  // ── Load from API ────────────────────────────────────────────────────────────
  useEffect(() => {
    api.get<AutoReplyConfig>("/api/v1/auto-reply")
      .then((response) => setCfg(response.data))
      .catch(() => { /* Use defaults in dev */ })
      .finally(() => setLoading(false));
  }, []);

  const update = useCallback(<K extends keyof AutoReplyConfig>(
    key: K, value: AutoReplyConfig[K]
  ) => setCfg((prev) => ({ ...prev, [key]: value })), []);

  // ── Save handler ─────────────────────────────────────────────────────────────
  const handleSave = useCallback(async () => {
    setSaveState("saving");
    setErrorMsg("");
    try {
      const response = await api.put<AutoReplyConfig>("/api/v1/auto-reply", cfg);
      setCfg(response.data);
      setSaveState("success");
      setTimeout(() => setSaveState("idle"), 2500);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Failed to save";
      setErrorMsg(msg);
      setSaveState("error");
      setTimeout(() => setSaveState("idle"), 3000);
    }
  }, [cfg]);

  // ── Save button ──────────────────────────────────────────────────────────────
  const SaveButton = () => {
    if (saveState === "saving") return (
      <button disabled className="w-full sm:w-auto px-6 py-2.5 rounded-lg bg-white/60 text-black text-sm font-bold flex items-center justify-center gap-2 opacity-70">
        <Loader2 className="w-4 h-4 animate-spin" /> Saving...
      </button>
    );
    if (saveState === "success") return (
      <button disabled className="w-full sm:w-auto px-6 py-2.5 rounded-lg bg-green-500 text-white text-sm font-bold flex items-center justify-center gap-2">
        <CheckCircle2 className="w-4 h-4" /> Saved
      </button>
    );
    if (saveState === "error") return (
      <button onClick={handleSave} className="w-full sm:w-auto px-6 py-2.5 rounded-lg bg-alert text-white text-sm font-bold flex items-center justify-center gap-2">
        <AlertCircle className="w-4 h-4" /> Retry
      </button>
    );
    return (
      <button
        onClick={handleSave}
        className="w-full sm:w-auto px-6 py-2.5 rounded-lg bg-white text-black text-sm font-bold hover:bg-gray-200 transition-colors shadow-sm"
      >
        Save Configuration
      </button>
    );
  };

  return (
    <div className="flex flex-col h-full bg-void">
      {/* Header */}
      <header className="h-16 border-b border-border-subtle flex items-center justify-between px-4 md:px-8 shrink-0 sticky top-0 bg-void/80 backdrop-blur-md z-10">
        <div className="flex items-center gap-2 min-w-0">
          <Bot className="w-4 h-4 text-text-secondary shrink-0" />
          <h1 className="text-lg font-semibold tracking-tight text-text-primary truncate">Autonomous Mode</h1>
          <span className="px-2 py-0.5 rounded-md bg-surface-raised border border-border-subtle text-[10px] font-medium text-text-tertiary uppercase tracking-wider shrink-0">
            Beta
          </span>
        </div>

        <div className="flex items-center gap-3 shrink-0">
          <span className="text-sm font-medium text-text-secondary hidden xs:inline">Master Switch</span>
          <Toggle enabled={cfg.is_enabled} onChange={(v) => update("is_enabled", v)} />
        </div>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className={cn("w-full max-w-5xl p-4 md:p-8 pt-6 transition-opacity", loading && "opacity-40 pointer-events-none")}>
          <p className="text-sm text-text-secondary mb-8">
            Configure how the AI handles incoming emails when Autonomous Mode is active.
            The AI will only draft replies for emails that meet your defined priority thresholds.
          </p>

          {saveState === "error" && (
            <div className="flex items-center gap-2 mb-6 p-3 rounded-xl border border-alert/30 bg-alert/5 text-alert text-sm">
              <AlertCircle className="w-4 h-4 shrink-0" />
              {errorMsg}
            </div>
          )}

          <div className={cn("transition-opacity duration-300", !cfg.is_enabled && "opacity-50 pointer-events-none")}>

            {/* Safety */}
            <Section
              title="Safety & Guardrails"
              description="Control the level of autonomy the AI has over your inbox."
              icon={Shield}
            >
              <div className="flex items-center justify-between gap-4 p-4 rounded-xl border border-border-subtle bg-surface">
                <div>
                  <p className="text-sm font-medium text-text-primary">Dry-run mode</p>
                  <p className="text-xs text-text-secondary mt-1">
                    AI drafts the reply but waits for your explicit approval before sending.
                  </p>
                </div>
                <Toggle enabled={cfg.dry_run} onChange={(v) => update("dry_run", v)} />
              </div>

              {!cfg.dry_run && (
                <div className="flex items-start gap-3 p-4 rounded-xl border border-yellow-500/20 bg-yellow-500/5 text-yellow-400 text-sm">
                  <Info className="w-4 h-4 shrink-0 mt-0.5" />
                  <p>
                    Dry-run is disabled. Replies will be sent automatically after the cancellation
                    window. Ensure your minimum score threshold is configured correctly.
                  </p>
                </div>
              )}

              <div className="space-y-3">
                <div className="flex justify-between">
                  <p className="text-sm font-medium text-text-primary">Cancellation Window</p>
                  <span className="text-sm font-medium text-text-secondary tabular-nums">{cfg.cancel_window_seconds}s</span>
                </div>
                <input
                  type="range" min={15} max={300} step={15}
                  value={cfg.cancel_window_seconds}
                  onChange={(e) => update("cancel_window_seconds", Number(e.target.value))}
                  className="w-full accent-white"
                />
                <p className="text-xs text-text-tertiary">
                  Time delay before the email is actually dispatched. You will receive a WhatsApp
                  alert during this window with an option to abort.
                </p>
              </div>
            </Section>

            {/* Triggers */}
            <Section
              title="Trigger Thresholds"
              description="Determine which emails qualify for an automatic response."
              icon={SlidersHorizontal}
            >
              <div className="space-y-3">
                <div className="flex justify-between">
                  <p className="text-sm font-medium text-text-primary">Minimum Importance Score</p>
                  <span className="text-sm font-medium text-text-secondary tabular-nums">{cfg.min_importance_score}</span>
                </div>
                <input
                  type="range" min={80} max={99}
                  value={cfg.min_importance_score}
                  onChange={(e) => update("min_importance_score", Number(e.target.value))}
                  className="w-full accent-white"
                />
                <p className="text-xs text-text-tertiary">
                  Only emails scored at or above this threshold by the AI will trigger a response.
                </p>
              </div>

              <div className="pt-4">
                <p className="text-sm font-medium text-text-primary mb-3">AI Persona / Tone</p>
                <div className="flex gap-2">
                  {(["professional", "friendly", "brief"] as const).map((t) => (
                    <button
                      key={t}
                      onClick={() => update("reply_tone", t)}
                      className={cn(
                        "px-4 py-2 text-sm font-medium rounded-lg border transition-all capitalize",
                        cfg.reply_tone === t
                          ? "bg-white text-black border-white"
                          : "bg-surface border-border-subtle text-text-secondary hover:text-text-primary hover:bg-surface-raised"
                      )}
                    >
                      {t}
                    </button>
                  ))}
                </div>
              </div>
            </Section>

            {/* Schedule */}
            <Section
              title="Operational Schedule"
              description="Restrict autonomous actions to specific times of the day."
              icon={Clock}
            >
              <div className="flex items-center justify-between gap-4">
                <div>
                  <p className="text-sm font-medium text-text-primary">Business hours only</p>
                  <p className="text-xs text-text-secondary mt-1">Halt auto-replies outside of your configured working hours.</p>
                </div>
                <Toggle enabled={cfg.business_hours_only} onChange={(v) => update("business_hours_only", v)} />
              </div>

              {cfg.business_hours_only && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 pt-2">
                  <div>
                    <label className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">Start Time</label>
                    <input
                      type="time" value={cfg.business_hours_start}
                      onChange={(e) => update("business_hours_start", e.target.value)}
                      className="w-full bg-surface border border-border-subtle rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-text-tertiary transition-colors"
                    />
                  </div>
                  <div>
                    <label className="block text-xs font-medium text-text-secondary mb-1.5 uppercase tracking-wider">End Time</label>
                    <input
                      type="time" value={cfg.business_hours_end}
                      onChange={(e) => update("business_hours_end", e.target.value)}
                      className="w-full bg-surface border border-border-subtle rounded-lg px-3 py-2 text-sm text-text-primary focus:outline-none focus:border-text-tertiary transition-colors"
                    />
                  </div>
                </div>
              )}
            </Section>

            {/* Limits */}
            <Section title="Rate Limits" icon={Zap}>
              <div className="space-y-3">
                <div className="flex justify-between">
                  <p className="text-sm font-medium text-text-primary">Daily Dispatches Limit</p>
                  <span className="text-sm font-medium text-text-secondary tabular-nums">{cfg.daily_auto_reply_limit}</span>
                </div>
                <input
                  type="range" min={5} max={100} step={5}
                  value={cfg.daily_auto_reply_limit}
                  onChange={(e) => update("daily_auto_reply_limit", Number(e.target.value))}
                  className="w-full accent-white"
                />
                <p className="text-xs text-text-tertiary">
                  Maximum number of autonomous replies the AI is allowed to send per 24-hour period.
                </p>
              </div>
            </Section>

            {/* Save */}
            <div className="pt-8 pb-12">
              <SaveButton />
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
