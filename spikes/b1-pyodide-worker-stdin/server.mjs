// Servidor mínimo (sin dependencias) para el Spike B-1 — sirve los estáticos
// con COOP/COEP reales, aislado del Vite del proyecto para no acoplar el
// experimento a su configuración mientras la hipótesis sigue sin verificar.
import { createServer } from 'node:http'
import { readFile } from 'node:fs/promises'
import { extname, join } from 'node:path'
import { fileURLToPath } from 'node:url'

const dir = fileURLToPath(new URL('.', import.meta.url))
const port = process.argv[2] ? Number(process.argv[2]) : 5180

// require-corp es el modo estándar que documenta Pyodide; credentialless es
// el fallback más permisivo con recursos cross-origin sin cabecera CORP
// propia — exactamente el punto que SPIKE-B0 dejó sin verificar (si
// cdn.jsdelivr.net envía Cross-Origin-Resource-Policy compatible).
const coepMode = process.env.COEP_MODE === 'credentialless' ? 'credentialless' : 'require-corp'

const MIME = { '.html': 'text/html', '.js': 'text/javascript', '.mjs': 'text/javascript' }

createServer(async (req, res) => {
  const path = req.url === '/' ? '/index.html' : req.url
  try {
    const body = await readFile(join(dir, path))
    res.writeHead(200, {
      'Content-Type': MIME[extname(path)] || 'application/octet-stream',
      'Cross-Origin-Opener-Policy': 'same-origin',
      'Cross-Origin-Embedder-Policy': coepMode,
    })
    res.end(body)
  } catch {
    res.writeHead(404)
    res.end('not found')
  }
}).listen(port, () => {
  console.log(`spike b1 server on http://localhost:${port} (COEP_MODE=${coepMode})`)
})
