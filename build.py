#!/usr/bin/env python3
"""Build a ready-to-run Rollcage Stage II folder for modern PCs from your own CD and the official 1.0c patch.

Usage:
  python3 build.py DISC.cue|DISC.ccd --patch roll2v1c.zip --dgvoodoo DGVOODOO.zip --ogg-winmm OGG-WINMM.zip
                   [--out DIR] [--windows]

  DISC          your Rollcage Stage II CD (Attention to Detail / Psygnosis, 2000, the European release, English /
                French / German / Spanish / Italian) as .cue + .bin or .ccd + .img, with its audio tracks
  --patch       the official 1.0c patch as downloaded (roll2v1c.zip), or the rc2patch10c.exe inside it. It isn't
                run: build.py takes the 1.0c exes out of it
  --dgvoodoo    dgVoodoo2 2.79.3 zip (or its unpacked folder)
  --ogg-winmm   ogg-winmm v2025.01.16 release zip (or folder)
  --out         where to create RollcageStageII/ (default: this folder)
  --windows     a folder for Windows only: the same game/ folder, without the Steam Deck launch script

Needs Python 3.8+ and an Ogg Vorbis encoder on the PATH: oggenc (vorbis-tools) or ffmpeg.
Nothing from the game is in this repository: every game file comes from your disc and the patch.
"""
import argparse, hashlib, os, shutil, struct, subprocess, sys, tempfile, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import disc, patch_exe

DISC_EXE_MD5 = "c2207a27bcd04cb15d9ccdd0a0d1d3f6"       # disk1\Rollcage\BIN\Rollcage D3D.exe
IMG_MD5 = "9534c871ed031f57655641034299a1bc"            # disk1\Rollcage\IDXData\ROLLCAGE.IMG
PATCHER_SHA256 = "5a8393d14042361ec8e8e97d522b6bb95e65c15387daa6f5c5d1e66b6918494d"   # rc2patch10c.exe, 9 Aug 2000
# rc2patch10c.exe carries the two 1.0c exes as BINARY resources 119 (Direct3D) and 120 (Glide), at these offsets
RESOURCES = {"d3d": (0x9e70, 835584, patch_exe.MD5), "glide": (0xd5e70, 811008, "07b4f90c74c273ebe7626ca8a7d3a97a")}
PATCHED_MD5 = "245446a9ba6e60c1e40abff2f5f69253"
WINMM_MD5 = "f4896addb8e4da30ebcfa2d9cc203c0e"          # ogg-winmm v2025.01.16 (used as released: Miles opens the
                                                        # CD with mciSendCommand, never the string "open cdaudio")
R = "disk1/rollcage/"
BIN_FILES = ["binkw32.dll", "mss32.dll", "MSSA3D.M3D", "Mssa3d2.m3d", "MSSDS3DH.M3D", "MSSDS3DS.M3D", "Mssdx7sh.m3d",
             "Mssdx7sl.m3d", "Mssdx7sn.m3d", "MSSEAX.M3D", "Msseax2.m3d", "MSSFAST.M3D", "MSSRSX.M3D", "texture.dat"]
MOVIES = ["Atd", "Crystal", "Gold", "intro", "Laser", "Marble", "Octarine", "Outtro Beginner", "Outtro Expert",
          "Psygnosis", "Silver", "Win Car"]


def md5(data): return hashlib.md5(data).hexdigest()


def patcher(path):
    d = open(path, "rb").read()
    if d[:2] == b"PK":
        with zipfile.ZipFile(path) as z:
            names = [n for n in z.namelist() if n.lower() == "rc2patch10c.exe"]
            if not names: sys.exit(f"{path}: no rc2patch10c.exe inside: not the 1.0c patch zip")
            d = z.read(names[0])
    if hashlib.sha256(d).hexdigest() != PATCHER_SHA256:
        sys.exit(f"{path}: rc2patch10c.exe is not the official 1.0c one (9 Aug 2000)")
    exes = {}
    for name, (off, size, want) in RESOURCES.items():
        exes[name] = d[off:off + size]
        if md5(exes[name]) != want: sys.exit(f"rc2patch10c.exe: its {name} exe isn't where expected")
    return exes


def patch_readme(path):
    if open(path, "rb").read(2) != b"PK": return None
    with zipfile.ZipFile(path) as z:
        names = [n for n in z.namelist() if n.lower() == "readme.txt"]
        return z.read(names[0]) if names else None


def encoder():
    if shutil.which("oggenc"): return lambda wav, ogg: ["oggenc", "-Q", "-q", "7", wav, "-o", ogg]
    if shutil.which("ffmpeg"):
        return lambda wav, ogg: ["ffmpeg", "-loglevel", "error", "-y", "-i", wav, "-c:a", "libvorbis", "-q:a", "7", ogg]
    sys.exit("needs oggenc (vorbis-tools) or ffmpeg on the PATH to encode the soundtrack")


def rip(tracks, music):
    enc = encoder(); os.makedirs(music, exist_ok=True); zero = bytes(2352); n = 0
    with tempfile.TemporaryDirectory() as tmp:
        for t in tracks:
            if t.kind != "AUDIO": continue
            data = disc.audio(t)          # INDEX 01 to the next track's start (or its file's end)
            tail = 0                      # minus up to 2 s of digital silence at the end
            while tail < 150 and data[len(data) - (tail + 1) * 2352:len(data) - tail * 2352] == zero: tail += 1
            if tail: data = data[:len(data) - tail * 2352]
            wav = os.path.join(tmp, f"track{t.n:02d}.wav")
            with open(wav, "wb") as o:
                o.write(b"RIFF" + struct.pack("<I", 36 + len(data)) + b"WAVEfmt " +
                        struct.pack("<IHHIIHH", 16, 1, 2, 44100, 176400, 4, 16) + b"data" +
                        struct.pack("<I", len(data)) + data)
            subprocess.run(enc(wav, os.path.join(music, f"Track{t.n:02d}.ogg")), check=True); os.remove(wav)
            print(f"  Music/Track{t.n:02d}.ogg  {len(data) / 2352 / 75:6.1f} s"); n += 1
    if n != 9: sys.exit(f"expected 9 audio tracks (the game's music), found {n}: is the image missing them?")


def take(src, member):
    """Bytes of the file whose path ends with `member` (case-insensitive) in a zip or folder."""
    want = member.lower()
    if os.path.isdir(src):
        for d, _, fs in os.walk(src):
            for f in fs:
                p = os.path.join(d, f)
                if os.path.relpath(p, src).replace(os.sep, "/").lower().endswith(want): return open(p, "rb").read()
    else:
        with zipfile.ZipFile(src) as z:
            for name in z.namelist():
                if name.lower().endswith(want): return z.read(name)
    sys.exit(f"{member} not found in {src}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("disc"); ap.add_argument("--patch", required=True)
    ap.add_argument("--dgvoodoo", required=True); ap.add_argument("--ogg-winmm", required=True)
    ap.add_argument("--out", default=HERE); ap.add_argument("--windows", action="store_true")
    a = ap.parse_args()

    tracks = disc.tracks(a.disc)
    data = [t for t in tracks if t.kind != "AUDIO"]
    if not data: sys.exit("no data track in " + a.disc)
    dt = disc.DataTrack(data[0])
    entries = {p.lower(): (p, is_dir, l, s) for p, is_dir, l, s in dt.walk(joliet=True)}
    for key, want in [(R + "bin/rollcage d3d.exe", DISC_EXE_MD5), (R + "idxdata/rollcage.img", IMG_MD5)]:
        if key not in entries: sys.exit(f"no {key} on this CD: it isn't the Rollcage Stage II disc the kit was made for")
        got = md5(dt.read_file(*entries[key][2:]))
        if got != want:
            sys.exit(f"this CD's {entries[key][0]} is not the one the kit was made for (MD5 {got}); "
                     "nothing else is supported yet")
    exes = patcher(a.patch)
    winmm = take(a.ogg_winmm, "winmm.dll")
    if md5(winmm) != WINMM_MD5: sys.exit(f"{a.ogg_winmm}: winmm.dll is not ogg-winmm v2025.01.16")

    pkg = os.path.join(os.path.abspath(a.out), "RollcageStageII"); game = os.path.join(pkg, "game")
    if os.path.exists(pkg): sys.exit(f"{pkg} already exists: move or delete it first")

    print("1/5 game files from the CD")   # what the installer puts in the install folder, with its names
    def copy(key, dst): dt.copy_file(*entries[(R + key).lower()][2:], os.path.join(game, *dst.split("/")))
    copy("readme.txt", "readme.txt"); copy("Setup.ico", "Setup.ico")
    for f in BIN_FILES: copy("BIN/" + f, "BIN/" + f)
    for f in ("ROLLCAGE.IMG", "ROLLCAGE.IDX", "Configuration Data"): copy("IDXData/" + f, "IDXData/" + f)
    for m in MOVIES: copy(f"movies/{m}.bik", f"movies/{m}.bik")
    copy("Rollcage.exe", "_spare/Rollcage.exe")                                  # the dispatcher (registry)
    copy("BIN/Rollcage D3D.exe", "_spare/Rollcage D3D-disc.exe")                # the disc's own exes (before 1.0c)
    copy("BIN/Rollcage Glide.exe", "_spare/Rollcage Glide-disc.exe")
    os.makedirs(os.path.join(game, "Save"))      # settings, controls, records and progress (patch savefile)
    os.makedirs(os.path.join(game, "_spare", "Glide"))
    open(os.path.join(game, "_spare", "Glide", "Rollcage Glide.exe"), "wb").write(exes["glide"])   # 1.0c Glide
    open(os.path.join(game, "_spare", "Rollcage D3D-1.0c.exe"), "wb").write(exes["d3d"])           # untouched
    readme = patch_readme(a.patch)
    if readme: open(os.path.join(game, "_spare", "readme-1.0c.txt"), "wb").write(readme)

    print("2/5 exe patches (the 1.0c Direct3D exe)")
    out = patch_exe.patch(exes["d3d"])
    if md5(out) != PATCHED_MD5: sys.exit("patching gave an unexpected Rollcage D3D.exe")
    # the name "Rollcage D3D.exe" and the folder BIN are fixed: the game changes to ..\Bin\ and starts
    # "Rollcage D3D.exe /FRONTEND" itself between the front end and a race
    open(os.path.join(game, "BIN", "Rollcage D3D.exe"), "wb").write(out)

    print("3/5 soundtrack")
    rip(tracks, os.path.join(game, "BIN", "Music"))

    print("4/5 wrappers and settings")
    for member, name in [("MS/x86/DDraw.dll", "ddraw.dll"), ("MS/x86/D3DImm.dll", "d3dimm.dll")]:
        open(os.path.join(game, "BIN", name), "wb").write(take(a.dgvoodoo, member))
    open(os.path.join(game, "BIN", "winmm.dll"), "wb").write(winmm)
    with open(os.path.join(game, "BIN", "winmm.ini"), "wb") as f:
        f.write(b"[OGG-WinMM]\r\nCDDAPath = Music\r\nCDDAVolume = 100\r\nMIDIVolume = 100\r\nWAVEVolume = 100\r\n")
    shutil.copyfile(os.path.join(HERE, "config", "dgVoodoo.conf"), os.path.join(game, "BIN", "dgVoodoo.conf"))

    print("5/5 Steam Deck launch script" if not a.windows else "5/5 done")
    if not a.windows:
        launch = os.path.join(pkg, "rollcage2_launch.sh")
        shutil.copyfile(os.path.join(HERE, "steamdeck", "rollcage2_launch.sh"), launch); os.chmod(launch, 0o755)
    print(f"\ndone: {pkg}  (see README.md)")


if __name__ == "__main__":
    main()
