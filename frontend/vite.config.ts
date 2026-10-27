import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    // Flask backend hazır olduğunda /api istekleri buraya yönlenecek
    proxy: { '/api': 'http://localhost:5000' },
  },
});
