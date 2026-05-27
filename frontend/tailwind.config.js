/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      keyframes: {
        grow: {
          '0%': { width: '0%' },
          '100%': { width: 'var(--target-width)' },
        },
        'fade-in': {
          '0%': { opacity: '0', transform: 'translateY(10px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      animation: {
        'grow': 'grow 1.2s ease-out forwards',
        'fade-in': 'fade-in 0.8s ease-out forwards',
      },
    },
  },
  plugins: [],
}