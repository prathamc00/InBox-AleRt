"use client";

import { motion } from "framer-motion";
import { 
  Mail, 
  Sparkles, 
  ChevronRight, 
  Activity, 
  ShieldCheck,
  Brain,
  MessageCircle,
  Zap,
  Lock,
  CheckCircle2,
  ArrowRight
} from "lucide-react";
import Link from "next/link";

export default function LandingPage() {
  return (
    <div className="min-h-screen mesh-bg flex flex-col relative overflow-hidden">
      {/* Navbar */}
      <nav className="fixed top-0 inset-x-0 h-20 z-50 flex items-center justify-between px-6 md:px-12 max-w-7xl mx-auto w-full backdrop-blur-md bg-void/50 border-b border-white/5">
        <div className="flex items-center gap-3">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center shadow-lg" style={{background: "linear-gradient(135deg, #6366f1, #8b5cf6)", boxShadow: "0 0 20px rgba(99,102,241,0.5)"}}>
            <Mail className="w-4 h-4 text-white" strokeWidth={2.5} />
          </div>
          <span className="font-bold text-xl tracking-wide text-white">InboxAlert<span style={{color: "#818cf8"}}>.</span></span>
        </div>
        <div className="flex items-center gap-6">
          <Link href="#features" className="hidden md:block text-sm font-medium text-text-secondary hover:text-white transition-colors">
            Features
          </Link>
          <Link href="#how-it-works" className="hidden md:block text-sm font-medium text-text-secondary hover:text-white transition-colors">
            How it Works
          </Link>
          <Link href="#pricing" className="hidden md:block text-sm font-medium text-text-secondary hover:text-white transition-colors">
            Pricing
          </Link>
          <Link 
            href="/login" 
            className="px-5 py-2.5 rounded-full bg-white text-void font-bold text-sm hover:bg-gray-200 transition-colors shadow-lg"
          >
            Log in
          </Link>
        </div>
      </nav>

      {/* Hero Section */}
      <section className="flex flex-col items-center justify-center text-center px-4 z-10 pt-40 pb-24">
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-full border border-brand-500/30 bg-brand-500/10 text-brand-400 text-sm font-semibold mb-8 backdrop-blur-md"
        >
          <Sparkles className="w-4 h-4" />
          <span>The next evolution of email is here</span>
        </motion.div>

        <motion.h1 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.1, ease: [0.16, 1, 0.3, 1] }}
          className="text-5xl md:text-8xl font-extrabold tracking-tighter max-w-5xl leading-[1.05] text-white"
        >
          Your inbox, <br className="hidden md:block" />
          <span className="text-transparent bg-clip-text bg-gradient-to-br from-brand-400 via-white to-white/40">
            filtered by intelligence.
          </span>
        </motion.h1>

        <motion.p 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.2, ease: [0.16, 1, 0.3, 1] }}
          className="mt-8 text-lg md:text-xl text-text-secondary max-w-2xl font-medium"
        >
          Connect Gmail or Outlook. Let our AI process the noise. 
          Receive only what truly matters, instantly on WhatsApp with smart auto-replies.
        </motion.p>

        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, delay: 0.3, ease: [0.16, 1, 0.3, 1] }}
          className="mt-12 flex flex-col sm:flex-row items-center justify-center gap-4"
        >
          <Link 
            href="/login"
            className="group relative px-8 py-4 rounded-full bg-brand-600 hover:bg-brand-500 text-white font-bold text-lg transition-all flex items-center gap-2 overflow-hidden premium-border w-full sm:w-auto justify-center"
          >
            <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/10 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
            Connect Your Inbox
            <ChevronRight className="w-5 h-5 group-hover:translate-x-1 transition-transform" />
          </Link>
          <Link 
            href="#how-it-works"
            className="px-8 py-4 rounded-full bg-white/5 hover:bg-white/10 border border-white/10 text-white font-bold text-lg transition-all w-full sm:w-auto text-center"
          >
            See how it works
          </Link>
        </motion.div>

        {/* Abstract UI Preview */}
        <motion.div 
          initial={{ opacity: 0, y: 40 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 1, delay: 0.5, ease: [0.16, 1, 0.3, 1] }}
          className="mt-24 w-full max-w-4xl relative px-4"
        >
          <div className="absolute inset-0 bg-gradient-to-b from-brand-500/20 to-transparent blur-3xl opacity-50 pointer-events-none -z-10" />
          <div className="glass-panel premium-border rounded-2xl p-4 md:p-6 text-left shadow-2xl">
            <div className="flex items-center gap-2 mb-6 px-2">
              <div className="w-3 h-3 rounded-full bg-red-500/80" />
              <div className="w-3 h-3 rounded-full bg-yellow-500/80" />
              <div className="w-3 h-3 rounded-full bg-green-500/80" />
              <div className="ml-4 text-xs font-semibold text-text-tertiary tracking-widest uppercase">Live AI Analysis</div>
            </div>
            
            <div className="space-y-4">
              {/* High Priority Email Mock */}
              <div className="flex flex-col md:flex-row md:items-center justify-between p-5 rounded-xl bg-surface-raised/80 border border-brand-500/30 shadow-[0_0_15px_rgba(99,102,241,0.1)]">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-full bg-brand-500/20 flex items-center justify-center shrink-0 mt-1 md:mt-0">
                    <Activity className="w-6 h-6 text-brand-400" />
                  </div>
                  <div>
                    <h4 className="font-bold text-white text-lg">Investor Update: Term Sheet</h4>
                    <p className="text-sm text-text-secondary mt-1">Requires signature by EOD. Legal team has already approved.</p>
                    <div className="flex items-center gap-2 mt-3">
                      <span className="text-xs bg-green-500/20 text-green-400 px-2 py-1 rounded font-semibold flex items-center gap-1">
                        <MessageCircle className="w-3 h-3" /> WhatsApp Alert Sent
                      </span>
                    </div>
                  </div>
                </div>
                <div className="mt-4 md:mt-0 flex flex-col items-end">
                  <div className="px-4 py-2 rounded-full bg-brand-500/10 border border-brand-500/30 text-brand-400 text-sm font-bold shadow-[0_0_10px_rgba(99,102,241,0.2)]">
                    Score: 98/100
                  </div>
                </div>
              </div>

              {/* Low Priority Email Mock */}
              <div className="flex flex-col md:flex-row md:items-center justify-between p-5 rounded-xl bg-surface/40 border border-border-subtle opacity-70">
                <div className="flex items-start gap-4">
                  <div className="w-12 h-12 rounded-full bg-surface-raised flex items-center justify-center shrink-0 mt-1 md:mt-0">
                    <ShieldCheck className="w-6 h-6 text-text-tertiary" />
                  </div>
                  <div>
                    <h4 className="font-semibold text-text-secondary text-lg">Weekly Marketing Newsletter</h4>
                    <p className="text-sm text-text-tertiary mt-1">Silently archived. No notification triggered.</p>
                  </div>
                </div>
                <div className="mt-4 md:mt-0">
                  <div className="px-4 py-2 rounded-full bg-surface-raised border border-border-subtle text-text-tertiary text-sm font-bold">
                    Score: 24/100
                  </div>
                </div>
              </div>
            </div>
          </div>
        </motion.div>
      </section>

      {/* How It Works Section */}
      <section id="how-it-works" className="py-24 relative z-10 bg-surface/30 border-y border-white/5">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-6">How InboxAlert Works</h2>
            <p className="text-lg text-text-secondary max-w-2xl mx-auto">Set it up in 60 seconds. Let the AI handle the rest forever.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8 relative">
            {/* Connecting line for desktop */}
            <div className="hidden md:block absolute top-12 left-1/6 right-1/6 h-0.5 bg-gradient-to-r from-transparent via-brand-500/50 to-transparent -z-10" />

            <div className="flex flex-col items-center text-center">
              <div className="w-24 h-24 rounded-full bg-surface border border-border-subtle flex items-center justify-center mb-6 shadow-xl relative">
                <div className="absolute inset-0 rounded-full border border-brand-500/30 animate-ping opacity-20" />
                <Mail className="w-10 h-10 text-white" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">1. Connect Inboxes</h3>
              <p className="text-text-secondary">Securely link your Gmail or Outlook. We never store your passwords or email bodies.</p>
            </div>

            <div className="flex flex-col items-center text-center">
              <div className="w-24 h-24 rounded-full bg-surface border border-border-subtle flex items-center justify-center mb-6 shadow-xl relative">
                <Brain className="w-10 h-10 text-brand-400" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">2. AI Scores & Summarizes</h3>
              <p className="text-text-secondary">Our Gemini-powered engine reads incoming mail, scores it from 0-100, and drafts a 2-line summary.</p>
            </div>

            <div className="flex flex-col items-center text-center">
              <div className="w-24 h-24 rounded-full bg-surface border border-border-subtle flex items-center justify-center mb-6 shadow-xl relative">
                <MessageCircle className="w-10 h-10 text-[#25D366]" />
              </div>
              <h3 className="text-xl font-bold text-white mb-3">3. WhatsApp Alerts</h3>
              <p className="text-text-secondary">If the score is 80+, your phone buzzes. Reply "1" to auto-send a response, or "3" to snooze.</p>
            </div>
          </div>
        </div>
      </section>

      {/* Features Grid */}
      <section id="features" className="py-24 relative z-10">
        <div className="max-w-7xl mx-auto px-6 md:px-12">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-bold text-white mb-6">Enterprise-Grade Features</h2>
            <p className="text-lg text-text-secondary max-w-2xl mx-auto">Built for founders, executives, and anyone drowning in communication.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
            <div className="glass-panel p-10 rounded-3xl premium-border hover:bg-surface-raised/50 transition-colors group">
              <Brain className="w-12 h-12 text-brand-400 mb-6 group-hover:scale-110 transition-transform" />
              <h3 className="text-2xl font-bold text-white mb-4">Autonomous Smart-Replies</h3>
              <p className="text-text-secondary leading-relaxed">
                Turn on autopilot. If a VIP emails you, the AI drafts a context-aware response based on your preferred tone, sends it, and notifies you on WhatsApp of what it said (with a 60s cancellation window).
              </p>
            </div>

            <div className="glass-panel p-10 rounded-3xl premium-border hover:bg-surface-raised/50 transition-colors group">
              <Lock className="w-12 h-12 text-accent mb-6 group-hover:scale-110 transition-transform" />
              <h3 className="text-2xl font-bold text-white mb-4">SaaS-Grade Privacy</h3>
              <p className="text-text-secondary leading-relaxed">
                We use AES-256-GCM encryption for your OAuth tokens. Raw email bodies are processed in memory and immediately discarded. We only store the metadata and the AI summary.
              </p>
            </div>

            <div className="glass-panel p-10 rounded-3xl premium-border hover:bg-surface-raised/50 transition-colors group">
              <Zap className="w-12 h-12 text-yellow-400 mb-6 group-hover:scale-110 transition-transform" />
              <h3 className="text-2xl font-bold text-white mb-4">Lightning Fast Webhooks</h3>
              <p className="text-text-secondary leading-relaxed">
                Integrated directly with Google Cloud Pub/Sub and Microsoft Graph. The moment an email hits your actual inbox, our background Celery workers process it in milliseconds.
              </p>
            </div>

            <div className="glass-panel p-10 rounded-3xl premium-border hover:bg-surface-raised/50 transition-colors group">
              <MessageCircle className="w-12 h-12 text-[#25D366] mb-6 group-hover:scale-110 transition-transform" />
              <h3 className="text-2xl font-bold text-white mb-4">Interactive WhatsApp Control</h3>
              <p className="text-text-secondary leading-relaxed">
                Don't just read alerts—act on them. Our Twilio integration allows you to reply with numbers to trigger manual actions like "Snooze" or "Send standard acknowledgement" without opening your email app.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section id="pricing" className="py-24 relative z-10 bg-surface/30 border-t border-white/5">
        <div className="max-w-5xl mx-auto px-6 md:px-12 text-center">
          <h2 className="text-3xl md:text-5xl font-bold text-white mb-6">Simple, Transparent Pricing</h2>
          <p className="text-lg text-text-secondary max-w-2xl mx-auto mb-16">Start for free. Upgrade when you need ultimate autonomy.</p>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8 text-left">
            {/* Free Tier */}
            <div className="p-10 rounded-3xl border border-border-subtle bg-surface/50">
              <h3 className="text-2xl font-semibold mb-2 text-white">Basic</h3>
              <p className="text-5xl font-bold mb-6 text-white">$0<span className="text-lg font-normal text-text-secondary">/month</span></p>
              <ul className="space-y-5 mb-10">
                <li className="flex items-center gap-3 text-text-secondary">
                  <CheckCircle2 className="w-5 h-5 text-text-tertiary" />
                  50 incoming emails/day scanned
                </li>
                <li className="flex items-center gap-3 text-text-secondary">
                  <CheckCircle2 className="w-5 h-5 text-text-tertiary" />
                  WhatsApp instant alerts
                </li>
                <li className="flex items-center gap-3 text-text-secondary">
                  <CheckCircle2 className="w-5 h-5 text-text-tertiary" />
                  1 connected inbox
                </li>
              </ul>
              <Link href="/login" className="block w-full py-4 text-center rounded-xl bg-surface-raised hover:bg-border-subtle text-white font-bold transition-colors">
                Start Free
              </Link>
            </div>

            {/* Pro Tier */}
            <div className="relative p-10 rounded-3xl border border-brand-500/50 bg-brand-500/10 premium-border overflow-hidden transform md:-translate-y-4 shadow-[0_0_50px_rgba(99,102,241,0.15)]">
              <div className="absolute top-0 right-0 bg-brand-500 text-white text-[10px] font-bold px-4 py-1.5 rounded-bl-xl uppercase tracking-widest">
                Recommended
              </div>
              <h3 className="text-2xl font-semibold mb-2 text-brand-400">Elite</h3>
              <p className="text-5xl font-bold mb-6 text-white">$29<span className="text-lg font-normal text-text-secondary">/month</span></p>
              <ul className="space-y-5 mb-10">
                <li className="flex items-center gap-3 text-white font-medium">
                  <CheckCircle2 className="w-5 h-5 text-brand-400" />
                  Unlimited email AI scanning
                </li>
                <li className="flex items-center gap-3 text-white font-medium">
                  <CheckCircle2 className="w-5 h-5 text-brand-400" />
                  Autonomous Smart-Replies
                </li>
                <li className="flex items-center gap-3 text-white font-medium">
                  <CheckCircle2 className="w-5 h-5 text-brand-400" />
                  Unlimited connected inboxes
                </li>
                <li className="flex items-center gap-3 text-white font-medium">
                  <CheckCircle2 className="w-5 h-5 text-brand-400" />
                  Priority WhatsApp routing
                </li>
              </ul>
              <Link href="/login" className="block w-full py-4 text-center rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-bold transition-colors shadow-[0_0_20px_rgba(99,102,241,0.4)]">
                Get Elite
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="border-t border-white/5 py-12 text-center relative z-10 bg-void">
        <div className="flex items-center justify-center gap-3 mb-6">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center" style={{background: "linear-gradient(135deg, #6366f1, #8b5cf6)"}}>
            <Mail className="w-3.5 h-3.5 text-white" strokeWidth={2.5} />
          </div>
          <span className="font-bold text-lg tracking-wide text-white">InboxAlert<span style={{color: "#818cf8"}}>.</span></span>
        </div>
        <p className="text-text-tertiary text-sm">
          &copy; {new Date().getFullYear()} InboxAlert Inc. All rights reserved. <br/>
          Secure. Private. Intelligent.
        </p>
      </footer>
    </div>
  );
}
