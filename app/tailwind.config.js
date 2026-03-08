/** @type {import('tailwindcss').Config} */
export default {
  darkMode: "class",
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
    "../app/index.html",
    "../app/src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        "primary": "#135bec",
        "background-light": "#f6f6f8",
        "background-dark": "#0a0a0c",
        "slate-panel": "#141a26",
        "neon-green": "#00ff41",
        "neon-amber": "#ffb000",
        "neon-red": "#ff3e3e"
      },
      fontFamily: {
        "display": ["Space Grotesk", "sans-serif"],
        "mono": ["Fira Code", "monospace"]
      },
      borderRadius: {
        "DEFAULT": "0px",
        "lg": "0px",
        "xl": "0px",
        "full": "0px"
      },
    },
  },
  plugins: [],
}
