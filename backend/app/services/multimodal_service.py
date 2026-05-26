import base64
import json
import logging
import os
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Optional

from app.core.config import settings

logger = logging.getLogger(__name__)


class ContentCategory(str, Enum):
    TEXT = "text"
    IMAGE = "image"
    PDF = "pdf"
    VIDEO = "video"
    AUDIO = "audio"
    INTERACTIVE = "interactive"
    CODE = "code"
    DIAGRAM = "diagram"
    FORMULA = "formula"
    CHART = "chart"


class ProcessingStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class MultimodalService:
    """
    Servicio multimodal para procesar y almacenar contenido educativo
    en múltiples formatos: texto, imágenes, PDF, audio, video, interactivos.
    Preparado para futuras integraciones de voz y explicaciones multimodales.
    """

    def __init__(self):
        self.storage_base = Path(settings.UPLOAD_DIR) / "multimodal"
        self._ensure_directories()

    def _ensure_directories(self):
        categories = [c.value for c in ContentCategory]
        for cat in categories:
            (self.storage_base / cat).mkdir(parents=True, exist_ok=True)
        (self.storage_base / "processed").mkdir(parents=True, exist_ok=True)
        (self.storage_base / "thumbnails").mkdir(parents=True, exist_ok=True)

    def store_content(
        self,
        content: bytes,
        category: ContentCategory,
        filename: str,
        metadata: Optional[dict] = None,
    ) -> dict:
        content_id = str(uuid.uuid4())
        ext = Path(filename).suffix
        safe_name = f"{content_id}{ext}"
        file_path = self.storage_base / category.value / safe_name

        with open(file_path, "wb") as f:
            f.write(content)

        result = {
            "id": content_id,
            "category": category.value,
            "filename": safe_name,
            "original_filename": filename,
            "size_bytes": len(content),
            "mime_type": self._guess_mime_type(category, ext),
            "stored_at": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {},
            "url": f"/uploads/multimodal/{category.value}/{safe_name}",
            "thumbnail_url": None,
        }

        if category in (ContentCategory.IMAGE, ContentCategory.DIAGRAM, ContentCategory.CHART):
            result["thumbnail_url"] = result["url"]

        return result

    def _guess_mime_type(self, category: ContentCategory, ext: str) -> str:
        mime_map = {
            ".pdf": "application/pdf",
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".webp": "image/webp",
            ".mp4": "video/mp4",
            ".webm": "video/webm",
            ".mp3": "audio/mpeg",
            ".wav": "audio/wav",
            ".ogg": "audio/ogg",
            ".html": "text/html",
            ".md": "text/markdown",
        }
        return mime_map.get(ext.lower(), "application/octet-stream")

    def content_to_base64(self, content: bytes) -> str:
        return base64.b64encode(content).decode("utf-8")

    def prepare_ai_context(self, content_type: str, content_data: dict) -> str:
        if content_type == "text":
            return content_data.get("text", "")
        elif content_type == "image":
            return f"[Imagen: {content_data.get('filename', 'unknown')}]"
        elif content_type == "pdf":
            return f"[Documento PDF: {content_data.get('filename', 'unknown')} - {content_data.get('pages', 0)} páginas]"
        elif content_type == "code":
            return f"[Código: {content_data.get('language', 'text')}]\n{content_data.get('code', '')}"
        elif content_type == "formula":
            return f"[Fórmula: {content_data.get('latex', '')}]"
        return str(content_data)


class ContentChunk:
    """
    Representa un fragmento de contenido multimodal
    que puede ser texto, imagen, video, etc.
    Usado para construir explicaciones multimodales.
    """

    def __init__(self, chunk_type: str, data: dict, order: int = 0):
        self.chunk_type = chunk_type
        self.data = data
        self.order = order

    def to_dict(self) -> dict:
        return {
            "type": self.chunk_type,
            "data": self.data,
            "order": self.order,
        }


class MultimodalExplanation:
    """
    Explicación multimodal compuesta por múltiples chunks
    (texto + imagen + código + diagrama).
    Preparado para futuras explicaciones con voz.
    """

    def __init__(self, title: str, chunks: Optional[list[ContentChunk]] = None):
        self.id = str(uuid.uuid4())
        self.title = title
        self.chunks = chunks or []
        self.created_at = datetime.now(timezone.utc)

    def add_chunk(self, chunk: ContentChunk):
        chunk.order = len(self.chunks)
        self.chunks.append(chunk)

    def add_text(self, text: str):
        self.add_chunk(ContentChunk("text", {"content": text}))

    def add_image(self, url: str, caption: str = ""):
        self.add_chunk(ContentChunk("image", {"url": url, "caption": caption}))

    def add_code(self, code: str, language: str = "python"):
        self.add_chunk(ContentChunk("code", {"code": code, "language": language}))

    def add_diagram(self, diagram_type: str, data: dict):
        self.add_chunk(ContentChunk("diagram", {"type": diagram_type, "data": data}))

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "title": self.title,
            "chunks": [c.to_dict() for c in self.chunks],
            "created_at": self.created_at.isoformat(),
        }


multimodal_service = MultimodalService()
