# Rollcage Stage II (BIN\Rollcage D3D.exe as the official 1.0c patch of Aug 2000 installs it, 835,584 bytes, MSVC;
# Attention to Detail / Psygnosis): new code for patch_exe.py. It goes into a section patch_exe.py adds to the exe,
# ".rdeck" at VA 0x6ca000 (file offset 0xcc000, the end of the file, 0x1000 bytes, readable / writable /
# executable): this code from 0x6ca000, its variables from 0x6cac00 (zero when the exe loads). The exe always loads
# at its 0x400000 base (no dynamic-base flag, "relocations stripped" already set), so absolute addresses are used
# throughout.
#
# The routines are Rollcage's (games/windows/Rollcage/caves.s, working on the Deck 24 Oct 2026) moved to this exe:
# the engine is the same (the raw input record, the PlayStation pad converter, the action bits, the registry save
# blocks, the timeGetTime waits), at other addresses; what differs is said at each routine.
#
# Assembled with Apple clang (integrated assembler):
#   clang -target i386-pc-linux-gnu -c caves.s -o caves.o
# patch_exe.py carries the resulting bytes (CAVE) and checks them against this file when clang is around
# (patch_exe.py --check-caves). docs/TECHNICAL.md explains each routine.
#
# Lesson kept from Speedster (23 Oct 2026): never keep a value in ecx / edx across an API call (Proton's
# timeGetTime and friends change them). Every routine that calls an API saves what it uses with pushad / popad and
# keeps values across API calls only in ebx / esi / edi / ebp or memory.
.intel_syntax noprefix
.set BASE, 0x6ca000

# imports used (IAT slots of Rollcage D3D.exe 1.0c)
.set GetProcAddress,     0x4b40b4
.set Sleep,              0x4b40e0
.set CreateDirectoryA,   0x4b40f0
.set CloseHandle,        0x4b4110
.set ReadFile,           0x4b4114
.set WriteFile,          0x4b4118
.set GetModuleFileNameA, 0x4b4128
.set LoadLibraryA,       0x4b4158
.set CreateFileA,        0x4b416c
.set BinkWait,           0x4b426c

# game
.set TIMENOW,  0x4953b0              # the game's timeGetTime thunk (jmp [timeGetTime]; every wait loop calls it)
.set PADRAW,   0x493720              # (player) -> eax = action bits, edx = bytes: menu directions, X, Y, Z axis
.set MOVIEFRM, 0x49c790              # (bink, buffer): show one movie picture; eax 0 = the movie has ended
.set BRAKERET, 0x4927fb              # back in the pad converter after the analogue brake (patch pad, brakez)
.set BINDNEXT, 0x4923c8              # the bindings loop (0x492330): on to the next binding (patch nojoy)
.set BINDJT,   0x49250c              # its jump table by binding type: 0 joystick button, 1 joystick axis, 2 key,
                                     #   3 joystick hat
.set MENUJOY,  0x493660              # (player, actions) -> the menu bits from the game's own joystick

# our variables (.rdeck from 0x6cac00, zero at load)
.set XGS,     0x6cac00               # XInputGetState (0 = no XInput DLL)
.set XINIT,   0x6cac04               # 1 once xget has looked for XInput
.set MOVPREV, 0x6cac08               # movieskip: pad buttons down at the previous look
.set NRW,     0x6cac0c               # bytes read / written (ReadFile / WriteFile)
.set XS,      0x6cac10               # an XINPUT_STATE (16 bytes): +4 wButtons, +6 LT, +7 RT, +8 LX, +10 LY, +12 RX,
                                     #   +14 RY
.set NOJOY,   0x6cac20               # 1 while PADRAW runs for a player whose Xbox pad is connected (padraw)
.set PATH,    0x6cad00               # a file name (0x200 bytes)

.set DZ,      7000                   # left stick dead zone (of 32767), about 21 % (scaled from its edge: no jump)
.set RDZ,     16000                  # right stick: half way = a look / zoom button
.set TDZ,     8                      # trigger dead zone (of 255)

.macro PUSHI v                       # push imm32 (clang's intel syntax would make "push offset" 16-bit)
  .byte 0x68
  .long \v
.endm
.macro CALLG target                  # call a game address (rel32)
  .byte 0xe8
  .long \target - (BASE + (. + 4 - start))
.endm
.macro JMPG target                   # jmp to a game address (rel32)
  .byte 0xe9
  .long \target - (BASE + (. + 4 - start))
.endm

.text
start:

# ---------------------------------------------------------------------------------------------------------------
# stime (patch nobusy): the game's wait loops spin on its timeGetTime thunk TIMENOW ("call TIMENOW; cmp ...; jb
# back"): the frame limiter (0x495516: until 33 ms since the last picture; 16 ms in one mode) and the 2 s pause at
# start-up (0x494016). Their "call TIMENOW" comes here: Sleep(1) first, then the time. The loops sleep instead of
# burning a CPU core.
stime:
  push 1
  call dword ptr [Sleep]
  JMPG TIMENOW

# ---------------------------------------------------------------------------------------------------------------
# xget: eax = XInput user index (0..3) -> XS = its state, eax = 1; eax = 0 if not connected or no XInput. The first
# call looks for XInputGetState in xinput1_4.dll, else xinput1_3.dll, else xinput9_1_0.dll (Proton has all three;
# Windows 8+ has 1_4 and 9_1_0; the exe imports none of them). Keeps every other register.
xget:
  pushad
  mov esi, eax
  cmp dword ptr [XINIT], 0
  jne 2f
  mov dword ptr [XINIT], 1
  .byte 0xbf                         # mov edi, the three names (16 bytes each)
  .long A_XINPUT
  mov ebx, 3
1:
  push edi
  call dword ptr [LoadLibraryA]
  test eax, eax
  jz 3f
  PUSHI A_XGS
  push eax
  call dword ptr [GetProcAddress]
  test eax, eax
  jz 3f
  mov dword ptr [XGS], eax
  jmp 2f
3:
  add edi, 16
  dec ebx
  jnz 1b
2:
  mov eax, dword ptr [XGS]
  test eax, eax
  jz 9f
  cmp esi, 3
  ja 9f
  PUSHI XS
  push esi
  call eax
  test eax, eax
  jnz 9f
  popad
  mov eax, 1
  ret
9:
  popad
  xor eax, eax
  ret

# ---------------------------------------------------------------------------------------------------------------
# padraw (patch pad): the game builds each local player's input once a frame with PADRAW(player) (0x493720, called
# at 0x495451, 0x495479 and 0x495494): eax = the 32 action bits from the player's bindings (keyboard by default),
# edx = 4 bytes: the menu direction / choose / back bits, then the joystick's X, Y and Z axes (-127..127). That raw
# input is what replays and network games record; the pad converter (0x4926a0) turns it into the PlayStation pad the
# game logic reads. The calls come here: the game's own result, plus the Xbox pad with the player's number (XInput
# user 0 = player 1):
#   edx byte 1 (X)  the left stick (dead zone DZ), the D-pad left / right at full deflection: analogue steering
#   edx byte 2 (Y)  -RT / 2 (0..-127): analogue accelerate (the converter takes Y < 0 as accelerate)
#   edx byte 3 (Z)  LT / 2 (0..127): analogue brake (brakez makes the converter read it from Z)
#   eax |= the actions in padmap (buttons), Look Left / Right and Zoom in / out from the right stick, and the
#          digital steer / accelerate / brake bits past half way (for anything that reads those)
# Without a connected pad for that player: the game's result unchanged. Byte 0 (the game's menu bits from the
# keyboard) is kept as it is.
# With a pad, NOJOY is 1 while PADRAW runs (patch nojoy): the game then ignores its own DirectInput reading of the
# same pad (the joystick bindings and the stick-driven menu bits), so only the actions below come from the pad.
padraw:
  pushad
  mov eax, dword ptr [esp + 0x24]    # the player
  call xget
  mov dword ptr [NOJOY], eax
  popad
  push dword ptr [esp + 4]
  CALLG PADRAW
  add esp, 4
  mov dword ptr [NOJOY], 0
  pushad                             # [esp + 0x1c] = eax (actions), [esp + 0x14] = edx (bytes)
  mov eax, dword ptr [esp + 0x24]    # the player (pushad 0x20 + return address)
  call xget
  test eax, eax
  jz 90f
  movzx ebx, word ptr [XS + 4]       # buttons
  xor edi, edi                       # actions to add
  .byte 0xbe                         # mov esi, padmap
  .long A_PADMAP
1:
  mov eax, dword ptr [esi]
  test eax, eax
  jz 2f
  test ebx, eax
  jz 3f
  or edi, dword ptr [esi + 4]
3:
  add esi, 8
  jmp 1b
2:
  movsx eax, word ptr [XS + 12]      # right stick X: look left / right
  cmp eax, -RDZ
  jg 4f
  or edi, 0x10000                    # Look Left
4:
  cmp eax, RDZ
  jl 5f
  or edi, 0x20000                    # Look Right
5:
  movsx eax, word ptr [XS + 14]      # right stick Y (up +): zoom in / out
  cmp eax, RDZ
  jl 6f
  or edi, 0x2                        # Zoom in
6:
  cmp eax, -RDZ
  jg 7f
  or edi, 0x1                        # Zoom out
7:
  movsx eax, word ptr [XS + 8]       # left stick X -> -127..127
  call axisb
  test bl, 4                         # D-pad left / right: full
  jz 8f
  mov eax, -127
8:
  test bl, 8
  jz 10f
  mov eax, 127
10:
  cmp eax, -64
  jg 11f
  or edi, 0x8000                     # Left
11:
  cmp eax, 64
  jl 12f
  or edi, 0x2000                     # Right
12:
  movzx ebp, al
  shl ebp, 8                         # ebp: X in byte 1
  movzx eax, byte ptr [XS + 7]       # RT: accelerate
  cmp eax, 128
  jb 13f
  or edi, 0x40                       # Accelerate
13:
  call trigb
  neg eax
  movzx eax, al
  shl eax, 16
  or ebp, eax                        # Y = -RT / 2 in byte 2
  movzx eax, byte ptr [XS + 6]       # LT: brake
  cmp eax, 128
  jb 14f
  or edi, 0x80                       # Brake
14:
  call trigb
  shl eax, 24
  or ebp, eax                        # Z = LT / 2 in byte 3
  mov eax, dword ptr [esp + 0x14]
  and eax, 0xff                      # keep the game's menu bits
  or eax, ebp
  mov dword ptr [esp + 0x14], eax
  or dword ptr [esp + 0x1c], edi
90:
  popad
  ret

# axisb: eax = a stick axis (-32768..32767) -> eax = -127..127, 0 inside the dead zone DZ and scaled from its edge.
# Changes eax, ecx, edx.
axisb:
  mov ecx, eax
  cdq
  xor eax, edx
  sub eax, edx                       # |value|
  sub eax, DZ
  jg 1f
  xor eax, eax
  ret
1:
  imul eax, eax, 127
  xor edx, edx
  push ecx
  mov ecx, 32767 - DZ
  div ecx
  pop ecx
  cmp eax, 127
  jbe 2f
  mov eax, 127
2:
  test ecx, ecx
  jns 3f
  neg eax
3:
  ret

# trigb: eax = a trigger (0..255) -> eax = 0..127, 0 below TDZ.
trigb:
  cmp eax, TDZ
  jae 1f
  xor eax, eax
  ret
1:
  shr eax, 1
  ret

# ---------------------------------------------------------------------------------------------------------------
# bindtype (patch nojoy): the bindings loop 0x492330 (each binding: action bits, type, code) jumps on the binding's
# type through BINDJT (0x4923a7, "jmp [ecx*4 + 0x49250c]", eax = the list). That jump comes here: while NOJOY is
# set only key bindings (type 2) count, the joystick ones (buttons, axes, hat) are skipped. Without that
# the game had given player 1 its joystick preset (the Xbox pad as a DirectInput joystick: stick down = Look Back,
# stick up = Target Car, A = Accelerate, R3 = Pause ...) on top of padraw's actions.
bindtype:
  cmp dword ptr [NOJOY], 0
  je 1f
  cmp ecx, 2
  je 1f
  JMPG BINDNEXT
1:
  .byte 0xff, 0x24, 0x8d             # jmp dword ptr [ecx*4 + BINDJT]
  .long BINDJT

# menujoy (patch nojoy): PADRAW gets the menu bits from the game's own joystick with MENUJOY(player, actions)
# (0x493756: stick directions past half way, the buttons bound to Accelerate / Pause as choose / back). With NOJOY
# set: none (the menus are on the keyboard keys Steam Input types: D-pad, Start, View).
menujoy:
  cmp dword ptr [NOJOY], 0
  je 1f
  xor eax, eax
  ret
1:
  JMPG MENUJOY

# ---------------------------------------------------------------------------------------------------------------
# padflags (patch pad): when a race is set up (0x432300, edi = the player, esi = the car), each player's analogue
# flags are worked out by 0x456270(player, 8, 4, 2) (from the Controls menu: 1 analogue, 8 steer, 4 accelerate,
# 2 brake; Rollcage's were 0x80 / 4 / 2 / 1 in a word) and stored with "mov [esi + 0x42e], al" (0x4325e5, a byte;
# the converter reads it as [player * 0x434 + 0x61184e]). That store comes here: with an Xbox pad for that player
# the flags get 1 | 8 | 4 | 2 (analogue steering, accelerate and brake from padraw's X / Y / Z) and 0x10 (ours, no
# other reader tests it: brake from Z, brakez). Without one, the game's flags. (ecx and edx must survive: pushad.)
padflags:
  pushad
  mov eax, edi
  call xget
  test eax, eax
  jz 1f
  or byte ptr [esp + 0x1c], 0x1f
1:
  popad
  mov byte ptr [esi + 0x42e], al
  ret

# brakez (patch pad): the pad converter (0x4926a0) takes the analogue brake from the joystick's Y axis (Y > 0,
# written under "test dl, 2"; dl = the flags, al = Y): an Xbox pad's brake and throttle would share one axis (both
# held = neither). With our flag 0x10 the brake comes from the Z byte padraw fills from LT instead, so RT and LT work
# together. The converter's 20 bytes at 0x4927e7 jump here; back to 0x4927fb.
brakez:
  test dl, 2
  jz 9f
  test dl, 0x10
  jz 5f
  mov al, byte ptr [ebp + 7]         # Z: LT / 2
  test al, al
  jle 4f
  add al, al
  mov byte ptr [esi + 0xa], al
  jmp 9f
4:
  mov byte ptr [esi + 0xa], 0
  jmp 9f
5:
  test eax, eax                      # the game's own: Y > 0 is brake
  jle 4b
  add al, al
  mov byte ptr [esi + 0xa], al
9:
  JMPG BRAKERET

# ---------------------------------------------------------------------------------------------------------------
# movieskip (patch movieskip): the Bink movie player (0x49c4a0) stops a movie on any key (WM_KEYDOWN) or at its
# end; each picture is shown by MOVIEFRM(bink, buffer) (called at 0x49c746, eax 0 = ended). That call comes here:
# the picture as before, then "ended" also when A, B, X, Y, View or Start on the first Xbox pad is newly pressed.
movieskip:
  push dword ptr [esp + 8]
  push dword ptr [esp + 8]
  CALLG MOVIEFRM
  add esp, 8
  test eax, eax
  jz 9f
  pushad
  xor eax, eax
  call xget
  test eax, eax
  jz 8f
  movzx eax, word ptr [XS + 4]
  and eax, 0xf030                    # A B X Y View Start
  mov ecx, dword ptr [MOVPREV]
  mov dword ptr [MOVPREV], eax
  not ecx
  and eax, ecx                       # newly pressed
  jz 8f
  mov dword ptr [esp + 0x1c], 0
8:
  popad
9:
  ret

# binkwait (patch moviewait): between pictures the movie loop goes round PeekMessage and BinkWait (0x49c73a) as
# fast as it can until BinkWait says the next picture is due (0). Its "call [BinkWait]" comes here: the same call,
# and Sleep(1) while the picture is not due yet (stdcall, one argument).
binkwait:
  push dword ptr [esp + 4]
  call dword ptr [BinkWait]
  test eax, eax
  jz 1f
  push eax
  push 1
  call dword ptr [Sleep]
  pop eax
1:
  ret 4

# ---------------------------------------------------------------------------------------------------------------
# regget / regset (patch savefile): the game keeps its settings, records and progress as binary registry values in
# HKLM\Software\Psygnosis\Rollcage Stage II\BootSys: "DataPC" (0x1700 bytes) and "DataPSX" (0x2214), read with
# 0x4a3210(key, name, buffer, size) at 0x49ad4d (-> bytes read, or -1) and written with 0x4a32f0(key, name, buffer,
# size) at 0x49aed4 (-> 0, or -1). Those two calls come here: the same, with the file <exe folder>\..\Save\<name>.sav
# (the folder is made if missing) instead of the registry value.
regget:
  pushad
  mov esi, dword ptr [esp + 0x28]    # name
  mov edi, dword ptr [esp + 0x2c]    # buffer
  mov ebp, dword ptr [esp + 0x30]    # size
  call mkpath
  push 0
  push 0x80                          # FILE_ATTRIBUTE_NORMAL
  push 3                             # OPEN_EXISTING
  push 0
  push 1                             # FILE_SHARE_READ
  PUSHI 0x80000000                   # GENERIC_READ
  PUSHI PATH
  call dword ptr [CreateFileA]
  cmp eax, -1
  je 9f
  mov ebx, eax
  mov dword ptr [NRW], 0
  push 0
  PUSHI NRW
  push ebp
  push edi
  push ebx
  call dword ptr [ReadFile]
  push ebx
  call dword ptr [CloseHandle]
  mov eax, dword ptr [NRW]
  mov dword ptr [esp + 0x1c], eax
  popad
  ret
9:
  mov dword ptr [esp + 0x1c], -1
  popad
  ret

regset:
  pushad
  mov esi, dword ptr [esp + 0x28]
  mov edi, dword ptr [esp + 0x2c]
  mov ebp, dword ptr [esp + 0x30]
  call mkpath
  push 0
  push 0x80
  push 2                             # CREATE_ALWAYS
  push 0
  push 0
  PUSHI 0x40000000                   # GENERIC_WRITE
  PUSHI PATH
  call dword ptr [CreateFileA]
  cmp eax, -1
  je 9f
  mov ebx, eax
  mov dword ptr [NRW], 0
  push 0
  PUSHI NRW
  push ebp
  push edi
  push ebx
  call dword ptr [WriteFile]
  push ebx
  call dword ptr [CloseHandle]
  cmp dword ptr [NRW], ebp
  jne 9f
  mov dword ptr [esp + 0x1c], 0
  popad
  ret
9:
  mov dword ptr [esp + 0x1c], -1
  popad
  ret

# mkpath: esi = a value name -> PATH = "<exe folder>\..\Save\<name>.sav", and the Save folder made if missing.
# Changes eax, ebx, ecx, edx, edi... (called inside pushad; keeps esi only). The exe's folder, not the current one:
# the game changes its current folder to ..\IDXData at start-up.
mkpath:
  push edi
  push 0x1c0
  PUSHI PATH
  push 0
  call dword ptr [GetModuleFileNameA]
  .byte 0xbf                         # mov edi, PATH
  .long PATH
  mov ebx, edi                       # just after the last backslash
1:
  mov al, byte ptr [edi]
  test al, al
  jz 2f
  inc edi
  cmp al, 0x5c
  jne 1b
  mov ebx, edi
  jmp 1b
2:
  mov edi, ebx
  push esi
  .byte 0xbe                         # mov esi, "..\Save"
  .long A_SAVEDIR
  call scopy
  pop esi
  push edi
  push 0
  PUSHI PATH
  call dword ptr [CreateDirectoryA]  # fails harmlessly when it is there
  pop edi
  mov byte ptr [edi], 0x5c
  inc edi
  call scopy                         # the name
  push esi
  .byte 0xbe                         # mov esi, ".sav"
  .long A_SAVEEXT
  call scopy
  pop esi
  pop edi
  ret

# scopy: copy the string at esi to edi (with its 0); edi -> that 0, esi unchanged. Changes eax.
scopy:
  push esi
1:
  mov al, byte ptr [esi]
  mov byte ptr [edi], al
  test al, al
  jz 2f
  inc esi
  inc edi
  jmp 1b
2:
  pop esi
  ret

# ---------------------------------------------------------------------------------------------------------------
  .p2align 2
padmap:                              # XInput button -> Rollcage action bits (the same bits as Rollcage's: docs/TECHNICAL.md "Pad")
  .long 0x1000, 0x00000008           # A      Fire 1
  .long 0x4000, 0x00000004           # X      Fire 2
  .long 0x2000, 0x00000010           # B      Reverse
  .long 0x8000, 0x00000020           # Y      Face Forward
  .long 0x0100, 0x00001000           # LB     Target Car
  .long 0x0200, 0x00004000           # RB     Look Back (held)
  .long 0x0040, 0x40000000           # L3     Rear View Mirror
  .long 0x0080, 0x80000000           # R3     Cinematic Camera
  .long 0x0030, 0x00000800           # Start / View: Pause (Windows: on the Deck Steam Input sends Enter / Esc)
  .long 0, 0
s_xgs:     .asciz "XInputGetState"
s_savedir: .asciz "..\\Save"
s_saveext: .asciz ".sav"
  .p2align 4
s_xinput:  .asciz "xinput1_4.dll"
  .p2align 4
           .asciz "xinput1_3.dll"
  .p2align 4
           .asciz "xinput9_1_0.dll"
.set A_XGS,     BASE + (s_xgs - start)
.set A_SAVEDIR, BASE + (s_savedir - start)
.set A_SAVEEXT, BASE + (s_saveext - start)
.set A_XINPUT,  BASE + (s_xinput - start)
.set A_PADMAP,  BASE + (padmap - start)
