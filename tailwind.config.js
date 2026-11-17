/** @type {import('tailwindcss').Config} */
export default {
  content: ["./frontend/index.html", "./frontend/src/**/*.{ts,tsx}"],
  theme: { extend: { colors: { accent: "#00F59B", surface: "#151A1D" } } },
  plugins: [],
};
