import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
});

export const metadata = {
  title: "AB Talks — AI Interview Agent",
  description:
    "An AI-powered technical interview agent for AI engineering candidates. Conducts structured assessments with real-time evaluation and detailed reporting.",
  keywords: [
    "AI interview",
    "technical assessment",
    "AI engineering",
    "interview agent",
  ],
};

export default function RootLayout({ children }) {
  return (
    <html lang="en" className="dark">
      <body className={`${inter.variable} antialiased`}>{children}</body>
    </html>
  );
}
