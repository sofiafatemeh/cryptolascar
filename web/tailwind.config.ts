import type { Config } from 'tailwindcss'

const config: Config = {
  content: ['./src/**/*.{js,ts,jsx,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        'or-lascar': '#F5C542',
        'noir-bitume': '#0D0D0D',
        'blanc-linen': '#F2EFE6',
        'vert-marche': '#2E7D32',
        anthracite: '#1A1A1A',
        'or-sale': '#B8860B',
      },
      fontFamily: {
        display: ['Impact', 'Arial Narrow', 'sans-serif'],
        body: ['Inter', 'system-ui', 'sans-serif'],
      },
    },
  },
  plugins: [],
}
export default config
