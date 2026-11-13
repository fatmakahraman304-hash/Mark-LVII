"""OSIRIS world-map voice bridge for MARK LVII.

Opens documented OSIRIS layer links in the MARK LVII Qt window or browser.
Optional PyQt6-WebEngine provides an embedded view. No live data reading.
No third-party Python packages, credentials, web scraping, or background polling.

OSIRIS: https://github.com/simplifaisoul/osiris (MIT licence).
The OSIRIS client restores a comma-separated ?layers= query parameter.
"""
from __future__ import annotations

import os
import re
import threading
import unicodedata
import webbrowser
from urllib.parse import urlencode, urlsplit

PUBLIC_URL = "https://osirisai.live/"
ALLOWED_LAYERS = frozenset({
    "flights", "private", "jets", "military", "maritime", "transit",
    "satellites", "sat_comms", "sat_military", "sat_navigation",
    "sat_earth", "sat_science", "balloons", "cctv", "cctv_previews",
    "live_news", "earthquakes", "fires", "weather", "radiation",
    "infrastructure", "global_incidents", "alert_pins", "war_alerts",
    "day_night", "cables", "sdk_sea", "sdk_air", "sdk_naval",
    "live_clouds", "wind", "rain", "wind_controls", "rain_controls",
    "wind_particles", "terrain_3d", "terrain_elevation",
    "gdelt_events", "cf_outages", "cf_attacks",
})
# Match the OSIRIS page.tsx defaults; a voice command starts from this set.
DEFAULT_LAYERS = frozenset({
    "maritime", "satellites", "cctv", "cctv_previews", "live_news",
    "earthquakes", "global_incidents", "day_night", "cables",
    "sdk_sea", "sdk_air", "sdk_naval", "wind_controls", "rain_controls",
})
PRESETS = {
    "world": DEFAULT_LAYERS,
    "air": frozenset({"flights", "private", "jets", "day_night"}),
    "sea": frozenset({"maritime", "sdk_sea", "day_night"}),
    "space": frozenset({"satellites", "sat_comms", "sat_navigation",
                        "sat_earth", "sat_science", "day_night"}),
    "cameras": frozenset({"cctv", "cctv_previews", "day_night"}),
    "disasters": frozenset({"earthquakes", "fires", "weather",
                            "global_incidents", "day_night"}),
    "weather": frozenset({"weather", "wind", "rain", "wind_controls",
                          "rain_controls", "day_night"}),
    "news": frozenset({"live_news", "global_incidents", "earthquakes"}),
}

# Only these layer IDs can enter an URL. Synonyms are interpreted locally.
ALIASES = {
    "ucak": "flights", "ucaklar": "flights", "ucus": "flights",
    "ucuslar": "flights", "flight": "flights",
    "ozel ucak": "private", "ozel ucaklar": "private",
    "jet": "jets", "jetler": "jets",
    "askeri ucak": "military", "askeri ucaklar": "military",
    "gemi": "maritime", "gemiler": "maritime", "deniz trafigi": "maritime",
    "uydu": "satellites", "uydular": "satellites",
    "kamera": "cctv", "kameralar": "cctv", "trafik kamerasi": "cctv",
    "kamera onizleme": "cctv_previews",
    "deprem": "earthquakes", "depremler": "earthquakes",
    "yangin": "fires", "yanginlar": "fires",
    "hava durumu": "weather", "meteoroloji": "weather",
    "ruzgar": "wind", "yagmur": "rain", "yagis": "rain",
    "haber": "live_news", "haberler": "live_news",
    "olay": "global_incidents", "olaylar": "global_incidents",
    "gece gunduz": "day_night", "gunduz gece": "day_night",
    "kablolar": "cables", "denizalti kablolari": "cables",
    "3d arazi": "terrain_3d",
}
PRESET_ALIASES = {
    "dunya": "world", "varsayilan": "world", "default": "world",
    "havacilik": "air", "ucak": "air", "ucuslar": "air",
    "deniz": "sea", "gemi": "sea",
    "uzay": "space", "uydular": "space",
    "kameralar": "cameras", "kamera": "cameras",
    "afet": "disasters", "afetler": "disasters", "depremler": "disasters",
    "meteoroloji": "weather", "hava": "weather",
    "haberler": "news",
}

PLUGIN = {
    "name": "osiris_world",
    "description": (
        "Use ONLY when the user explicitly asks for OSIRIS, the world command "
        "map, or to show/hide map data layers (aircraft, ships, public CCTV, "
        "satellites, earthquakes, weather, news). Open a browser URL with the "
        "chosen layer configuration. This does NOT read live information or "
        "control arbitrary web tabs; do not claim the map loaded or that any "
        "event or aircraft was observed. Turkish requests are supported. "
        "Modes: open, show, hide, focus, preset, reset, clear, locate, zoom, status. "
        "locate/zoom/status require a patched local OSIRIS instance; results arrive "
        "asynchronously in the activity log. Never claim completion from a queued response."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "mode": {"type": "STRING",
                     "description": "open/show/hide/focus/preset/reset/clear/locate/zoom/status"},
            "layers": {"type": "STRING",
                       "description": "Comma-separated layer names, e.g. earthquakes, cctv, flights. For show/hide/focus."},
            "place": {"type": "STRING", "description": "City or place name for locate, e.g. Gazimağusa. Do not invent coordinates."},
            "delta": {"type": "NUMBER", "description": "Zoom change from -3 to 3; positive zooms in."},
            "preset": {"type": "STRING",
                       "description": "world, air, sea, space, cameras, disasters, weather, news. For preset mode."},
        },
        "required": [],
    },
}

_lock = threading.Lock()
_selected_layers = set(DEFAULT_LAYERS)


def _normalize(value: object) -> str:
    value = str(value or "").strip().casefold()
    value = value.replace("ı", "i")
    value = "".join(ch for ch in unicodedata.normalize("NFKD", value)
                    if not unicodedata.combining(ch))
    return re.sub(r"\s+", " ", value)


def parse_layers(value: object) -> set[str]:
    """Fail closed on any unknown layer (no partially accepted command)."""
    parts = re.split(r"\s*(?:,|;|\+|\bve\b|\band\b)\s*", _normalize(value))
    if not 1 <= len(parts) <= 12 or any(not part for part in parts):
        raise ValueError("Katman adlarını virgülle ayırarak belirt.")
    resolved = set()
    for part in parts:
        key = ALIASES.get(part, part.replace(" ", "_"))
        if key not in ALLOWED_LAYERS:
            raise ValueError("Tanınmayan OSIRIS katmanı: " + part[:60])
        resolved.add(key)
    return resolved


def trusted_base_url() -> str:
    """Allow official HTTPS site or a self-hosted *loopback* instance only."""
    candidate = os.environ.get("JARVIS_OSIRIS_URL", PUBLIC_URL).strip()
    parsed = urlsplit(candidate)
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ValueError("OSIRIS adresi geçersiz: kimlik bilgisi ve sorgu kullanılamaz.")
    if parsed.path not in ("", "/"):
        raise ValueError("OSIRIS adresi yalnızca sunucu kökü olabilir.")
    try:
        port = parsed.port
    except ValueError as exc:
        raise ValueError("OSIRIS adresinde geçersiz port.") from exc
    official = (parsed.scheme == "https" and parsed.hostname == "osirisai.live"
                and port in (None, 443))
    local = (parsed.scheme == "http" and parsed.hostname in
             ("127.0.0.1", "localhost", "::1") and (port is None or port > 0))
    if not (official or local):
        raise ValueError("OSIRIS için yalnızca resmi HTTPS sitesi veya yerel sunucu kullanılabilir.")
    if local:
        host = "[::1]" if parsed.hostname == "::1" else parsed.hostname
        return "http://" + host + ":" + str(port or 3000) + "/"
    return PUBLIC_URL


def build_url(layers: set[str] | frozenset[str]) -> str:
    if not set(layers).issubset(ALLOWED_LAYERS):
        raise ValueError("Geçersiz OSIRIS katmanı.")
    # OSIRIS ignores empty ?layers=. An unknown, nonempty sentinel means all
    # visual data layers are OFF; its two old weather control boxes may remain.
    enabled = ",".join(sorted(layers)) if layers else "none"
    return trusted_base_url() + "?" + urlencode({"layers": enabled})


def _prepare(mode: str, args: dict, current: set[str]) -> set[str]:
    if mode in ("open", "reset"):
        return set(DEFAULT_LAYERS)
    if mode == "clear":
        return set()
    if mode == "preset":
        preset = _normalize(args.get("preset") or "world")
        preset = PRESET_ALIASES.get(preset, preset)
        if preset not in PRESETS:
            raise ValueError("Tanınmayan görünüm. Seçenekler: world, air, sea, space, cameras, disasters, weather, news.")
        return set(PRESETS[preset])
    if mode in ("show", "hide", "focus"):
        layers = parse_layers(args.get("layers"))
        if mode == "focus":
            return layers
        if mode == "show":
            return current | layers
        return current - layers
    raise ValueError("Geçersiz işlem. open, show, hide, focus, preset, reset veya clear kullan.")


def run(parameters: dict, player=None, session_memory=None) -> str:
    """Called by MARK LVII plugin loader; may run on a worker thread."""
    global _selected_layers
    try:
        params = parameters if isinstance(parameters, dict) else {}
        mode = _normalize(params.get("mode") or "open")
        mode = {
            "ac": "open", "baslat": "open",
            "goster": "show", "ekle": "show",
            "gizle": "hide", "kapat": "hide",
            "odaklan": "focus", "sadece": "focus",
            "gorunum": "preset", "sifirla": "reset",
            "temizle": "clear", "hepsini kapat": "clear",
            "git": "locate", "konum": "locate", "durum": "status",
            "yaklas": "zoom", "uzaklas": "zoom",
        }.get(mode, mode)
        if mode in ("locate", "zoom", "status"):
            if urlsplit(trusted_base_url()).scheme != "http":
                return "Bu komut köprü kurulmuş yerel OSIRIS gerektirir; çevrimiçi sürümde anlık kontrol yok."
            control = getattr(player, "control_osiris", None)
            if not callable(control):
                return "Anlık OSIRIS kontrolü için JARVIS harita penceresi gerekli."
            command = {"kind": mode}
            if mode == "locate":
                place = params.get("place")
                if not isinstance(place, str) or not 1 <= len(place.strip()) <= 120:
                    return "Gitmek istediğin şehri veya yeri belirt."
                command["place"] = place.strip()
            if mode == "zoom":
                delta = params.get("delta", -1 if _normalize(params.get("mode")) == "uzaklas" else 1)
                if type(delta) not in (int, float) or not -3 <= delta <= 3:
                    return "Yakınlaştırma değişimi -3 ile 3 arasında olmalı."
                command["delta"] = delta
            control(command)
            return "OSIRIS komutu kuyruğa alındı; harita sonucu etkinlik günlüğünde doğrulanacak."
        with _lock:
            selected = _prepare(mode, params, set(_selected_layers))
            url = build_url(selected)
            # A successful return only means the OS accepted the browser request.
            display = getattr(player, "show_osiris", None) if player is not None else None
            if callable(display):
                display(url)  # Emits a Qt signal; navigation happens on the GUI thread.
                accepted = True
            else:
                accepted = webbrowser.open(url, new=2, autoraise=True)
            if not accepted:
                return "OSIRIS bağlantısı hazır ancak tarayıcı açma isteği kabul edilmedi."
            _selected_layers = selected
        count = len(selected)
        message = (
            f"OSIRIS haritası görüntüleyiciye iletildi. Seçili katman sayısı: {count}. "
            "Haritanın yüklendiği henüz doğrulanmadı."
        )
        if player is not None:
            try:
                player.write_log("OSIRIS: " + message)
            except Exception:
                pass
        return message
    except Exception as exc:
        return "OSIRIS komutu çalışmadı: " + str(exc)[:180]
