"use client";

import { Check, CreditCard, Sparkles, ExternalLink } from "lucide-react";
import { useState } from "react";
import { useAuthStore } from "@/store/auth";
import { api } from "@/lib/api";

export default function BillingPage() {
  const { user } = useAuthStore();
  const [loading, setLoading] = useState(false);
  const isPro = user?.role === "pro" || false;

  const handleCheckout = async (plan: string) => {
    setLoading(true);
    try {
      const { data } = await api.post(`/billing/checkout?plan=${plan}`);
      window.location.href = data.url;
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  const handlePortal = async () => {
    setLoading(true);
    try {
      const { data } = await api.post(`/billing/portal`);
      window.location.href = data.url;
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full bg-void">
      {/* Header */}
      <header className="h-16 border-b border-border-subtle flex items-center justify-between px-8 shrink-0 sticky top-0 bg-void/80 backdrop-blur-md z-10">
        <h1 className="text-lg font-semibold tracking-tight text-text-primary">Billing & Subscription</h1>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        <div className="w-full max-w-6xl p-8 pt-6">
          
          {/* Current Status */}
          <div className="p-6 rounded-2xl border border-border-subtle bg-surface mb-10 flex flex-col md:flex-row md:items-center justify-between gap-4">
            <div>
              <p className="text-sm text-text-secondary mb-1 uppercase tracking-wider font-medium text-[10px]">Current Plan</p>
              <div className="flex items-center gap-3">
                <h2 className="text-2xl font-bold tracking-tight text-text-primary">
                  {isPro ? "Elite Plan" : "Basic Tier"}
                </h2>
                {isPro && (
                  <span className="px-2 py-0.5 rounded bg-white text-black text-[10px] font-bold flex items-center gap-1 uppercase tracking-widest">
                    <Sparkles className="w-3 h-3" />
                    Active
                  </span>
                )}
              </div>
            </div>
            
            {isPro ? (
              <button 
                onClick={handlePortal}
                disabled={loading}
                className="px-4 py-2 rounded-lg bg-surface-raised border border-border-strong hover:border-text-tertiary text-sm font-medium transition-all flex items-center gap-2 text-text-primary"
              >
                <CreditCard className="w-4 h-4" />
                Manage Billing
                <ExternalLink className="w-3.5 h-3.5 text-text-tertiary" />
              </button>
            ) : (
              <p className="text-sm text-text-secondary">
                You are currently limited to 50 AI scans/day.
              </p>
            )}
          </div>

          {/* Pricing Tables */}
          {!isPro && (
            <div className="p-8 rounded-2xl border border-border-subtle bg-surface text-center">
              <h3 className="text-lg font-semibold mb-2 text-text-primary">Premium Plans</h3>
              <p className="text-sm text-text-secondary">Coming soon.</p>
            </div>
          )}

        </div>
      </div>
    </div>
  );
}
