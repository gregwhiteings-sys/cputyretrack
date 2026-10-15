"""Build and validate a Windows x64 portable folder. Run on Windows only."""
from pathlib import Path
import hashlib,json,os,platform,shutil,subprocess,sys
ROOT=Path(__file__).resolve().parent
LOGS=ROOT/'build_logs';BUNDLE=ROOT/'dist'/'TyreTrack';RELEASE=ROOT/'release'/'TyreTrack'

def run(args):
    subprocess.run([str(a) for a in args],cwd=ROOT,check=True)

def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()

def main():
    if sys.platform!='win32' or sys.version_info[:2]!=(3,12) or platform.architecture()[0]!='64bit':
        raise RuntimeError('Windows x64 Python 3.12 required')
    LOGS.mkdir(exist_ok=True)
    # Source probe gives a useful diagnostic before spending time freezing.
    env=os.environ.copy();env['QT_QPA_PLATFORM']='offscreen';env['OMP_NUM_THREADS']='2'
    source_result=LOGS/'source-smoke.json'
    run([sys.executable,'-m','compileall','-q','TyreTrack_Production_Monitor.py','count_line.py','hourly_dashboard.py','build_support'])
    subprocess.run([sys.executable,str(ROOT/'TyreTrack_Production_Monitor.py'),'--build-smoke-test',str(source_result)],cwd=ROOT,env=env,check=True,timeout=180)
    command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--windowed',
             '--name','TyreTrack','--paths',ROOT,'--noupx',
             '--hidden-import','count_line','--hidden-import','hourly_dashboard',
             '--hidden-import','build_support.smoke_test',
             '--hidden-import','ultralytics.nn.tasks',
             '--hidden-import','ultralytics.trackers.byte_tracker',
             '--hidden-import','ultralytics.trackers.bot_sort',
             '--hidden-import','scipy.linalg',
             '--collect-data','ultralytics','--collect-all','torchvision',
             '--collect-all','depthai','--collect-all','lap','--collect-all','optree',
             '--copy-metadata','torch','--copy-metadata','ultralytics',
             '--exclude-module','tensorflow','--exclude-module','keras','--exclude-module','tkinter',
             '--add-data',str(ROOT/'tyre_detector.pt')+';.']
    if (ROOT/'tyrecycle_logo.png').exists():command+=['--add-data',str(ROOT/'tyrecycle_logo.png')+';.']
    command += [ROOT/'TyreTrack_Production_Monitor.py'];run(command)
    internal=BUNDLE/'_internal'
    # Match the previous duplicate-Qt-runtime workaround. Never remove torch/lib.
    for qtbin in [internal/'PyQt5'/'Qt5'/'bin',internal/'PyQt5'/'Qt'/'bin']:
        for name in ['MSVCP140.dll','VCRUNTIME140.dll','VCRUNTIME140_1.dll']:
            dll=qtbin/name
            if dll.exists() and (internal/name).exists():
                backup=LOGS/'qt_duplicate_dll_backup'/qtbin.relative_to(internal)/name
                backup.parent.mkdir(parents=True,exist_ok=True);shutil.move(str(dll),str(backup))
    models=list(BUNDLE.rglob('tyre_detector.pt'))
    assert len(models)==1 and digest(models[0])==digest(ROOT/'tyre_detector.pt'), 'Model missing or changed'
    assert not list(BUNDLE.rglob('email_config.ini')), 'Private configuration in bundle'
    result=LOGS/'packaged-smoke.json'
    # Test from an unrelated working directory to catch resource-path assumptions.
    unrelated=LOGS/'unrelated_cwd';unrelated.mkdir(exist_ok=True)
    with (LOGS/'packaged_stdout.txt').open('w',encoding='utf-8') as f:
        subprocess.run([str(BUNDLE/'TyreTrack.exe'),'--build-smoke-test',str(result)],
                       cwd=unrelated,env=env,stdout=f,stderr=subprocess.STDOUT,check=True,timeout=240)
    assert json.loads(result.read_text())['status']=='passed'
    # Smoke-test DB and auto-generated email template must never ship as user data.
    for name in ['data','reports']:
        shutil.rmtree(BUNDLE/name,ignore_errors=True);(BUNDLE/name).mkdir()
    shutil.copy2(ROOT/'START_WINDOWS_BUILD.txt',BUNDLE/'START_HERE.txt')
    shutil.copy2(LOGS/'installed-versions.txt',BUNDLE/'BUILD_VERSIONS.txt')
    prerequisites=BUNDLE/'prerequisites';prerequisites.mkdir(exist_ok=True)
    shutil.copy2(ROOT/'vc_redist.x64.exe',prerequisites/'vc_redist.x64.exe')
    if RELEASE.exists():shutil.rmtree(RELEASE)
    RELEASE.parent.mkdir(exist_ok=True);shutil.copytree(BUNDLE,RELEASE)
    shutil.make_archive(str(ROOT/'release'/'TyreTrack-Windows-x64-Portable'),'zip',RELEASE.parent,RELEASE.name)
    print('SUCCESS: release/TyreTrack-Windows-x64-Portable.zip')

if __name__=='__main__':main()
