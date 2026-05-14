import { useCallback, useState } from 'react'
import { Upload, X, FileText, Film, Image, File } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { ACCEPTED_FILE_TYPES, MAX_FILE_SIZE_MB } from '@/lib/constants'
import { formatFileSize } from '@/lib/utils'

interface FileUploaderProps {
    onUpload: (file: File) => void
    isUploading?: boolean
    accept?: string
    maxSizeMB?: number
}

function getFileIcon(type: string) {
    if (type === 'application/pdf') return <FileText className="h-8 w-8 text-red-500" />
    if (type.startsWith('video/')) return <Film className="h-8 w-8 text-blue-500" />
    if (type.startsWith('image/')) return <Image className="h-8 w-8 text-green-500" />
    return <File className="h-8 w-8 text-gray-500" />
}

export default function FileUploader({
    onUpload,
    isUploading = false,
    accept = ACCEPTED_FILE_TYPES,
    maxSizeMB = MAX_FILE_SIZE_MB,
}: FileUploaderProps) {
    const [dragOver, setDragOver] = useState(false)
    const [selectedFile, setSelectedFile] = useState<File | null>(null)
    const [error, setError] = useState<string | null>(null)

    const validateFile = useCallback((file: File): boolean => {
        setError(null)
        const maxBytes = maxSizeMB * 1024 * 1024
        if (file.size > maxBytes) {
            setError(`El archivo excede el tamaño máximo de ${maxSizeMB}MB`)
            return false
        }
        const ext = '.' + file.name.split('.').pop()?.toLowerCase()
        if (!accept.split(',').includes(ext)) {
            setError(`Tipo de archivo no permitido. Permitidos: ${accept}`)
            return false
        }
        return true
    }, [accept, maxSizeMB])

    const handleFile = useCallback((file: File) => {
        if (validateFile(file)) {
            setSelectedFile(file)
        }
    }, [validateFile])

    const handleDrop = useCallback((e: React.DragEvent) => {
        e.preventDefault()
        setDragOver(false)
        const file = e.dataTransfer.files[0]
        if (file) handleFile(file)
    }, [handleFile])

    const handleSubmit = () => {
        if (selectedFile) {
            onUpload(selectedFile)
            setSelectedFile(null)
        }
    }

    return (
        <div className="space-y-4">
            <div
                className={`border-2 border-dashed rounded-lg p-8 text-center transition-colors cursor-pointer
                    ${dragOver ? 'border-primary bg-primary/5' : 'border-gray-300 hover:border-primary/50'}
                    ${error ? 'border-red-300 bg-red-50' : ''}`}
                onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
                onDragLeave={() => setDragOver(false)}
                onDrop={handleDrop}
                onClick={() => document.getElementById('file-upload')?.click()}
            >
                <input
                    id="file-upload"
                    type="file"
                    className="hidden"
                    accept={accept}
                    onChange={(e) => {
                        const file = e.target.files?.[0]
                        if (file) handleFile(file)
                        e.target.value = ''
                    }}
                />
                <Upload className="h-10 w-10 text-gray-400 mx-auto mb-3" />
                <p className="text-sm font-medium text-gray-700">
                    Arrastra un archivo aquí o haz clic para seleccionar
                </p>
                <p className="text-xs text-muted-foreground mt-1">
                    PDF, MP4, JPG, PNG, TXT, DOCX — Máx. {maxSizeMB}MB
                </p>
            </div>

            {error && <p className="text-sm text-red-600">{error}</p>}

            {selectedFile && (
                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg border">
                    {getFileIcon(selectedFile.type)}
                    <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{selectedFile.name}</p>
                        <p className="text-xs text-muted-foreground">{formatFileSize(selectedFile.size)}</p>
                    </div>
                    <Button
                        variant="ghost"
                        size="sm"
                        onClick={(e) => { e.stopPropagation(); setSelectedFile(null); setError(null) }}
                    >
                        <X className="h-4 w-4" />
                    </Button>
                    <Button size="sm" onClick={handleSubmit} disabled={isUploading}>
                        {isUploading ? 'Subiendo...' : 'Subir'}
                    </Button>
                </div>
            )}
        </div>
    )
}
