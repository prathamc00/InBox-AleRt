"use client";

import { useEffect, useMemo, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Sparkles, Search, Bot, X, RefreshCw } from "lucide-react";
import { api } from "@/lib/api";

type FilterTab = "Priority" | "Auto-Replied" | "Archived";

type InboxEmail = {
  id: string;
  sender_name: string;
  sender_email: string;
  subject: string;
  ai_summary: string;
  importance_score: number;
  received_at: string;
  status: string;
  auto_replied: boolean;
  auto_reply_content?: string | null;
};

function ScoreBadge({ score }: { score: number }) {
  const isHigh = score >= 90;
  return (
    <div
      className={`px-2 py-0.5 rounded text-[11px] font-bold tracking-wide ${
        isHigh
          ? "bg-brand-500/10 text-brand-400 border border-brand-500/20"
          : "bg-surface-raised text-text-secondary border border-border-subtle"
      }`}
    >
      {score}
    </div>
  );
}

function filterToApiParam(tab: FilterTab): string {
  if (tab === "Priority") return "important";
  if (tab === "Auto-Replied") return "auto_replied";
  return "all";
}

export default function DashboardPage() {
  const [tab, setTab] = useState<FilterTab>("Priority");
  const [emails, setEmails] = useState<InboxEmail[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [selectedEmailId, setSelectedEmailId] = useState<string | null>(null);

  const selectedEmail = useMemo(
    () => emails.find((e) => e.id === selectedEmailId) ?? null,
    [emails, selectedEmailId]
  );

  const fetchEmails = async () => {
    setLoading(true);
    setError("");
    try {
      const response = await api.get<InboxEmail[]>("/api/emails", {
        params: { filter_type: filterToApiParam(tab) },
      });
      setEmails(response.data ?? []);
      if (response.data.length > 0 && !selectedEmailId) {
        setSelectedEmailId(response.data[0].id);
      }
      if (selectedEmailId && !response.data.some((e) => e.id === selectedEmailId)) {
        setSelectedEmailId(response.data[0]?.id ?? null);
      }
    } catch (err) {
      console.error("Failed to fetch inbox emails:", err);
      setError("Could not load inbox intelligence.");
      setEmails([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchEmails();
  }, [tab]);

  return (
    <div className="flex flex-col h-full relative">
      <div className="absolute top-0 right-0 w-[500px] h-[500px] bg-brand-500/5 blur-[120px] rounded-full pointer-events-none" />

      <header className="h-auto md:h-20 border-b border-border-subtle flex flex-col md:flex-row md:items-center justify-between p-4 md:px-8 shrink-0 relative z-10 bg-void/50 backdrop-blur-md gap-4">
        <h1 className="text-lg md:text-xl font-semibold tracking-tight">Intelligence Dashboard</h1>

        <div className="flex flex-wrap items-center gap-3 w-full md:w-auto">
          <div className="relative flex-1 md:flex-initial">
            <Search className="w-4 h-4 absolute left-3 top-1/2 -translate-y-1/2 text-text-tertiary" />
            <input
              type="text"
              placeholder="Search intelligence..."
              className="w-full md:w-64 bg-surface-raised border border-border-subtle rounded-full py-1.5 pl-9 pr-4 text-sm focus:outline-none focus:border-brand-500/50 transition-colors"
            />
          </div>
          <button
            onClick={fetchEmails}
            className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-surface-raised border border-border-subtle hover:bg-surface transition-colors"
          >
            <RefreshCw className="w-3.5 h-3.5 text-text-secondary" />
            <span className="text-xs font-semibold text-text-secondary">Refresh</span>
          </button>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-full bg-brand-500/10 border border-brand-500/20">
            <Sparkles className="w-3.5 h-3.5 text-brand-400" />
            <span className="text-xs font-semibold text-brand-400">AI Active</span>
          </div>
        </div>
      </header>

      <div className="flex-1 flex overflow-hidden relative z-10">
        <div className={`flex flex-col border-r border-border-subtle transition-all duration-300 ${selectedEmail ? "hidden md:flex md:w-1/2 lg:w-5/12" : "w-full"}`}>
          <div className="p-4 md:p-6 pb-0 border-b border-border-subtle flex items-center gap-6 overflow-x-auto scrollbar-none">
            {(["Priority", "Auto-Replied", "Archived"] as FilterTab[]).map((t) => (
              <button
                key={t}
                onClick={() => setTab(t)}
                className={`pb-3 text-sm font-medium transition-colors relative shrink-0 ${tab === t ? "text-white" : "text-text-secondary hover:text-white"}`}
              >
                {t}
                {tab === t && <motion.div layoutId="activeTab" className="absolute bottom-0 inset-x-0 h-0.5 bg-brand-500" />}
              </button>
            ))}
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-2">
            {loading ? (
              <div className="p-8 text-sm text-text-tertiary">Loading inbox intelligence...</div>
            ) : error ? (
              <div className="p-8 text-sm text-alert">{error}</div>
            ) : emails.length === 0 ? (
              <div className="p-8 text-sm text-text-tertiary">No processed emails yet. Use Integrations and click Sync Now to pull latest messages.</div>
            ) : (
              emails.map((email, i) => (
                <motion.div
                  key={email.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                  onClick={() => setSelectedEmailId(email.id)}
                  className={`group flex flex-col p-4 rounded-xl border transition-all cursor-pointer ${
                    selectedEmailId === email.id
                      ? "bg-brand-500/10 border-brand-500/30 shadow-[0_0_20px_rgba(99,102,241,0.05)]"
                      : "bg-surface hover:bg-surface-raised border-transparent hover:border-border-subtle"
                  }`}
                >
                  <div className="flex items-center justify-between mb-2">
                    <div className="flex items-center gap-2 truncate pr-4">
                      <div className="w-6 h-6 rounded bg-surface-raised flex items-center justify-center text-[10px] font-bold text-text-secondary shrink-0">
                        {(email.sender_name || email.sender_email || "?")[0]}
                      </div>
                      <span className="text-sm font-semibold text-white truncate">{email.sender_name || email.sender_email}</span>
                      <span className="text-xs text-text-tertiary hidden xl:inline-block truncate">&lt;{email.sender_email}&gt;</span>
                    </div>
                    <div className="flex items-center gap-2 shrink-0">
                      <span className="text-[11px] text-text-tertiary shrink-0">
                        {new Date(email.received_at).toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                      </span>
                      <ScoreBadge score={email.importance_score ?? 0} />
                    </div>
                  </div>

                  <div className="flex items-center gap-2 mb-1.5">
                    <p className={`text-sm truncate ${selectedEmailId === email.id ? "text-brand-400 font-semibold" : "text-white font-medium"}`}>
                      {email.subject}
                    </p>
                    {email.status === "auto_replied" && (
                      <span className="shrink-0 text-[10px] uppercase tracking-wider font-bold text-green-400 bg-green-500/10 px-1.5 py-0.5 rounded border border-green-500/20">
                        Auto-Replied
                      </span>
                    )}
                    {email.status === "cancelled" && (
                      <span className="shrink-0 text-[10px] uppercase tracking-wider font-bold text-red-400 bg-red-500/10 px-1.5 py-0.5 rounded border border-red-500/20">
                        Cancelled
                      </span>
                    )}
                    {email.status === "alerted" && email.auto_replied && (
                      <span className="shrink-0 text-[10px] uppercase tracking-wider font-bold text-amber-400 bg-amber-500/10 px-1.5 py-0.5 rounded border border-amber-500/20">
                        Auto-Reply Pending
                      </span>
                    )}
                  </div>

                  <p className="text-xs text-text-secondary line-clamp-2 leading-relaxed">
                    <Sparkles className="w-3 h-3 inline-block mr-1 text-brand-500/70" />
                    {email.ai_summary}
                  </p>
                </motion.div>
              ))
            )}
          </div>
        </div>

        <AnimatePresence>
          {selectedEmail && (
            <motion.div
              initial={{ opacity: 0, x: 20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              className="flex-1 flex flex-col bg-void overflow-hidden"
            >
              <div className="h-16 border-b border-border-subtle flex items-center justify-between px-4 md:px-6 shrink-0 bg-surface/50">
                <div className="text-xs text-text-tertiary uppercase tracking-wider">Status: {selectedEmail.status}</div>
                <button
                  onClick={() => setSelectedEmailId(null)}
                  className="p-2 text-text-tertiary hover:text-white rounded-lg transition-colors"
                >
                  <X className="w-5 h-5" />
                </button>
              </div>

              <div className="flex-1 overflow-y-auto p-4 md:p-8">
                <div className="mb-8 p-5 rounded-2xl bg-gradient-to-br from-brand-500/10 to-surface border border-brand-500/20">
                  <div className="flex items-center gap-2 mb-3">
                    <Sparkles className="w-4 h-4 text-brand-400" />
                    <h3 className="font-semibold text-brand-400 text-sm tracking-wide uppercase">AI Analysis</h3>
                  </div>
                  <p className="text-sm text-slate-200 leading-relaxed max-w-xl">{selectedEmail.ai_summary}</p>
                </div>

                <div className="max-w-2xl">
                  <h2 className="text-xl md:text-2xl font-bold text-white mb-6 leading-snug">{selectedEmail.subject}</h2>

                  <div className="flex items-center gap-4 mb-8">
                    <div className="w-10 h-10 rounded-full bg-gradient-to-tr from-brand-600 to-accent flex items-center justify-center font-bold text-white shrink-0">
                      {(selectedEmail.sender_name || selectedEmail.sender_email || "?")[0]}
                    </div>
                    <div className="min-w-0">
                      <p className="font-semibold text-white truncate">{selectedEmail.sender_name || selectedEmail.sender_email}</p>
                      <p className="text-xs text-text-tertiary break-all">
                        {selectedEmail.sender_email} • {new Date(selectedEmail.received_at).toLocaleString()}
                      </p>
                    </div>
                  </div>

                  <div className="text-sm text-text-secondary leading-relaxed">
                    Raw body is intentionally not stored for privacy. Use the connected mailbox for full thread context.
                  </div>
                </div>

                {selectedEmail.auto_reply_content && (
                  <div className="mt-12 max-w-2xl">
                    <div className="flex items-center gap-2 mb-4">
                      <Bot className="w-4 h-4 text-accent" />
                      <h4 className="text-xs font-bold uppercase tracking-widest text-text-secondary">Auto Reply</h4>
                    </div>
                    <div className="p-5 rounded-xl border border-border-subtle bg-surface-raised/50 text-sm text-text-secondary leading-relaxed">
                      {selectedEmail.auto_reply_content}
                    </div>
                  </div>
                )}
              </div>
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </div>
  );
}
