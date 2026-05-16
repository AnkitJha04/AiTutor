/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,jsx}"] ,
  theme: {
    extend: {
      colors: {
        ink: "#0b1b22",
        sand: "#f5efe2",
        clay: "#e7c3a2",
        moss: "#5c7a5d",
        ember: "#d97941"
      },
      fontFamily: {
        display: ["'Space Grotesk'", "sans-serif"],
        body: ["'Merriweather'", "serif"]
      }
    }
  },
  plugins: []
};
