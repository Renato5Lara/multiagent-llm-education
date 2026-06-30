/**
 * Code Lab module selector — for Fundamentos de la Programación (thesis scope).
 *
 * Keyed by module_id fragment, NOT module_title.
 * Using module_id makes this resilient to display-name changes.
 * Update this single file if backend module IDs change.
 */

const MODULE_CODE_LAB: ReadonlyArray<{ fragment: string; slug: string }> = [
  { fragment: 'variables',   slug: 'variables'    },
  { fragment: 'conditional', slug: 'conditionals' },
  { fragment: 'loop',        slug: 'loops'        },
  { fragment: 'function',    slug: 'functions'    },
  { fragment: 'array',       slug: 'arrays'       },
]

export function getCodeLabSlug(moduleId: string): string | null {
  const id = moduleId.toLowerCase()
  for (const { fragment, slug } of MODULE_CODE_LAB) {
    if (id.includes(fragment)) return slug
  }
  return null
}
