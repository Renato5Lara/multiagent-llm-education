import { Link } from 'react-router-dom'
import { Home, AlertTriangle } from 'lucide-react'
import { Button } from '@/components/ui/button'

export default function NotFound() {
    return (
        <div className="min-h-screen flex items-center justify-center bg-gray-50">
            <div className="text-center">
                <div className="mx-auto w-20 h-20 rounded-full bg-yellow-100 flex items-center justify-center mb-6">
                    <AlertTriangle className="h-10 w-10 text-yellow-600" />
                </div>
                <h1 className="text-6xl font-bold text-gray-900 mb-2">404</h1>
                <h2 className="text-xl font-semibold text-gray-700 mb-4">Página no encontrada</h2>
                <p className="text-muted-foreground mb-8 max-w-md mx-auto">
                    La página que buscas no existe o fue movida.
                </p>
                <Link to="/">
                    <Button>
                        <Home className="mr-2 h-4 w-4" />
                        Volver al inicio
                    </Button>
                </Link>
            </div>
        </div>
    )
}
