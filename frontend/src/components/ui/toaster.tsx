import { useToast } from '@/hooks/use-toast'
import { X } from 'lucide-react'

export function Toaster() {
  const { toasts, dismiss } = useToast()

  if (toasts.length === 0) return null

  return (
    <div className="fixed bottom-4 right-4 z-50 flex flex-col gap-2 max-w-sm">
      {toasts.map((t) => (
        <div
          key={t.id}
          className={`rounded-lg border px-4 py-3 shadow-lg text-sm flex items-start gap-3 animate-in slide-in-from-right ${
            t.variant === 'destructive'
              ? 'bg-red-50 border-red-200 text-red-900'
              : 'bg-white border-gray-200 text-gray-900'
          }`}
        >
          <div className="flex-1">
            {t.title && <p className="font-semibold">{t.title}</p>}
            {t.description && <p className="text-xs mt-0.5 opacity-80">{t.description}</p>}
          </div>
          <button onClick={() => dismiss(t.id)} className="shrink-0 opacity-60 hover:opacity-100">
            <X className="h-4 w-4" />
          </button>
        </div>
      ))}
    </div>
  )
}
