import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

export default defineConfig({
  root: 'app',
  build: {
    outDir: '../dist',
    emptyOutDir: true,
  },
  server: {
    host: '127.0.0.1',
    proxy: {
      '/api': 'http://127.0.0.1:8080'
    }
  },
  plugins: [
    react(),
    {
      name: 'serve-session-state',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          // Serve session_state.json from the repository root
          if (req.url && req.url.startsWith('/session_state.json')) {
            try {
              const filePath = path.resolve(__dirname, 'session_state.json');
              if (fs.existsSync(filePath)) {
                res.setHeader('Content-Type', 'application/json');
                res.end(fs.readFileSync(filePath));
                return;
              }
            } catch (e) {
              console.error(e);
            }
          }
          next();
        });
      },
      configurePreviewServer(server) {
        server.middlewares.use((req, res, next) => {
          // Serve session_state.json from the repository root
          if (req.url && req.url.startsWith('/session_state.json')) {
            try {
              const filePath = path.resolve(__dirname, 'session_state.json');
              if (fs.existsSync(filePath)) {
                res.setHeader('Content-Type', 'application/json');
                res.end(fs.readFileSync(filePath));
                return;
              }
            } catch (e) {
              console.error(e);
            }
          }
          next();
        });
      }
    }
  ],
})
