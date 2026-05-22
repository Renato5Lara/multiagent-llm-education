const STORAGE_PREFIX = 'upao-'

export const storage = {
  get<T>(key: string): T | null {
    try {
      const raw = localStorage.getItem(`${STORAGE_PREFIX}${key}`)
      if (!raw) return null
      return JSON.parse(raw) as T
    } catch {
      return null
    }
  },

  set<T>(key: string, value: T): void {
    try {
      localStorage.setItem(`${STORAGE_PREFIX}${key}`, JSON.stringify(value))
    } catch {
      // localStorage quota exceeded or unavailable
    }
  },

  remove(key: string): void {
    try {
      localStorage.removeItem(`${STORAGE_PREFIX}${key}`)
    } catch {
      // ignore
    }
  },

  clear(): void {
    try {
      const keys = Object.keys(localStorage).filter(k => k.startsWith(STORAGE_PREFIX))
      keys.forEach(k => localStorage.removeItem(k))
    } catch {
      // ignore
    }
  },
}
