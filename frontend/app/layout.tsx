import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";

const outfit = Outfit({
  subsets: ["latin"],
  variable: "--font-outfit",
  display: "swap",
  weight: ["300", "400", "500", "600", "700", "800"],
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
    <html lang="en" className={outfit.variable}>
      <body className="min-h-screen font-sans antialiased" style={{ background: "#f0f1f8" }}>
        {children}
      </body>
    </html>
  );
}