import * as React from 'react'
import { useLocation } from 'react-router-dom'
import { cn } from '@/lib/utils'

type DropdownMenuContextType = {
  open: boolean
  setOpen: React.Dispatch<React.SetStateAction<boolean>>
  triggerRef: React.RefObject<HTMLDivElement | null>
}

const DropdownMenuContext = React.createContext<DropdownMenuContextType | null>(null)

function useDropdown() {
  const ctx = React.useContext(DropdownMenuContext)
  if (!ctx) throw new Error('DropdownMenu sub-components must be used within DropdownMenu')
  return ctx
}

export function DropdownMenu({ children }: { children: React.ReactNode }) {
  const [open, setOpen] = React.useState(false)
  const triggerRef = React.useRef<HTMLDivElement>(null)
  const location = useLocation()

  React.useEffect(() => {
    setOpen(false)
  }, [location.pathname])

  React.useEffect(() => {
    if (!open) return

    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setOpen(false)
        triggerRef.current?.querySelector('button')?.focus()
      }
    }

    const handleClickOutside = (e: MouseEvent) => {
      if (triggerRef.current && !triggerRef.current.contains(e.target as Node)) {
        setOpen(false)
      }
    }

    document.addEventListener('keydown', handleKeyDown)
    document.addEventListener('mousedown', handleClickOutside)
    return () => {
      document.removeEventListener('keydown', handleKeyDown)
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [open])

  return (
    <DropdownMenuContext.Provider value={{ open, setOpen, triggerRef }}>
      <div ref={triggerRef} className="relative inline-block">
        {children}
      </div>
    </DropdownMenuContext.Provider>
  )
}

type DropdownMenuTriggerProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  asChild?: boolean
}

export const DropdownMenuTrigger = React.forwardRef<HTMLButtonElement, DropdownMenuTriggerProps>(
  ({ className, onClick, ...props }, ref) => {
    const { open, setOpen } = useDropdown()

    return (
      <button
        ref={ref}
        type="button"
        aria-haspopup="true"
        aria-expanded={open}
        onClick={(e) => {
          onClick?.(e)
          setOpen((prev: boolean) => !prev)
        }}
        className={cn('inline-flex items-center', className)}
        {...props}
      />
    )
  }
)
DropdownMenuTrigger.displayName = 'DropdownMenuTrigger'

type DropdownMenuContentProps = React.HTMLAttributes<HTMLDivElement> & {
  align?: 'start' | 'end'
}

export const DropdownMenuContent = React.forwardRef<HTMLDivElement, DropdownMenuContentProps>(
  ({ className, align = 'end', children, ...props }, ref) => {
    const { open } = useDropdown()
    const contentRef = React.useRef<HTMLDivElement>(null)

    React.useEffect(() => {
      if (open) {
        const timer = setTimeout(() => {
          contentRef.current?.focus()
        }, 50)
        return () => clearTimeout(timer)
      }
    }, [open])

    if (!open) return null

    return (
      <div
        ref={(node) => {
          if (typeof ref === 'function') ref(node)
          else if (ref) ref.current = node
          contentRef.current = node
        }}
        role="menu"
        tabIndex={-1}
        className={cn(
          'absolute z-40 mt-1.5 min-w-[14rem] rounded-xl border bg-white p-1.5 shadow-xl',
          'animate-in fade-in zoom-in-95 origin-top-right',
          align === 'end' ? 'right-0' : 'left-0',
          className
        )}
        {...props}
      >
        {children}
      </div>
    )
  }
)
DropdownMenuContent.displayName = 'DropdownMenuContent'

export const DropdownMenuLabel = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('px-2.5 py-2 text-sm font-semibold text-gray-900', className)} {...props} />
  )
)
DropdownMenuLabel.displayName = 'DropdownMenuLabel'

export const DropdownMenuSeparator = React.forwardRef<HTMLDivElement, React.HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={cn('-mx-1.5 my-1 h-px bg-gray-100', className)} {...props} />
  )
)
DropdownMenuSeparator.displayName = 'DropdownMenuSeparator'

type DropdownMenuItemProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  disabled?: boolean
}

export const DropdownMenuItem = React.forwardRef<HTMLButtonElement, DropdownMenuItemProps>(
  ({ className, disabled, onClick, ...props }, ref) => {
    const { setOpen } = useDropdown()

    return (
      <button
        ref={ref}
        type="button"
        role="menuitem"
        disabled={disabled}
        onClick={(e) => {
          onClick?.(e)
          setOpen(false)
        }}
        className={cn(
          'flex w-full items-center gap-2.5 rounded-lg px-2.5 py-2 text-sm transition-colors',
          'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-primary/30',
          'disabled:pointer-events-none disabled:opacity-50',
          'hover:bg-gray-100 text-gray-700 hover:text-gray-900',
          className
        )}
        {...props}
      />
    )
  }
)
DropdownMenuItem.displayName = 'DropdownMenuItem'
