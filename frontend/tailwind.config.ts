import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./components/**/*.{js,ts,jsx,tsx,mdx}",
    "./app/**/*.{js,ts,jsx,tsx,mdx}",
    "./features/**/*.{js,ts,jsx,tsx,mdx}",
    "./lib/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  darkMode: "class",
  theme: {
    extend: {
      fontFamily: {
        sans: ["var(--font-inter)", "system-ui", "sans-serif"],
        mono: ["var(--font-jetbrains)", "Menlo", "monospace"],
      },
      colors: {
        // Brand palette — deep blue-indigo tones
        brand: {
          50:  "#eef2ff",
          100: "#e0e7ff",
          200: "#c7d2fe",
          300: "#a5b4fc",
          400: "#818cf8",
          500: "#6366f1",
          600: "#4f46e5",
          700: "#4338ca",
          800: "#3730a3",
          900: "#312e81",
          950: "#1e1b4b",
        },
        // Surface system (dark mode first)
        surface: {
          950: "#0a0a0f",
          900: "#0f0f1a",
          850: "#13131f",
          800: "#1a1a2e",
          750: "#1e1e35",
          700: "#252540",
          600: "#2e2e52",
          500: "#3d3d6b",
        },
        // Semantic status colors
        status: {
          success: "#10b981",
          warning: "#f59e0b",
          error:   "#ef4444",
          info:    "#3b82f6",
          muted:   "#6b7280",
        },
      },
      backgroundImage: {
        "brand-gradient": "linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%)",
        "surface-gradient": "linear-gradient(180deg, #0f0f1a 0%, #1a1a2e 100%)",
        "card-glow": "radial-gradient(ellipse at 50% 0%, rgba(99,102,241,0.15) 0%, transparent 70%)",
      },
      boxShadow: {
        "brand-sm":  "0 0 0 1px rgba(99,102,241,0.3)",
        "brand-md":  "0 0 20px rgba(99,102,241,0.2), 0 0 0 1px rgba(99,102,241,0.3)",
        "card":      "0 1px 3px rgba(0,0,0,0.4), 0 0 0 1px rgba(255,255,255,0.05)",
        "card-hover":"0 4px 16px rgba(0,0,0,0.5), 0 0 0 1px rgba(99,102,241,0.3)",
      },
      animation: {
        "fade-in":    "fadeIn 0.3s ease-out",
        "slide-up":   "slideUp 0.35s ease-out",
        "pulse-slow": "pulse 3s cubic-bezier(0.4,0,0.6,1) infinite",
        "shimmer":    "shimmer 1.5s linear infinite",
      },
      keyframes: {
        fadeIn:  { from: { opacity: "0" }, to: { opacity: "1" } },
        slideUp: { from: { opacity: "0", transform: "translateY(12px)" }, to: { opacity: "1", transform: "translateY(0)" } },
        shimmer: { from: { backgroundPosition: "-200% 0" }, to: { backgroundPosition: "200% 0" } },
      },
    },
  },
  plugins: [],
};

export default config;
