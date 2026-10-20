import type { Metadata } from "next";
import { Outfit } from "next/font/google";
import "./globals.css";
import Navbar from "@/components/Navbar";

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
      <body className="min-h-screen font-sans antialiased flex flex-col" style={{ background: "#eef0f7" }}>
        <Navbar />
        <div className="flex-1">
          {children}
        </div>
        <footer className="border-t border-gray-200/70 py-6 text-center bg-white/40 backdrop-blur-sm mt-12">
          <p className="text-xs text-gray-500 font-medium">
            FirstPatch AI &bull; Evidence-backed open-source mentorship &bull; v0.1.0
          </p>
        </footer>
      </body>
    </html>
  );
}