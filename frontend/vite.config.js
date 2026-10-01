import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'

// Public pages that belong in the sitemap (private/app pages are excluded on purpose).
const PUBLIC_ROUTES = ['/', '/events', '/ngos', '/nss-units', '/analytics', '/calendar', '/certificate/verify', '/register', '/login', '/privacy', '/terms']

// Fills %SITE_URL% in index.html and emits sitemap.xml + robots.txt at build time.
function seoPlugin(siteUrl) {
  return {
    name: 'nss-seo-files',
    // order: 'pre' is required — Vite's built-in HTML processor decodes every href/content URL
    // and throws "URI malformed" on a raw "%SITE_URL%" if we substitute it any later than this.
    transformIndexHtml: {
      order: 'pre',
      handler: (html) => html.replaceAll('%SITE_URL%', siteUrl),
    },
    generateBundle() {
      const urls = PUBLIC_ROUTES.map((r) => `  <url><loc>${siteUrl}${r === '/' ? '' : r}</loc></url>`).join('\n')
      this.emitFile({
        type: 'asset',
        fileName: 'sitemap.xml',
        source: `<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n${urls}\n</urlset>\n`,
      })
      this.emitFile({
        type: 'asset',
        fileName: 'robots.txt',
        source: `User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\nDisallow: /django-admin/\nDisallow: /dashboard\nDisallow: /profile\nDisallow: /notifications\nDisallow: /attendance/\n\nSitemap: ${siteUrl}/sitemap.xml\n`,
      })
    },
  }
}

// In development the Vite server proxies /api and /media to Django, so the browser sees ONE origin.
// That keeps the httpOnly refresh cookie first-party and lets a single tunnel URL (Cloudflare/ngrok)
// expose the whole app to a phone on any network.
export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), '')
  const backend = env.BACKEND_URL || 'http://127.0.0.1:8000'
  const siteUrl = (env.VITE_SITE_URL || 'http://localhost:5173').replace(/\/$/, '')
  return {
    plugins: [react(), seoPlugin(siteUrl)],
    build: {
      chunkSizeWarningLimit: 700,
      rollupOptions: {
        output: {
          manualChunks: {
            react: ['react', 'react-dom', 'react-router-dom'],
            charts: ['recharts'],
            maps: ['leaflet', 'react-leaflet'],
          },
        },
      },
    },
    server: {
      host: true, // listen on LAN too (phone on same Wi-Fi: http://<laptop-ip>:5173)
      port: 5173,
      allowedHosts: true, // accept tunnel hostnames (*.trycloudflare.com, *.ngrok-free.app)
      proxy: {
        '/api': { target: backend, changeOrigin: false, xfwd: true },
        '/media': { target: backend, changeOrigin: false },
      },
    },
    preview: { host: true, port: 4173, allowedHosts: true },
    test: {
      environment: 'jsdom',
      globals: true,
      setupFiles: './src/__tests__/setup.js',
    },
  }
})
