"""Background Nano Banana 2 Lite creation/editing, displayed in the existing HUD."""
from pathlib import Path
import threading
import uuid
from core import gemini

PLUGIN = {
    "name": "generate_image",
    "description": "Create or edit images with Nano Banana 2 Lite. Use for 'resim oluştur', 'görsel çiz', 'bu resmi düzenle', 'arka planını değiştir'. Runs in background and displays the result inside JARVIS. For editing use mode=edit and the user-provided image_path, or omit image_path to edit the last result. Never invent paths. Do not use a browser or desktop app.",
    "parameters": {"type": "OBJECT", "properties": {
        "prompt": {"type": "STRING", "description": "Full image creation or editing instructions."},
        "mode": {"type": "STRING", "enum": ["create", "edit"]},
        "image_path": {"type": "STRING", "description": "Exact local path supplied by the user for editing; omit for last generated image."}},
        "required": ["prompt"]}}

_lock = threading.Lock()
_last_image = None


def run(parameters, player=None, session_memory=None):
    global _last_image
    try:
        prompt = str(parameters.get("prompt", "")).strip()
        mode = parameters.get("mode", "create")
        if not prompt or len(prompt) > 12000 or mode not in {"create", "edit"}:
            return "Geçerli bir görsel açıklaması ve oluşturma/düzenleme işlemi gerekli."
        if player is None or not callable(getattr(player, "show_image", None)):
            return "Görsel göstermek için JARVIS arayüzü açık olmalı."
        if not _lock.acquire(blocking=False):
            return "Önceki görsel hâlâ hazırlanıyor."
        try:
            source = None
            if mode == "edit":
                raw = parameters.get("image_path") or _last_image
                if not raw:
                    raise ValueError("Düzenlenecek resmi ekleyin veya önce bir resim oluşturun.")
                source = Path(raw).expanduser().resolve()
                if not source.is_file():
                    raise ValueError("Düzenlenecek resim bulunamadı.")
            thread = threading.Thread(target=_work, args=(prompt, source, player), daemon=True, name="jarvis-image")
            thread.start()
        except Exception:
            _lock.release()
            raise
        return "Görsel arka planda hazırlanıyor; tamamlanınca JARVIS içinde gösterilecek."
    except Exception as exc:
        return str(exc) if isinstance(exc, ValueError) else "Görsel işlemi başlatılamadı."


def _work(prompt, source, player):
    global _last_image
    try:
        data, mime = gemini.generate_picture(prompt, source)
        directory = gemini._BASE / "downloads" / "images"
        directory.mkdir(parents=True, exist_ok=True)
        suffix = {"image/png": ".png", "image/jpeg": ".jpg", "image/webp": ".webp"}[mime]
        path = directory / (uuid.uuid4().hex + suffix)
        path.write_bytes(data)
        _last_image = str(path)
        player.show_image(str(path), "Görsel")
    except Exception as exc:
        # Never expose API keys or request payloads in UI errors.
        code = str(getattr(exc, "code", ""))
        message = ("Gemini görsel erişimi veya kotası yetersiz; API hesabını kontrol edin."
                   if code in {"401", "403", "429"} else
                   "Görsel oluşturulamadı. Gemini anahtarını, model erişimini ve bağlantıyı kontrol edin.")
        player.write_log("GÖRSEL: " + message)
    finally:
        _lock.release()
