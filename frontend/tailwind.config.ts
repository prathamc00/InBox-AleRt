import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        paper: "#FAF9F6",
        "paper-raised": "#FFFFFF",
        ink: "#14171B",
        "ink-soft": "#43484F",
        slate: "#6B7178",
        hairline: "#E4E1D9",
        "hairline-strong": "#D2CEC3",
        signal: "#0E6F5C",
        "signal-soft": "#E5F1EC",
        "signal-soft-border": "#BFDDD2",
        amber: "#B8791A",
        "amber-soft": "#FBF1DF",
        mute: "#9A9FA6",
      },
      fontFamily: {
        display: ["var(--font-instrument-serif)", "serif"],
        sans: ["var(--font-inter-tight)", "sans-serif"],
        mono: ["var(--font-plex-mono)", "monospace"],
      },
      fontSize: {
        hero: ["56px", { lineHeight: "1.05", letterSpacing: "-0.02em" }],
        h2: ["34px", { lineHeight: "1.15", letterSpacing: "-0.015em" }],
        h3: ["24px", { lineHeight: "1.25" }],
        body: ["16px", { lineHeight: "1.6" }],
        "body-sm": ["14px", { lineHeight: "1.5" }],
        caption: ["12.5px", { lineHeight: "1.4" }],
      },
      spacing: {
        "1": "4px",
        "2": "8px",
        "3": "12px",
        "4": "16px",
        "6": "24px",
        "8": "32px",
        "10": "40px",
        "16": "64px",
        "24": "96px",
      },
      borderRadius: {
        sm: "6px",
        md: "10px",
        lg: "16px",
      },
      boxShadow: {
        card: "0 1px 2px rgba(20,23,27,0.04), 0 1px 1px rgba(20,23,27,0.03)",
        raised: "0 4px 16px rgba(20,23,27,0.07), 0 1px 3px rgba(20,23,27,0.06)",
      },
    },
  },
  plugins: [],
};

export default config;
