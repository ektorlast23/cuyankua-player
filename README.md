# cuyankua Player 2.4.0 — clon de VLC 3.0.24, skin Winamp a tamaño normal

Ejecutable: `H:\REA-tools\VLD\cuyankua.exe` (SHA256 `80AC58CC...79E091B3`)
Build: PyInstaller 6.22.3 windowed (sin consola) desde `vld_winamp.py`, Python 3.14.6.
Anteriores: `vld.exe` (marca VLD), `vld-v1-qt.exe` (interfaz qt stock).

## Funciones absorbidas del original
Transporte, seek, volumen, playlist ADD/DEL, pantalla completa ([ ]/doble-click/F11/ESC),
resume SQLite, repetir no/todo/uno, aleatorio, velocidad 0.5–2x, pistas de audio y
subtítulos (menús dinámicos + cargar .srt/.ass), aspecto 16:9/4:3/1:1, snapshots a
`capturas/`, mute, ecualizador con 18 presets, info del medio, atajos
(espacio/M/S/F/N/P). Todo verificado contra libvlc 3.0.24 real.

## Ventana (960x680, redimensionable, no mini)
Skin Winamp a tamaño normal: display LED verde de ancho completo con ticker + tiempo,
analizador ambar de 36 barras, area de video grande que se expande, playlist lateral
con scroll + ADD/DEL, seek de ancho completo, transporte grande (|< > || [] >| [ ] +),
volumen, pantalla completa ([ ], doble-click en el video, F11; ESC sale — la ventana
se vuelve fullscreen sin mover el video de HWND, que era lo que dejaba la pantalla en negro).

## Marca
Ventana "cuyankua Player 2.1.0", app-id `org.cuyankua.player`, user-agent `cuyankua/2.1.0`,
DB `cuyankua_resume.db`, log `cuyankua_debug.log`, env `CUYANKUA_VLC_DIR` (acepta `VLD_VLC_DIR`).
Interfaz: fondo negro, display LED verde, botones ambar, analizador, playlist,
seek, volumen, video embebido HWND, resume SQLite. Doble-click abre sin consola.

## Motor y evidencia
`libvlc.dll` 3.0.24 Vetinari (instalación VLC o `CUYANKUA_VLC_DIR`). Secuencia Ghidra 12.1.4
de `vlc.exe` WinMain@`0x140001510`: new → set_app_id → set_user_agent → playlist_play →
wait → release (sin `add_intf(qt)`; interfaz propia). Evidencias en `H:\REA-tools\`
(`vlc-func-main.json`, `vlc-search-procs.json`, `vlc-ghidra-analyze.json`).

## Probar
```powershell
H:\REA-tools\VLD\cuyankua.exe
H:\REA-tools\VLD\cuyankua.exe "H:\movies\Coraline (2009) 1080p.mkv"
H:\REA-tools\VLD\cuyankua.exe --selftest "C:\Windows\Media\Alarm01.wav"  # reproduce 8s headless, exige avance real
H:\REA-tools\VLD\cuyankua.exe --version
```
Verificado: SELFTEST OK (t 0→5572ms), ventana propia respondiendo, sin errores en log.

## Portable (sin VLC instalado)
- Carpeta: `H:\REA-tools\VLD\portable\` (~137MB: exe + libvlc/libvlccore + 360 plugins + lua/hrtfs).
- El exe usa el motor junto a el (`_motor_dir()`); solo si no esta recurre a
  `CUYANKUA_VLC_DIR` y por ultimo a `C:\Program Files\VideoLAN\VLC`.
- Recorte: fuera `plugins\gui` (qt, 18.9MB: los flags `--qt-*` los rechaza libvlc
  sin ese modulo y no se usan), `locale` (41.9MB), `skins`, ejecutables/txt de VLC.
- Prueba de independencia: proceso portable carga **361 módulos desde portable y
  0 desde Program Files**, reproduce Coraline con ticks avanzando.
- Llevar: `H:\REA-tools\VLD\cuyankua-portable.zip` (67.5MB). Descomprimir y doble-click.
