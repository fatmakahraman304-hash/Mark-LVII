"""Optional local-only ComfyUI image generation and editing.

The adapter connects only to 127.0.0.1/::1 and never installs or downloads
models. Standard SD1.x/SDXL checkpoint workflows are supported; FLUX and other
architectures need their own separate workflow. No cloud fallback or paid API.
Official API: /system_stats, /models/checkpoints, /prompt, /history/id, /view.
"""
from __future__ import annotations

import json
import mimetypes
import os
from pathlib import Path
import secrets
import time
from urllib.parse import urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, Request, build_opener

JSON_LIMIT = 2 * 1024 * 1024
IMAGE_LIMIT = 24 * 1024 * 1024
INPUT_LIMIT = 15 * 1024 * 1024


class LocalImageError(RuntimeError):
    """Actionable, safe messages suitable for the JARVIS activity log."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


_OPENER = build_opener(ProxyHandler({}), _NoRedirect())


def base_url() -> str:
    """Ignore proxies and require a loopback-only origin, without credentials."""
    raw = os.environ.get("JARVIS_COMFY_URL", "http://127.0.0.1:8188/").strip()
    try:
        parsed = urlsplit(raw)
        if (parsed.scheme != "http" or parsed.hostname not in
                ("127.0.0.1", "localhost", "::1") or
                parsed.username or parsed.password or parsed.query or
                parsed.fragment or parsed.path not in ("", "/")):
            raise ValueError
        port = parsed.port or 8188
        if not 1 <= port <= 65535:
            raise ValueError
    except ValueError as exc:
        raise LocalImageError(
            "ComfyUI adresi yalnızca http://127.0.0.1:8188 gibi yerel adres olabilir."
        ) from exc
    host = "[::1]" if parsed.hostname == "::1" else "127.0.0.1"
    return f"http://{host}:{port}"


def _read(path: str, *, body: bytes | None = None, mime: str | None = None,
          limit: int = JSON_LIMIT, timeout: int = 12) -> tuple[bytes, str]:
    if not path.startswith("/") or path.startswith("//"):
        raise LocalImageError("Geçersiz yerel API yolu.")
    req = Request(base_url() + path,
                  data=body,
                  headers={"Accept": "application/json" if body is None else "*/*",
                           **({"Content-Type": mime} if mime else {})},
                  method="POST" if body is not None else "GET")
    with _OPENER.open(req, timeout=timeout) as resp:
        raw = resp.read(limit + 1)
        if len(raw) > limit:
            raise LocalImageError("ComfyUI yanıtı izin verilen boyutu aştı.")
        return raw, resp.headers.get("Content-Type", "").lower()


def _json(path: str, *, body: dict | None = None, timeout: int = 12) -> object:
    packed = json.dumps(body, ensure_ascii=False).encode("utf-8") if body is not None else None
    if packed is not None and len(packed) > 128 * 1024:
        raise LocalImageError("Görsel isteği aşırı uzun.")
    data, mime = _read(path, body=packed,
                       mime="application/json" if packed is not None else None,
                       timeout=timeout)
    if "application/json" not in mime:
        raise LocalImageError("Yerel sunucu ComfyUI JSON yanıtı vermedi.")
    return json.loads(data.decode("utf-8"))


def _checkpoints() -> list[str]:
    try:
        value = _json("/models/checkpoints", timeout=3)
    except (OSError, ValueError, TimeoutError) as exc:
        raise LocalImageError(
            "Yerel ComfyUI çalışmıyor. Ücretsiz görsel için ComfyUI ve bir "
            "SDXL/SD1.5 modeli kurup ComfyUI'yi başlatmak gerekiyor."
        ) from exc
    if not isinstance(value, list):
        raise LocalImageError("ComfyUI checkpoint listesi anlaşılamadı.")
    names = [v for v in value if isinstance(v, str) and
             v.lower().endswith((".safetensors", ".ckpt"))]
    if not names:
        raise LocalImageError(
            "ComfyUI açık ama görsel modeli yok. SDXL veya SD1.5 checkpoint "
            "dosyasını ComfyUI/models/checkpoints içine kurmak gerekiyor."
        )
    return names


def ready() -> tuple[bool, str]:
    try:
        _checkpoints()
        return True, ""
    except LocalImageError as exc:
        return False, str(exc)


def _checkpoint(available: list[str]) -> str:
    configured = os.environ.get("JARVIS_COMFY_CHECKPOINT", "").strip()
    if configured:
        if configured not in available:
            raise LocalImageError("Seçili ComfyUI checkpoint bulunamadı.")
        return configured
    # A classic checkpoint workflow cannot operate a FLUX/SD3/other
    # architecture reliably. Prefer a recognisable SDXL / SD1.5 file.
    compatible = [name for name in available if not any(
        k in name.casefold() for k in ("flux", "sd3", "stable_diffusion_3", "z_image",
                                       "qwen_image", "wan2", "hunyuan", "chroma"))]
    if not compatible:
        raise LocalImageError(
            "ComfyUI modelleri basit SDXL/SD1.5 iş akışıyla uyumlu görünmüyor. "
            "SDXL veya SD1.5 checkpoint gerekiyor."
        )
    sdxl = [x for x in compatible if "xl" in x.casefold()]
    return (sdxl or compatible)[0]


def _upload(source: Path) -> str:
    src = source.resolve()
    if not src.is_file() or src.stat().st_size > INPUT_LIMIT:
        raise LocalImageError("Düzenlenecek dosya bulunamadı veya 15 MB'tan büyük.")
    mime = mimetypes.guess_type(src.name)[0]
    if mime not in ("image/png", "image/jpeg", "image/webp"):
        raise LocalImageError("Düzenleme için PNG, JPEG veya WebP görseli gerekli.")
    # Distinct random file name avoids collisions and never exposes source paths.
    filename = secrets.token_hex(12) + Path(src.name).suffix.lower()
    boundary = "jarvis" + secrets.token_hex(12)
    prefix = (
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"type\"\r\n\r\ninput\r\n"
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {mime}\r\n\r\n"
    ).encode("utf-8")
    body = prefix + src.read_bytes() + f"\r\n--{boundary}--\r\n".encode()
    data, kind = _read("/upload/image", body=body,
                       mime=f"multipart/form-data; boundary={boundary}", timeout=30)
    if "application/json" not in kind:
        raise LocalImageError("ComfyUI resim yükleme yanıtı geçersiz.")
    result = json.loads(data)
    name = result.get("name") if isinstance(result, dict) else None
    if not isinstance(name, str) or "/" in name or "\\" in name or not name:
        raise LocalImageError("ComfyUI yükleme dosya adı geçersiz.")
    return name


def make_workflow(prompt: str, checkpoint: str, *, image: str | None = None) -> dict:
    """Standard checkpoints only: SD1.5 and SDXL text-to-image / img2img."""
    workflow = {
        "4": {"class_type": "CheckpointLoaderSimple",
              "inputs": {"ckpt_name": checkpoint}},
        "6": {"class_type": "CLIPTextEncode",
              "inputs": {"text": prompt, "clip": ["4", 1]}},
        "7": {"class_type": "CLIPTextEncode",
              "inputs": {"text": "blurry, low quality, artifacts, distorted, watermark",
                         "clip": ["4", 1]}},
        "3": {"class_type": "KSampler",
              "inputs": {"seed": secrets.randbelow(2**48), "steps": 22,
                         "cfg": 7.0, "sampler_name": "euler",
                         "scheduler": "normal", "denoise": 0.62 if image else 1.0,
                         "model": ["4", 0], "positive": ["6", 0],
                         "negative": ["7", 0],
                         "latent_image": ["11", 0] if image else ["5", 0]}},
        "8": {"class_type": "VAEDecode",
              "inputs": {"samples": ["3", 0], "vae": ["4", 2]}},
        "9": {"class_type": "SaveImage",
              "inputs": {"images": ["8", 0], "filename_prefix": "JARVIS"}},
    }
    if image:
        workflow["10"] = {"class_type": "LoadImage",
                          "inputs": {"image": image}}
        workflow["11"] = {"class_type": "VAEEncode",
                          "inputs": {"pixels": ["10", 0], "vae": ["4", 2]}}
    else:
        workflow["5"] = {"class_type": "EmptyLatentImage",
                         "inputs": {"width": 512, "height": 512, "batch_size": 1}}
    return workflow


def generate(prompt: str, source: Path | None = None) -> tuple[bytes, str]:
    """Run a bounded, local-only job and return image bytes and verified MIME."""
    if not isinstance(prompt, str) or not prompt.strip() or len(prompt) > 12000:
        raise LocalImageError("Görsel açıklaması boş veya çok uzun.")
    try:
        checkpoint = _checkpoint(_checkpoints())
        source_name = _upload(source) if source is not None else None
        queued = _json("/prompt", body={
            "prompt": make_workflow(prompt, checkpoint, image=source_name),
            "client_id": secrets.token_hex(16),
        }, timeout=30)
        job = queued.get("prompt_id") if isinstance(queued, dict) else None
        if not isinstance(job, str) or not (5 <= len(job) <= 128) or any(
            ch not in "0123456789abcdef-" for ch in job.lower()
        ):
            raise LocalImageError(
                "ComfyUI görevi kabul etmedi. Model/iş akışı uyumunu kontrol edin."
            )
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            status = _json("/history/" + job, timeout=12)
            entry = status.get(job) if isinstance(status, dict) else None
            if isinstance(entry, dict):
                detail = entry.get("status")
                if isinstance(detail, dict) and detail.get("status_str") == "error":
                    raise LocalImageError("ComfyUI görsel görevi hata ile sonlandı.")
                outputs = entry.get("outputs")
                node = outputs.get("9") if isinstance(outputs, dict) else None
                images = node.get("images") if isinstance(node, dict) else None
                if isinstance(images, list) and images:
                    item = images[0]
                    if not isinstance(item, dict):
                        raise LocalImageError("ComfyUI beklenmeyen görsel yanıtı döndürdü.")
                    filename, subfolder, kind = (
                        item.get("filename"), item.get("subfolder", ""), item.get("type", "output")
                    )
                    if (not isinstance(filename, str) or not filename or
                            "/" in filename or "\\" in filename or
                            not isinstance(subfolder, str) or ".." in subfolder or
                            kind not in ("output", "temp")):
                        raise LocalImageError("ComfyUI yanıtında güvensiz dosya adı.")
                    url = "/view?" + urlencode({
                        "filename": filename, "subfolder": subfolder, "type": kind
                    })
                    blob, mime = _read(url, limit=IMAGE_LIMIT, timeout=30)
                    mime = mime.split(";")[0].strip()
                    if mime not in ("image/png", "image/jpeg", "image/webp"):
                        raise LocalImageError("ComfyUI resim yerine beklenmeyen veri döndürdü.")
                    signatures = {
                        "image/png": blob.startswith(b"\x89PNG\r\n\x1a\n"),
                        "image/jpeg": blob.startswith(b"\xff\xd8\xff"),
                        "image/webp": blob[:4] == b"RIFF" and blob[8:12] == b"WEBP",
                    }
                    if not signatures[mime]:
                        raise LocalImageError("ComfyUI görsel dosyası geçersiz.")
                    return blob, mime
            time.sleep(1.0)
        raise LocalImageError("ComfyUI oluşturma işlemi zaman sınırına ulaştı.")
    except LocalImageError:
        raise
    except Exception as exc:
        # No raw payload or secret-bearing backend body appears in the UI.
        raise LocalImageError(
            "ComfyUI isteği başarısız. Yerel sunucuyu ve uygun SDXL/SD1.5 "
            "modelini kontrol edin."
        ) from exc
