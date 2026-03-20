import base64
import io
from typing import Optional, Tuple


def extract_content_from_file(
    content: bytes, ext: str, filename: str
) -> Tuple[str, Optional[str]]:
    """
    Extract readable text (or prepare base64 for vision) from the uploaded file.
    Returns:
        (extracted_content: str, warning: Optional[str])

    Content prefixes:
        __IMAGE_BASE64__:<mime>:<b64>  → image for OpenAI vision API
        plain text                     → text for text-based analysis
    """
    warning = None

    # ── TXT ──────────────────────────────────────────────────────────────────
    if ext == ".txt":
        try:
            text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                text = content.decode("latin-1")
                warning = "El archivo fue decodificado con codificación latin-1."
            except Exception:
                return "", "No se pudo leer el archivo de texto."
        return text, warning

    # ── PDF ──────────────────────────────────────────────────────────────────
    elif ext == ".pdf":
        try:
            import pdfplumber

            with pdfplumber.open(io.BytesIO(content)) as pdf:
                pages_text = []
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        pages_text.append(page_text)

            if pages_text:
                return "\n".join(pages_text), None

            # Scanned PDF — no text layer; send first page as image via vision
            warning = "PDF escaneado detectado (sin capa de texto). Se intentará análisis visual de la primera página."
            b64 = base64.b64encode(content).decode()
            return f"__IMAGE_BASE64__:application/pdf:{b64}", warning

        except Exception as e:
            return "", f"Error leyendo el PDF: {str(e)}"

    # ── IMAGE ─────────────────────────────────────────────────────────────────
    elif ext in {".png", ".jpg", ".jpeg"}:
        mime = "image/jpeg" if ext in {".jpg", ".jpeg"} else "image/png"
        b64 = base64.b64encode(content).decode()
        return f"__IMAGE_BASE64__:{mime}:{b64}", None

    return "", "Formato de archivo no reconocido internamente."
