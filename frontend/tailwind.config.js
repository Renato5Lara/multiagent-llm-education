/** @type {import('tailwindcss').Config} */
export default {
  darkMode: ["class"],
  content: [
    "./index.html",
    "./src/**/*.{ts,tsx,js,jsx}",
  ],
  theme: {
    container: {
      center: true,
      padding: "2rem",
      screens: { "2xl": "1400px" },
    },
    extend: {
      fontFamily: {
        sans: ['Outfit', 'system-ui', '-apple-system', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      colors: {
        border: "hsl(var(--border))",
        input: "hsl(var(--input))",
        ring: "hsl(var(--ring))",
        background: "hsl(var(--background))",
        foreground: "hsl(var(--foreground))",
        primary: {
          DEFAULT: "hsl(var(--primary))",
          foreground: "hsl(var(--primary-foreground))",
          // UPAO brand kept as static tokens for light-mode references
          upao: "#003D7A",
          50: "#e6eef7",
          100: "#ccdcef",
          200: "#99b9df",
          300: "#6696cf",
          400: "#3373bf",
          500: "#003D7A",
          600: "#003168",
          700: "#002556",
          800: "#001944",
          900: "#000d32",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary))",
          foreground: "hsl(var(--secondary-foreground))",
          upao: "#D4A017",
        },
        success: {
          DEFAULT: "#16a34a",
          foreground: "#ffffff",
        },
        danger: {
          DEFAULT: "#dc2626",
          foreground: "#ffffff",
        },
        muted: {
          DEFAULT: "hsl(var(--muted))",
          foreground: "hsl(var(--muted-foreground))",
        },
        accent: {
          DEFAULT: "hsl(var(--accent))",
          foreground: "hsl(var(--accent-foreground))",
        },
        popover: {
          DEFAULT: "hsl(var(--popover))",
          foreground: "hsl(var(--popover-foreground))",
        },
        card: {
          DEFAULT: "hsl(var(--card))",
          foreground: "hsl(var(--card-foreground))",
        },
        destructive: {
          DEFAULT: "hsl(var(--destructive))",
          foreground: "hsl(var(--destructive-foreground))",
        },
        // Neural Swarm design tokens
        neural: {
          surface:  "#10131a",   // page background
          panel:    "#1d2026",   // card / container
          elevated: "#272a31",   // elevated surface
          lowest:   "#0b0e14",   // sidebar / deepest layer
          glow:     "#00dbe7",   // primary cyan accent
          "glow-bright": "#74f5ff", // lighter cyan (text on dark)
          pulse:    "#00fb83",   // green status / active
          violet:   "#ce5dff",   // secondary accent (dominance ring, tutor accents)
          muted:    "#b9cacb",   // muted text
          text:     "#e1e2eb",   // primary text on dark
          // Épica D — regla híbrida: violeta/índigo para marca/hero/CTA
          // principal, cian se mantiene para todo lo "en vivo" (activo,
          // progreso, ejecución, streaming) — ver QA_EPICA_D.md.
          brand:        "#7c3aed",  // indigo-violeta — hero, CTA principal, marca
          "brand-bright": "#a78bfa", // texto/glow claro sobre fondo oscuro
        },
      },
      borderRadius: {
        lg: "var(--radius)",
        md: "calc(var(--radius) - 2px)",
        sm: "calc(var(--radius) - 4px)",
      },
      keyframes: {
        "accordion-down": {
          from: { height: "0" },
          to: { height: "var(--radix-accordion-content-height)" },
        },
        "accordion-up": {
          from: { height: "var(--radix-accordion-content-height)" },
          to: { height: "0" },
        },
        "scanline": {
          "0%":   { transform: "translateY(-100%)" },
          "100%": { transform: "translateY(100%)" },
        },
        "pulse-ring": {
          "0%":   { transform: "scale(0.8)", opacity: "0.5" },
          "100%": { transform: "scale(1.5)", opacity: "0" },
        },
        "pulse-slow": {
          "0%, 100%": { opacity: "0.3", transform: "scale(1)" },
          "50%":      { opacity: "0.6", transform: "scale(1.05)" },
        },
        "float": {
          "0%, 100%": { transform: "translateY(0)" },
          "50%":      { transform: "translateY(-6px)" },
        },
        "glow-pulse": {
          "0%, 100%": { boxShadow: "0 0 8px rgba(0,219,231,0.2)" },
          "50%":      { boxShadow: "0 0 20px rgba(0,219,231,0.5)" },
        },
      },
      animation: {
        "accordion-down": "accordion-down 0.2s ease-out",
        "accordion-up":   "accordion-up 0.2s ease-out",
        "scanline":       "scanline 4s linear infinite",
        "pulse-ring":     "pulse-ring 2s cubic-bezier(0.455,0.03,0.515,0.955) infinite",
        "pulse-slow":     "pulse-slow 3s ease-in-out infinite",
        "float":          "float 3s ease-in-out infinite",
        "glow-pulse":     "glow-pulse 2.5s ease-in-out infinite",
      },
    },
  },
  plugins: [],
}
