"use client";

import { motion } from "framer-motion";
import { BellRing, Shield, ArrowRight } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuthStore } from "@/store/auth";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

export default function LoginPage() {
  const router = useRouter();
  const setAuth = useAuthStore((s) => s.setAuth);

  const handleGoogleLogin = () => {
    window.location.href = `${API_URL}/auth/google/login`;
  };

  const handleMicrosoftLogin = () => {
    window.location.href = `${API_URL}/auth/microsoft/login`;
  };

  return (
    <div className="min-h-screen bg-void flex items-center justify-center relative overflow-hidden px-4">
      {/* Background blobs */}
      <div className="absolute top-[-20%] left-[-10%] w-[50%] h-[50%] rounded-full bg-white/3 blur-[140px] pointer-events-none" />
      <div className="absolute bottom-[-20%] right-[-10%] w-[40%] h-[40%] rounded-full bg-white/2 blur-[120px] pointer-events-none" />

      <motion.div
        initial={{ opacity: 0, y: 30 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md z-10"
      >
        {/* Logo */}
        <div className="flex flex-col items-center mb-10">
          <div className="w-12 h-12 rounded-2xl bg-white flex items-center justify-center mb-4">
            <BellRing className="w-6 h-6 text-black" />
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">InboxAlert</h1>
          <p className="text-text-secondary mt-2 text-center text-sm">
            Connect your inbox. Let AI decide what matters.
          </p>
        </div>

        {/* Card */}
        <div className="bg-surface border border-border-subtle rounded-2xl p-8">
          <h2 className="text-xl font-semibold mb-1 text-white">Sign in</h2>
          <p className="text-text-secondary text-sm mb-8">
            We use OAuth — we never see your password.
          </p>

          <div className="flex flex-col gap-3">
            {/* Google */}
            <button
              onClick={handleGoogleLogin}
              className="group flex items-center justify-between w-full px-5 py-3.5 rounded-xl bg-surface-raised border border-border-subtle hover:border-border-strong transition-all"
            >
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                  <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                  <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                  <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
                </svg>
                <span className="font-medium text-sm text-white">Continue with Google</span>
              </div>
              <ArrowRight className="w-4 h-4 text-text-tertiary group-hover:text-white group-hover:translate-x-1 transition-all" />
            </button>

            {/* Microsoft */}
            <button
              onClick={handleMicrosoftLogin}
              className="group flex items-center justify-between w-full px-5 py-3.5 rounded-xl bg-surface-raised border border-border-subtle hover:border-border-strong transition-all"
            >
              <div className="flex items-center gap-3">
                <svg className="w-5 h-5" viewBox="0 0 24 24">
                  <path fill="#F25022" d="M1 1h10v10H1z"/>
                  <path fill="#7FBA00" d="M13 1h10v10H13z"/>
                  <path fill="#00A4EF" d="M1 13h10v10H1z"/>
                  <path fill="#FFB900" d="M13 13h10v10H13z"/>
                </svg>
                <span className="font-medium text-sm text-white">Continue with Microsoft</span>
              </div>
              <ArrowRight className="w-4 h-4 text-text-tertiary group-hover:text-white group-hover:translate-x-1 transition-all" />
            </button>

          </div>

          {/* Security note */}
          <div className="mt-8 flex items-start gap-2 text-xs text-text-tertiary">
            <Shield className="w-3.5 h-3.5 mt-0.5 shrink-0 text-text-secondary" />
            <span>
              OAuth 2.0 only. We encrypt your tokens with AES-256-GCM and never store your raw email body.
            </span>
          </div>
        </div>

        {/* Back */}
        <p className="text-center text-sm text-text-tertiary mt-6">
          <Link href="/" className="hover:text-white transition-colors">
            ← Back to home
          </Link>
        </p>
      </motion.div>
    </div>
  );
}
