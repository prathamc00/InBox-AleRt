"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Mail, Phone, Bot, Check, ArrowRight, Sparkles } from "lucide-react";
import { useRouter } from "next/navigation";

export default function OnboardingPage() {
  const [step, setStep] = useState(1);
  const router = useRouter();
  const [whatsapp, setWhatsapp] = useState("");
  const [tone, setTone] = useState("professional");

  const handleNext = () => {
    if (step < 3) {
      setStep(step + 1);
    } else {
      router.push("/dashboard");
    }
  };

  return (
    <div className="min-h-screen bg-void flex flex-col items-center justify-center p-6 relative overflow-hidden">
      <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[600px] h-[600px] bg-brand-500/5 blur-[120px] rounded-full pointer-events-none" />

      {/* Brand */}
      <div className="absolute top-8 left-8 flex items-center gap-2">
        <div className="w-6 h-6 rounded bg-white flex items-center justify-center">
          <Sparkles className="w-3.5 h-3.5 text-black" />
        </div>
        <span className="font-bold text-sm tracking-wide text-white">InboxAlert.</span>
      </div>

      <div className="w-full max-w-lg relative z-10">
        
        {/* Progress Bar */}
        <div className="flex gap-2 mb-12">
          {[1, 2, 3].map((s) => (
            <div key={s} className="h-1 flex-1 bg-surface-raised rounded-full overflow-hidden">
              <motion.div 
                className="h-full bg-white"
                initial={{ width: "0%" }}
                animate={{ width: step >= s ? "100%" : "0%" }}
                transition={{ duration: 0.5, ease: "easeInOut" }}
              />
            </div>
          ))}
        </div>

        {/* Steps Container */}
        <div className="bg-surface border border-border-subtle rounded-3xl p-8 md:p-12 shadow-2xl relative overflow-hidden">
          <AnimatePresence mode="wait">
            
            {step === 1 && (
              <motion.div
                key="step1"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
              >
                <div className="w-12 h-12 rounded-full bg-surface-raised border border-border-subtle flex items-center justify-center mb-6">
                  <Mail className="w-6 h-6 text-text-primary" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">Connect your inbox</h2>
                <p className="text-text-secondary text-sm mb-8">We'll scan incoming emails using the official APIs. We never store your data.</p>
                
                <div className="space-y-3">
                  <button onClick={handleNext} className="w-full p-4 rounded-xl border border-border-strong hover:border-text-tertiary bg-surface-raised transition-all flex items-center gap-4 text-left group">
                    <svg className="w-6 h-6 shrink-0" viewBox="0 0 24 24">
                      <path fill="#EA4335" d="M12 13L2.2 6.5C2.6 5.6 3.5 5 4.5 5h15c1 0 1.9.6 2.3 1.5L12 13z"/>
                      <path fill="#34A853" d="M22 6.5V19c0 1.1-.9 2-2 2h-4.5v-9L22 6.5z"/>
                      <path fill="#4285F4" d="M2 6.5V19c0 1.1.9 2 2 2h4.5v-9L2 6.5z"/>
                      <path fill="#FBBC05" d="M12 13L2.2 6.5A2.99 2.99 0 0 0 2 8v1.5l10 6.5 10-6.5V8a3.1 3.1 0 0 0-.2-1.5L12 13z"/>
                    </svg>
                    <span className="font-semibold text-white flex-1">Continue with Gmail</span>
                    <ArrowRight className="w-4 h-4 text-text-tertiary group-hover:text-white transition-colors" />
                  </button>
                  <button onClick={handleNext} className="w-full p-4 rounded-xl border border-border-strong hover:border-text-tertiary bg-surface-raised transition-all flex items-center gap-4 text-left group">
                    <svg className="w-6 h-6 shrink-0" viewBox="0 0 24 24">
                      <path fill="#00A4EF" d="M2 4.5h20v15H2z" opacity="0.1"/>
                      <path fill="#0078D4" d="M22 4.5H2v15h20v-15z"/>
                      <path fill="#005A9E" d="M2 4.5l10 7.5 10-7.5v-1H2v1z"/>
                      <path fill="#00A4EF" d="M2 18l7.5-6.5L2 10.5V18z"/>
                    </svg>
                    <span className="font-semibold text-white flex-1">Continue with Outlook</span>
                    <ArrowRight className="w-4 h-4 text-text-tertiary group-hover:text-white transition-colors" />
                  </button>
                </div>
              </motion.div>
            )}

            {step === 2 && (
              <motion.div
                key="step2"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
              >
                <div className="w-12 h-12 rounded-full bg-surface-raised border border-border-subtle flex items-center justify-center mb-6">
                  <Phone className="w-6 h-6 text-[#25D366]" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">WhatsApp Delivery</h2>
                <p className="text-text-secondary text-sm mb-8">Where should the AI send your high-priority alerts and summaries?</p>
                
                <div className="relative mb-8">
                  <span className="absolute left-4 top-1/2 -translate-y-1/2 text-text-tertiary text-lg">💬</span>
                  <input 
                    type="text" 
                    value={whatsapp}
                    onChange={(e) => setWhatsapp(e.target.value)}
                    placeholder="+1 234 567 8900"
                    autoFocus
                    className="w-full bg-void border border-border-strong rounded-xl pl-12 pr-4 py-4 text-white text-lg focus:outline-none focus:border-text-primary transition-colors"
                  />
                </div>

                <button 
                  onClick={handleNext} 
                  disabled={!whatsapp}
                  className="w-full py-4 rounded-xl bg-white text-black font-bold text-lg hover:bg-gray-200 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
                >
                  Confirm Number
                </button>
              </motion.div>
            )}

            {step === 3 && (
              <motion.div
                key="step3"
                initial={{ opacity: 0, x: 20 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -20 }}
                transition={{ duration: 0.3 }}
              >
                <div className="w-12 h-12 rounded-full bg-surface-raised border border-border-subtle flex items-center justify-center mb-6">
                  <Bot className="w-6 h-6 text-text-primary" />
                </div>
                <h2 className="text-2xl font-bold text-white mb-2">Choose AI Persona</h2>
                <p className="text-text-secondary text-sm mb-8">How should the AI sound when drafting replies on your behalf?</p>
                
                <div className="space-y-3 mb-8">
                  {[
                    { id: "professional", label: "Professional", desc: "Polite, formal, and structured." },
                    { id: "friendly", label: "Friendly", desc: "Warm, approachable, and casual." },
                    { id: "brief", label: "Brief", desc: "Direct, concise, no fluff." }
                  ].map((t) => (
                    <button 
                      key={t.id}
                      onClick={() => setTone(t.id)} 
                      className={`w-full p-4 rounded-xl border transition-all text-left flex items-start gap-4 ${tone === t.id ? 'bg-surface-raised border-white' : 'border-border-strong hover:border-text-tertiary'}`}
                    >
                      <div className={`w-5 h-5 rounded-full border flex items-center justify-center shrink-0 mt-0.5 ${tone === t.id ? 'border-white bg-white' : 'border-text-tertiary'}`}>
                        {tone === t.id && <Check className="w-3 h-3 text-black" />}
                      </div>
                      <div>
                        <span className={`font-semibold ${tone === t.id ? 'text-white' : 'text-text-primary'}`}>{t.label}</span>
                        <p className="text-xs text-text-secondary mt-1">{t.desc}</p>
                      </div>
                    </button>
                  ))}
                </div>

                <button 
                  onClick={handleNext} 
                  className="w-full py-4 rounded-xl bg-white text-black font-bold text-lg hover:bg-gray-200 transition-colors flex items-center justify-center gap-2 shadow-[0_0_30px_rgba(255,255,255,0.1)]"
                >
                  <Sparkles className="w-5 h-5" />
                  Enter Dashboard
                </button>
              </motion.div>
            )}

          </AnimatePresence>
        </div>
      </div>
    </div>
  );
}
