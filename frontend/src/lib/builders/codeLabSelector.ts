/**
 * Code Lab module selector — for Fundamentos de la Programación (thesis scope).
 *
 * Matches keywords against module_id + module_title (lowercased), because
 * real module ids are UUIDs: the title is what carries the semantics.
 * Update this single file if backend module naming changes.
 */

const MODULE_CODE_LAB: ReadonlyArray<{ fragments: string[]; slug: string }> = [
  { fragments: ['variable', 'tipo de dato'],                slug: 'variables'    },
  { fragments: ['conditional', 'condicional', 'condición'], slug: 'conditionals' },
  { fragments: ['loop', 'bucle', 'ciclo', 'iterac'],        slug: 'loops'        },
  { fragments: ['function', 'función', 'funcion'],          slug: 'functions'    },
  { fragments: ['array', 'arreglo'],                        slug: 'arrays'       },
]

export function getCodeLabSlug(moduleIdAndTitle: string): string | null {
  const haystack = moduleIdAndTitle.toLowerCase()
  for (const { fragments, slug } of MODULE_CODE_LAB) {
    if (fragments.some(f => haystack.includes(f))) return slug
  }
  return null
}
