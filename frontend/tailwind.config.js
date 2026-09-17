/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        brand: {
          dark: '#0e1726',
          sidebar: '#0b1622',
          card: '#ffffff',
          bg: '#f3f6f9',
          emerald: '#10b981',
          emeraldDark: '#059669',
          high: '#ef4444',
          moderate: '#f59e0b',
          low: '#10b981'
        }
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', '-apple-system', 'BlinkMacSystemFont', 'Segoe UI', 'Roboto', 'sans-serif'],
      }
    },
  },
  plugins: [],
}
