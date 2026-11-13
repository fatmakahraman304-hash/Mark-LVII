"""User-triggered, pinned GitHub updates. No Qt or credentials in this module."""
from __future__ import annotations

import hashlib
import io
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import time
from urllib.parse import quote
from urllib.request import Request, urlopen
import zipfile

REPOSITORY = 'fatmakahraman304-hash/Mark-LVII'
ROOT = Path(__file__).resolve().parents[1]
LIMIT = 150 * 1024 * 1024


def _git(root, *args):
    p = subprocess.run(['git', '-C', str(root), *args], capture_output=True,
                       text=True, timeout=180, creationflags=0x08000000 if os.name == 'nt' else 0)
    if p.returncode:
        raise RuntimeError(p.stderr.strip() or 'Git işlemi başarısız.')
    return p.stdout.strip()


def _get(url):
    req = Request(url, headers={'User-Agent': 'Jarvis-Updater', 'Accept': 'application/vnd.github+json'})
    with urlopen(req, timeout=45) as response:
        data = response.read(LIMIT + 1)
    if len(data) > LIMIT:
        raise RuntimeError('Güncelleme indirme sınırını aşıyor.')
    return data


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _protected(name):
    p = PurePosixPath(name)
    return (any(part.startswith('.') for part in p.parts)
            or p.parts[0] in {'venv', 'env', 'ENV', 'logs', 'downloads', 'screenshots', '__pycache__'}
            or (p.parts[0] == 'config' and name not in {'config/__init__.py', 'config/jarvis.ico'})
            or p.suffix.lower() in {'.db', '.log', '.pyc'}
            or (p.parts[0] == 'memory' and p.suffix != '.py')
            or any(x in p.name.lower() for x in ('token', 'credential', 'client_secret')))


def _archive(data):
    files = {}
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        total = 0
        for info in archive.infolist():
            raw = info.filename
            path = PurePosixPath(raw)
            if '\\' in raw or path.is_absolute() or '..' in path.parts or ':' in raw:
                raise RuntimeError('Güvensiz arşiv yolu.')
            if info.is_dir() or len(path.parts) < 2:
                continue
            if (info.external_attr >> 16) & 0o170000 == 0o120000:
                raise RuntimeError('Arşivde sembolik bağlantı var.')
            name = str(PurePosixPath(*path.parts[1:]))
            if _protected(name):
                continue
            total += info.file_size
            if total > LIMIT or name in files:
                raise RuntimeError('Geçersiz veya çok büyük güncelleme arşivi.')
            files[name] = archive.read(info)
    if not {'main.py', 'requirements.txt', 'gui/window.py'} <= files.keys():
        raise RuntimeError('Eksik JARVIS arşivi.')
    return files


def _target(root, name):
    path = root / name
    if not path.resolve().is_relative_to(root.resolve()) or path.is_symlink():
        raise RuntimeError('Güncelleme yolu uygulama dışına çıkıyor.')
    return path


def _apply_zip(root, files, sha, branch):
    """Back up before writing; restore every changed/deleted file on failure."""
    state_path = root / '.jarvis-update.json'
    old = json.loads(state_path.read_text('utf-8')) if state_path.exists() else {}
    previous = old.get('files', {})
    for name, digest in previous.items():
        path = _target(root, name)
        if path.exists() and _hash(path.read_bytes()) != digest:
            raise RuntimeError(f'Yerel değişiklik korunuyor: {name}. Güncelleme uygulanmadı.')
    names = set(files) | {n for n in previous if not _protected(n)}
    backup = root / '.jarvis-backups' / (time.strftime('%Y%m%d-%H%M%S') + '-' + sha[:8])
    backup.mkdir(parents=True, exist_ok=False)
    existed = set()
    for name in names:
        path = _target(root, name)
        if path.exists():
            target = backup / name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(path, target)
            existed.add(name)
    old_state = state_path.read_bytes() if state_path.exists() else None
    touched = []
    try:
        for name in sorted(names):
            path = _target(root, name)
            touched.append(name)
            if name in files:
                path.parent.mkdir(parents=True, exist_ok=True)
                tmp = path.with_name(path.name + '.jarvis-new')
                try:
                    tmp.write_bytes(files[name])
                    os.replace(tmp, path)
                finally:
                    tmp.unlink(missing_ok=True)
            else:
                path.unlink(missing_ok=True)
        state = {'sha': sha, 'branch': branch, 'files': {n: _hash(b) for n, b in files.items()}}
        temp_state = state_path.with_suffix('.tmp')
        temp_state.write_text(json.dumps(state), encoding='utf-8')
        os.replace(temp_state, state_path)
    except Exception:
        for name in reversed(touched):
            path = root / name
            if name in existed:
                shutil.copy2(backup / name, path)
            else:
                path.unlink(missing_ok=True)
        if old_state is None:
            state_path.unlink(missing_ok=True)
        else:
            state_path.write_bytes(old_state)
        raise
    return backup


def update(root=ROOT, progress=lambda message: None):
    root = Path(root)
    if getattr(sys, 'frozen', False):
        raise RuntimeError('Bu paketli sürüm için kurulum paketi gerekir; kaynak güncellemesi uygulanmadı.')
    lock = root / '.jarvis-update.lock'
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise RuntimeError('Başka bir güncelleme çalışıyor. Önceki işlem kesildiyse .jarvis-update.lock dosyasını kaldırın.') from None
    os.close(fd)
    try:
        is_git = (root / '.git').exists()
        state_file = root / '.jarvis-update.json'
        state = json.loads(state_file.read_text('utf-8')) if state_file.exists() else {}
        if is_git:
            if _git(root, 'status', '--porcelain', '--untracked-files=no'):
                raise RuntimeError('Yerel kod değişiklikleri var; üzerine yazılmadı.')
            branch = _git(root, 'symbolic-ref', '--short', 'HEAD')
            current = _git(root, 'rev-parse', 'HEAD')
        else:
            channel = json.loads((root / 'update_channel.json').read_text('utf-8'))
            branch = state.get('branch', channel['branch'])
            current = state.get('sha')
        progress(f'GitHub kontrol ediliyor · {branch}')
        commit = json.loads(_get(f'https://api.github.com/repos/{REPOSITORY}/commits/{quote(branch, safe="")}'))
        sha = commit['sha']
        if not re.fullmatch('[0-9a-f]{40}', sha):
            raise RuntimeError('Geçersiz GitHub sürüm kimliği.')
        if current == sha:
            return False, f'JARVIS güncel · {sha[:8]}'
        progress('Yeni sürüm indiriliyor…')
        files = _archive(_get(f'https://codeload.github.com/{REPOSITORY}/zip/{sha}'))
        # Dependency replacement while Qt/audio DLLs are loaded is unsafe on Windows.
        # Stop before touching source if this update needs a different environment.
        old_req = (root / 'requirements.txt').read_text('utf-8').replace('\r\n', '\n')
        new_req = files['requirements.txt'].decode('utf-8').replace('\r\n', '\n')
        if old_req != new_req:
            raise RuntimeError('Bu sürüm yeni bağımlılıklar gerektiriyor. JARVIS’i kapatıp yeni sürümün setup.py kurulumunu çalıştırın. Mevcut sürüm korunuyor.')
        progress('Yedek alınıyor ve güncelleme uygulanıyor…')
        if is_git:
            _git(root, 'fetch', '--no-tags', f'https://github.com/{REPOSITORY}.git', sha)
            _git(root, 'merge-base', '--is-ancestor', current, sha)
            if _git(root, 'rev-parse', 'HEAD') != current or _git(root, 'status', '--porcelain', '--untracked-files=no'):
                raise RuntimeError('Kontrol sırasında yerel kod değişti; güncelleme durduruldu.')
            # Keep a local recovery reference; ff-only refuses divergence and untracked conflicts.
            _git(root, 'branch', f'jarvis-backup/{time.time_ns()}', current)
            _git(root, 'merge', '--ff-only', sha)
            if _git(root, 'rev-parse', 'HEAD') != sha:
                raise RuntimeError('Güncelleme sonucu doğrulanamadı.')
        else:
            _apply_zip(root, files, sha, branch)
        return True, f'Güncellendi · {sha[:8]}. Yeni sürüm için JARVIS’i kapatıp yeniden açın.'
    finally:
        lock.unlink(missing_ok=True)
