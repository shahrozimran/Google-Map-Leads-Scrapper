/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        beige: {
          50:  '#faf9f7',
          100: '#f5f2ee',
          200: '#ede8e1',
          300: '#ddd5c8',
          400: '#c9bfb0',
          500: '#b5a898',
        },
        ink: {
          DEFAULT: '#111111',
          soft:    '#1a1a1a',
          muted:   '#2a2a2a',
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'Fira Code', 'monospace'],
      },
    },
  },
  plugins: [],
}
