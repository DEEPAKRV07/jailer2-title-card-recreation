"""Find installed tools or fetch the public Windows essentials build, with resumable curl."""
from pathlib import Path
import shutil
import subprocess
import zipfile
from analyze import ffmpeg

ROOT=Path(__file__).resolve().parent

def main():
    dest=ROOT/'tools'; dest.mkdir(exist_ok=True)
    if not (dest/'ffprobe.exe').exists():
        existing=shutil.which('ffprobe')
        if existing: shutil.copy2(existing,dest/'ffprobe.exe')
        else:
            print('Downloading FFmpeg essentials from gyan.dev (about 110 MB). Run again to resume an interrupted download.',flush=True)
            archive=dest/'ffmpeg-essentials.zip'
            subprocess.run(['curl.exe','-L','--fail','--retry','3','-C','-','-o',str(archive),'https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip'],check=True)
            with zipfile.ZipFile(archive) as z:
                for name in z.namelist():
                    if name.endswith(('/ffprobe.exe','/ffmpeg.exe')):
                        (dest/Path(name).name).write_bytes(z.read(name))
            archive.unlink()
    subprocess.run([ffmpeg(),'-version'],check=True,stdout=subprocess.DEVNULL)
    subprocess.run([str(dest/'ffprobe.exe'),'-version'],check=True,stdout=subprocess.DEVNULL)
    print('FFmpeg and ffprobe are ready.')
    from hardware import ensure_gpu_dependencies
    ensure_gpu_dependencies()

if __name__=='__main__': main()
