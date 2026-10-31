#!/usr/bin/env python3
"""Patch Rollcage Stage II's Direct3D exe as the official 1.0c patch installs it (rc2patch10c.exe of 9 Aug 2000, its
resource BINARY 119: "Bin\\Rollcage D3D.exe", 4 Aug 2000; 835,584 bytes, MD5 1e059a30b2a2aaa2ee3538dc3c24ab6d, MSVC;
Attention to Detail / Psygnosis) into a copy.

  patch_exe.py <Rollcage D3D.exe 1.0c> <out.exe>   write the patched exe (refuses, writes nothing, on any unexpected
                                                   byte)
  patch_exe.py --check-caves                       re-assemble caves.s with clang and compare with CAVE below

New code (caves.s, assembled bytes in CAVE) goes into a section the patch adds: ".rdeck", VA 0x6ca000, 0x1000 bytes
at file offset 0xcc000 (the end of the file, right after .rsrc), readable / writable / executable; its variables
from 0x6cac00. The section table had room for a fifth entry (it ended at 0x2b0, the first section starts at
0x1000); SizeOfImage 0x2ca000 -> 0x2cb000. The exe has no checksum, no relocations ("relocations stripped" is
already set) and loads at its 0x400000 base.

The engine is Rollcage's (games/windows/Rollcage/patch_exe.py, working on the Deck 24 Oct 2026): every site below
was found again in this exe from the same strings and code shapes (docs/TECHNICAL.md), the addresses all differ.
Addresses are the 1.0c exe's (the disc's own exe of Feb 2000 is another build: not used).

  rdeck      the section (above) with the code of caves.s.
  nocd       the CD check 0x49af20 (found from "Rollcage Stage II needs to be installed from a CD ROM drive." /
             "Please insert the Rollcage Stage II CD into the CD ROM drive.", 0x4c5ae8 / 0x4c5aa8; called at
             0x49443e and from the start-up dialog 0x495a8c): reads the installer's CD path (HKLM\\Software\\
             Psygnosis\\Rollcage Stage II\\Installer "Source"), wants GetDriveTypeA = CD-ROM and Rollcage\\IDXData\\
             Rollcage.idx on a CD drive, then 0x49c220: closes any "SJE_CdPlayerClass" window, reads the CD's table of
             contents over MCI (0x49bf60: open cdaudio by type ID with the drive as element, track count and
             positions) and compares it with BIN\\texture.dat (40 bytes: a track count of 10 and 9 scrambled
             numbers, decoded by 0x49bf20) - a TOC fingerprint, the disc's only protection. Returns 2 = disc found,
             1 / 0 = not; the result goes to [0x4c5648] (2 by default). Now "mov eax, 2; ret" at its entry: no drive,
             no MCI, no fingerprint. The data comes from ..\\IDXData\\ and the movies from ..\\MOVIES\\ beside BIN\\,
             as installed (the game looks there first: 0x49c4a0).
  nodialog   the start-up dialog (resource 129: language, display device, display mode, a check box; dialog proc
             0x495890), shown by 0x495830 on every start that is not a restart (/FRONTEND) once the display devices
             are listed (0x49d110). Its first instruction 0x495854 is now "jmp 0x495884", the dialog's own OK
             return path (free the device list, return 1): never shown. The game keeps what it has: the saved
             settings or its defaults (0x44fab0: 640 x 480 x 16, the first display device, English); the restarted
             runs (/FRONTEND and every race) never showed it anyway. dgVoodoo2 renders 640 x 480 at the screen's
             height.
  savefile   the registry. Settings, controls, records and progress are binary values in HKLM\\Software\\Psygnosis\\
             Rollcage Stage II\\BootSys ("DataPC" 0x1700 bytes, "DataPSX" 0x2214; strings 0x4c5b30 / 0x4c5b28 /
             0x4c5b38), read by 0x49ad10 -> "call 0x4a3210" (0x49ad4d) and written by 0x49aec0 -> "call 0x4a32f0"
             (0x49aed4). Both calls now go to regget / regset: the files ..\\Save\\DataPC.sav, DataPSX.sav beside
             the exe's folder. The other registry reads (Installer "Source" in the CD check, "Uninstall" for the
             dialog's Uninstall button) find nothing and the game takes its defaults; nothing else is written.
             ("DataReplay" appears only in the uninstall code: the replay is the file IDXData\\REPLAY.ARF.)
  pad        the Xbox pad through XInput. The game builds each local player's raw input once a frame with
             0x493720(player) (action bits from the bindings + byte 0 menu bits, the joystick's X / Y / Z bytes),
             called at 0x495451, 0x495479, 0x495494: those calls go to padraw (caves.s), which adds the pad of the
             same number (docs/TECHNICAL.md, "Pad"). Race set-up (0x432300) stores each car's analogue flags with "mov [esi +
             0x42e], al" (0x4325e5, 6 bytes): now "call padflags" + 1 nop (analogue steer / accelerate / brake when
             that player has a pad). The pad converter's analogue brake (0x4927e7, 20 bytes, "test dl, 2" ... "mov
             byte [esi + 0xa], 0") is now "jmp brakez" + 15 nops: the brake from LT (Z byte), separate from the
             throttle. Button map (caves.s padmap): RB = Look Back, R3 = Cinematic Camera.
  nojoy      the game's own DirectInput reading of the same pad (without it the game gives player 1 its
             joystick preset as soon as a joystick is there - stick down = Look Back, stick up = Target Car, A =
             Accelerate, R3 = Pause ... - on top of padraw's actions). padraw sets NOJOY while 0x493720 runs for a
             player with an Xbox pad; then the bindings loop's type jump (0x4923a7, "jmp [ecx*4 + 0x49250c]", 7
             bytes) goes to bindtype + 2 nops (only key bindings count), and the menu bits from the joystick
             (0x493756, "call 0x493660") come from menujoy (none). No stick direction does anything but steering
             (left) and look / zoom (right, through padraw).
  movieskip  the Bink movie loop (0x49c4a0, found from "..\\MOVIES\\" 0x4c5c98 and the Bink imports): its "call
             0x49c790" (one picture, 0 = the end; 0x49c746) now calls movieskip (the pad's A B X Y View Start also
             end the movie; any key still does).
  moviewait  the same loop's "call [BinkWait]" (0x49c73a, 6 bytes) is now "call binkwait" + 1 nop: Sleep(1) while
             the next picture is not due, instead of spinning on PeekMessage / BinkWait.
  nobusy     the wait loops spin on 0x4953b0 (jmp [timeGetTime]): the frame limiter 0x495516 (the frame function
             0x4954b0: 33 ms a picture, 16 ms in one mode, none in another; the game runs its logic once a picture)
             and the 2 s pause at start-up 0x494016. Each loop's "call 0x4953b0" now calls stime: Sleep(1), then the
             time. (The other waits, 0x45a17c and 0x494d18, already sleep 10 ms a turn.)

Not patched (docs/TECHNICAL.md): the frame time itself (33 ms; with dgVoodoo's vsync at 60 Hz every picture lands on every
second refresh: a steady 30), the process chaining (the race and the front end are separate runs of "Rollcage D3D.exe":
it changes to ..\\Bin\\, starts "Rollcage D3D.exe /FRONTEND", waits for its ATDGFXCHAINING event and exits), the CD
music code (Miles AIL_redbook_open(0) -> MCI cdaudio by type ID, polled with AIL_redbook_status: no notify wait), the
territory test (0x4944b0 is already "return 0" in 1.0c), the mouse pointer (hidden by the game in full screen).
"""
import hashlib, os, struct, subprocess, sys, tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
SIZE, MD5 = 835584, "1e059a30b2a2aaa2ee3538dc3c24ab6d"

SECTIONS = [(0x401000, 0x4b4000, 0x1000), (0x4b4000, 0x4b7000, 0xb4000), (0x4b7000, 0x4ca000, 0xb7000)]
def T(va):                             # file offset of a VA in .text / .rdata / initialised .data
    for lo, hi, off in SECTIONS:
        if lo <= va < hi: return va - lo + off
    raise AssertionError(hex(va))

def rel32(src, dst, op):               # e8 / e9 at src (5 bytes) -> dst
    return bytes([op]) + (dst - (src + 5)).to_bytes(4, "little", signed=True)

SECT_VA, SECT_RVA, SECT_OFF, SECT_SIZE = 0x6ca000, 0x2ca000, 0xcc000, 0x1000
CAVE_VA = SECT_VA
CAVE = bytes.fromhex(
    "6a01ff15e0404b00e9a3b3dcff6089c6833d04ac6c0000753cc70504ac6c0001000000bf70a46c00bb0300000057ff15"
    "58414b0085c074176848a46c0050ff15b4404b0085c07407a300ac6c00eb0683c7104b75d8a100ac6c0085c0741883fe"
    "0377136810ac6c0056ffd085c0750761b801000000c36131c0c3608b442424e889ffffffa320ac6c0061ff742404e88d"
    "96dcff83c404c70520ac6c0000000000608b442424e863ffffff85c00f84e90000000fb71d14ac6c0031ffbef8a36c00"
    "8b0685c0740c85c374030b7e0483c608ebee0fbf051cac6c003d80c1ffff7f0681cf000001003d803e00007c0681cf00"
    "0002000fbf051eac6c003d803e00007c0383cf023d80c1ffff7f0383cf010fbf0518ac6c00e883000000f6c3047405b8"
    "81fffffff6c3087405b87f00000083f8c07f0681cf0080000083f8407c0681cf002000000fb6e8c1e5080fb60517ac6c"
    "003d80000000720383cf40e86d000000f7d80fb6c0c1e01009c50fb60516ac6c003d80000000720681cf80000000e84a"
    "000000c1e01809c58b44241425ff00000009e889442414097c241c61c389c19931d029d02d581b00007f0331c0c36bc0"
    "7f31d251b9a7640000f7f15983f87f7605b87f00000085c97902f7d8c383f808730331c0c3d1e8c3833d20ac6c000074"
    "0a83f9027405e9dd81dcffff248d0c254900833d20ac6c0000740331c0c3e95d94dcff6089f8e802feffff85c0740580"
    "4c241c1f6188862e040000c3f6c2027422f6c21074148a450784c07e0700c088460aeb0fc6460a00eb0985c07ef600c0"
    "88460ae9b385dcffff742408ff742408e83b25ddff83c40885c074326031c0e8a9fdffff85c074250fb70514ac6c0025"
    "30f000008b0d08ac6c00a308ac6c00f7d121c87408c744241c0000000061c3ff742404ff156c424b0085c0740a506a01"
    "ff15e0404b0058c20400608b7424288b7c242c8b6c2430e8cd0000006a0068800000006a036a006a0168000000806800"
    "ad6c00ff156c414b0083f8ff742e89c3c7050cac6c00000000006a00680cac6c00555753ff1514414b0053ff1510414b"
    "00a10cac6c008944241c61c3c744241cffffffff61c3608b7424288b7c242c8b6c2430e8610000006a0068800000006a"
    "026a006a0068000000406800ad6c00ff156c414b0083f8ff743589c3c7050cac6c00000000006a00680cac6c00555753"
    "ff1518414b0053ff1510414b00392d0cac6c00750ac744241c0000000061c3c744241cffffffff61c35768c001000068"
    "00ad6c006a00ff1528414b00bf00ad6c0089fb8a0784c07409473c5c75f589fbebf189df56be57a46c00e8270000005e"
    "576a006800ad6c00ff15f0404b005fc6075c47e80e00000056be5fa46c00e8030000005e5fc3568a06880784c0740446"
    "47ebf45ec30f1f0000100000080000000040000004000000002000001000000000800000200000000001000000100000"
    "0002000000400000400000000000004080000000000000803000000000080000000000000000000058496e7075744765"
    "745374617465002e2e5c53617665002e73617600662e0f1f840000000000669078696e707574315f342e646c6c006690"
    "78696e707574315f332e646c6c00669078696e707574395f315f302e646c6c00"
    )
SYM = {"stime": 0x000, "padraw": 0x07a, "bindtype": 0x1d8, "menujoy": 0x1f2, "padflags": 0x203,
       "brakez": 0x21c, "movieskip": 0x248, "binkwait": 0x28f, "regget": 0x2aa, "regset": 0x316}                 # labels of caves.s

def C(name): return CAVE_VA + SYM[name]

def build():
    """(name, va, old bytes, new bytes) for every patch site."""
    e = []
    # nocd: "sub esp, 0x414" at the CD check's entry -> "mov eax, 2; ret"
    e.append(("nocd", 0x49af20, bytes.fromhex("81ec14040000"), bytes.fromhex("b802000000c3")))
    # nodialog: "mov ecx, [0x5368e8]" (the dialog's parent window, first of the DialogBoxParamA call) -> "jmp 0x495884"
    e.append(("nodialog", 0x495854, bytes.fromhex("8b0d"), bytes.fromhex("eb2e")))
    # savefile: the registry read / write calls -> regget / regset
    e.append(("savefile", 0x49ad4d, rel32(0x49ad4d, 0x4a3210, 0xe8), rel32(0x49ad4d, C("regget"), 0xe8)))
    e.append(("savefile", 0x49aed4, rel32(0x49aed4, 0x4a32f0, 0xe8), rel32(0x49aed4, C("regset"), 0xe8)))
    # pad: the raw-input builder's three callers -> padraw; the analogue flags store -> padflags; the converter's
    # analogue brake -> brakez
    for va in (0x495451, 0x495479, 0x495494):
        e.append(("pad", va, rel32(va, 0x493720, 0xe8), rel32(va, C("padraw"), 0xe8)))
    # nojoy: the bindings loop's type jump -> bindtype; the menu bits from the game's joystick -> menujoy
    e.append(("nojoy", 0x4923a7, bytes.fromhex("ff248d0c254900"), rel32(0x4923a7, C("bindtype"), 0xe9) + b"\x90" * 2))
    e.append(("nojoy", 0x493756, rel32(0x493756, 0x493660, 0xe8), rel32(0x493756, C("menujoy"), 0xe8)))
    e.append(("pad", 0x4325e5, bytes.fromhex("88862e040000"), rel32(0x4325e5, C("padflags"), 0xe8) + b"\x90"))
    e.append(("pad", 0x4927e7, bytes.fromhex("f6c202740f85c07e0702c088460aeb04c6460a00"),
              rel32(0x4927e7, C("brakez"), 0xe9) + b"\x90" * 15))
    # movieskip: the movie loop's "call 0x49c790" (one picture) -> movieskip
    e.append(("movieskip", 0x49c746, rel32(0x49c746, 0x49c790, 0xe8), rel32(0x49c746, C("movieskip"), 0xe8)))
    # moviewait: "call [BinkWait]" -> "call binkwait; nop"
    e.append(("moviewait", 0x49c73a, bytes.fromhex("ff156c424b00"), rel32(0x49c73a, C("binkwait"), 0xe8) + b"\x90"))
    # nobusy: "call 0x4953b0" in the wait loops -> call stime
    for va in (0x494016, 0x495516):
        e.append(("nobusy", va, rel32(va, 0x4953b0, 0xe8), rel32(va, C("stime"), 0xe8)))
    return e

def add_section(data):
    lfanew = struct.unpack_from("<I", data, 0x3c)[0]
    nsec = struct.unpack_from("<H", data, lfanew + 6)[0]
    optsize = struct.unpack_from("<H", data, lfanew + 20)[0]
    sh = lfanew + 24 + optsize + 40 * nsec
    if nsec != 4 or sh != 0x2b0 or any(data[sh:sh + 40]) or len(data) != SECT_OFF:
        sys.exit("unexpected PE header; nothing written")
    struct.pack_into("<8sIIIIIIHHI", data, sh, b".rdeck", SECT_SIZE, SECT_RVA, SECT_SIZE, SECT_OFF, 0, 0, 0, 0,
                     0xE0000060)       # code | initialised data | execute | read | write
    struct.pack_into("<H", data, lfanew + 6, nsec + 1)
    if not struct.unpack_from("<H", data, lfanew + 22)[0] & 1: sys.exit("relocations not stripped?")
    if struct.unpack_from("<I", data, lfanew + 24 + 56)[0] != SECT_RVA: sys.exit("unexpected SizeOfImage")
    struct.pack_into("<I", data, lfanew + 24 + 56, SECT_RVA + SECT_SIZE)
    data += CAVE + bytes(SECT_SIZE - len(CAVE))

def elf_text(path):                    # .text bytes and label offsets of an i386 ELF object (no relocations)
    d = open(path, "rb").read()
    shoff = struct.unpack_from("<I", d, 0x20)[0]; shentsize, shnum, shstrndx = struct.unpack_from("<HHH", d, 0x2e)
    secs = [struct.unpack_from("<10I", d, shoff + i * shentsize) for i in range(shnum)]
    names = [d[secs[shstrndx][4] + x[0]:].split(b"\0")[0].decode() for x in secs]
    if any(n.startswith(".rel") and x[5] for n, x in zip(names, secs)): sys.exit("caves.o has relocations")
    ti = names.index(".text"); text = d[secs[ti][4]:secs[ti][4] + secs[ti][5]]; syms = {}
    for x in secs:
        if x[1] != 2: continue                                   # SHT_SYMTAB
        strs = secs[x[6]]
        for i in range(x[5] // 16):
            nm, val, size, info, oth, shn = struct.unpack_from("<IIIBBH", d, x[4] + 16 * i)
            if shn == ti: syms[d[strs[4] + nm:].split(b"\0")[0].decode()] = val
    return text, syms

def check_caves():
    with tempfile.TemporaryDirectory() as t:
        o = os.path.join(t, "caves.o")
        subprocess.run(["clang", "-target", "i386-pc-linux-gnu", "-c", os.path.join(HERE, "caves.s"), "-o", o], check=True)
        text, syms = elf_text(o)
    ok = text == CAVE and all(syms.get(k) == v for k, v in SYM.items())
    print("caves.s matches CAVE" if ok else "caves.s differs from CAVE / SYM: update patch_exe.py")
    if not ok:
        print("CAVE =", text.hex()); print("SYM =", {k: hex(syms[k]) for k in SYM})
    return ok

def patch(data, label="Rollcage D3D.exe"):
    """Returns the patched exe; exits on any unexpected byte."""
    data = bytearray(data)
    if len(data) != SIZE or hashlib.md5(data).hexdigest() != MD5:
        sys.exit(f"{label}: not the 1.0c patch's Rollcage D3D.exe (size {SIZE}, MD5 {MD5}); nothing written")
    assert 0 < len(CAVE) < 0xc00, "CAVE empty or running into the variables at 0x6cac00"
    edits = build()
    for name, va, old, new in edits:
        off = T(va)
        if bytes(data[off:off + len(old)]) != old or len(old) != len(new):
            sys.exit(f"{name}: unexpected bytes at VA {va:#x}; nothing written")
    for name, va, old, new in edits:
        data[T(va):T(va) + len(new)] = new
    add_section(data)
    names = " ".join(dict.fromkeys(["rdeck"] + [n for n, *_ in edits]))
    print(f"  {names} ({len(edits)} edits)")
    return bytes(data)

def main(src, dst):
    data = patch(open(src, "rb").read(), src)
    tmp = dst + ".tmp"
    open(tmp, "wb").write(data)
    os.replace(tmp, dst)
    print(f"{dst}: MD5 {hashlib.md5(data).hexdigest()}")

if __name__ == "__main__":
    if len(sys.argv) == 2 and sys.argv[1] == "--check-caves": sys.exit(0 if check_caves() else 1)
    if len(sys.argv) != 3: sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
