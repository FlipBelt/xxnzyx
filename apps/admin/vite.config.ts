import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  base: process.env.VITE_BASE || '/flipbelt-admin/',
  server: { port: 5188, strictPort: true },
  preview: { port: 4188, strictPort: true }
})
