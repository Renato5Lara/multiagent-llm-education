import { Component, type ReactNode, type ErrorInfo } from 'react'
import { AlertTriangle, RefreshCw } from 'lucide-react'
import { Button } from '@/components/ui/button'

interface Props {
  children: ReactNode
  fallback?: ReactNode
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) return this.props.fallback

      return (
        <div className="min-h-[400px] flex items-center justify-center p-8">
          <div className="text-center max-w-md">
            <div className="w-16 h-16 rounded-full bg-red-100 flex items-center justify-center mx-auto mb-4">
              <AlertTriangle className="h-8 w-8 text-red-600" />
            </div>
            <h2 className="text-xl font-semibold text-gray-900 mb-2">
              Algo salió mal
            </h2>
            <p className="text-sm text-muted-foreground mb-6">
              Ocurrió un error inesperado en esta sección. Puede intentar de nuevo o contactar al soporte.
            </p>
            <div className="flex gap-3 justify-center">
              <Button variant="outline" onClick={() => window.location.reload()}>
                <RefreshCw className="h-4 w-4 mr-2" />
                Recargar página
              </Button>
              <Button onClick={this.handleRetry}>
                Reintentar
              </Button>
            </div>
            {this.state.error && (
              <details className="mt-4 text-left">
                <summary className="text-xs text-muted-foreground cursor-pointer hover:text-foreground">
                  Detalles técnicos
                </summary>
                <pre className="mt-2 text-xs bg-gray-50 p-3 rounded-lg overflow-auto max-h-32 text-red-700">
                  {this.state.error.message}
                </pre>
              </details>
            )}
          </div>
        </div>
      )
    }

    return this.props.children
  }
}

export function QueryErrorFallback({
  error,
  retry,
}: {
  error: unknown
  retry?: () => void
}) {
  const message = error instanceof Error ? error.message : 'Error al cargar datos'

  return (
    <div className="flex flex-col items-center justify-center py-16 px-4">
      <div className="w-14 h-14 rounded-full bg-red-50 flex items-center justify-center mb-4">
        <AlertTriangle className="h-7 w-7 text-red-500" />
      </div>
      <h3 className="text-lg font-medium text-gray-900 mb-1">
        Error al cargar datos
      </h3>
      <p className="text-sm text-muted-foreground text-center max-w-sm mb-6">
        {message}
      </p>
      {retry && (
        <Button variant="outline" size="sm" onClick={retry}>
          <RefreshCw className="h-4 w-4 mr-2" />
          Intentar de nuevo
        </Button>
      )}
    </div>
  )
}
