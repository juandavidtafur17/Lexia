/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        ink: "#0F172A",
        slate: {
          950: "#0B1220",
        },
        navy: {
          900: "#0B1B33",
          800: "#122340",
          700: "#1A2E4F",
        },
        brand: {
          50: "#EFF6FF",
          500: "#2563EB",
          600: "#1D4ED8",
          700: "#1E40AF",
        },
        accent: {
          500: "#F59E0B",
          600: "#EA8A00",
          700: "#C96F00",
        },
        signal: "#EA580C",
        star: "#FBBF24",
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Inter'", "sans-serif"],
        mono: ["'JetBrains Mono'", "monospace"],
      },
    },
  },
  plugins: [],
};
