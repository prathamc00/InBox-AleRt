"use client";

import { useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import { useAuthStore } from "@/store/auth";
import { motion } from "framer-motion";
import { Loader2, AlertCircle } from "lucide-react";

function CallbackHandler() {
  const router = useRouter();
  const params = useSearchParams();
  const setAuth = useAuthStore((s) => s.setAuth);

  useEffect(() => {
    const error = params.get("error");
    const accessToken = params.get("access_token");
    const refreshToken = params.get("refresh_token");
    const isNewUser = params.get("is_new_user") === "true";

    if (error) {
      router.replace("/login?error=oauth_failed");
      return;
    }

    if (!accessToken || !refreshToken) {
      router.replace("/login");
      return;
    }

    // Build user object from URL params (sent by backend redirect)
    const user = {
      id: params.get("user_id") ?? "",
      email: params.get("email") ?? "",
      display_name: params.get("display_name") ?? "",
      avatar_url: params.get("avatar_url") ?? undefined,
      role: params.get("role") ?? "owner",
    };

    setAuth(user, accessToken, refreshToken);

    router.replace(isNewUser ? "/onboarding" : "/dashboard");
  }, [params, router, setAuth]);

  return (
    <div className="min-h-screen bg-void flex flex-col items-center justify-center gap-6">
      <motion.div
        animate={{ rotate: 360 }}
        transition={{ repeat: Infinity, duration: 1, ease: "linear" }}
      >
        <Loader2 className="w-10 h-10 text-white" />
      </motion.div>
      <div className="text-center">
        <p className="text-white font-semibold">Signing you in securely…</p>
        <p className="text-text-tertiary text-sm mt-1">Setting up your account</p>
      </div>
    </div>
  );
}

export default function AuthCallbackPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen bg-void flex items-center justify-center">
          <Loader2 className="w-10 h-10 text-white animate-spin" />
        </div>
      }
    >
      <CallbackHandler />
    </Suspense>
  );
}
