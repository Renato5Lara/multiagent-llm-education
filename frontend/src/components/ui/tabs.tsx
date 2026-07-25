import * as React from 'react'
import { cn } from '@/lib/utils'

type TabsContextType = {
  value: string
  onValueChange: (value: string) => void
}

const TabsContext = React.createContext<TabsContextType | null>(null)

function useTabs() {
  const ctx = React.useContext(TabsContext)
  if (!ctx) throw new Error('Tabs components must be used within a Tabs provider')
  return ctx
}

function Tabs({
  value,
  onValueChange,
  defaultValue,
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & {
  value?: string
  onValueChange?: (value: string) => void
  defaultValue?: string
}) {
  const [internalValue, setInternalValue] = React.useState(defaultValue || '')
  const isControlled = value !== undefined
  const currentValue = isControlled ? value : internalValue

  const handleChange = React.useCallback(
    (newValue: string) => {
      if (!isControlled) setInternalValue(newValue)
      onValueChange?.(newValue)
    },
    [isControlled, onValueChange]
  )

  return (
    <TabsContext.Provider value={{ value: currentValue, onValueChange: handleChange }}>
      <div className={cn('w-full', className)} {...props}>
        {children}
      </div>
    </TabsContext.Provider>
  )
}

function TabsList({ className, children, ...props }: React.HTMLAttributes<HTMLDivElement>) {
  return (
    <div
      role="tablist"
      // Épica E — EP-02: bg-gray-100 (tema claro) reemplazado por un
      // contenedor de vidrio oscuro consistente con glass-panel; ver
      // ENGINEERING-GATE-EPICA-E.md para la causa raíz del bug de
      // invisibilidad que motivó este cambio.
      className={cn('inline-flex h-9 items-center rounded-lg bg-white/[0.04] p-1 text-neural-muted', className)}
      {...props}
    >
      {children}
    </div>
  )
}

function TabsTrigger({
  value,
  className,
  children,
  ...props
}: React.ButtonHTMLAttributes<HTMLButtonElement> & { value: string }) {
  const { value: selectedValue, onValueChange } = useTabs()
  const isActive = selectedValue === value

  return (
    <button
      role="tab"
      data-state={isActive ? 'active' : 'inactive'}
      onClick={() => onValueChange(value)}
      className={cn(
        'inline-flex items-center justify-center whitespace-nowrap rounded-md px-3 py-1 text-sm font-medium transition-all',
        'focus-visible:outline-none disabled:pointer-events-none disabled:opacity-50',
        // Épica E — EP-02: bg-white + text-foreground era el bug real
        // (--foreground vale un color CLARO en modo oscuro — texto casi
        // invisible sobre fondo blanco). Superficie elevada + texto claro,
        // mismo lenguaje que .glass-panel-elevated.
        isActive ? 'bg-white/[0.08] text-neural-text shadow-sm' : 'text-neural-muted hover:text-neural-text',
        className
      )}
      {...props}
    >
      {children}
    </button>
  )
}

function TabsContent({
  value,
  className,
  children,
  ...props
}: React.HTMLAttributes<HTMLDivElement> & { value: string }) {
  const { value: selectedValue } = useTabs()

  if (selectedValue !== value) return null

  return (
    <div
      role="tabpanel"
      data-state={selectedValue === value ? 'active' : 'inactive'}
      className={cn('mt-2', className)}
      {...props}
    >
      {children}
    </div>
  )
}

export { Tabs, TabsList, TabsTrigger, TabsContent }
