"""Read-only OSIRIS public data for MARK LVII voice conversations.

No new dependencies. No credentials. No write/action endpoints. This module
does not control or track individual aircraft, ships, military entities or
people. Each result carries a source URL and API-supplied collection time.
"""
from __future__ import annotations

import datetime as dt
import json
import math
import threading
import time
from urllib import error, request
from urllib.parse import urlsplit

from plugins.osiris_world import trusted_base_url

MAX_RESPONSE_BYTES = 2 * 1024 * 1024
CACHE_SECONDS = 90
_ALLOWED_PATHS = frozenset({"/api/stats", "/api/earthquakes"})
_cache: dict[str, tuple[float, dict]] = {}
_cache_lock = threading.Lock()
_fetch_lock = threading.Lock()

PLUGIN = {
    "name": "osiris_intel",
    "description": (
        "Read and summarize OSIRIS open-source map statistics or recent global "
        "earthquakes. Call for questions about number of map records, current "
        "global overview or recent/strong earthquakes; this tool fetches the "
        "OSIRIS public JSON API and reports its timestamps. Do not make up "
        "live counts. Does NOT show moving aircraft, track individuals, or "
        "provide military targeting information. For showing map layers use "
        "osiris_world instead. Modes: stats, earthquakes."
    ),
    "parameters": {
        "type": "OBJECT",
        "properties": {
            "mode": {"type": "STRING",
                     "description": "'stats' for global OSIRIS counters or 'earthquakes' for past-day USGS seismic events"},
            "sort": {"type": "STRING",
                     "description": "Earthquakes only: 'recent' (default) or 'strongest'"},
            "limit": {"type": "INTEGER",
                      "description": "Earthquakes only: 1 to 8 (default 5)"},
        },
        "required": [],
    },
}


class _NoRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never follow 30x to a private IP, another hostname, or an HTTP origin.
        return None


def _endpoint(path: str) -> str:
    if path not in _ALLOWED_PATHS:
        raise ValueError("Desteklenmeyen veri kaynağı.")
    return trusted_base_url() + path.removeprefix("/")


def _fetch_json(path: str) -> dict:
    """Read bounded JSON from one of two fixed APIs; deny redirects and proxies."""
    url = _endpoint(path)
    parts = urlsplit(url)
    if parts.scheme not in ("https", "http"):
        raise ValueError("Geçersiz veri adresi.")
    opener = request.build_opener(request.ProxyHandler({}), _NoRedirect())
    req = request.Request(url, headers={
        "User-Agent": "MARK-LVII-OSIRIS-ReadOnly/1.0",
        "Accept": "application/json",
    }, method="GET")
    with opener.open(req, timeout=18) as response:
        content_type = response.headers.get("Content-Type", "").lower()
        if "application/json" not in content_type:
            raise ValueError("Veri sunucusu JSON döndürmedi.")
        blob = response.read(MAX_RESPONSE_BYTES + 1)
        if len(blob) > MAX_RESPONSE_BYTES:
            raise ValueError("Veri yanıtı güvenli boyut sınırını aştı.")
        data = json.loads(blob.decode("utf-8"))
        if not isinstance(data, dict):
            raise ValueError("Beklenen JSON nesnesi bulunamadı.")
        return data


def _read(path: str) -> dict:
    now = time.monotonic()
    with _cache_lock:
        cached = _cache.get(path)
        if cached and now - cached[0] < CACHE_SECONDS:
            return cached[1]
    # Avoid parallel reads and stampedes on external data providers.
    with _fetch_lock:
        with _cache_lock:
            cached = _cache.get(path)
            if cached and time.monotonic() - cached[0] < CACHE_SECONDS:
                return cached[1]
        result = _fetch_json(path)
        with _cache_lock:
            _cache[path] = (time.monotonic(), result)
        return result


def _source_time(value: object) -> str:
    if not isinstance(value, str):
        return "belirtilmedi"
    try:
        stamp = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
        if stamp.tzinfo is None:
            return "belirtilmedi"
        return stamp.astimezone(dt.timezone.utc).strftime("%d.%m.%Y %H:%M UTC")
    except ValueError:
        return "belirtilmedi"


def _count(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "veri yok"
    if not math.isfinite(value) or value < 0:
        return "veri yok"
    return f"{int(value):,}".replace(",", ".")


def _stats(data: dict) -> tuple[str, str]:
    stats = data.get("stats")
    if not isinstance(stats, dict) or not stats:
        raise ValueError("OSIRIS istatistik yanıtında veri bulunamadı.")
    headings = [
        ("flights", "Uçuş kayıtları"),
        ("sats", "Uydu kayıtları"),
        ("cctv", "Kamera kayıtları"),
        ("weather", "Hava olayı kayıtları"),
        ("incidents", "Olay kayıtları"),
    ]
    rows = [f"{label}: {_count(stats.get(key))}" for key, label in headings]
    captured = _source_time(data.get("timestamp"))
    content = (
        "OSIRIS — Küresel veri özeti\n"
        + "\n".join(rows)
        + f"\nAPI zaman damgası: {captured}"
        + "\nKaynak: " + _endpoint("/api/stats")
        + "\nNot: Bunlar platformun raporladığı kayıt sayılarıdır; "
          "bütün dünyadaki gerçek nesne toplamları veya eşzamanlı canlı gözlem değildir. "
          "Bazı kaynaklar gecikmeli, önbellekli veya eksik olabilir."
    )
    spoken = (
        "OSIRIS kayıt özetini aldım. "
        + ", ".join(rows[:3])
        + ". Bu sayılar API kayıtlarıdır; canlılıkları doğrulanmış değildir."
    )
    return spoken, content


def _time_ms(value: object) -> str:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "zaman yok"
    try:
        if not math.isfinite(value):
            return "zaman yok"
        return dt.datetime.fromtimestamp(
            value / 1000, tz=dt.timezone.utc
        ).strftime("%d.%m %H:%M UTC")
    except (OverflowError, OSError, ValueError):
        return "zaman yok"


def _earthquakes(data: dict, sort: str, limit: int) -> tuple[str, str]:
    if data.get("error"):
        raise ValueError("OSIRIS deprem servisi kaynak hatası döndürdü.")
    events = data.get("earthquakes")
    if not isinstance(events, list):
        raise ValueError("Deprem listesi bulunamadı.")

    clean = []
    for entry in events[:5000]:
        if not isinstance(entry, dict):
            continue
        mag = entry.get("magnitude")
        epoch = entry.get("time")
        if (isinstance(mag, bool) or not isinstance(mag, (float, int))
                or not math.isfinite(mag)
                or isinstance(epoch, bool) or not isinstance(epoch, (float, int))
                or not math.isfinite(epoch)):
            continue
        place = str(entry.get("place") or "Yeri belirtilmemiş").replace("\n", " ").strip()
        place = place[:110]
        clean.append((float(mag), float(epoch), place))
    clean.sort(key=(lambda e: (e[0], e[1])) if sort == "strongest"
               else (lambda e: (e[1], e[0])), reverse=True)
    selected = clean[:limit]
    reported = data.get("total")
    total = int(reported) if type(reported) is int and 0 <= reported <= 100_000 else len(events)
    captured = _source_time(data.get("timestamp"))
    if not selected:
        spoken = "OSIRIS kaynağı şu anda görüntülenebilir deprem kaydı döndürmedi."
        rows = ["Uygun deprem kaydı yok."]
    else:
        spoken = (
            f"OSIRIS üzerinden son 24 saatlik deprem listesini aldım. "
            f"Toplam kayıt: {total}. "
            + ("En güçlü" if sort == "strongest" else "En güncel")
            + f" {len(selected)} kaydın ayrıntıları ekranda."
        )
        rows = [
            f"M {mag:.1f} | {_time_ms(epoch)} | {place}"
            for mag, epoch, place in selected
        ]
    content = (
        "OSIRIS / USGS — Son 24 saatlik depremler (M 2.5+)\n"
        + f"Görünüm: {'En güçlü' if sort == 'strongest' else 'En yeni'} | Toplam: {total}\n"
        + "\n".join(rows)
        + f"\nAPI zaman damgası: {captured}"
        + "\nKaynak: " + _endpoint("/api/earthquakes")
        + "\nAsıl sismoloji kaynağı: https://earthquake.usgs.gov/"
        + "\nVeri kaynağı gecikebilir. Bu bir afet alarmı veya resmi tahmin değildir."
    )
    return spoken, content


def run(parameters: dict, player=None, session_memory=None) -> str:
    args = parameters if isinstance(parameters, dict) else {}
    mode = str(args.get("mode") or "stats").strip().casefold()
    mode = {"istatistik": "stats", "ozet": "stats", "deprem": "earthquakes",
            "depremler": "earthquakes"}.get(mode, mode)
    if mode not in ("stats", "earthquakes"):
        return "OSIRIS için 'stats' veya 'earthquakes' seçilebilir."
    sort = str(args.get("sort") or "recent").strip().casefold()
    sort = {"en yeni": "recent", "en guclu": "strongest"}.get(sort, sort)
    if sort not in ("recent", "strongest"):
        return "Sıralama 'recent' veya 'strongest' olmalı."
    try:
        limit = int(args.get("limit", 5))
    except (ValueError, TypeError):
        return "Gösterilecek deprem sayısı 1 ile 8 arasında olmalı."
    if isinstance(args.get("limit", 5), bool) or not 1 <= limit <= 8:
        return "Gösterilecek deprem sayısı 1 ile 8 arasında olmalı."
    path = "/api/earthquakes" if mode == "earthquakes" else "/api/stats"
    try:
        data = _read(path)
        spoken, report = (
            _earthquakes(data, sort, limit)
            if mode == "earthquakes" else _stats(data)
        )
        if player is not None:
            display = getattr(player, "show_content", None)
            if callable(display):
                try:
                    display("OSIRIS — Dünya Verileri", report)
                except Exception:
                    pass
        return spoken
    except (ValueError, OSError, error.HTTPError, error.URLError,
            TimeoutError, json.JSONDecodeError) as exc:
        return (
            "OSIRIS verileri doğrulanamadı; güncel sayılar veya olaylar için "
            "tahminde bulunmayacağım. Hata: " + str(exc)[:120]
        )
