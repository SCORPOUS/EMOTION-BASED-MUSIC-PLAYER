/** @type {import('tailwindcss').Config} */
export default {
  darkMode: 'class',
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      fontFamily: {
        display: ['Sora', 'sans-serif'],
        sans: ['Inter', 'sans-serif'],
      },
      colors: {
        ink: '#111126',
        lilac: '#9272ff',
        coral: '#ff719f',
        aqua: '#68e5e8',
      },
      borderRadius: {
        '4xl': '2rem',
      },
      boxShadow: {
        glass: '0 24px 80px rgba(27, 21, 67, 0.14)',
      },
    },
  },
  plugins: [],
}
