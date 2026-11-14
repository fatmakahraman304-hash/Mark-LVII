"""Create/edit an image inside JARVIS, using local ComfyUI when available.

The Gemini Nano Banana 2 Lite image API is paid-only. Never silently call a
billable endpoint. Opt-in requires JARVIS_ALLOW_PAID_IMAGES=1 and provider=gemini
(or provider=auto with a local service unavailable and the opt-in enabled).
"""
from pathlib import Path
import os
import threading
import uuid

from core import gemini, local_image

PLUGIN = {
    "name": "generate_image",
    "description": (
        "Create or edit an image for the user. Call for 'resim oluştur', "
        "'görsel çiz', 'bu resmi düzenle', 'arka planını değiştir'. "
        "The image displays inside JARVIS and is saved under downloads/images. "
        "Prefer the free LOCAL ComfyUI server when available. Nano Banana 2 Lite "
        "Gemini API is paid-only and disabled without local opt-in. "
        "Do not claim completion until the result appears. "
        "For editing, use a file dropped into the JARVIS interface or the "
        "last generated image; do not invent paths."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "prompt": {"type": "STRING", "description": "Image request or editing instructions."},
            "mode": {"type": "STRING", "enum": ["create", "edit"]},
            "provider": {
                "type": "STRING", "enum": ["auto", "local", "gemini"],
                "description": "auto (default) tries local first. gemini requires explicit account opt-in."
            },
            "image_path": {
                "type": "STRING",
                "description": "Optional exact path of image currently dropped into JARVIS."
            },
        },
        "required": ["prompt"]
    },
}

_lock = threading.Lock()
_last_image = None


def _paid_allowed() -> bool:
    return os.environ.get("JARVIS_ALLOW_PAID_IMAGES", "").strip() == "1"


def _backend(provider: str) -> tuple[str | None, str]:
    if provider not in ("auto", "local", "gemini"):
        return None, "Görsel sağlayıcısı auto, local veya gemini olmalı."
    if provider in ("auto", "local"):
        ok, reason = local_image.ready()
        if ok:
            return "local", ""
        if provider == "local" or not _paid_allowed():
            return None, (
                reason + " Nano Banana 2 Lite Gemini API ücretsiz değil; "
                "ücretli API çağrısı otomatik yapılmadı."
            )
    if not _paid_allowed():
        return None, (
            "Nano Banana 2 Lite Gemini API ücretlidir; bu kurulumda ücretli "
            "görsel çağrıları kapalı. Ücretsiz yerel seçenek için ComfyUI gerekir."
        )
    return "gemini", ""


def _selected_source(parameters: dict, player) -> Path:
    """Only the user's dropped file or the previous output may be edited."""
    candidates = []
    if player is not None:
        try:
            chosen = getattr(player, "current_file", None)
            if isinstance(chosen, str) and chosen:
                candidates.append(Path(chosen).expanduser().resolve())
        except Exception:
            pass
    if _last_image:
        candidates.append(Path(_last_image).expanduser().resolve())
    raw = parameters.get("image_path")
    if raw:
        requested = Path(str(raw)).expanduser().resolve()
        if requested not in candidates:
            raise ValueError(
                "Düzenlenecek resmi önce JARVIS'in sağdaki dosya alanına bırakın."
            )
        selected = requested
    elif candidates:
        selected = candidates[0]
    else:
        raise ValueError(
            "Düzenlenecek resmi sağdaki dosya alanına bırakın "
            "veya önce bir resim oluşturun."
        )
    if not selected.is_file():
        raise ValueError("Düzenlenecek görsel bulunamadı.")
    return selected


def run(parameters, player=None, session_memory=None):
    try:
        params = parameters if isinstance(parameters, dict) else {}
        prompt = str(params.get("prompt", "")).strip()
        mode = str(params.get("mode") or "create")
        provider = str(params.get("provider") or "auto").lower().strip()
        if not prompt or len(prompt) > 12000 or mode not in ("create", "edit"):
            return "Geçerli bir görsel açıklaması ve oluşturma/düzenleme işlemi gerekli."
        if player is None or not callable(getattr(player, "show_image", None)):
            return "Görsel göstermek için JARVIS arayüzü açık olmalı."
        if not _lock.acquire(blocking=False):
            return "Önceki görsel hâlâ hazırlanıyor."
        try:
            source = _selected_source(params, player) if mode == "edit" else None
            backend, message = _backend(provider)
            if not backend:
                return message
            worker = threading.Thread(
                target=_work, args=(prompt, source, player, backend),
                daemon=True, name="jarvis-image"
            )
            worker.start()
        finally:
            # A worker holds the lock until it completes; no worker = unlock now.
            if "worker" not in locals() or not worker.is_alive():
                _lock.release()
        return (
            f"Görsel {('yerel ComfyUI' if backend == 'local' else 'Gemini API')} "
            "ile arka planda hazırlanıyor; tamamlanınca JARVIS içinde gösterilecek."
        )
    except ValueError as exc:
        return str(exc)
    except Exception:
        return "Görsel işlemi başlatılamadı."


def _work(prompt, source, player, backend):
    global _last_image
    try:
        data, mime = (
            local_image.generate(prompt, source)
            if backend == "local" else gemini.generate_picture(prompt, source)
        )
        directory = gemini._BASE / "downloads" / "images"
        directory.mkdir(parents=True, exist_ok=True)
        suffix = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[mime]
        path = directory / (uuid.uuid4().hex + suffix)
        path.write_bytes(data)
        _last_image = str(path)
        player.show_image(str(path), "Görsel")
        player.write_log("GÖRSEL: Oluşturuldu ve downloads/images içine kaydedildi.")
    except Exception as exc:
        if backend == "local":
            message = (
                str(exc) if isinstance(exc, local_image.LocalImageError)
                else "Yerel görsel üretimi başarısız; ComfyUI modelini kontrol edin."
            )
        else:
            code = str(getattr(exc, "code", getattr(exc, "status_code", "")))
            if code == "429":
                message = "Gemini görsel API kotası tükendi (429)."
            elif code in ("401", "403"):
                message = "Gemini görsel API erişimi yok (401/403). Ücretli erişim ve anahtarı kontrol edin."
            elif code == "404":
                message = "Gemini görsel modeli bu API anahtarı için bulunamadı (404)."
            else:
                message = "Gemini görsel API isteği başarısız. Model erişimini ve hesabınızı kontrol edin."
        try:
            player.write_log("GÖRSEL: " + message)
            display = getattr(player, "show_content", None)
            if callable(display):
                display("GÖRSEL OLUŞTURULAMADI", message)
        except Exception:
            pass
    finally:
        _lock.release()
