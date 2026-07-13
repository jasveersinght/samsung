/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        darkBg: '#09090b',
        panelBg: '#18181b',
        borderColor: '#27272a',
        textMuted: '#a1a1aa',
        textMain: '#f4f4f5',
      }
    },
  },
  plugins: [],
}
