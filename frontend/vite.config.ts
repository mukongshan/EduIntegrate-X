import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react-swc'
import { fileURLToPath } from 'node:url'
import { dirname } from 'node:path'

const rootDir = dirname(fileURLToPath(import.meta.url))

export default defineConfig({
    root: rootDir,
    appType: 'spa',
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            '/api': {
                target: 'http://localhost:8081',
                changeOrigin: true,
                secure: false
            }
        }
    }
})
