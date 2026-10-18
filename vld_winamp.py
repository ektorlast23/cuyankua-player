"""cuyankua Player 2.1.0 - clon de VLC 3.0.24 con interfaz propia oscura estilo Winamp.
Ventana Tk propia titulada "cuyankua Player", playlist, seek, volumen,
resume SQLite y video embebido (HWND).
Motor: libvlc.dll de tu instalacion VLC (o CUYANKUA_VLC_DIR), secuencia
libvlc_new -> set_app_id(org.cuyankua.player) -> set_user_agent(cuyankua/2.1.0).
Uso: doble-click abre el reproductor; cuyankua.exe "D:/Video.mp4" reproduce directo.
"""
import ctypes, os, random, sqlite3, sys, time
from pathlib import Path

VERSION = "2.5.0"
APP_ID = "org.cuyankua.player"
USER_AGENT = "cuyankua/2.5.0"
TITLE = "cuyankua Player"

def _motor_dir():
    base = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    if (base / "libvlc.dll").exists():
        return base  # portable: motor junto al exe, sin depender de VLC instalado
    env = os.environ.get("CUYANKUA_VLC_DIR") or os.environ.get("VLD_VLC_DIR")
    if env and (Path(env) / "libvlc.dll").exists():
        return Path(env)
    return Path(r"C:\Program Files\VideoLAN\VLC")

VLC_DIR = _motor_dir()
BASE_DIR = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
DB = BASE_DIR / "cuyankua_resume.db"

BG, PANEL, LED, AMBAR, GRIS, TXT = "#0b0b0d", "#141416", "#39ff6a", "#ffb000", "#2a2a2e", "#e8e8e8"

def log(*a):
    try: print(*a)
    except Exception: pass
    try:
        with open(BASE_DIR / "cuyankua_debug.log", "a", encoding="utf-8") as f:
            f.write(time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a) + "\n")
    except Exception: pass

def db():
    c = sqlite3.connect(DB)
    c.execute("CREATE TABLE IF NOT EXISTS reproduccion(ruta TEXT PRIMARY KEY, posicion REAL DEFAULT 0, updated INTEGER)")
    return c

def guardar(ruta, pos):
    try:
        c = db()
        c.execute("INSERT INTO reproduccion(ruta,posicion,updated) VALUES(?,?,?) "
                  "ON CONFLICT(ruta) DO UPDATE SET posicion=excluded.posicion,updated=excluded.updated",
                  (ruta, pos, int(time.time())))
        c.commit(); c.close()
    except Exception: pass

def recordar(ruta):
    try:
        c = db()
        r = c.execute("SELECT posicion FROM reproduccion WHERE ruta=?", (ruta,)).fetchone()
        c.close()
        return r[0] if r else 0.0
    except Exception: return 0.0

class TrackDesc(ctypes.Structure):
    pass
TrackDesc._fields_ = [("i_id", ctypes.c_int), ("psz_name", ctypes.c_char_p),
                      ("p_next", ctypes.POINTER(TrackDesc))]

class LibVLC:
    def __init__(self):
        try: os.add_dll_directory(str(VLC_DIR))
        except Exception: pass
        k = ctypes.WinDLL("kernel32", use_last_error=True)
        try: k.SetErrorMode(0x0001 | 0x0002)
        except Exception: pass
        try: k.SetDllDirectoryW(str(VLC_DIR))
        except Exception: pass
        self.lib = ctypes.CDLL(str(VLC_DIR / "libvlc.dll"))
        L = self.lib
        L.libvlc_new.argtypes = [ctypes.c_int, ctypes.POINTER(ctypes.c_char_p)]; L.libvlc_new.restype = ctypes.c_void_p
        L.libvlc_release.argtypes = [ctypes.c_void_p]
        L.libvlc_set_app_id.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
        L.libvlc_set_user_agent.argtypes = [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_char_p]
        L.libvlc_media_new_path.argtypes = [ctypes.c_void_p, ctypes.c_char_p]; L.libvlc_media_new_path.restype = ctypes.c_void_p
        L.libvlc_media_release.argtypes = [ctypes.c_void_p]
        L.libvlc_media_player_new_from_media.argtypes = [ctypes.c_void_p]; L.libvlc_media_player_new_from_media.restype = ctypes.c_void_p
        L.libvlc_media_player_release.argtypes = [ctypes.c_void_p]
        L.libvlc_media_player_play.argtypes = [ctypes.c_void_p]; L.libvlc_media_player_play.restype = ctypes.c_int
        L.libvlc_media_player_pause.argtypes = [ctypes.c_void_p]
        L.libvlc_media_player_stop.argtypes = [ctypes.c_void_p]
        L.libvlc_media_player_is_playing.argtypes = [ctypes.c_void_p]; L.libvlc_media_player_is_playing.restype = ctypes.c_int
        L.libvlc_media_player_get_time.argtypes = [ctypes.c_void_p]; L.libvlc_media_player_get_time.restype = ctypes.c_longlong
        L.libvlc_media_player_get_length.argtypes = [ctypes.c_void_p]; L.libvlc_media_player_get_length.restype = ctypes.c_longlong
        L.libvlc_media_player_set_time.argtypes = [ctypes.c_void_p, ctypes.c_longlong]
        L.libvlc_media_player_set_hwnd.argtypes = [ctypes.c_void_p, ctypes.c_void_p]
        L.libvlc_audio_set_volume.argtypes = [ctypes.c_void_p, ctypes.c_int]; L.libvlc_audio_set_volume.restype = ctypes.c_int
        L.libvlc_audio_get_volume.argtypes = [ctypes.c_void_p]; L.libvlc_audio_get_volume.restype = ctypes.c_int
        L.libvlc_audio_toggle_mute.argtypes = [ctypes.c_void_p]
        L.libvlc_audio_get_mute.argtypes = [ctypes.c_void_p]; L.libvlc_audio_get_mute.restype = ctypes.c_int
        L.libvlc_audio_set_mute.argtypes = [ctypes.c_void_p, ctypes.c_int]
        L.libvlc_audio_get_track_description.argtypes = [ctypes.c_void_p]; L.libvlc_audio_get_track_description.restype = ctypes.POINTER(TrackDesc)
        L.libvlc_audio_set_track.argtypes = [ctypes.c_void_p, ctypes.c_int]; L.libvlc_audio_set_track.restype = ctypes.c_int
        L.libvlc_video_get_spu_description.argtypes = [ctypes.c_void_p]; L.libvlc_video_get_spu_description.restype = ctypes.POINTER(TrackDesc)
        L.libvlc_video_set_spu.argtypes = [ctypes.c_void_p, ctypes.c_int]; L.libvlc_video_set_spu.restype = ctypes.c_int
        L.libvlc_video_set_subtitle_file.argtypes = [ctypes.c_void_p, ctypes.c_char_p]; L.libvlc_video_set_subtitle_file.restype = ctypes.c_int
        L.libvlc_track_description_list_release.argtypes = [ctypes.POINTER(TrackDesc)]
        L.libvlc_media_player_set_rate.argtypes = [ctypes.c_void_p, ctypes.c_float]; L.libvlc_media_player_set_rate.restype = ctypes.c_int
        L.libvlc_media_player_get_rate.argtypes = [ctypes.c_void_p]; L.libvlc_media_player_get_rate.restype = ctypes.c_float
        L.libvlc_video_set_aspect_ratio.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        L.libvlc_video_set_crop_geometry.argtypes = [ctypes.c_void_p, ctypes.c_char_p]
        L.libvlc_video_take_snapshot.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_char_p, ctypes.c_uint, ctypes.c_uint]; L.libvlc_video_take_snapshot.restype = ctypes.c_int
        L.libvlc_video_get_size.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.POINTER(ctypes.c_uint), ctypes.POINTER(ctypes.c_uint)]; L.libvlc_video_get_size.restype = ctypes.c_int
        L.libvlc_audio_equalizer_new.restype = ctypes.c_void_p
        L.libvlc_audio_equalizer_new_from_preset.argtypes = [ctypes.c_uint]; L.libvlc_audio_equalizer_new_from_preset.restype = ctypes.c_void_p
        L.libvlc_audio_equalizer_get_preset_count.restype = ctypes.c_uint
        L.libvlc_audio_equalizer_get_preset_name.argtypes = [ctypes.c_uint]; L.libvlc_audio_equalizer_get_preset_name.restype = ctypes.c_char_p
        L.libvlc_audio_equalizer_release.argtypes = [ctypes.c_void_p]
        L.libvlc_media_player_set_equalizer.argtypes = [ctypes.c_void_p, ctypes.c_void_p]; L.libvlc_media_player_set_equalizer.restype = ctypes.c_int
        # Sin flags --qt-*: son del modulo qt (plugins\gui) que el portable no
        # incluye a proposito; libvlc_new los rechaza si el modulo no existe.
        # El resume/continue lo gestiona cuyankua (start_ms), no hace falta qt.
        argv_list = [b"cuyankua"]
        if os.environ.get("CUYANKUA_SILENT") == "1":
            argv_list.append(b"--no-audio")  # sondas silenciosas: video sin molestar
        argv = (ctypes.c_char_p * len(argv_list))(*argv_list)
        self.inst = L.libvlc_new(len(argv_list), argv)
        if not self.inst: raise RuntimeError("libvlc_new fallo")
        L.libvlc_set_app_id(self.inst, APP_ID.encode(), VERSION.encode(), TITLE.encode())
        L.libvlc_set_user_agent(self.inst, USER_AGENT.encode(), f"{USER_AGENT} LibVLC".encode())
        self.player = None

    def abrir(self, ruta, hwnd=None, start_ms=0):
        # Normalizar: el filedialog entrega H:/... y libvlc falla con slashes
        ruta = os.path.abspath(os.path.normpath(str(ruta)))
        L = self.lib
        self.cerrar_player()
        m = L.libvlc_media_new_path(self.inst, os.fsencode(ruta))
        if not m:
            log(f"abrir FALLA media_new_path ruta={ruta}")
            return False
        self.player = L.libvlc_media_player_new_from_media(m)
        L.libvlc_media_release(m)
        if not self.player:
            log(f"abrir FALLA player_new ruta={ruta}")
            return False
        if hwnd: L.libvlc_media_player_set_hwnd(self.player, ctypes.c_void_p(hwnd))
        rc = L.libvlc_media_player_play(self.player)
        log(f"abrir ruta={ruta} hwnd={hwnd} start_ms={start_ms} play_rc={rc}")
        if rc != 0: return False
        if start_ms > 0:
            for _ in range(40):
                if L.libvlc_media_player_get_length(self.player) > 0: break
                time.sleep(0.1)
            L.libvlc_media_player_set_time(self.player, int(start_ms))
        try: L.libvlc_audio_set_volume(self.player, self._vol)
        except Exception: pass
        return True

    _vol = 80
    _eq = None
    def cerrar_player(self):
        if self.player:
            try: self.lib.libvlc_media_player_stop(self.player)
            except Exception: pass
            try: self.lib.libvlc_media_player_release(self.player)
            except Exception: pass
            self.player = None

    def _tracks(self, getter):
        out = []
        if not self.player: return out
        head = getter(self.player)
        p = head
        seen = 0
        while p and seen < 64:
            try:
                tid = p.contents.i_id
                nom = p.contents.psz_name.decode("utf-8", "replace") if p.contents.psz_name else str(tid)
                out.append((tid, nom))
                p = p.contents.p_next
            except Exception: break
            seen += 1
        try:
            if head: self.lib.libvlc_track_description_list_release(head)
        except Exception: pass
        return out

    def spu_list(self): return self._tracks(self.lib.libvlc_video_get_spu_description)
    def audio_list(self): return self._tracks(self.lib.libvlc_audio_get_track_description)
    def set_spu(self, tid):
        return self.lib.libvlc_video_set_spu(self.player, tid) == 0 if self.player else False
    def set_audio(self, tid):
        return self.lib.libvlc_audio_set_track(self.player, tid) == 0 if self.player else False
    def set_rate(self, r):
        return self.lib.libvlc_media_player_set_rate(self.player, float(r)) == 0 if self.player else False
    def get_rate(self):
        try: return round(float(self.lib.libvlc_media_player_get_rate(self.player)), 2)
        except Exception: return 1.0
    def set_aspect(self, asp):
        try: self.lib.libvlc_video_set_aspect_ratio(self.player, asp.encode() if asp else None)
        except Exception: pass
    def snapshot(self):
        try:
            d = BASE_DIR / "capturas"; d.mkdir(exist_ok=True)
            p = d / f"cuyankua_{time.strftime('%Y%m%d_%H%M%S')}.png"
            return self.lib.libvlc_video_take_snapshot(self.player, 0, os.fsencode(str(p)), 0, 0) == 0, str(p)
        except Exception: return False, ""
    def toggle_mute(self):
        try: self.lib.libvlc_audio_toggle_mute(self.player)
        except Exception: pass
    def is_mute(self):
        try: return bool(self.lib.libvlc_audio_get_mute(self.player))
        except Exception: return False
    def eq_preset_names(self):
        try:
            n = self.lib.libvlc_audio_equalizer_get_preset_count()
            return [self.lib.libvlc_audio_equalizer_get_preset_name(i).decode() for i in range(n)]
        except Exception: return []
    def eq_apply(self, idx):
        # idx None = desactivar
        try:
            if self._eq:
                self.lib.libvlc_audio_equalizer_release(self._eq); self._eq = None
            if idx is None:
                if self.player: self.lib.libvlc_media_player_set_equalizer(self.player, None)
                return True
            eq = self.lib.libvlc_audio_equalizer_new_from_preset(idx)
            if not eq: return False
            self._eq = eq
            return self.lib.libvlc_media_player_set_equalizer(self.player, eq) == 0 if self.player else True
        except Exception: return False
    def video_size(self):
        try:
            w, h = ctypes.c_uint(0), ctypes.c_uint(0)
            if self.lib.libvlc_video_get_size(self.player, 0, ctypes.byref(w), ctypes.byref(h)) == 0:
                return w.value, h.value
        except Exception: pass
        return 0, 0

def fmt(ms):
    if ms is None or ms < 0: return "--:--"
    s = int(ms // 1000); return f"{s//60:02d}:{s%60:02d}"

class GanchoDobleClick:
    """Detecta doble-click a nivel sistema (WH_MOUSE_LL) solo dentro de un rect.
    Necesario porque la subventana de video Direct3D se come los clicks y Tk
    nunca los ve. Mecanismo unico: los binds Tk de doble-click no se usan."""

    def __init__(self, dentro_fn, alternar_fn, agenda_fn):
        # dentro_fn(x, y) -> True si el punto debe alternar fullscreen
        # alternar_fn() -> toggle (se ejecuta en hilo UI via agenda_fn)
        self._dentro = dentro_fn
        self._alternar = alternar_fn
        self._agenda = agenda_fn
        self._u32 = ctypes.windll.user32
        self._k32 = ctypes.windll.kernel32
        self._ult = {"t": 0.0, "x": 0, "y": 0}
        self._hook = None
        self._tid = None
        self._hilo = None
        self._cb = None
        u32 = self._u32
        try:
            u32.SetWindowsHookExW.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p, ctypes.c_ulong]
            u32.SetWindowsHookExW.restype = ctypes.c_void_p
            u32.CallNextHookEx.argtypes = [ctypes.c_void_p, ctypes.c_int, ctypes.c_void_p, ctypes.c_void_p]
            u32.CallNextHookEx.restype = ctypes.c_long
            u32.UnhookWindowsHookEx.argtypes = [ctypes.c_void_p]
            u32.PostThreadMessageW.argtypes = [ctypes.c_ulong, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
        except Exception:
            pass

    def _doble(self, x, y):
        ahora = time.monotonic()
        ok = ((ahora - self._ult["t"]) * 1000 < self._u32.GetDoubleClickTime()
              and abs(x - self._ult["x"]) < 8 and abs(y - self._ult["y"]) < 8)
        self._ult.update(t=ahora, x=x, y=y)
        return ok

    def instalar(self):
        WM_LBUTTONDOWN, WH_MOUSE_LL = 0x0201, 14
        u32, k32 = self._u32, self._k32

        class Pt(ctypes.Structure):
            _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]

        class HookSt(ctypes.Structure):
            _fields_ = [("pt", Pt), ("mouseData", ctypes.c_ulong),
                        ("flags", ctypes.c_ulong), ("time", ctypes.c_ulong),
                        ("dwExtra", ctypes.c_void_p)]

        def cb(nCode, wParam, lParam):
            try:
                if nCode >= 0 and wParam == WM_LBUTTONDOWN:
                    st = ctypes.cast(lParam, ctypes.POINTER(HookSt)).contents
                    if self._doble(st.pt.x, st.pt.y) and self._dentro(st.pt.x, st.pt.y):
                        self._agenda(self._alternar)
            except Exception:
                pass
            return u32.CallNextHookEx(None, nCode, wParam, lParam)

        self._cb = ctypes.WINFUNCTYPE(ctypes.c_long, ctypes.c_int, ctypes.c_int,
                                      ctypes.c_void_p)(cb)

        def bucle():
            self._tid = k32.GetCurrentThreadId()
            # Hook de BAJO NIVEL: corre en este proceso -> hMod debe ser NULL
            # (GetModuleHandleW da ERROR_MOD_NOT_FOUND 126)
            self._hook = u32.SetWindowsHookExW(WH_MOUSE_LL, self._cb, None, 0)
            if not self._hook:
                return
            buf = ctypes.create_string_buffer(48)
            while u32.GetMessageW(buf, None, 0, 0) > 0:
                u32.TranslateMessage(buf)
                u32.DispatchMessageW(buf)

        import threading
        self._hilo = threading.Thread(target=bucle, daemon=True)
        self._hilo.start()
        return True

    def desinstalar(self):
        try:
            if self._tid:
                self._u32.PostThreadMessageW(self._tid, 0x0012, 0, 0)
            if self._hook:
                self._u32.UnhookWindowsHookEx(self._hook)
        except Exception:
            pass
        self._hook, self._tid = None, None

def main(arranque):
    import tkinter as tk
    from tkinter import filedialog, messagebox
    engine = LibVLC()
    root = tk.Tk()

    def _reporte_tk(exc, val, tb):
        import traceback
        log("ERROR-TK:", "".join(traceback.format_exception(exc, val, tb))[-2000:])
    root.report_callback_exception = _reporte_tk
    root.title(TITLE + f" {VERSION}")
    root.configure(bg=BG)
    root.geometry("960x680")
    root.resizable(True, True)
    root.minsize(680, 500)

    estado = {"ruta": None, "tocando": False, "sonando": False, "seek_lock": False, "fs": None,
              "repeat": "no", "shuffle": False, "rate": 1.0, "tracks_built": False}

    # --- display LED ancho completo estilo Winamp ---
    disp = tk.Canvas(root, bg="#020403", height=96, highlightthickness=1, highlightbackground=GRIS)
    disp.pack(side="top", fill="x", padx=10, pady=(10, 6))
    txt_track = disp.create_text(14, 14, anchor="w", text="cuyankua 2.5  -  listo",
                                fill=LED, font=("Consolas", 12, "bold"))
    txt_time = disp.create_text(946, 14, anchor="e", text="--:-- / --:--",
                                fill=LED, font=("Consolas", 12, "bold"))
    NBARS = 36
    bars = []
    for i in range(NBARS):
        x0 = 14 + i * 26
        bars.append(disp.create_rectangle(x0, 90, x0 + 18, 90, fill=AMBAR, outline=""))

    # --- centro: video grande (expande) + playlist lateral ---
    mid = tk.Frame(root, bg=BG)
    mid.pack(side="top", fill="both", expand=True, padx=10)
    marco = tk.Frame(mid, bg="#000000")
    marco.pack(side="left", fill="both", expand=True)
    lienzo = tk.Frame(marco, bg="#000000")
    lienzo.pack(fill="both", expand=True)
    side = tk.Frame(mid, bg=BG, width=280)
    side.pack(side="right", fill="y", padx=(10, 0))
    side.pack_propagate(False)

    # --- abajo: seek + transporte + volumen ---
    bottom = tk.Frame(root, bg=BG)
    bottom.pack(side="bottom", fill="x", padx=10, pady=10)
    seek = tk.Scale(bottom, from_=0, to=1000, orient="horizontal", showvalue=False, bg=BG, fg=AMBAR,
                    troughcolor=PANEL, highlightthickness=0)
    seek.pack(side="top", fill="x")

    def tocar(ruta):
        try:
            ruta = os.path.abspath(os.path.normpath(str(ruta)))  # misma clave p/resume
            hwnd = lienzo.winfo_id()
            st = recordar(ruta)
            ok = engine.abrir(ruta, hwnd, int(st * 1000))
            estado.update(ruta=str(ruta), tocando=bool(ok), sonando=False, tracks_built=False)
            nombre = Path(str(ruta)).name
            disp.itemconfig(txt_track, text=(nombre[:70] + (" (resume %s)" % fmt(st * 1000) if st else nombre[:80])))
            if not ok: messagebox.showerror(TITLE, f"No se pudo abrir:\n{ruta}")
            log(f"tocar ruta={ruta} ok={ok}")
        except Exception as ex:
            import traceback
            log("ERROR tocar:", ex, traceback.format_exc())
            messagebox.showerror(TITLE, f"Error al reproducir:\n{ex}")

    def anterior():
        sel = pl.curselection()
        i = (sel[0] - 1) % pl.size() if sel and pl.size() else 0
        if pl.size(): pl.selection_clear(0, "end"); pl.selection_set(i); tocar(pl.get(i))

    def siguiente(auto=False):
        sel = pl.curselection()
        i = (sel[0] + 1) % pl.size() if sel and pl.size() else 0
        if pl.size():
            if not auto or i != 0 or len(sel) == 0:
                pl.selection_clear(0, "end"); pl.selection_set(i); tocar(pl.get(i))
            elif estado.get("repeat") == "todo":
                pl.selection_clear(0, "end"); pl.selection_set(0); tocar(pl.get(0))
            else:
                estado["tocando"] = False

    def pista_aleatoria():
        if pl.size() < 2: return siguiente()
        cur = pl.curselection()[0] if pl.curselection() else -1
        op = [i for i in range(pl.size()) if i != cur]
        i = random.choice(op)
        pl.selection_clear(0, "end"); pl.selection_set(i); tocar(pl.get(i))

    def pausar():
        if engine.player: engine.lib.libvlc_media_player_pause(engine.player)

    def detener():
        if engine.player:
            t = engine.lib.libvlc_media_player_get_time(engine.player)
            if estado["ruta"] and t > 5000: guardar(estado["ruta"], t / 1000.0)
            engine.lib.libvlc_media_player_stop(engine.player)
        estado["tocando"] = False
        disp.itemconfig(txt_time, text="--:-- / --:--")

    def agregar():
        fs = filedialog.askopenfilenames(title="Agregar a cuyankua",
            filetypes=[("Media", "*.mp3 *.mp4 *.mkv *.avi *.flac *.ogg *.wav *.m4a *.webm"), ("Todo", "*.*")])
        for f in fs: pl.insert("end", f)

    def quitar_sel():
        for i in reversed(pl.curselection()):
            pl.delete(i)

    def alternar_mute():
        engine.toggle_mute()
        var_mute.set(engine.is_mute())

    def foto():
        if not engine.player:
            messagebox.showinfo(TITLE, "Abre un video primero.")
            return
        ok, ruta = engine.snapshot()
        messagebox.showinfo(TITLE, f"Snapshot guardado:\n{ruta}" if ok else "No se pudo guardar el snapshot.")

    def info_medio():
        if not engine.player or not estado["ruta"]:
            messagebox.showinfo(TITLE, "Nada en reproduccion.")
            return
        try:
            L = engine.lib
            dur = L.libvlc_media_player_get_length(engine.player)
            t = L.libvlc_media_player_get_time(engine.player)
            w, h = engine.video_size()
            tam = os.path.getsize(estado["ruta"]) / (1024 * 1024)
            na = len(engine.audio_list())
            ns = len(engine.spu_list())
            messagebox.showinfo(TITLE,
                f"Archivo: {Path(estado['ruta']).name}\n"
                f"Tamaño: {tam:.1f} MB\nDuración: {fmt(dur)}\nPosición: {fmt(t)}\n"
                f"Video: {w}x{h}\nPistas audio: {na} | Subtítulos: {ns}\n"
                f"Velocidad: {engine.get_rate()}x | Volumen: {vol.get()}")
        except Exception as ex:
            messagebox.showerror(TITLE, f"No se pudo leer info:\n{ex}")

    def poner_velocidad(r):
        estado["rate"] = r
        var_rate.set(f"{r}x")
        if engine.player: engine.set_rate(r)

    def poner_aspecto(a):
        if engine.player: engine.set_aspect(a if a != "Default" else None)

    def poner_eq(idx):
        engine.eq_apply(idx)
        estado["eq"] = idx

    def cargar_sub():
        f = filedialog.askopenfilename(title="Cargar subtitulo",
            filetypes=[("Subtitulos", "*.srt *.ass *.ssa *.sub *.vtt"), ("Todo", "*.*")])
        if f and engine.player:
            if engine.lib.libvlc_video_set_subtitle_file(engine.player, os.fsencode(f)) < 0:
                messagebox.showerror(TITLE, "No se pudo cargar el subtitulo.")
            else:
                estado["tracks_built"] = False

    def reconstruir_pistas():
        # rellena los submenus de pistas de audio/subtitulos con lo detectado
        try:
            for m, getter, setter in ((menu_audio_pista, engine.audio_list, engine.set_audio),
                                      (menu_spu, engine.spu_list, engine.set_spu)):
                m.delete(0, "end")
                pistas = getter()
                if not pistas:
                    m.add_command(label="(sin pistas)", state="disabled")
                for tid, nom in pistas:
                    m.add_command(label=f"{tid}: {nom}",
                                  command=lambda t=tid, s=setter: s(t))
            if menu_spu.index("end") is not None:
                menu_spu.add_separator()
                menu_spu.add_command(label="Cargar archivo...", command=cargar_sub)
            estado["tracks_built"] = True
        except Exception as ex:
            log("ERROR pistas:", ex)

    def entrar_fs():
        # Pantalla completa SIN mover el video de HWND (moverlo lo dejaba en negro):
        # se oculta el resto de la UI y la ventana raiz pasa a fullscreen.
        if not engine.player:
            messagebox.showinfo(TITLE, "Abre un video primero.")
            return
        if estado["fs"] is not None: return
        try:
            disp.pack_forget()
            side.pack_forget()
            bottom.pack_forget()
            root.config(menu=tk.Menu(root))  # oculta la barra de menus en fullscreen
            root.attributes("-fullscreen", True)
            estado["fs"] = True
            root.focus_set()
            log("fullscreen ON (misma ventana/hwmd)")
        except Exception as ex:
            import traceback
            log("ERROR fullscreen ON:", ex, traceback.format_exc())

    def salir_fs():
        try:
            root.attributes("-fullscreen", False)
            disp.pack(side="top", fill="x", padx=10, pady=(10, 6))
            side.pack(side="right", fill="y", padx=(10, 0))
            bottom.pack(side="bottom", fill="x", padx=10, pady=10)
            root.config(menu=barra)  # restaura la barra de menus
            estado["fs"] = None
            log("fullscreen OFF")
        except Exception as ex:
            import traceback
            log("ERROR fullscreen OFF:", ex, traceback.format_exc())

    def toggle_fs():
        if estado["fs"] is not None: salir_fs()
        else: entrar_fs()

    # --- playlist lateral (antes de los botones que la usan) ---
    tk.Label(side, text="PLAYLIST", bg=BG, fg=GRIS, font=("Consolas", 9, "bold")).pack(side="top", anchor="w")
    plf = tk.Frame(side, bg=BG)
    plf.pack(side="top", fill="both", expand=True)
    pl = tk.Listbox(plf, bg="#101012", fg=TXT, selectbackground="#3a2b00", font=("Consolas", 9))
    pl.pack(side="left", fill="both", expand=True)
    sbar = tk.Scrollbar(plf, orient="vertical", command=pl.yview)
    sbar.pack(side="right", fill="y")
    pl.config(yscrollcommand=sbar.set)
    pl.bind("<Double-Button-1>", lambda e: play_sel())
    pf = tk.Frame(side, bg=BG)
    pf.pack(side="top", fill="x", pady=(6, 0))
    tk.Button(pf, text="ADD", command=agregar, bg=PANEL, fg=AMBAR,
              activebackground="#1e1e22", activeforeground=AMBAR,
              font=("Consolas", 9, "bold"), relief="raised", bd=2).pack(side="left", expand=True, fill="x", padx=(0, 3))
    tk.Button(pf, text="DEL", command=quitar_sel, bg=PANEL, fg=AMBAR,
              activebackground="#1e1e22", activeforeground=AMBAR,
              font=("Consolas", 9, "bold"), relief="raised", bd=2).pack(side="left", expand=True, fill="x", padx=(3, 0))

    # --- botones transporte (tras definir callbacks y playlist) ---
    bf = tk.Frame(bottom, bg=BG); bf.pack(side="left", pady=(6, 0))
    def btn(parent, txto, cmd, w=7):
        return tk.Button(parent, text=txto, command=cmd, width=w, bg=PANEL, fg=AMBAR,
                         activebackground="#1e1e22", activeforeground=AMBAR,
                         font=("Consolas", 11, "bold"), relief="raised", bd=2)
    def play_sel():
        sel = pl.curselection()
        if sel: tocar(pl.get(sel[0]))
    btn(bf, "|<", anterior).pack(side="left", padx=2)
    btn(bf, ">", play_sel).pack(side="left", padx=2)
    btn(bf, "||", pausar).pack(side="left", padx=2)
    btn(bf, "[]", detener).pack(side="left", padx=2)
    btn(bf, ">|", lambda: siguiente()).pack(side="left", padx=2)
    btn(bf, "[ ]", toggle_fs).pack(side="left", padx=2)
    btn(bf, "+", agregar).pack(side="left", padx=2)
    btn(bf, "M", alternar_mute, w=4).pack(side="left", padx=2)
    # Doble-click via hook de sistema (los binds Tk no reciben los clicks que
    # caen en la subventana de video Direct3D). Mecanismo unico para no alternar doble.
    def rect_video():
        try:
            return (lienzo.winfo_rootx(), lienzo.winfo_rooty(),
                    lienzo.winfo_rootx() + lienzo.winfo_width(),
                    lienzo.winfo_rooty() + lienzo.winfo_height())
        except Exception:
            return None

    def rect_root():
        try:
            return (root.winfo_rootx(), root.winfo_rooty(),
                    root.winfo_rootx() + root.winfo_width(),
                    root.winfo_rooty() + root.winfo_height())
        except Exception:
            return None

    def punto_dentro(x, y):
        r = rect_root() if estado["fs"] is not None else rect_video()
        return bool(r) and r[0] <= x <= r[2] and r[1] <= y <= r[3]

    gancho = GanchoDobleClick(punto_dentro, toggle_fs, lambda fn: root.after(0, fn))
    gancho.instalar()
    root.bind("<F11>", lambda e: toggle_fs())
    root.bind("<Escape>", lambda e: salir_fs() if estado["fs"] is not None else None)
    root.bind("<space>", lambda e: pausar())
    root.bind("m", lambda e: alternar_mute())
    root.bind("s", lambda e: foto())
    root.bind("f", lambda e: toggle_fs())
    root.bind("n", lambda e: siguiente())
    root.bind("p", lambda e: anterior())

    # --- barra de menus (funciones del original absorbidas) ---
    var_mute = tk.BooleanVar(value=False)
    var_rate = tk.StringVar(value="1.0x")
    var_repeat = tk.StringVar(value="no")
    var_shuffle = tk.BooleanVar(value=False)
    barra = tk.Menu(root)
    m_arch = tk.Menu(barra, tearoff=0)
    m_arch.add_command(label="Abrir archivos...", command=agregar)
    m_arch.add_command(label="Guardar snapshot", command=foto)
    m_arch.add_separator()
    m_arch.add_command(label="Salir", command=lambda: al_cerrar())
    barra.add_cascade(label="Archivo", menu=m_arch)
    m_rep = tk.Menu(barra, tearoff=0)
    m_vel = tk.Menu(m_rep, tearoff=0)
    for r in (0.5, 0.75, 1.0, 1.25, 1.5, 2.0):
        m_vel.add_radiobutton(label=f"{r}x", variable=var_rate, value=f"{r}x",
                              command=lambda v=r: poner_velocidad(v))
    m_rep.add_cascade(label="Velocidad", menu=m_vel)
    m_rep.add_separator()
    for val, nom in (("no", "No repetir"), ("todo", "Repetir todo"), ("uno", "Repetir una")):
        m_rep.add_radiobutton(label=nom, variable=var_repeat, value=val,
                              command=lambda v=val: estado.update(repeat=v))
    m_rep.add_checkbutton(label="Aleatorio", variable=var_shuffle,
                          command=lambda: estado.update(shuffle=var_shuffle.get()))
    barra.add_cascade(label="Reproducción", menu=m_rep)
    m_aud = tk.Menu(barra, tearoff=0)
    menu_audio_pista = tk.Menu(m_aud, tearoff=0)
    m_aud.add_cascade(label="Pista", menu=menu_audio_pista)
    m_aud.add_checkbutton(label="Silenciar", variable=var_mute, command=alternar_mute)
    m_eq = tk.Menu(m_aud, tearoff=0)
    m_eq.add_command(label="Desactivado", command=lambda: poner_eq(None))
    for i, nom in enumerate(engine.eq_preset_names()):
        m_eq.add_command(label=nom, command=lambda v=i: poner_eq(v))
    m_aud.add_cascade(label="Ecualizador", menu=m_eq)
    barra.add_cascade(label="Audio", menu=m_aud)
    m_vid = tk.Menu(barra, tearoff=0)
    m_vid.add_command(label="Pantalla completa", command=toggle_fs)
    m_asp = tk.Menu(m_vid, tearoff=0)
    for a in ("Default", "16:9", "4:3", "1:1"):
        m_asp.add_command(label=a, command=lambda v=a: poner_aspecto(v))
    m_vid.add_cascade(label="Aspecto", menu=m_asp)
    m_vid.add_command(label="Guardar snapshot", command=foto)
    barra.add_cascade(label="Video", menu=m_vid)
    m_sub = tk.Menu(barra, tearoff=0)
    menu_spu = tk.Menu(m_sub, tearoff=0)
    m_sub.add_cascade(label="Pista", menu=menu_spu)
    m_sub.add_command(label="Cargar archivo...", command=cargar_sub)
    barra.add_cascade(label="Subtítulos", menu=m_sub)
    m_ayu = tk.Menu(barra, tearoff=0)
    m_ayu.add_command(label="Info del medio", command=lambda: info_medio())
    m_ayu.add_command(label="Acerca de", command=lambda: messagebox.showinfo(
        TITLE, f"{TITLE} {VERSION}\nClon de VLC 3.0.24, motor libvlc.\nInterfaz propia estilo Winamp."))
    barra.add_cascade(label="Ayuda", menu=m_ayu)
    root.config(menu=barra)

    # --- volumen ---
    vf = tk.Frame(bottom, bg=BG); vf.pack(side="right", pady=(6, 0))
    tk.Label(vf, text="VOL", bg=BG, fg=GRIS, font=("Consolas", 9, "bold")).pack(side="left", padx=(0, 4))
    vol = tk.Scale(vf, from_=0, to=100, orient="horizontal", showvalue=True, bg=BG, fg=TXT,
                   troughcolor=PANEL, highlightthickness=0, length=170)
    vol.set(80); vol.pack(side="left")

    def on_vol(_=None):
        engine._vol = vol.get()
        if engine.player: engine.lib.libvlc_audio_set_volume(engine.player, vol.get())
    vol.config(command=on_vol)

    def on_seek(_=None):
        if engine.player and not estado["seek_lock"]:
            L = engine.lib
            dur = L.libvlc_media_player_get_length(engine.player)
            if dur > 0: L.libvlc_media_player_set_time(engine.player, int(seek.get() / 1000 * dur))
    seek.bind("<ButtonRelease-1>", on_seek)

    def scroll():
        t = disp.itemcget(txt_track, "text")
        if len(t) > 70 and estado["tocando"]:
            disp.itemconfig(txt_track, text=t[1:] + t[0])

    def tick():
        scroll()
        L = engine.lib
        if engine.player and engine.player:
            try:
                playing = L.libvlc_media_player_is_playing(engine.player)
                t = L.libvlc_media_player_get_time(engine.player)
                dur = L.libvlc_media_player_get_length(engine.player)
            except Exception as ex:
                log("ERROR tick:", ex)
                root.after(250, tick)
                return
            tick.n = getattr(tick, "n", 0) + 1
            if tick.n % 8 == 0:
                log(f"tick playing={playing} t={t} dur={dur} ruta={estado['ruta']}")
            if dur > 0:
                estado["seek_lock"] = True
                seek.set(int(t / dur * 1000))
                estado["seek_lock"] = False
                disp.itemconfig(txt_time, text=f"{fmt(t)} / {fmt(dur)}")
                if not estado.get("tracks_built"):
                    reconstruir_pistas()
            for i, b in enumerate(bars):
                h = random.randint(2, 52) if playing else 2
                x0 = 14 + i * 26
                disp.coords(b, x0, 90, x0 + 18, 90 - h)
            if playing:
                estado["tocando"] = True
                estado["sonando"] = True
            elif estado["sonando"] and not playing:
                # la pista sono y termino -> que sigue depende de repetir/aleatorio
                estado["sonando"] = False
                if estado["ruta"]: guardar(estado["ruta"], 0)
                if estado.get("repeat") == "uno" and estado["ruta"]:
                    tocar(estado["ruta"])
                elif estado.get("shuffle"):
                    pista_aleatoria()
                else:
                    siguiente(auto=True)
        root.after(250, tick)

    for a in arranque: pl.insert("end", a)
    if arranque:
        root.update_idletasks()
        tocar(arranque[0])
    root.after(250, tick)

    def al_cerrar():
        log("CIERRE ventana (al_cerrar)")
        try: gancho.desinstalar()
        except Exception: pass
        try:
            root.attributes("-fullscreen", False)
        except Exception: pass
        try:
            if engine.player and estado["ruta"]:
                t = engine.lib.libvlc_media_player_get_time(engine.player)
                if t > 5000: guardar(estado["ruta"], t / 1000.0)
        except Exception: pass
        try: engine.cerrar_player()
        except Exception: pass
        try: engine.lib.libvlc_release(engine.inst)
        except Exception: pass
        root.destroy()
    root.protocol("WM_DELETE_WINDOW", al_cerrar)
    root.mainloop()

if __name__ == "__main__":
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    if any(x in ("--version", "-v") for x in sys.argv[1:]):
        log(f"{TITLE} {VERSION} (clon de VLC 3.0.24, motor libvlc)"); sys.exit(0)
    if "--selftest" in sys.argv[1:]:
        # prueba headless verificable: reproduce 8s y reporta avance real de tiempo
        f = sys.argv[sys.argv.index("--selftest") + 1]
        e = LibVLC()
        ok = e.abrir(f, None, 0)
        log("abrir:", ok)
        ini = e.lib.libvlc_media_player_get_time(e.player) if ok else -1
        time.sleep(8)
        fin = e.lib.libvlc_media_player_get_time(e.player) if ok else -1
        sonando = e.lib.libvlc_media_player_is_playing(e.player) if ok else 0
        log(f"t_ini={ini} t_fin={fin} playing={sonando}")
        r = 0 if (ok and fin > ini) else 1
        log("SELFTEST:", "OK" if r == 0 else "FAIL")
        sys.exit(r)
    if "--uitest" in sys.argv[1:]:
        # prueba UI verificable en hilo principal: abre video, entra/sale de
        # fullscreen (oculta/muestra UI sin mover el hwnd), verifica doble-click
        # real del SO via GanchoDobleClick y que sigue sonando
        import tkinter as tk
        f = sys.argv[sys.argv.index("--uitest") + 1]
        eng = LibVLC()
        root = tk.Tk()
        disp = tk.Frame(root, height=40); disp.pack(side="top", fill="x")
        marco = tk.Frame(root, bg="#000", width=640, height=360); marco.pack(side="top", fill="both", expand=True)
        root.update_idletasks()
        hw0 = marco.winfo_id()
        st = {"fs": False}
        u32 = ctypes.windll.user32

        def rect_video():
            return (marco.winfo_rootx(), marco.winfo_rooty(),
                    marco.winfo_rootx() + marco.winfo_width(),
                    marco.winfo_rooty() + marco.winfo_height())

        def alternar():
            if st["fs"]:
                root.attributes("-fullscreen", False)
                disp.pack(side="top", fill="x")
                st["fs"] = False
            else:
                disp.pack_forget()
                root.attributes("-fullscreen", True)
                st["fs"] = True
            log(f"uitest fs={st['fs']}")

        gancho = GanchoDobleClick(lambda x, y: True, alternar, lambda fn: root.after(0, fn))
        gancho.instalar()

        def click(x, y):
            u32.SetCursorPos(x, y)
            time.sleep(0.05)
            for _ in range(2):
                u32.mouse_event(0x0002, 0, 0, 0, 0)
                time.sleep(0.03)
                u32.mouse_event(0x0004, 0, 0, 0, 0)
                time.sleep(0.08)

        def paso1():
            st["ok"] = eng.abrir(f, hw0, 0)
            root.after(3000, paso2)
        def paso2():
            st["jugando"] = eng.lib.libvlc_media_player_is_playing(eng.player)
            r = rect_video()
            cx, cy = (r[0] + r[2]) // 2, (r[1] + r[3]) // 2
            click(cx, cy)  # doble-click real del SO sobre el video
            root.after(1500, paso3)
        def paso3():
            st["fs_on"] = st["fs"]
            st["jugando_fs"] = eng.lib.libvlc_media_player_is_playing(eng.player)
            r = rect_video()
            click((r[0] + r[2]) // 2, (r[1] + r[3]) // 2)  # segundo doble-click: salir
            root.after(1500, paso4)
        def paso4():
            st["fs_off"] = not st["fs"]
            st["jugando_back"] = eng.lib.libvlc_media_player_is_playing(eng.player)
            st["t"] = eng.lib.libvlc_media_player_get_time(eng.player)
            ok = st.get("ok") and st["jugando"] and st["fs_on"] and st["jugando_fs"] \
                and st["fs_off"] and st["jugando_back"] and st["t"] > 0
            log(f"UITEST abrir={st.get('ok')} jugando={st.get('jugando')} "
                f"fs_on={st.get('fs_on')} jugando_fs={st.get('jugando_fs')} "
                f"fs_off={st.get('fs_off')} jugando_back={st.get('jugando_back')} t={st.get('t')}")
            log("UITEST:", "OK" if ok else "FAIL")
            try: gancho.desinstalar(); root.destroy()
            except Exception: pass
        root.after(500, paso1)
        root.mainloop()
        sys.exit(0)
    main(args)
