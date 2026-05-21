"use client";

import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Plus, AlertCircle, RefreshCw } from "lucide-react";
import { cn } from "@/lib/utils";
import { api } from "@/lib/api";

interface ConnectedAccount {
  id: string;
  provider: "gmail" | "outlook";
  email_address: string;
  is_active: boolean;
  last_sync?: string;
}

export default function AccountsPage() {
  const [accounts, setAccounts] = useState<ConnectedAccount[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [syncingId, setSyncingId] = useState<string | null>(null);
  const [syncStatus, setSyncStatus] = useState<Record<string, { ok: boolean; msg: string }>>({});

  useEffect(() => {
    fetchAccounts();
  }, []);

  const fetchAccounts = async () => {
    try {
      const response = await api.get<ConnectedAccount[]>("/api/v1/accounts");
      setAccounts(response.data);
    } catch (err) {
      console.error("Failed to fetch accounts:", err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleRemoveAccount = async (id: string) => {
    if (!confirm("Are you sure you want to remove this account?")) return;
    try {
      await api.delete(`/api/v1/accounts/${id}`);
      setAccounts((prev) => prev.filter((a) => a.id !== id));
    } catch (err) {
      console.error("Failed to delete account:", err);
    }
  };

  const handleSyncNow = async (id: string) => {
    setSyncingId(id);
    setSyncStatus((prev) => ({ ...prev, [id]: undefined as any }));
    try {
      const response = await api.post<{ ok: boolean; queued: number }>(`/api/v1/accounts/${id}/sync`);
      const msg = response.data.queued > 0
        ? `${response.data.queued} message${response.data.queued > 1 ? "s" : ""} queued for processing`
        : "Inbox is up to date";
      setSyncStatus((prev) => ({ ...prev, [id]: { ok: true, msg } }));
      setTimeout(() => setSyncStatus((prev) => { const n = { ...prev }; delete n[id]; return n; }), 4000);
    } catch (err: any) {
      const detail = err?.response?.data?.detail ?? "Sync failed. Check backend/worker logs.";
      setSyncStatus((prev) => ({ ...prev, [id]: { ok: false, msg: detail } }));
      setTimeout(() => setSyncStatus((prev) => { const n = { ...prev }; delete n[id]; return n; }), 6000);
    } finally {
      setSyncingId(null);
    }
  };

  const handleConnectGoogle = () => {
    const token = localStorage.getItem("access_token");
    const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const redirectUrl = token
      ? `${baseUrl}/auth/google/login?token=${encodeURIComponent(token)}`
      : `${baseUrl}/auth/google/login`;
    window.location.href = redirectUrl;
  };

  const handleConnectMicrosoft = () => {
    const token = localStorage.getItem("access_token");
    const baseUrl = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    const redirectUrl = token
      ? `${baseUrl}/auth/microsoft/login?token=${encodeURIComponent(token)}`
      : `${baseUrl}/auth/microsoft/login`;
    window.location.href = redirectUrl;
  };

  return (
    <div className="flex flex-col h-full bg-void">
      {/* Header */}
      <header className="h-16 border-b border-border-subtle flex items-center justify-between px-8 shrink-0 sticky top-0 bg-void/80 backdrop-blur-md z-10">
        <h1 className="text-lg font-semibold tracking-tight text-text-primary">Integrations</h1>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="w-full max-w-6xl p-8 pt-6">
          <p className="text-sm text-text-secondary mb-10">
            Connect your inboxes. The AI will securely process incoming mail via webhooks without storing your emails.
          </p>

          <div className="space-y-6">
            
            {/* Connected Accounts */}
            <div>
              <h2 className="text-sm font-semibold text-text-primary mb-4">Active Connections</h2>
              <div className="space-y-3">
                {isLoading ? (
                  <div className="p-8 text-center text-text-tertiary">Loading accounts...</div>
                ) : accounts.length === 0 ? (
                  <div className="p-8 text-center border border-dashed border-border-subtle rounded-xl text-text-tertiary">
                    No accounts connected yet.
                  </div>
                ) : accounts.map((account, i) => (
                  <div key={account.id}>
                  <motion.div
                    initial={{ opacity: 0, y: 5 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.1 }}
                    className={cn(
                      "flex items-center justify-between p-4 rounded-xl border transition-all",
                      account.is_active 
                        ? "bg-surface border-border-subtle hover:border-border-strong" 
                        : "bg-surface border-alert/30"
                    )}
                  >
                    <div className="flex items-center gap-4">
                      {/* Provider Icon */}
                      <div className="w-10 h-10 rounded-lg bg-surface-raised border border-border-subtle flex items-center justify-center shrink-0">
                        {account.provider === "gmail" ? (
                          <svg className="w-5 h-5" viewBox="0 0 24 24">
                            <path fill="#EA4335" d="M12 13L2.2 6.5C2.6 5.6 3.5 5 4.5 5h15c1 0 1.9.6 2.3 1.5L12 13z"/>
                            <path fill="#34A853" d="M22 6.5V19c0 1.1-.9 2-2 2h-4.5v-9L22 6.5z"/>
                            <path fill="#4285F4" d="M2 6.5V19c0 1.1.9 2 2 2h4.5v-9L2 6.5z"/>
                            <path fill="#FBBC05" d="M12 13L2.2 6.5A2.99 2.99 0 0 0 2 8v1.5l10 6.5 10-6.5V8a3.1 3.1 0 0 0-.2-1.5L12 13z"/>
                          </svg>
                        ) : (
                          <svg className="w-5 h-5" viewBox="0 0 24 24">
                            <path fill="#00A4EF" d="M2 4.5h20v15H2z" opacity="0.1"/>
                            <path fill="#0078D4" d="M22 4.5H2v15h20v-15z"/>
                            <path fill="#005A9E" d="M2 4.5l10 7.5 10-7.5v-1H2v1z"/>
                            <path fill="#00A4EF" d="M2 18l7.5-6.5L2 10.5V18z"/>
                          </svg>
                        )}
                      </div>

                      <div>
                        <p className="font-medium text-sm text-text-primary">{account.email_address}</p>
                        <div className="flex items-center gap-2 mt-1">
                          <span className={cn(
                            "text-[10px] font-bold px-1.5 py-0.5 rounded uppercase tracking-wider",
                            account.is_active ? "bg-success/10 text-success" : "bg-alert/10 text-alert"
                          )}>
                            {account.is_active ? "Active" : "Action Required"}
                          </span>
                          <span className="text-xs text-text-tertiary flex items-center gap-1">
                            <RefreshCw className="w-3 h-3" />
                            {account.last_sync}
                          </span>
                        </div>
                      </div>
                    </div>

                    <div className="flex items-center gap-2">
                      <button
                        onClick={() => handleSyncNow(account.id)}
                        disabled={syncingId === account.id}
                        className="px-3 py-1.5 text-xs font-medium rounded-lg bg-surface-raised border border-border-subtle text-text-secondary hover:text-text-primary transition-colors disabled:opacity-60"
                      >
                        {syncingId === account.id ? "Syncing..." : "Sync Now"}
                      </button>
                      {!account.is_active && (
                        <button 
                          onClick={account.provider === "gmail" ? handleConnectGoogle : handleConnectMicrosoft}
                          className="px-3 py-1.5 text-xs font-medium rounded-lg bg-alert text-white hover:bg-alert/90 transition-colors flex items-center gap-1.5"
                        >
                          <AlertCircle className="w-3.5 h-3.5" />
                          Reconnect
                        </button>
                      )}
                      <button 
                        onClick={() => handleRemoveAccount(account.id)}
                        className="px-3 py-1.5 text-xs font-medium rounded-lg bg-surface-raised border border-border-subtle text-text-secondary hover:text-alert hover:border-alert/50 transition-colors"
                      >
                        Remove
                      </button>
                    </div>
                  </motion.div>
                  {syncStatus[account.id] && (
                    <p className={cn(
                      "text-xs px-1 mt-1",
                      syncStatus[account.id].ok ? "text-success" : "text-alert"
                    )}>
                      {syncStatus[account.id].msg}
                    </p>
                  )}
                  </div>
                ))}
              </div>
            </div>

            {/* Add New */}
            <div className="pt-6">
              <h2 className="text-sm font-semibold text-text-primary mb-4">Add Account</h2>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                
                <button 
                  onClick={handleConnectGoogle}
                  className="group flex items-center gap-4 p-4 rounded-xl border border-dashed border-border-strong hover:border-text-tertiary bg-void hover:bg-surface-raised transition-all text-left"
                >
                  <div className="w-10 h-10 rounded-full bg-surface-raised flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform border border-border-subtle">
                    <Plus className="w-5 h-5 text-text-secondary group-hover:text-text-primary" />
                  </div>
                  <div>
                    <p className="font-medium text-sm text-text-primary">Connect Gmail</p>
                    <p className="text-xs text-text-secondary mt-0.5">Google Workspace or personal</p>
                  </div>
                </button>

                <button 
                  onClick={handleConnectMicrosoft}
                  className="group flex items-center gap-4 p-4 rounded-xl border border-dashed border-border-strong hover:border-text-tertiary bg-void hover:bg-surface-raised transition-all text-left"
                >
                  <div className="w-10 h-10 rounded-full bg-surface-raised flex items-center justify-center shrink-0 group-hover:scale-105 transition-transform border border-border-subtle">
                    <Plus className="w-5 h-5 text-text-secondary group-hover:text-text-primary" />
                  </div>
                  <div>
                    <p className="font-medium text-sm text-text-primary">Connect Outlook</p>
                    <p className="text-xs text-text-secondary mt-0.5">Microsoft 365 or personal</p>
                  </div>
                </button>

              </div>
            </div>

          </div>
        </div>
      </div>
    </div>
  );
}
