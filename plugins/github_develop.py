"""GitHub coding workspace and checked publication, separate from the running app."""
import json
import os
import sys
import re
import subprocess
import threading
import time
from pathlib import Path

REPO = 'fatmakahraman304-hash/Mark-LVII'
WORK = Path.home() / 'JarvisDevelopment' / 'Mark-LVII'
_LOCK = threading.Lock()
PLUGIN = {'name':'github_develop','description':
    'JARVIS GitHub development workflow. prepare clones the user JARVIS repo into a separate workspace and creates a development branch; inspect reports its state. develop uses the coding agent to write/fix code there. sync updates a clean development branch from main by fast-forward only. test runs the Python tests and shows failures inside JARVIS. publish commits ONLY the explicitly selected files, pushes a branch, creates a PR and merges into main ONLY after GitHub checks succeed. Use publish only when the user asks to publish/merge. main then becomes available through the existing GÜNCELLE button; this tool never updates running source. Requires local Git and authenticated GitHub CLI for publication. Existing dev_agent builds other projects.',
    'parameters':{'type':'OBJECT','properties':{
        'mode':{'type':'STRING','enum':['prepare','inspect','develop','sync','test','publish','merge']},
        'instruction':{'type':'STRING'},
        'files':{'type':'ARRAY','items':{'type':'STRING'},'description':'Exact changed source/test paths to include; never secrets or personal config.'}},'required':['mode']}}


_LOCAL_COMMANDS = {
    "/git sync": "sync",
    "/git test": "test",
    "github geliştirme alanını main ile eşitle": "sync",
    "github geliştirme alanındaki testleri çalıştır": "test",
    "github geliştirme alanındaki testleri çalıştır ve sonucu göster": "test",
}


def local_command_mode(text: str) -> str | None:
    """Recognize explicit typed commands without interpreting free-form prose."""
    normalized = " ".join(text.strip().replace("İ", "i").casefold().split())
    return _LOCAL_COMMANDS.get(normalized.rstrip(".!"))


class TestFailure(RuntimeError):
    """Test output safe to show locally, without losing the failing filename."""


def command(args, cwd=None, timeout=180, *, test_name=None):
    options = {}
    if os.name == "nt":
        options["creationflags"] = subprocess.CREATE_NO_WINDOW
    if test_name:
        options["env"] = dict(os.environ, QT_QPA_PLATFORM="offscreen", PYTHONUTF8="1")
    try:
        result = subprocess.run(
            args, cwd=WORK if cwd is None else cwd, capture_output=True, text=True, encoding="utf-8",
            errors="replace", timeout=timeout, **options,
        )
    except subprocess.TimeoutExpired as exc:
        if test_name:
            raise TestFailure(f"{test_name}: {timeout} saniyede tamamlanamadı.") from exc
        raise
    if test_name:
        output = "\n".join(part for part in (result.stdout, result.stderr) if part).strip()
        if result.returncode:
            raise TestFailure(
                f"{test_name}: test başarısız (kod {result.returncode}).\n\n"
                + (output[-6000:] or "Python hata çıktısı üretmedi.")
            )
        return output
    if result.returncode:
        raise RuntimeError(
            f"{Path(args[0]).name} işlemi başarısız (kod {result.returncode}). "
            "Yerel Git/CLI oturumunu kontrol edin."
        )
    return result.stdout.strip()


def selected_files(files):
    if not files:
        raise ValueError('Yayınlanacak dosyalar belirtilmeli.')
    for name in files:
        p=Path(name)
        if p.is_absolute() or '..' in p.parts or not (WORK/p).resolve().is_relative_to(WORK.resolve()):
            raise ValueError('Geçersiz kaynak yolu.')
        if any(part.startswith('.') for part in p.parts) or any(x in name.lower() for x in ('api_keys','token','secret','credential','.env')) or p.parts[0] in {'config','downloads','logs'}:
            raise ValueError('Kişisel/gizli dosya yayına alınamaz.')
    return files


def tests():
    paths = sorted((WORK / "tests").glob("test_*.py"))
    if not paths:
        raise RuntimeError('Test bulunamadı; yayın durduruldu.')
    python = Path(sys.executable)
    if python.name.lower() == "pythonw.exe":
        console_python = python.with_name("python.exe")
        if console_python.is_file():
            python = console_python
    for path in paths:
        output=command([str(python),'-m','unittest','discover','-s','tests','-p',path.name,'-v'], timeout=300, test_name=path.name)
        if not re.search(r"Ran [1-9][0-9]* tests?", output):
            raise TestFailure(f"{path.name}: test çalışması doğrulanamadı.\n\n{output[-6000:]}")
    return f'{len(paths)} Python test dosyası başarıyla çalıştı.'


def workflow(mode, instruction, files):
    if mode=='prepare':
        if WORK.exists():
            raise ValueError('Geliştirme klasörü zaten var. İncele veya geliştir komutunu kullanın.')
        WORK.parent.mkdir(parents=True,exist_ok=True)
        command(['git','clone','https://github.com/'+REPO+'.git',str(WORK)],cwd=WORK.parent)
        command(['git','switch','-c','jarvis-dev/'+str(int(time.time()))])
        return 'Ayrı geliştirme alanı hazır: '+str(WORK)
    if not (WORK/'.git').exists():
        raise ValueError('Önce geliştirme alanını hazırla komutunu verin.')
    if mode=='inspect':
        return command(['git','status','--short'])+'\n'+command(['git','log','-5','--oneline'])
    if mode == "sync":
        from actions import dev_agent
        branch = command(["git", "branch", "--show-current"])
        if not branch.startswith("jarvis-dev/") or command(["git", "status", "--porcelain"]):
            raise ValueError("Eşitlemek için temiz bir JARVIS geliştirme dalı gerekli.")
        if dev_agent._job_lock.locked():
            raise ValueError("Kod geliştirme işi tamamlanınca tekrar deneyin.")
        command(["git", "fetch", "https://github.com/" + REPO + ".git", "refs/heads/main"])
        command(["git", "merge", "--ff-only", "FETCH_HEAD"])
        return "Geliştirme alanı güncel. Testleri çalıştırabilirsiniz."
    if mode=='test':
        return tests()
    if mode=='merge':
        branch=command(['git','branch','--show-current'])
        if not branch.startswith('jarvis-dev/') or command(['git','status','--porcelain']):
            raise ValueError('Temiz geliştirme dalı gerekli.')
        head=command(['git','rev-parse','HEAD'])
        info=json.loads(command(['gh','pr','view',branch,'--repo',REPO,'--json','headRefOid,baseRefName,statusCheckRollup']))
        checks=info.get('statusCheckRollup') or []
        if info['headRefOid']!=head or info['baseRefName']!='main' or not checks or any(c.get('conclusion',c.get('state')) not in {'SUCCESS'} for c in checks):
            return 'Main değişmedi: doğru sürümün bütün GitHub kontrolleri başarılı olmalı.'
        command(['gh','pr','merge',branch,'--repo',REPO,'--merge','--match-head-commit',head])
        return 'Main’e birleştirildi. GÜNCELLE düğmesini kullanabilirsiniz.'
    if mode=='publish':
        selected_files(files)
        branch=command(['git','branch','--show-current'])
        if not branch.startswith('jarvis-dev/'):
            raise ValueError('Yayın yalnızca ayrı geliştirme dalından yapılır.')
        from actions import dev_agent
        if dev_agent._job_lock.locked():
            raise ValueError('Kod geliştirme işi henüz bitmedi.')
        command(['gh','auth','status'])
        tests()
        if command(['git','diff','--cached','--name-only']):
            raise ValueError('Önceden hazırlanmış commit değişiklikleri var; önce inceleyin.')
        command(['git','add','--',*files])
        command(['git','commit','-m',instruction or 'JARVIS geliştirmesi'])
        head=command(['git','rev-parse','HEAD'])
        command(['git','push','-u','origin',branch])
        prs=json.loads(command(['gh','pr','list','--repo',REPO,'--head',branch,'--json','number']))
        if not prs:
            command(['gh','pr','create','--repo',REPO,'--base','main','--head',branch,'--title',instruction[:120] or 'JARVIS geliştirmesi','--body','JARVIS geliştirme alanında hazırlanmış değişiklikler. Python testleri yerel olarak çalıştırıldı; GitHub kontrolleri birleştirmeden önce zorunludur.'])
        checks=json.loads(command(['gh','pr','checks',branch,'--repo',REPO,'--json','name,state']))
        if not checks or any(c['state']!='SUCCESS' for c in checks):
            return 'PR oluşturuldu; kontroller henüz başarılı değil. Main değişmedi. Daha sonra merge işlemiyle tekrar kontrol edin.'
        command(['gh','pr','merge',branch,'--repo',REPO,'--merge','--match-head-commit',head],timeout=90)
        return 'Main’e birleştirildi. GÜNCELLE düğmesiyle bu sürümü yükleyebilirsiniz.'
    raise ValueError('Geçersiz işlem.')


def run(parameters, player=None, session_memory=None):
    mode=parameters.get('mode','')
    instruction=str(parameters.get('instruction','')).strip()
    if mode=='develop':
        if _LOCK.locked(): return 'GitHub işlemi bitene kadar kod düzenleme beklemeli.'
        if not (WORK/'.git').exists(): return 'Önce geliştirme alanını hazırlayın.'
        from actions.dev_agent import dev_agent
        return dev_agent({'mode':'improve','folder':str(WORK),'description':instruction},player=player)
    if not player: return 'Geliştirme ilerlemesi için JARVIS arayüzü gerekli.'
    if not _LOCK.acquire(False): return 'Bir GitHub işlemi zaten çalışıyor.'
    def work():
        try:
            result=workflow(mode,instruction,parameters.get('files',[]))
            player.write_log('GELİŞTİRME: '+result)
        except TestFailure as exc:
            player.write_log("GELİŞTİRME: " + str(exc).splitlines()[0])
            show = getattr(player, "show_content", None)
            if callable(show):
                show("Geliştirme testi", str(exc))
        except Exception as exc:
            player.write_log('GELİŞTİRME: '+str(exc))
        finally:
            _LOCK.release()
    threading.Thread(target=work,daemon=True,name='jarvis-github').start()
    return 'GitHub geliştirme işlemi arka planda başladı; sonucu ekranda göstereceğim.'
