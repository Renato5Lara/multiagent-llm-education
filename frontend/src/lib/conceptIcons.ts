// Sprint L8: domain → emoji icon mapping for ConceptCard headers.
// Same prefix/phrase matching as the backend _match_domain function.

const ICON_DOMAINS: ReadonlyArray<{ keywords: readonly string[]; icon: string }> = [
  { keywords: ['base de datos', 'database', 'sql', 'relacional', 'nosql', 'dato', 'tabla'], icon: '🗄️' },
  { keywords: ['sistema operativo', 'operativo', 'linux', 'windows', 'kernel', 'proceso', 'planificacion'], icon: '⚙️' },
  { keywords: ['red', 'redes', 'protocolo', 'tcp', 'ip', 'internet', 'router', 'enrutamiento'], icon: '🌐' },
  { keywords: ['inteligencia artificial', 'machine learning', 'aprendizaje automatico', 'neural', 'modelo predictivo'], icon: '🤖' },
  { keywords: ['programacion', 'algoritmo', 'codigo', 'funcion', 'variable', 'python', 'java', 'javascript'], icon: '💻' },
  { keywords: ['seguridad', 'criptografia', 'cifrado', 'vulnerabilidad', 'ataque', 'firewall', 'autenticacion'], icon: '🔒' },
  { keywords: ['cloud', 'nube', 'aws', 'azure', 'contenedor', 'docker', 'kubernetes', 'microservicio'], icon: '☁️' },
  { keywords: ['estadistica', 'calculo', 'algebra', 'matematica', 'probabilidad', 'regresion', 'distribucion'], icon: '📐' },
  { keywords: ['arquitectura', 'patron de diseno', 'mvc', 'api', 'rest', 'graphql', 'diseno de software'], icon: '🏗️' },
  { keywords: ['hardware', 'procesador', 'memoria', 'cpu', 'gpu', 'circuito', 'microprocesador'], icon: '🔧' },
  { keywords: ['web', 'html', 'css', 'frontend', 'backend', 'http', 'navegador'], icon: '🌍' },
  { keywords: ['compilador', 'lenguaje de programacion', 'interprete', 'sintaxis', 'semantica'], icon: '🔤' },
]

function _norm(text: string): string {
  return text.toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '')
}

export function getConceptIcon(title: string): string {
  const norm  = _norm(title)
  const words = norm.split(/\s+/)
  for (const { keywords, icon } of ICON_DOMAINS) {
    for (const kw of keywords) {
      const kwNorm = _norm(kw)
      if (kwNorm.includes(' ')) {
        if (norm.includes(kwNorm)) return icon
      } else {
        if (words.some(w => w.startsWith(kwNorm))) return icon
      }
    }
  }
  return '📘'
}
