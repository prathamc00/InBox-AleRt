import type { Metadata } from "next";
import { Plus_Jakarta_Sans } from "next/font/google";
import "./globals.css";

const jakarta = Plus_Jakarta_Sans({ 
  subsets: ["latin"], 
  variable: "--font-jakarta",
  weight: ["300", "400", "500", "600", "700", "800"],
});

export const metadata: Metadata = {
  title: "InboxAlert — Elite Email Intelligence",
  description: "AI-curated inbox for the modern professional.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${jakarta.variable} selection:bg-brand-500/30`}>
      <body className="bg-void text-slate-100 antialiased font-sans min-h-screen">
        {children}
      </body>
    </html>
  );
}
