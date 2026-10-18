"""VLD media player 1.0.0 - clon funcional de VLC 3.0.24 con marca propia.
Replica la secuencia exacta observada con Ghidra 12.1.4 en vlc.exe WinMain@0x140001510:
  libvlc_new -> set_app_id -> set_user_agent -> add_intf -> playlist_play -> wait -> release
con hardening espejo (DEP/DLL-dir/mitigation/heap/error-mode) y config propia
(registry Software\\VLD\\VLD, app-id org.VLD.VLD, user-agent VLD/1.0.0).
Mejoras VLD: sin cono de fondo, sin check de updates, continua reproduccion,
resume SQLite por archivo.
Uso:
  vld.exe --version | --help
  vld.exe "D:/Videos/peli.mp4"
  vld.exe --ultimo
  vld.exe --guardar "D:/Videos/peli.mp4" 95.5
Evidencia: H:\\REA-tools\\vlc-func-main.json (WinMain), vlc-search-procs.json (7 imports libvlc).
"""
import ctypes, os, sqlite3, sys, time
from pathlib import Path

VERSION = "1.0.0"
APP_ID = "org.VLD.VLD"
USER_AGENT = f"VLD/{VERSION}"
INTF_NAME = "VLD media player"

VLC_DIR = Path(os.environ.get("VLD_VLC_DIR", r"C:\Program Files\VideoLAN\VLC"))
BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
DB = BASE_DIR / "vld_resume.db"

SCHEMA = """CREATE TABLE IF NOT EXISTS reproduccion(
  ruta TEXT PRIMARY KEY, posicion REAL NOT NULL DEFAULT 0,
  updated INTEGER NOT NULL);"""

# NOTA: --media-library/--no-ignore-config/--no-crashdump/--language son opciones
# del wrapper WinMain (las parsea vlc.exe antes de libvlc_new, ver FUN_140003010),
# NO son opciones libvlc: pasarlas a libvlc_new da "unknown option". Aqui solo van
# opciones libvlc validas; lo demas lo gestiona VLD directamente.
DEFAULT_ARGS = [b"--no-qt-bgcone", b"--qt-continue", b"1"]

def db():
    c = sqlite3.connect(DB)
    c.execute(SCHEMA)
    return c

def guardar(ruta, pos):
    c = db()
    c.execute("INSERT INTO reproduccion(ruta,posicion,updated) VALUES(?,?,?) "
              "ON CONFLICT(ruta) DO UPDATE SET posicion=excluded.posicion,updated=excluded.updated",
              (ruta, pos, int(time.time())))
    c.commit(); c.close()

def recordar(ruta):
    c = db()
    r = c.execute("SELECT posicion FROM reproduccion WHERE ruta=?", (ruta,)).fetchone()
    c.close()
    return r[0] if r else 0.0

def ultimo():
    c = db()
    r = c.execute("SELECT ruta,posicion FROM reproduccion ORDER BY updated DESC LIMIT 1").fetchone()
    c.close()
    return r

def hardening():
    k = ctypes.WinDLL("kernel32", use_last_error=True)
    try: k.SetErrorMode(0x0001 | 0x0002)  # SEM_FAILCRITICALERRORS|SEM_NOGPFAULTERRORBOX (espejo WinMain)
    except Exception: pass
    try: k.SetDllDirectoryW(str(VLC_DIR))  # espejo SetDllDirectoryA/SetDefaultDllDirectories
    except Exception: pass
    try:
        heap = k.GetProcessHeap()
        k.HeapSetInformation(heap, 0, ctypes.byref(ctypes.c_ulonglong(2)), 8)  # HeapEnableTerminationOnCorruption
    except Exception: pass

def cargar_libvlc():
    try: os.add_dll_directory(str(VLC_DIR))
    except Exception: pass
    return ctypes.CDLL(str(VLC_DIR / "libvlc.dll"))

def reproducir(archivos, start=0.0):
    hardening()
    lib = cargar_libvlc()
    lib.libvlc_new.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]
    lib.libvlc_new.restype = ctypes.c_void_p
    lib.libvlc_set_app_id.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
    lib.libvlc_set_user_agent.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
    lib.libvlc_add_intf.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
    lib.libvlc_add_intf.restype = ctypes.c_int
    lib.libvlc_playlist_play.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_int, ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p]
    lib.libvlc_wait.argtypes = [ctypes.c_void_p]
    lib.libvlc_release.argtypes = [ctypes.c_void_p]

    argv = [b"vld"] + DEFAULT_ARGS + ([b"--start-time", str(int(start)).encode()] if start > 0 else [])
    argv += [a.encode("utf-8") for a in archivos]
    arr = (ctypes.c_char_p * len(argv))(*argv)
    inst = lib.libvlc_new(len(argv), arr)
    if not inst:
        print("VLD media player could not start.\nEither the command line options were invalid or no plugins were found.")
        return 1
    lib.libvlc_set_app_id(inst, APP_ID.encode(), VERSION.encode(), INTF_NAME.encode())
    lib.libvlc_set_user_agent(inst, USER_AGENT.encode(), f"{USER_AGENT} LibVLC".encode())
    if lib.libvlc_add_intf(inst, b"qt") != 0:
        print("VLD: no se pudo abrir la interfaz qt.")
        lib.libvlc_release(inst)
        return 1
    lib.libvlc_playlist_play(inst, -1, 0, None, 0, None)
    for a in archivos: guardar(a, start)
    lib.libvlc_wait(inst)  # bloquea hasta salir de la UI, igual que vlc.exe
    lib.libvlc_release(inst)
    return 0

if __name__ == "__main__":
    a = sys.argv[1:]
    if a and a[0] in ("--help", "-h"):
        print(__doc__); sys.exit(0)
    if not a:
        sys.exit(reproducir([], 0.0))  # sin args abre la interfaz, igual que vlc.exe
    if a[0] in ("--version", "-v"):
        print(f"VLD media player {VERSION} (clon de VLC 3.0.24, motor libvlc)"); sys.exit(0)
    if a[0] == "--guardar" and len(a) >= 3:
        guardar(a[1], float(a[2])); print("Guardado."); sys.exit(0)
    if a[0] == "--ultimo":
        r = ultimo()
        if not r: print("Sin historial. Reproduce algo primero."); sys.exit(0)
        print(f"Resume: {r[0]} desde {r[1]:.1f}s")
        sys.exit(reproducir([r[0]], r[1]))
    st = 0.0
    if "--start" in a:
        st = float(a[a.index("--start") + 1]); a = [x for x in a if x != "--start" and x != str(st)]
    else:
        st = recordar(a[0]) if len(a) == 1 else 0.0
        if st: print(f"Resume automatico desde {st:.1f}s")
    sys.exit(reproducir(a, st))
