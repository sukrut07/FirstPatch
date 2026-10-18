import type { Metadata } from "next";
import { Inter } from "next/font/google";
import "./globals.css";

const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});

export const metadata: Metadata = {
  title: "FirstPatch AI — Your Open-Source Mentor",
  description:
    "Evidence-backed AI mentor that helps beginners make their first meaningful contribution to an unfamiliar GitHub repository.",
  keywords: ["open source", "contribution", "GitHub", "beginner", "AI mentor", "first pull request"],
  openGraph: {
    title: "FirstPatch AI",
    description: "Your Open-Source Mentor — make your first contribution with confidence",
    type: "website",
  },
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className={`${inter.variable} dark`}>
      <body className="min-h-screen bg-surface-950 text-gray-100 font-sans antialiased">
        {children}
      </body>
    </html>
  );
}
