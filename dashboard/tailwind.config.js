/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        brand: {
          50: '#fff1f1',
          100: '#ffe0e1',
          200: '#ffc3c5',
          300: '#ff999d',
          400: '#f66d73',
          500: '#df454c',
          600: '#c6323a',
          700: '#a92730',
          800: '#87232a',
          900: '#561b21',
        },
        accent: {
          50: '#fff4e8',
          100: '#ffe8cf',
          500: '#ed8a32',
          600: '#cf6d1a',
        },
      },
      boxShadow: {
        card: '0 8px 24px -16px rgb(15 35 39 / 0.24), 0 2px 6px -3px rgb(15 35 39 / 0.12)',
      },
    },
  },
  plugins: [],
};
