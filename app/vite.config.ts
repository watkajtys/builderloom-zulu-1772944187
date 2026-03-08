import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import fs from 'fs'
import path from 'path'

export default defineConfig({
  server: { host: '127.0.0.1' },
  plugins: [
    react(),
    {
      name: 'serve-offline-state',
      configureServer(server) {
        server.middlewares.use((req, res, next) => {
          if (req.url === '/session_state.json') {
            const filePath = path.resolve(__dirname, '../session_state.json');
            if (fs.existsSync(filePath)) {
              res.setHeader('Content-Type', 'application/json');
              res.end(fs.readFileSync(filePath));
              return;
            }
          }
          if (req.url === '/execution_state.json') {
            const filePath = path.resolve(__dirname, '../execution_state.json');
            if (fs.existsSync(filePath)) {
              res.setHeader('Content-Type', 'application/json');
              res.end(fs.readFileSync(filePath));
              return;
            }
          }
          next();
        });
      }
    }
  ],
})
