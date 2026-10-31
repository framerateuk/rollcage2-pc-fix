# Rollcage Stage II (PC, 2000) on modern PCs and the Steam Deck

## Why this exists

Rollcage was like a spiritual successor to Wipeout, but less futuristic, with the weapons playing a
bigger role. Stage II builds on it with new tracks, cars and game modes, the same wall-and-ceiling
driving, and the official patch's bump-mapped graphics. On modern systems it wants its CD, a
registry key from its installer and a start-up dialog, and a modern pad's triggers can't be
throttle and brake. This kit sorts that out, so it can be played again.

**Looking for widescreen and a rebuilt engine?** [Rollcage Extreme](https://codemonkey.me.uk) by
Robert Baker, one of the original programmers, is a rebuilt version with new frame timing, sound and
a music player in place of the CD tracks. This kit is the other option: the original 2000 game with
the official 1.0c patch, kept as it was, just made to run. The first Rollcage has its own kit:
[rollcage-pc-fix](https://github.com/framerateuk/rollcage-pc-fix).

## What this does

Turns **your own** Rollcage Stage II CD and the official 1.0c patch into a folder that runs on the
Steam Deck (Proton) or on Windows 10/11, with no installer and no registry entries:

- **Copied straight from the CD**: what the installer copies, with the 1.0c patch's Direct3D exe
  (Pentium III E, ATI Rage and GeForce driver fixes, environment-mapped bump mapping) taken out of
  the patch without running its patcher, which needs the installer's registry key.
- **No CD check, no start-up dialog**, and settings, controls, records and progress saved to files
  in `game/Save/` instead of the registry.
- **Direct3D through dgVoodoo2**: 640x480 rendered at your screen's height, 4:3 with black bars, a
  steady 30 frames a second (the game's own rate). The Bink movies play full screen.
- **CD soundtrack** from OGG files ripped from your disc.
- **Gamepad**: an Xbox-style pad (the Steam Deck's included) is read directly: analogue steering,
  analogue throttle and brake on the two triggers, weapons and cameras on the buttons, the same
  layout as the Rollcage kit. The pad skips the movies.
- **No busy waits**: the frame limiter, the movie player and the start-up pause used to spin a CPU
  core at 100%.

**No game files are in this repository.** Everything from the game comes from your disc and the
official patch when you run `build.py`.

## What you need

| | |
|---|---|
| The game | The **European Rollcage Stage II CD** (Attention to Detail / Psygnosis, 2000; English, French, German, Spanish and Italian) as `.cue` + `.bin` (one file or one per track) or CloneCD `.ccd` + `.img`, with its 9 audio tracks. `build.py` checks the exe and the game data and stops on another edition. |
| Patch 1.0c | The official patch, `roll2v1c.zip` (9 August 2000), for example from [archive.org's patch archive](https://archive.org/download/video-game-patches_r/Video%20Game%20Patches%20R.Part1.7z/Rollcage%20Stage%20II%2Fpatch%201.0c%2Froll2v1c.zip). Keep it as downloaded; it isn't run. The `rc2patch10c.exe` inside it works too. It holds whole exes, so none of the earlier patches are needed. |
| Python | 3.8 or newer (python.org on Windows; already on macOS/Linux). |
| An OGG encoder | `oggenc` (vorbis-tools; Windows builds at rarewares.org) or `ffmpeg`, on the PATH. |
| dgVoodoo2 **2.79.3** | by Dege: [GitHub release v2.79.3](https://github.com/dege-diosg/dgVoodoo2/releases/tag/v2.79.3). Use 2.79.3: newer versions don't start under Wine/Proton. Keep the zip as downloaded. |
| ogg-winmm **v2025.01.16** | by AyuanX: [GitHub releases](https://github.com/ayuanx/ogg-winmm/releases). Keep the zip as downloaded; `build.py` checks it's that release. |

## Build

```
python3 build.py "Rollcage Stage II (Europe) (En,Fr,De,Es,It).cue" --patch roll2v1c.zip \
    --dgvoodoo dgVoodoo2_79_3.zip --ogg-winmm ogg-winmm_binary.zip
```

creates `RollcageStageII/` with `game/` and `rollcage2_launch.sh` (for the Steam Deck), in about a
minute. The same `game/` folder runs on Windows; `--windows` leaves out the launch script.
`--out DIR` puts the result somewhere else. The disc's original exes, the untouched 1.0c exe and the
1.0c Glide exe are kept in `game/_spare/`.

## Play on the Steam Deck

1. Copy `RollcageStageII/` to the Deck, for example to `/home/deck/Games/RollcageStageII/`.
2. Desktop Mode: Steam > Add a Non-Steam Game > Browse > `.../RollcageStageII/game/BIN/Rollcage D3D.exe`.
   Rename the shortcut "Rollcage Stage II". Start In must be the `BIN` folder (Steam sets it).
3. Properties > Compatibility: force **Proton 9.0**. Pin it rather than floating on Experimental.
4. Properties > Launch Options:
   ```
   /home/deck/Games/RollcageStageII/rollcage2_launch.sh %command%
   ```
5. Controller layout: start from the standard **Gamepad** layout and set these to keyboard keys:
   **Start = Enter**, **View = Esc**, **D-pad = arrow keys**. The front end and the pause menu are
   keyboard menus; everything in a race is the pad as itself.

## Play on Windows

Run `game/BIN/Rollcage D3D.exe`. An Xbox pad works in races as on the Deck, and Start or View
pause; the menus are on the keyboard (arrows, Enter, Esc), unless you map them in Steam or your pad
software.

## Controls

| Pad | In a race |
|---|---|
| Left stick | steer (analogue) |
| RT / LT | throttle / brake (analogue; both at once work) |
| A / X | fire left / right weapon slot |
| B | reverse |
| Y | face forward (after a spin) |
| LB | target car |
| RB | look back (while held) |
| Right stick | look left / right, zoom the camera in / out |
| L3 | rear-view mirror on / off |
| R3 | cinematic camera |
| View (Esc) | pause |

In the menus: D-pad (arrows) to move, Start (Enter) to choose, View (Esc) to go back. A, B, X, Y,
Start or View skip the movies. While the pad is in use the game's own reading of it as a joystick is
switched off, so its built-in joystick preset doesn't add actions of its own on top. The keyboard
keeps the game's own bindings (Options > Controls). Pads 1-4 are players 1-4.

## Settings

`game/Save/DataPC.sav` holds all settings, controls, player names, records and progress;
`DataPSX.sav` the rest of the game state. The game writes them; the kit ships none.

- Sharper or softer: `[DirectX] Resolution` in `game/BIN/dgVoodoo.conf`.
- Music level: the in-game CD volume, or `CDDAVolume` in `game/BIN/winmm.ini`.
- Deck renderer: `RENDERER=wined3d` before the script path in the launch options uses Wine's own
  Direct3D instead of dgVoodoo.

**Widescreen**: not in this kit. AlphaYellow's FOV fix widens the 3D, but the menus and HUD stay
stretched. Rollcage Extreme (above) is the rebuilt option, though PCGamingWiki notes its menus are
still stretched on wide screens.

## Troubleshooting

- *"Please insert the Rollcage Stage II CD"* or a start-up dialog: you're running an unpatched exe
  from `_spare/`.
- *The race doesn't start*: the shortcut must start in `game/BIN/`, and the names `BIN` and
  `Rollcage D3D.exe` must stay as they are (the game restarts itself between the front end and
  each race).
- *Movies small in a corner*: `EnableGDIHooking = true` must be in `game/BIN/dgVoodoo.conf`.
- *No music*: on the Deck `launch.log` must show `WINEDLLOVERRIDES=winmm=n,b;...` (no log: the
  launch option is missing `%command%`), and `game/BIN/Music/Track02.ogg` must exist.
- *Judder on a G-Sync / FreeSync monitor*: turn variable refresh off for this game.

## What's in this repository

| File | What |
|---|---|
| `build.py` | Builds the folder: copies the CD's game files, takes the 1.0c exes out of the patch, patches the exe, rips the soundtrack, adds the wrappers and settings. Python standard library only. |
| `patch_exe.py` | The exe patches, each explained; adds a code section to the exe. Also runs on its own. |
| `caves.s` | The new code's source (x86 assembly). `python3 patch_exe.py --check-caves` re-assembles it with clang and checks it against the bytes in `patch_exe.py`. |
| `disc.py` | Reads the CD image: `.cue`/`.bin` or `.ccd`/`.img`, ISO 9660 with Joliet names, and audio tracks. |
| `config/dgVoodoo.conf` | dgVoodoo2's settings. |
| `steamdeck/rollcage2_launch.sh` | Proton launch wrapper: DLL overrides. |
| `docs/TECHNICAL.md` | How the game works and what each patch does. |

## Credits

- **Attention to Detail** made Rollcage Stage II; **Psygnosis** published it. Please own the game:
  this kit needs your disc.
- **Dege**: dgVoodoo2. **AyuanX**: ogg-winmm.

## License

The scripts and docs in this repository: MIT (see `LICENSE`). The license covers only this
repository's own files, not the game, its patch, dgVoodoo2 or ogg-winmm.

Not affiliated with or endorsed by the game's rights holders.
