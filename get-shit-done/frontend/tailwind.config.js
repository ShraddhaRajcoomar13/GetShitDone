export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  darkMode: "class",
  theme: {
    extend: {
      colors: {
        paper:   "rgb(var(--color-paper)   / <alpha-value>)",
        ink:     "rgb(var(--color-ink)     / <alpha-value>)",
        accent:  "rgb(var(--color-accent)  / <alpha-value>)",
        accent2: "rgb(var(--color-accent-2)/ <alpha-value>)",
      },
      fontFamily: {
        serif: ["Iowan Old Style", "Georgia", "serif"],
        sans: ["Inter", "system-ui", "sans-serif"],
      },
    },
  },
  plugins: [],
};