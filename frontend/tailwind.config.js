/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        ink: { DEFAULT: '#1A1830', 2: '#2D2B52' },
        surface: { DEFAULT: '#FFFFFF', 2: '#F0EEE9', 3: '#E8E6E0', bg: '#F5F4F1' },
        brand: {
          blue: '#1B5DB5', 'blue-bg': '#EBF2FC',
          green: '#1A6B3C', 'green-bg': '#E6F4ED',
          amber: '#7A4C08', 'amber-bg': '#FDF2DC',
          red: '#8C2020', 'red-bg': '#FBEAEA',
          teal: '#0D5850', 'teal-bg': '#E0F2EF',
          purple: '#3D2F8A', 'purple-bg': '#F0EEF9',
        },
      },
      fontFamily: {
        sans: ['DM Sans', 'system-ui', 'sans-serif'],
        mono: ['DM Mono', 'monospace'],
      },
      borderRadius: { DEFAULT: '8px', lg: '12px', xl: '16px' },
    },
  },
  plugins: [],
}
