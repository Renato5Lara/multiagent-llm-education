import * as React from 'react'
import { cn } from '@/lib/utils'

type ProgressProps = React.HTMLAttributes<HTMLDivElement> & {
  value?: number
}

const Progress = React.forwardRef<HTMLDivElement, ProgressProps>(({ className, value = 0, ...props }, ref) => (
  <div
    ref={ref}
    role="progressbar"
    aria-valuenow={value}
    aria-valuemin={0}
    aria-valuemax={100}
    className={cn('relative h-2 w-full overflow-hidden rounded-full bg-gray-200', className)}
    {...props}
  >
    <div
      className="h-full w-full flex-1 bg-primary transition-all duration-300 rounded-full"
      style={{ transform: `translateX(-${100 - Math.min(Math.max(value, 0), 100)}%)` }}
    />
  </div>
))
Progress.displayName = 'Progress'

export { Progress }
