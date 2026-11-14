"""GitHub coding workspace and checked publication, separate from the running app."""
import json
import re
import subprocess
import threading
import time
from pathlib import Path

REPO = 'fatmakahraman304-hash/Mark-LVII'
WORK = Path.home() / 'JarvisDevelopment' / 'Mark-LVII'
_LOCK = threading.Lock()
PLUGIN = {'name':'github_develop','description':
    'JARVIS GitHub development workflow. prepare clones the user JARVIS repo into a separate workspace and creates a development branch; inspect reports its state. develop uses the coding agent to write/fix code there. test runs the Python tests. publish commits ONLY the explicitly selected files, pushes a branch, creates a PR and merges into main ONLY after GitHub checks succeed. Use publish only when the user asks to publish/merge. main then becomes available through the existing GÜNCELLE button; this tool never updates running source. Requires local Git and authenticated GitHub CLI for publication. Existing dev_agent builds other projects.',
    'parameters':{'type':'OBJECT','properties':{
        'mode':{'type':'STRING','enum':['prepare','inspect','develop','test','publish','merge']},
        'instruction':{'type':'STRING'},
        'files':{'type':'ARRAY','items':{'type':'STRING'},'description':'Exact changed source/test paths to include; never secrets or personal config.'}},'required':['mode']}}


def command(args, cwd=WORK, timeout=180):
    p=subprocess.run(args,cwd=cwd,capture_output=True,text=True,encoding='utf-8',errors='replace',timeout=timeout)
    if p.returncode:
        raise RuntimeError(f'{args[0]} işlemi başarısız (kod {p.returncode}). Ayrıntılar için yerel Git/CLI oturumunu kontrol edin.')
    return (p.stdout + ('\n'+p.stderr if args[0].endswith('python') or 'unittest' in args else '')).strip()


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
    import sys
    paths=list((WORK/'tests').glob('test_*.py'))
    if not paths:
        raise RuntimeError('Test bulunamadı; yayın durduruldu.')
    for path in paths:
        output=command([sys.executable,'-m','unittest','discover','-s','tests','-p',path.name,'-v'],timeout=300)
        if not re.search(r"Ran [1-9][0-9]* tests?", output):
            raise RuntimeError("Test çalışması doğrulanamadı; yayın durduruldu.")
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
        except Exception as exc:
            player.write_log('GELİŞTİRME: '+str(exc))
        finally:
            _LOCK.release()
    threading.Thread(target=work,daemon=True,name='jarvis-github').start()
    return 'GitHub geliştirme işlemi arka planda başladı; sonucu ekranda göstereceğim.'
