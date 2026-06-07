/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./index.html",
    "./src/**/*.{vue,js,ts,jsx,tsx}"
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f5ff',
          100: '#d6e4ff',
          200: '#adc8ff',
          300: '#84a9ff',
          400: '#5b8aff',
          500: '#1677ff',
          600: '#0958d9',
          700: '#003eb3',
          800: '#002c8c',
          900: '#001d66',
        },
        success: '#52c41a',
        warning: '#faad14',
        danger: '#ff4d4f',
        info: '#1677ff',
        perf: {
          sidebar: '#1a1b2e',
          'sidebar-hover': '#252640',
          'sidebar-active': '#2d2e4a',
          content: '#f0f2f5',
          card: '#ffffff',
          'border-light': '#e8e8e8',
          'text-primary': '#1f1f1f',
          'text-secondary': '#666666',
          'text-muted': '#999999',
          accent: '#1677ff',
        }
      },
      fontFamily: {
        mono: ['ui-monospace', 'SFMono-Regular', 'Menlo', 'Monaco', 'Consolas', 'Liberation Mono', 'Courier New', 'monospace'],
      },
      animation: {
        'fade-in': 'fadeIn 0.3s ease-out',
        'slide-up': 'slideUp 0.3s ease-out',
      },
      keyframes: {
        'fadeIn': {
          '0%': { opacity: '0', transform: 'translateY(8px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
        'slideUp': {
          '0%': { opacity: '0', transform: 'translateY(16px)' },
          '100%': { opacity: '1', transform: 'translateY(0)' },
        },
      },
      boxShadow: {
        'card': '0 1px 4px rgba(0,0,0,0.08)',
        'card-hover': '0 4px 12px rgba(0,0,0,0.12)',
        'modal': '0 8px 24px rgba(0,0,0,0.15)',
      },
    },
  },
  plugins: [
    require('@tailwindcss/forms'),
  ],
}
