# How it works

Notes on Rollcage Stage II (Attention to Detail / Psygnosis, 2000), the European CD (English, French,
German, Spanish and Italian), with the official 1.0c patch (9 August 2000). Addresses are virtual
addresses in the 1.0c Direct3D exe.

## The disc and the installer

Track 1 is the data track; tracks 2-10 are the music. `disk1\Rollcage\` holds the installed files:
the `Rollcage.exe` dispatcher (starts the Direct3D or Glide build from the registry), `BIN\` (the two
exes, `binkw32.dll` for the Bink movies, `mss32.dll` = Miles Sound System 6.0a and its 11 `*.M3D` 3D
providers, `texture.dat` = the CD check's fingerprint), `IDXData\` (`ROLLCAGE.IMG` + `.IDX` = all the
game's data, and `Configuration Data`, a copy of the saved state the game rewrites and never reads)
and `movies\` (12 Bink movies). Several names don't fit 8.3 (`Rollcage D3D.exe`,
`Configuration Data`, `Outtro Beginner.bik`), so `build.py` reads the disc's Joliet names.

## Patch 1.0c

`roll2v1c.zip` holds `rc2patch10c.exe` (9 Aug 2000, SHA-256 `5a8393d1...494d`) and `readme.txt`
("fixes problems with latest Intel processors as well as adds Environment Mapped Bump Mapping on
those cards which support it ... also fixes PentiumIIIE problems for Direct3D and Glide, fixes
problems with ATI Rage drivers"; the patcher also mentions a workaround for an NVidia GeForce driver
bug). There were three releases (1.0a, its second revision, 1.0c); 1.0c holds whole exes, so it needs
none of the earlier ones. It carries them as BINARY resources: 119 `Rollcage D3D.exe` (835,584 bytes
at file offset 0x9e70) and 120 `Rollcage Glide.exe` (811,008 at 0xd5e70). `build.py` cuts both out,
checked by MD5, and patches 119. The patcher isn't run: it wants the installer's registry key.

## The patches

`patch_exe.py` adds a section `.rdeck` (VA 0x6ca000, 4 KB, at the end of the file) holding the new
code from `caves.s`. Every site was found again in this exe from the same strings and code shapes as
in Rollcage's; the addresses all differ.

| Patch | Hooks | Was | Now |
|---|---|---|---|
| `nocd` | the CD check 0x49af20: the installer's CD path from the registry, a CD-ROM drive with `Rollcage\IDXData\Rollcage.idx`, then the CD's table of contents over MCI against `texture.dat` | Without the installer's key and the disc: "needs to be installed from a CD ROM drive", quit | Returns "disc found" (2, as in Rollcage). Nothing is read from a CD |
| `nodialog` | the start-up dialog (language, display device, display mode), shown at every start that isn't a restart (0x495854) | A Windows dialog before the game | Never shown, as for the restarted runs: the saved settings, else 640x480x16, the first device, English (the language is in the game's Options) |
| `savefile` | the registry read / write of `HKLM\Software\Psygnosis\Rollcage Stage II\BootSys` "DataPC", "DataPSX" (0x49ad4d, 0x49aed4) | Binary registry values | Files `Save\DataPC.sav`, `DataPSX.sav` |
| `pad` | the raw-input builder 0x493720 (its three callers), the race's analogue-flags store 0x4325e5, the pad converter's analogue brake 0x4927e7 | DirectInput only, through the bindings; under Proton an Xbox pad's triggers are one shared axis | The XInput pad of the same number added to each player's input: analogue steering, RT / LT as separate analogue throttle and brake, the buttons as actions. Replays record it like the game's own input |
| `nojoy` | the bindings loop's type jump (0x4923a7) and the joystick menu bits (0x493756), while `pad` runs for a player with an Xbox pad | The game read the same pad again as a DirectInput joystick with its own preset (stick down = look back, stick up = target car, A = accelerate, R3 = pause...) on top of the XInput actions | Only the keyboard bindings and the XInput actions count |
| `movieskip` | the Bink movie loop's picture call (0x49c746) | Any key skips | Also A, B, X, Y, View or Start |
| `moviewait` | the movie loop's `BinkWait` (0x49c73a) | Spun between pictures | `Sleep(1)` while the next picture isn't due |
| `nobusy` | the waits on `timeGetTime`: the frame limiter 0x495516, the 2 s start-up pause 0x494016 | Spin a CPU core | `Sleep(1)` each time round |

Not patched: the frame time, the process restarts, the CD music code.

## Process restarts

The front end and every race are separate runs: the game changes to `..\Bin\` and starts
`Rollcage D3D.exe /FRONTEND` itself between them. So the exe must keep its name in a folder called
`BIN`, beside `IDXData` and `movies`.

## Picture

Direct3D 7 on DirectDraw, 640x480x16 by default. dgVoodoo2 2.79.3: `Resolution = max` renders the 3D
at the screen's height, `ScalingMode = stretched_ar` keeps 4:3 with black bars, vsync,
`FPSLimit = 60`. The Bink movies are drawn with GDI into the game's window, which dgVoodoo's output
otherwise covers or leaves in a corner; `EnableGDIHooking = true` copies them into the picture.

The game holds each frame to 33 ms in what was a busy loop; with vsync on a 60 Hz screen that's a
steady 30 frames a second.

## Music

Miles Sound System's CD player (`AIL_redbook_open`) opens the MCI `cdaudio` device by type with
`mciSendCommand`, never the string "open cdaudio", so ogg-winmm is used as released. Each track is
ripped from its INDEX 01 (the 2-second pregaps left out) minus the few sectors of digital silence at
its end.

## Pad

Up to four local players, read through their bindings and turned into a PlayStation pad. `pad` adds
XInput user n to player n+1 whatever the bindings say and switches that player's car to analogue
steering, throttle and brake at the start of each race; `nojoy` turns off the game's own joystick
reading of that pad meanwhile. The action bits and default keys are Rollcage's, so the layout is the
same, with look back on RB (held) and the cinematic camera on R3. The front end and the pause menu
are keyboard menus (0x493610: arrows, Enter, Esc), hence Start = Enter, View = Esc and the D-pad as
arrows in Steam Input on the Deck.
