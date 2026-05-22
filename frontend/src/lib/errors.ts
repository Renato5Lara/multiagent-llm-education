import axios from 'axios'

export class AppError extends Error {
  constructor(
    message: string,
    public readonly code?: string,
    public readonly status?: number,
    public readonly details?: unknown,
  ) {
    super(message)
    this.name = 'AppError'
  }
}

export function getErrorMessage(error: unknown): string {
  if (error instanceof AppError) return error.message

  if (axios.isAxiosError(error)) {
    if (error.code === 'ECONNABORTED') return 'La solicitud tardó demasiado. Intente de nuevo'
    if (error.code === 'ERR_NETWORK') return 'No se pudo conectar con el servidor. Verifique su conexión'

    if (!error.response) return 'No se pudo conectar con el servidor. Verifique su conexión'

    const { status, data } = error.response

    const detail = data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d: { msg?: string }) => d.msg).join(', ')

    const statusMessages: Record<number, string> = {
      400: 'Solicitud inválida. Verifique los datos ingresados',
      401: 'Su sesión ha expirado. Inicie sesión nuevamente',
      403: 'No tiene permisos para realizar esta acción',
      404: 'Recurso no encontrado',
      409: 'Ya existe un registro con esos datos',
      422: 'Los datos enviados no son válidos',
      429: 'Demasiadas solicitudes. Espere unos segundos',
    }

    return statusMessages[status] || 'Error interno del servidor. Intente de nuevo más tarde'
  }

  if (error instanceof TypeError) {
    if (error.message.includes('fetch')) return 'Error de conexión. Verifique su Internet'
    return 'Error inesperado en la aplicación'
  }

  if (error instanceof Error) return error.message

  return 'Ocurrió un error inesperado'
}

export function getErrorStatus(error: unknown): number | undefined {
  if (axios.isAxiosError(error)) return error.response?.status
  if (error instanceof AppError) return error.status
  return undefined
}
