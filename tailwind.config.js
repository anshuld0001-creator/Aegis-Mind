/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"],
  theme: {
    extend: {
      colors: {
        aegis: {
          navy: "#0B1220",
          navyLight: "#172033",
          slate: "#526174",

          teal: "#14B8A6",
          tealLight: "#E6FFFB",

          amber: "#F59E0B",

          rose: "#DC3F4B",

          sand: "#F1F5F9",
        },
      },
      fontFamily: {
        sans: ["Inter", "system-ui", "sans-serif"],
      },
      boxShadow: {
        card: "0 1px 2px rgba(14, 27, 44, 0.06), 0 1px 8px rgba(14, 27, 44, 0.06)",
      },
    },
  },
  plugins: [],
};
