from __future__ import annotations

import json
import math
import os
import platform
import random
import subprocess
import sys
import threading
import time
from pathlib import Path

import psutil

if platform.system() == "Windows":
    _WIN_HIDE: dict = {"creationflags": subprocess.CREATE_NO_WINDOW}
else:
    _WIN_HIDE: dict = {}

from PyQt6.QtCore import (
    QEasingCurve, QMimeData, QObject, QPointF, QRectF, QSize, Qt,
    QTimer, QUrl, pyqtSignal,
)
from PyQt6.QtGui import (
    QBrush, QColor, QConicalGradient, QDragEnterEvent, QDropEvent, QFont,
    QFontDatabase, QKeySequence, QLinearGradient, QPainter, QPainterPath,
    QPen, QPixmap, QRadialGradient, QShortcut,
)
from PyQt6.QtWidgets import (
    QApplication, QFileDialog, QFrame, QHBoxLayout, QLabel, QLineEdit,
    QMainWindow, QPushButton, QScrollArea, QSizePolicy, QSplitter,
    QStackedWidget, QTextEdit, QVBoxLayout, QWidget, QProgressBar,
)

def _base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent

BASE_DIR   = _base_dir()
CONFIG_DIR = BASE_DIR / "config"
API_FILE   = CONFIG_DIR / "api_keys.json"


def _read_full_config() -> dict:
    """Read api_keys.json config dict. Returns {} on any error."""
    try:
        return json.loads(API_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


_DEFAULT_W, _DEFAULT_H = 980, 700
_MIN_W,     _MIN_H     = 820, 580
_LEFT_W  = 180
_RIGHT_W = 340

_OS = platform.system()  # "Windows" | "Darwin" | "Linux"


class C:
    BG        = "#00060a"
    PANEL     = "#000b11"
    PANEL2    = "#000d16"
    BORDER    = "#0a293a"
    BORDER_B  = "#124b64"
    BORDER_A  = "#083548"
    PRI       = "#00d4ff"
    PRI_DIM   = "#007a99"
    PRI_GHO   = "#001b28"
    ACC       = "#ff6b00"
    ACC2      = "#ffcc00"
    GREEN     = "#00ff88"
    GREEN_D   = "#00aa55"
    RED       = "#ff3355"
    MUTED_C   = "#ff3366"
    TEXT      = "#8ffcff"
    TEXT_DIM  = "#2c6c7c"
    TEXT_MED  = "#4fa8bc"
    WHITE     = "#d8f8ff"
    DARK      = "#000508"
    BAR_BG    = "#001019"



# Accent-dependent color constants — status colors remain fixed
_HUE_LINKED = (
    "BG", "PANEL", "PANEL2", "BORDER", "BORDER_B", "BORDER_A",
    "PRI", "PRI_DIM", "PRI_GHO", "TEXT", "TEXT_DIM", "TEXT_MED",
    "WHITE", "DARK", "BAR_BG",
)
_PALETTE_DEFAULTS: dict[str, str] = {k: getattr(C, k) for k in _HUE_LINKED}

DEFAULT_UI_COLOR = _PALETTE_DEFAULTS["PRI"]

_ETHNOCENTRIC_FONT: str = "Courier New"
_DS_DIGI_FONT: str = "Courier New"
_PRIMARY_FONT: str = "Courier New"
_FONTS_LOADED: bool = False


def _load_custom_fonts() -> None:
    """Loads custom fonts (Ethnocentric-Regular, DS-Digital, Source Code Pro) into QFontDatabase."""
    global _ETHNOCENTRIC_FONT, _DS_DIGI_FONT, _PRIMARY_FONT, _FONTS_LOADED
    if _FONTS_LOADED:
        return
    _FONTS_LOADED = True

    ethno_path = BASE_DIR / "Ethnocentric-Regular.otf"
    if ethno_path.exists():
        try:
            fid = QFontDatabase.addApplicationFont(str(ethno_path))
            fams = QFontDatabase.applicationFontFamilies(fid)
            if fams:
                _ETHNOCENTRIC_FONT = fams[0]
        except Exception:
            pass

    for fname in ["DS-DIGII.TTF", "DS-DIGI.TTF", "DS-DIGIB.TTF", "DS-DIGIT.TTF"]:
        fpath = BASE_DIR / fname
        if fpath.exists():
            try:
                fid = QFontDatabase.addApplicationFont(str(fpath))
                fams = QFontDatabase.applicationFontFamilies(fid)
                if fams and _DS_DIGI_FONT == "Courier New":
                    _DS_DIGI_FONT = fams[0]
            except Exception:
                pass

    scp_dir = BASE_DIR / "Source_Code_Pro"
    scp_files = [
        scp_dir / "static" / "SourceCodePro-Regular.ttf",
        scp_dir / "static" / "SourceCodePro-Bold.ttf",
        scp_dir / "SourceCodePro-VariableFont_wght.ttf",
    ]
    for scp_path in scp_files:
        if scp_path.exists():
            try:
                fid = QFontDatabase.addApplicationFont(str(scp_path))
                fams = QFontDatabase.applicationFontFamilies(fid)
                if fams and _PRIMARY_FONT == "Courier New":
                    _PRIMARY_FONT = fams[0]
            except Exception:
                pass


def apply_ui_accent(accent_hex: str) -> bool:
    """
    Re-derives accent palette dynamically based on the selected UI color.
    (hue kaydırma — parlaklık/doygunluk oranları korunur, tasarım bozulmaz).
    Rendered elements (HUD, waveform, metrics) update on the next frame.
    rengi alır; stylesheet tabanlı paneller yeniden kurulduklarında alır.
    """
    import colorsys

    accent_hex = (accent_hex or "").strip().lower()
    if not (accent_hex.startswith("#") and len(accent_hex) == 7):
        return False
    try:
        int(accent_hex[1:], 16)
    except ValueError:
        return False

    def _hsv(h: str) -> tuple[float, float, float]:
        r = int(h[1:3], 16) / 255
        g = int(h[3:5], 16) / 255
        b = int(h[5:7], 16) / 255
        return colorsys.rgb_to_hsv(r, g, b)

    base_h            = _hsv(_PALETTE_DEFAULTS["PRI"])[0]
    acc_h, acc_s, _av = _hsv(accent_hex)
    dh   = acc_h - base_h
    grey = acc_s < 0.08   # griye yakın accent → tüm tema desaturize edilir

    for key, hex0 in _PALETTE_DEFAULTS.items():
        h, s, v = _hsv(hex0)
        if grey:
            s *= 0.15
        r, g, b = colorsys.hsv_to_rgb((h + dh) % 1.0, s, v)
        setattr(C, key, "#{:02x}{:02x}{:02x}".format(
            int(r * 255 + 0.5), int(g * 255 + 0.5), int(b * 255 + 0.5)))
    return True


def current_palette() -> dict[str, str]:
    """Snapshot of accent-dependent color constants."""
    return {k: getattr(C, k) for k in _HUE_LINKED}


def retheme_all_widgets(old: dict[str, str], new: dict[str, str]) -> None:
    """
    CANLI tam tema değişimi. Uygulamadaki HER widget'ın stylesheet'inde eski
    updates palette colors dynamically across panels, buttons, borders, and controls.
    
    arayüzde ANINDA uygulanır — yeniden başlatma gerekmez.
    """
    mapping = {old[k].lower(): new[k].lower()
               for k in old if old[k].lower() != new.get(k, old[k]).lower()}
    if not mapping:
        return
    app = QApplication.instance()
    if app is None:
        return
    for w in app.allWidgets():
        try:
            ss = w.styleSheet()
            if ss:
                s2 = ss
                for o, n in mapping.items():
                    if o in s2:
                        s2 = s2.replace(o, n)
                if s2 != ss:
                    w.setStyleSheet(s2)
            w.update()
        except Exception:
            pass


def qcol(h: str, a: int = 255) -> QColor:
    c = QColor(h); c.setAlpha(a); return c


# ── Windows GPU via NVML DLL (no subprocess, no console window) ──────────────
_nvml_lib: object = None   # cached ctypes DLL
_nvml_ok:  object = None   # None=untested, True=works, False=unavailable


def _nvml_gpu_windows() -> float:
    """Return NVIDIA GPU utilisation % using nvml.dll directly — zero subprocess."""
    global _nvml_lib, _nvml_ok
    if _nvml_ok is False:
        return -1.0
    try:
        import ctypes

        class _Util(ctypes.Structure):
            _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

        if _nvml_lib is None:
            for dll_name in ("nvml", r"C:\Windows\System32\nvml.dll"):
                try:
                    lib = ctypes.WinDLL(dll_name)
                    lib.nvmlInit_v2()
                    _nvml_lib = lib
                    break
                except Exception:
                    continue

        if _nvml_lib is None:
            import pynvml  # type: ignore
            pynvml.nvmlInit()
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            _nvml_ok = True
            return float(pynvml.nvmlDeviceGetUtilizationRates(h).gpu)

        dev = ctypes.c_void_p()
        _nvml_lib.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev))
        util = _Util()
        _nvml_lib.nvmlDeviceGetUtilizationRates(dev, ctypes.byref(util))
        _nvml_ok = True
        return float(util.gpu)
    except Exception:
        _nvml_ok = False
        return -1.0


class _SysMetrics:
    def __init__(self):
        self.cpu  = 0.0
        self.mem  = 0.0
        self.net  = 0.0   
        self.gpu  = -1.0  
        self.tmp  = -1.0  
        self._lock = threading.Lock()
        self._last_net = psutil.net_io_counters()
        self._last_net_t = time.time()
        self._running = True
        t = threading.Thread(target=self._loop, daemon=True)
        t.start()

    def _loop(self):
        while self._running:
            try:
                self._update()
            except Exception:
                pass
            time.sleep(1.5)

    def _update(self):
        cpu = psutil.cpu_percent(interval=None)
        mem = psutil.virtual_memory().percent

        nc  = psutil.net_io_counters()
        now = time.time()
        dt  = now - self._last_net_t
        if dt > 0:
            sent = (nc.bytes_sent - self._last_net.bytes_sent) / dt
            recv = (nc.bytes_recv - self._last_net.bytes_recv) / dt
            net  = (sent + recv) / (1024 * 1024)
        else:
            net = 0.0
        self._last_net   = nc
        self._last_net_t = now

        gpu = self._get_gpu()

        tmp = self._get_temp()

        with self._lock:
            self.cpu = cpu
            self.mem = mem
            self.net = net
            self.gpu = gpu
            self.tmp = tmp

    def _get_gpu(self) -> float:
        # pynvml — subprocess-free, works on all platforms if installed
        try:
            import pynvml  # type: ignore
            pynvml.nvmlInit()
            h = pynvml.nvmlDeviceGetHandleByIndex(0)
            return float(pynvml.nvmlDeviceGetUtilizationRates(h).gpu)
        except Exception:
            pass

        # Windows: nvml.dll via ctypes (already cached in _nvml_gpu_windows)
        if _OS == "Windows":
            return _nvml_gpu_windows()

        # Linux / macOS: libnvidia-ml shared lib via ctypes
        try:
            import ctypes
            _lib = "libnvidia-ml.so.1" if _OS == "Linux" else "libnvidia-ml.dylib"

            class _Util(ctypes.Structure):
                _fields_ = [("gpu", ctypes.c_uint), ("memory", ctypes.c_uint)]

            nv = ctypes.CDLL(_lib)
            nv.nvmlInit_v2()
            dev = ctypes.c_void_p()
            nv.nvmlDeviceGetHandleByIndex_v2(0, ctypes.byref(dev))
            u = _Util()
            nv.nvmlDeviceGetUtilizationRates(dev, ctypes.byref(u))
            return float(u.gpu)
        except Exception:
            pass

        return -1.0   # N/A — zero subprocess on all platforms

    def _get_temp(self) -> float:
        # psutil — works on Linux; occasionally Windows with driver support
        try:
            temps = psutil.sensors_temperatures()
            for name in ["coretemp", "k10temp", "cpu_thermal", "acpitz",
                         "cpu-thermal", "zenpower", "it8688"]:
                if name in temps and temps[name]:
                    return temps[name][0].current
            for entries in temps.values():
                if entries:
                    return entries[0].current
        except Exception:
            pass

        # Windows: wmi module (pure Python COM, zero subprocess)
        if _OS == "Windows":
            try:
                import wmi  # type: ignore
                w = wmi.WMI(namespace="root/wmi")
                tz = w.MSAcpi_ThermalZoneTemperature()
                if tz:
                    return (tz[0].CurrentTemperature / 10.0) - 273.15
            except Exception:
                pass

        return -1.0   # N/A — zero subprocess on all platforms

    def snapshot(self) -> dict:
        with self._lock:
            return {
                "cpu": self.cpu,
                "mem": self.mem,
                "net": self.net,
                "gpu": self.gpu,
                "tmp": self.tmp,
            }


_metrics = _SysMetrics()

class HudCanvas(QWidget):
    def __init__(self, face_path: str, assistant_name: str = "J.A.R.V.I.S", parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent)
        self.setMinimumSize(300, 300)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.muted    = False
        self.speaking = False
        self.state    = "INITIALISING"
        self._assistant_name = assistant_name

        self._tick       = 0
        self._scale      = 1.0
        self._tgt_scale  = 1.0
        self._halo       = 55.0
        self._tgt_halo   = 55.0
        self._last_t     = time.time()
        self._scan       = 0.0
        self._scan2      = 180.0
        self._rings      = [0.0, 120.0, 240.0]
        self._pulses: list[float] = [0.0, 50.0, 100.0]
        self._blink      = True
        self._blink_tick = 0
        self._particles: list[list[float]] = []
        self._face_px: QPixmap | None = None
        self._load_face(face_path)

        # Load custom fonts
        _load_custom_fonts()
        self._custom_font_family = _ETHNOCENTRIC_FONT

        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._tmr.start(16)

    def _load_face(self, path: str):
        try:
            from PIL import Image, ImageDraw
            import io
            img = Image.open(path).convert("RGBA")
            sz  = min(img.size)
            img = img.resize((sz, sz), Image.LANCZOS)
            mk  = Image.new("L", (sz, sz), 0)
            ImageDraw.Draw(mk).ellipse((2, 2, sz - 2, sz - 2), fill=255)
            img.putalpha(mk)
            buf = io.BytesIO()
            img.save(buf, format="PNG")
            px = QPixmap(); px.loadFromData(buf.getvalue())
            self._face_px = px
        except Exception:
            self._face_px = None

    def _step(self):
        self._tick += 1
        now = time.time()
        if now - self._last_t > (0.12 if self.speaking else 0.5):
            if self.speaking:
                self._tgt_scale = random.uniform(1.06, 1.14)
                self._tgt_halo  = random.uniform(145, 190)
            elif self.muted:
                self._tgt_scale = random.uniform(0.998, 1.002)
                self._tgt_halo  = random.uniform(15, 28)
            else:
                self._tgt_scale = random.uniform(1.001, 1.008)
                self._tgt_halo  = random.uniform(48, 68)
            self._last_t = now

        sp = 0.38 if self.speaking else 0.15
        self._scale += (self._tgt_scale - self._scale) * sp
        self._halo  += (self._tgt_halo  - self._halo)  * sp

        speeds = [1.3, -0.9, 2.0] if self.speaking else [0.55, -0.35, 0.9]
        for i, spd in enumerate(speeds):
            self._rings[i] = (self._rings[i] + spd) % 360

        self._scan  = (self._scan  + (3.0 if self.speaking else 1.3)) % 360
        self._scan2 = (self._scan2 + (-2.0 if self.speaking else -0.75)) % 360

        fw  = min(self.width(), self.height())
        lim = fw * 0.74
        spd = 4.2 if self.speaking else 2.0
        self._pulses = [r + spd for r in self._pulses if r + spd < lim]
        if len(self._pulses) < 3 and random.random() < (0.07 if self.speaking else 0.025):
            self._pulses.append(0.0)

        if self.speaking and random.random() < 0.28:
            cx, cy = self.width() / 2, self.height() / 2
            ang = random.uniform(0, 2 * math.pi)
            r_s = fw * 0.28
            self._particles.append([
                cx + math.cos(ang) * r_s, cy + math.sin(ang) * r_s,
                math.cos(ang) * random.uniform(0.9, 2.4),
                math.sin(ang) * random.uniform(0.9, 2.4) - 0.4, 1.0,
            ])
        self._particles = [
            [p[0]+p[2], p[1]+p[3], p[2]*0.97, p[3]*0.97, p[4]-0.028]
            for p in self._particles if p[4] > 0
        ]

        self._blink_tick += 1
        if self._blink_tick >= 38:
            self._blink = not self._blink
            self._blink_tick = 0
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), qcol(C.BG))

        W, H = self.width(), self.height()
        cx, cy = W / 2, H / 2
        fw = min(W, H)

        # Base colors based on muted state
        pri_col = C.MUTED_C if self.muted else C.PRI
        acc_col = C.MUTED_C if self.muted else C.ACC
        acc2_col = C.MUTED_C if self.muted else C.ACC2

        # 1. Blueprint Background (Grid & Tech Drawings)
        # Grid lines
        p.setPen(QPen(qcol(pri_col, 15), 1))
        for x in range(0, W, 32):
            p.drawLine(x, 0, x, H)
        for y in range(0, H, 32):
            p.drawLine(0, y, W, y)

        # Tech labels and alignment lines (Blueprint-style)
        p.setPen(QPen(qcol(pri_col, 50), 1))
        p.setFont(QFont(_PRIMARY_FONT, 7))
        p.drawText(QRectF(15, 15, 200, 20), Qt.AlignmentFlag.AlignLeft, "TOP SECRET CLEARANCE")
        p.drawText(QRectF(15, 30, 200, 20), Qt.AlignmentFlag.AlignLeft, "SYS_STATUS: ACTIVE")
        p.drawText(QRectF(W - 150, H - 45, 135, 15), Qt.AlignmentFlag.AlignRight, "Cu  Sc  At  Zn  No")
        p.drawText(QRectF(W - 150, H - 30, 135, 15), Qt.AlignmentFlag.AlignRight, "HUD_CONSOLE_V4.9")

        # Alignment circles (very faint)
        p.setPen(QPen(qcol(pri_col, 20), 1, Qt.PenStyle.DashLine))
        for r_factor in [0.48, 0.46, 0.28]:
            r_align = fw * r_factor
            p.drawEllipse(QRectF(cx - r_align, cy - r_align, r_align * 2, r_align * 2))

        # Thin line-based crosshairs
        ch_r = fw * 0.49
        p.setPen(QPen(qcol(pri_col, 30), 1))
        p.drawLine(QPointF(cx - ch_r, cy), QPointF(cx - fw * 0.15, cy))
        p.drawLine(QPointF(cx + fw * 0.15, cy), QPointF(cx + ch_r, cy))
        p.drawLine(QPointF(cx, cy - ch_r), QPointF(cx, cy - fw * 0.15))
        p.drawLine(QPointF(cx, cy + fw * 0.15), QPointF(cx, cy + ch_r))

        # 2. Outer Segmented Tick Ring
        p.setPen(QPen(qcol(pri_col, 100), 1))
        r_out_tick = fw * 0.44
        r_in_tick = fw * 0.42
        for deg in range(0, 360, 4):
            if (deg // 30) % 3 == 0:
                continue
            rad = math.radians(deg)
            p.drawLine(
                QPointF(cx + r_in_tick * math.cos(rad), cy - r_in_tick * math.sin(rad)),
                QPointF(cx + r_out_tick * math.cos(rad), cy - r_out_tick * math.sin(rad))
            )

        # 3. Outer Thin Circular Frame
        p.setPen(QPen(qcol(pri_col, 180), 1.5))
        r_outer_frame = fw * 0.442
        p.drawEllipse(QRectF(cx - r_outer_frame, cy - r_outer_frame, r_outer_frame * 2, r_outer_frame * 2))

        # 4. Thick Cyan Segmented Ring
        r_thick_ring = fw * 0.39
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.setPen(QPen(qcol(pri_col, 150), 14, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        for offset in [0, 120, 240]:
            angle = (self._rings[0] + offset) % 360
            p.drawArc(QRectF(cx - r_thick_ring, cy - r_thick_ring, r_thick_ring * 2, r_thick_ring * 2),
                      int(angle * 16), int(70 * 16))

        # Thick ring inner line highlight
        p.setPen(QPen(qcol(C.WHITE if not self.muted else C.MUTED_C, 220), 1.5))
        r_thick_inner_line = r_thick_ring + 7
        p.drawArc(QRectF(cx - r_thick_inner_line, cy - r_thick_inner_line, r_thick_inner_line * 2, r_thick_inner_line * 2),
                  int(self._rings[0] * 16), int(120 * 16))

        # 5. Yellow/Orange Indicator Arc (Left Side)
        r_yellow_arc = fw * 0.39
        p.setPen(QPen(qcol(acc2_col, 220), 6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.FlatCap))
        p.drawArc(QRectF(cx - r_yellow_arc, cy - r_yellow_arc, r_yellow_arc * 2, r_yellow_arc * 2),
                  int(135 * 16), int(90 * 16))

        # Yellow arc inner tick lines
        p.setPen(QPen(qcol(acc2_col, 180), 1))
        r_yellow_ticks_outer = r_yellow_arc - 3
        r_yellow_ticks_inner = r_yellow_arc - 10
        for deg in range(135, 226, 3):
            rad = math.radians(deg)
            p.drawLine(
                QPointF(cx + r_yellow_ticks_inner * math.cos(rad), cy - r_yellow_ticks_inner * math.sin(rad)),
                QPointF(cx + r_yellow_ticks_outer * math.cos(rad), cy - r_yellow_ticks_outer * math.sin(rad))
            )

        # 6. Yellow Indicator Dots (Top of the ring)
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(qcol(acc2_col, 255)))
        dot_r = fw * 0.355
        for deg in [75, 82, 90, 98, 105]:
            rad = math.radians(deg)
            dx = cx + dot_r * math.cos(rad)
            dy = cy - dot_r * math.sin(rad)
            p.drawEllipse(QPointF(dx, dy), 3, 3)

        # 7. Concentric Rings & Dynamic Scanners
        sr = fw * 0.35
        sa = min(255, int(self._halo * 1.5))
        ex = 75 if self.speaking else 44
        p.setPen(QPen(qcol(acc_col, sa // 2), 2))
        p.setBrush(Qt.BrushStyle.NoBrush)
        srect = QRectF(cx - sr, cy - sr, sr * 2, sr * 2)
        p.drawArc(srect, int(self._scan * 16), int(ex * 16))
        p.setPen(QPen(qcol(pri_col, sa), 1.5))
        p.drawArc(srect, int(self._scan2 * 16), int(ex * 16))

        # Pulse rings (expanding active circles)
        for pr in self._pulses:
            a = max(0, int(180 * (1.0 - pr / (fw * 0.74))))
            p.setPen(QPen(qcol(pri_col, a), 1.5))
            p.drawEllipse(QRectF(cx - pr, cy - pr, pr * 2, pr * 2))

        # 8. Inner J.A.R.V.I.S Dial/Circle
        r_face = fw * 0.28
        for i in range(5):
            r = r_face * (1.2 - i * 0.04)
            frc = 1.0 - i / 5
            a = max(0, min(255, int(self._halo * 0.08 * frc)))
            p.setPen(QPen(qcol(pri_col, a), 1.5))
            p.drawEllipse(QRectF(cx - r, cy - r, r * 2, r * 2))

        # Inner dial circular frame
        p.setPen(QPen(qcol(pri_col, 200), 1.5))
        p.drawEllipse(QRectF(cx - r_face, cy - r_face, r_face * 2, r_face * 2))

        # Inner dial small ticks
        p.setPen(QPen(qcol(pri_col, 120), 1))
        r_inner_ticks_out = r_face
        r_inner_ticks_in = r_face - 5
        for deg in range(0, 360, 6):
            rad = math.radians(deg)
            p.drawLine(
                QPointF(cx + r_inner_ticks_in * math.cos(rad), cy - r_inner_ticks_in * math.sin(rad)),
                QPointF(cx + r_inner_ticks_out * math.cos(rad), cy - r_inner_ticks_out * math.sin(rad))
            )

        # 9. Center Face image OR Fallback Jarvis Orb
        if self._face_px:
            fsz = int(fw * 0.52 * self._scale)
            scaled = self._face_px.scaled(
                fsz, fsz,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            p.drawPixmap(int(cx - fsz / 2), int(cy - fsz / 2), scaled)
        else:
            orb_r = int(fw * 0.22 * self._scale)
            oc = (200, 0, 50) if self.muted else (0, 60, 110)
            for i in range(8, 0, -1):
                r2 = int(orb_r * i / 8)
                frc = i / 8
                a = max(0, min(255, int(self._halo * 1.1 * frc)))
                p.setBrush(QBrush(QColor(int(oc[0] * frc), int(oc[1] * frc), int(oc[2] * frc), a)))
                p.setPen(Qt.PenStyle.NoPen)
                p.drawEllipse(QRectF(cx - r2, cy - r2, r2 * 2, r2 * 2))

            p.setPen(QPen(qcol(C.WHITE if not self.muted else C.MUTED_C, min(255, int(self._halo * 2.5))), 1.5))
            p.setFont(QFont(self._custom_font_family, 20, QFont.Weight.Bold))
            disp_name = "J.A.R.V.I.S." if self._assistant_name.upper() == "JARVIS" else self._assistant_name
            p.drawText(QRectF(cx - 150, cy - 22, 300, 44),
                       Qt.AlignmentFlag.AlignCenter, disp_name)

        # 10. Particles
        for pt in self._particles:
            a = max(0, min(255, int(pt[4] * 255)))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QBrush(qcol(pri_col, a)))
            p.drawEllipse(QPointF(pt[0], pt[1]), 2.5, 2.5)

        # Pedestal / Base Platform under the dial
        p.setPen(QPen(qcol(pri_col, 80), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        ped_y = cy + fw * 0.38
        for i in range(5):
            rx = fw * (0.28 - i * 0.04)
            ry = fw * (0.07 - i * 0.01)
            p.drawEllipse(QRectF(cx - rx, ped_y - ry, rx * 2, ry * 2))

class MetricBar(QWidget):

    def __init__(self, label: str, color: str = C.PRI, parent=None):
        super().__init__(parent)
        self._label = label
        self._color = color
        self._value = 0.0       # 0–100
        self._text  = "--"
        self.setFixedHeight(38)
        self.setMinimumWidth(80)

    def set_value(self, pct: float, text: str):
        self._value = max(0.0, min(100.0, pct))
        self._text  = text
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()

        p.setBrush(QBrush(qcol(C.PANEL2)))
        p.setPen(QPen(qcol(C.BORDER_A), 1))
        p.drawRoundedRect(QRectF(1, 1, W - 2, H - 2), 4, 4)

        bar_h   = 4
        bar_y   = H - bar_h - 5
        bar_w   = W - 12
        bar_x   = 6
        fill_w  = int(bar_w * self._value / 100)

        p.setBrush(QBrush(qcol(C.BAR_BG)))
        p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(QRectF(bar_x, bar_y, bar_w, bar_h), 2, 2)

        if self._value > 85:
            bar_col = qcol(C.RED)
        elif self._value > 65:
            bar_col = qcol(C.ACC)
        else:
            bar_col = qcol(self._color)

        if fill_w > 0:
            p.setBrush(QBrush(bar_col))
            p.drawRoundedRect(QRectF(bar_x, bar_y, fill_w, bar_h), 2, 2)

        p.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(8, 5, 50, 14), Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, self._label)

        p.setFont(QFont(_PRIMARY_FONT, 9, QFont.Weight.Bold))
        p.setPen(QPen(bar_col if self._text != "--" else qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(0, 4, W - 6, 16), Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter, self._text)

class LogWidget(QTextEdit):
    _sig = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setReadOnly(True)
        self.setFont(QFont(_PRIMARY_FONT, 9))
        self.setStyleSheet(f"""
            QTextEdit {{
                background: {C.PANEL};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 4px;
                padding: 6px;
                selection-background-color: {C.PRI_GHO};
            }}
            QScrollBar:vertical {{
                background: {C.BG};
                width: 8px;
                border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_B};
                border-radius: 4px;
                min-height: 20px;
            }}
        """)
        self._queue: list[str] = []
        self._typing  = False
        self._text    = ""
        self._pos     = 0
        self._tag     = "sys"
        self._ai_name_lc = "jarvis"   # updated when assistant name changes
        self._tmr = QTimer(self)
        self._tmr.timeout.connect(self._step)
        self._sig.connect(self._enqueue)

    def append_log(self, text: str):
        self._sig.emit(text)

    def _enqueue(self, text: str):
        self._queue.append(text)
        if not self._typing:
            self._next()

    def _next(self):
        if not self._queue:
            self._typing = False
            return
        self._typing = True
        self._text   = self._queue.pop(0)
        self._pos    = 0
        tl = self._text.lower()
        _ai_pfx = f"{self._ai_name_lc}:"
        if   tl.startswith("you:"):                              self._tag = "you"
        elif tl.startswith(_ai_pfx) or tl.startswith("jarvis:"): self._tag = "ai"
        elif tl.startswith("file:"):                             self._tag = "file"
        elif "err" in tl:                                        self._tag = "err"
        else:                                                    self._tag = "sys"
        self._tmr.start(6)

    def _step(self):
        if self._pos < len(self._text):
            ch  = self._text[self._pos]
            cur = self.textCursor()
            fmt = cur.charFormat()
            col = {
                "you":  qcol(C.WHITE),
                "ai":   qcol(C.PRI),
                "err":  qcol(C.RED),
                "file": qcol(C.GREEN),
                "sys":  qcol(C.ACC2),
            }.get(self._tag, qcol(C.TEXT))
            fmt.setForeground(QBrush(col))
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText(ch, fmt)
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            self._pos += 1
        else:
            self._tmr.stop()
            cur = self.textCursor()
            cur.movePosition(cur.MoveOperation.End)
            cur.insertText("\n")
            self.setTextCursor(cur)
            self.ensureCursorVisible()
            QTimer.singleShot(20, self._next)

_FILE_ICONS = {
    "image":   ("🖼", "#00d4ff"), "video":   ("🎬", "#ff6b00"),
    "audio":   ("🎵", "#cc44ff"), "pdf":     ("📄", "#ff4444"),
    "word":    ("📝", "#4488ff"), "excel":   ("📊", "#44bb44"),
    "code":    ("💻", "#ffcc00"), "archive": ("📦", "#ff8844"),
    "pptx":    ("📊", "#ff6622"), "text":    ("📃", "#aaaaaa"),
    "data":    ("🔧", "#88ddff"), "unknown": ("📎", "#888888"),
}
_EXT_TO_CAT = {
    **dict.fromkeys(["jpg","jpeg","png","gif","webp","bmp","tiff","svg","ico"], "image"),
    **dict.fromkeys(["mp4","avi","mov","mkv","wmv","flv","webm","m4v"],         "video"),
    **dict.fromkeys(["mp3","wav","ogg","m4a","aac","flac","wma","opus"],        "audio"),
    **dict.fromkeys(["pdf"],                                                     "pdf"),
    **dict.fromkeys(["doc","docx"],                                              "word"),
    **dict.fromkeys(["xls","xlsx","ods"],                                        "excel"),
    **dict.fromkeys(["ppt","pptx"],                                              "pptx"),
    **dict.fromkeys(["py","js","ts","jsx","tsx","html","css","java","c","cpp",
                     "cs","go","rs","rb","php","swift","kt","sh","sql","lua"],   "code"),
    **dict.fromkeys(["zip","rar","tar","gz","7z","bz2","xz"],                   "archive"),
    **dict.fromkeys(["txt","md","rst","log"],                                    "text"),
    **dict.fromkeys(["csv","tsv","json","xml"],                                  "data"),
}

def _file_category(path: Path) -> str:
    return _EXT_TO_CAT.get(path.suffix.lower().lstrip("."), "unknown")

def _fmt_size(size: int) -> str:
    if   size < 1024:    return f"{size} B"
    elif size < 1024**2: return f"{size/1024:.1f} KB"
    elif size < 1024**3: return f"{size/1024**2:.1f} MB"
    else:                return f"{size/1024**3:.1f} GB"


class FileDropZone(QWidget):
    file_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAcceptDrops(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFixedHeight(34)
        self._current_file: str | None = None
        self._hovering  = False
        self._drag_over = False
        self._dash_offset = 0.0
        self._anim_tmr = QTimer(self)
        self._anim_tmr.timeout.connect(self._animate)
        self._anim_tmr.start(40)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self._canvas = _DropCanvas(self)
        layout.addWidget(self._canvas)

    def _animate(self):
        self._dash_offset = (self._dash_offset + 0.8) % 20
        self._canvas.update()

    def dragEnterEvent(self, e: QDragEnterEvent):
        if e.mimeData().hasUrls():
            e.acceptProposedAction()
            self._drag_over = True; self._canvas.update()

    def dragLeaveEvent(self, e):
        self._drag_over = False; self._canvas.update()

    def dropEvent(self, e: QDropEvent):
        self._drag_over = False
        urls = e.mimeData().urls()
        if urls:
            path = urls[0].toLocalFile()
            if Path(path).is_file():
                self._set_file(path)
        self._canvas.update()

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            self._browse()

    def enterEvent(self, e):
        self._hovering = True; self._canvas.update()

    def leaveEvent(self, e):
        self._hovering = False; self._canvas.update()

    def current_file(self) -> str | None:
        return self._current_file

    def clear_file(self):
        self._current_file = None; self._canvas.update()

    def _browse(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Select a file for JARVIS", str(Path.home()),
            "All Files (*.*);;"
            "Images (*.jpg *.jpeg *.png *.gif *.webp *.bmp *.svg);;"
            "Documents (*.pdf *.docx *.txt *.md *.pptx);;"
            "Data (*.csv *.xlsx *.json *.xml);;"
            "Code (*.py *.js *.ts *.html *.css *.java *.cpp *.go);;"
            "Audio (*.mp3 *.wav *.ogg *.m4a *.aac *.flac);;"
            "Video (*.mp4 *.avi *.mov *.mkv *.wmv *.webm);;"
            "Archives (*.zip *.rar *.tar *.gz *.7z)",
        )
        if path:
            self._set_file(path)

    def _set_file(self, path: str):
        self._current_file = path
        self._canvas.update()
        self.file_selected.emit(path)


class _DropCanvas(QWidget):
    def __init__(self, zone: FileDropZone):
        super().__init__(zone)
        self._z = zone

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        z    = self._z
        W, H = self.width(), self.height()
        pad  = 6
        rect = QRectF(pad, pad, W - pad * 2, H - pad * 2)

        bg_col = qcol("#001a24" if z._drag_over else ("#001218" if z._hovering else C.PANEL))
        p.setBrush(QBrush(bg_col)); p.setPen(Qt.PenStyle.NoPen)
        p.drawRoundedRect(rect, 6, 6)

        if z._current_file:   border_col = qcol(C.GREEN, 200)
        elif z._drag_over:    border_col = qcol(C.PRI, 230)
        elif z._hovering:     border_col = qcol(C.BORDER_B, 200)
        else:                 border_col = qcol(C.BORDER, 160)

        pen = QPen(border_col, 1.5, Qt.PenStyle.DashLine)
        pen.setDashOffset(z._dash_offset)
        p.setPen(pen); p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRoundedRect(rect, 6, 6)

        if z._current_file:   self._paint_file(p, W, H)
        elif z._drag_over:    self._paint_drag_over(p, W, H)
        else:                 self._paint_idle(p, W, H, z._hovering)

    def _paint_idle(self, p, W, H, hover):
        col = qcol(C.PRI_DIM if not hover else C.PRI)
        p.setPen(QPen(col, 2)); p.setBrush(Qt.BrushStyle.NoBrush)
        cx = 20
        cy = H / 2
        p.drawLine(QPointF(cx, cy - 5), QPointF(cx, cy + 5))
        p.drawLine(QPointF(cx - 4, cy - 1), QPointF(cx, cy - 5))
        p.drawLine(QPointF(cx + 4, cy - 1), QPointF(cx, cy - 5))
        p.drawLine(QPointF(cx - 6, cy + 5), QPointF(cx + 6, cy + 5))
        p.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.PRI_DIM if not hover else C.WHITE), 1))
        p.drawText(QRectF(36, 0, W - 46, H), Qt.AlignmentFlag.AlignVCenter | Qt.AlignmentFlag.AlignLeft,
                   "UPLOAD FILE / DROP HERE")

    def _paint_drag_over(self, p, W, H):
        p.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.PRI), 1))
        p.drawText(QRectF(0, 0, W, H), Qt.AlignmentFlag.AlignCenter, "⬇  RELEASE TO LOAD FILE")

    def _paint_file(self, p, W, H):
        path = Path(self._z._current_file)
        cat  = _file_category(path)
        icon, icon_col = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size_str = _fmt_size(path.stat().st_size)
        ext_str  = path.suffix.upper().lstrip(".") or "FILE"

        block_x, block_w = 10, 60
        p.setFont(QFont("Segoe UI Emoji", 22) if _OS == "Windows" else QFont("Arial", 22))
        p.setPen(QPen(qcol(icon_col), 1))
        p.drawText(QRectF(block_x, 0, block_w, H), Qt.AlignmentFlag.AlignCenter, icon)

        tx = block_x + block_w + 6
        tw = W - tx - 38

        p.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.WHITE), 1))
        name = path.name if len(path.name) <= 34 else path.name[:31] + "..."
        p.drawText(QRectF(tx, H * 0.18, tw, 16),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, name)

        p.setFont(QFont(_PRIMARY_FONT, 7))
        p.setPen(QPen(qcol(C.TEXT_DIM), 1))
        p.drawText(QRectF(tx, H * 0.18 + 18, tw, 14),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter,
                   f"{ext_str}  ·  {size_str}")

        p.setFont(QFont(_PRIMARY_FONT, 6))
        p.setPen(QPen(qcol("#1e5c6a"), 1))
        par = str(path.parent)
        if len(par) > 42: par = "…" + par[-41:]
        p.drawText(QRectF(tx, H * 0.18 + 34, tw, 12),
                   Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter, par)

        p.setFont(QFont(_PRIMARY_FONT, 9, QFont.Weight.Bold))
        p.setPen(QPen(qcol(C.RED, 180), 1))
        p.drawText(QRectF(W - 34, 0, 28, H), Qt.AlignmentFlag.AlignCenter, "✕")

    def mousePressEvent(self, e):
        z = self._z
        if z._current_file and e.pos().x() > self.width() - 34:
            z.clear_file()
        else:
            z.mousePressEvent(e)


class _CameraPreview(QWidget):
    """Floating overlay that briefly shows what the camera captured."""

    _W, _H = 244, 188

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            _CameraPreview {{
                background: rgba(0, 6, 10, 242);
                border: 1px solid {C.PRI};
                border-radius: 6px;
            }}
        """)
        self.setFixedWidth(self._W)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 5, 6, 6)
        lay.setSpacing(4)

        hdr = QHBoxLayout()
        title = QLabel("◈  VISUAL INPUT")
        title.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        hdr.addWidget(title)
        hdr.addStretch()
        close_btn = QPushButton("✕")
        close_btn.setFixedSize(16, 16)
        close_btn.setFont(QFont(_PRIMARY_FONT, 8))
        close_btn.setStyleSheet(
            f"color: {C.TEXT_DIM}; background: transparent; border: none;"
        )
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.clicked.connect(self.hide)
        hdr.addWidget(close_btn)
        lay.addLayout(hdr)

        self._img_lbl = QLabel()
        self._img_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._img_lbl.setStyleSheet("background: transparent;")
        lay.addWidget(self._img_lbl)

        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.hide)

        self.hide()

    def show_frame(self, img_bytes: bytes) -> None:
        px = QPixmap()
        px.loadFromData(img_bytes)
        if not px.isNull():
            max_w = self._W - 12
            scaled = px.scaled(
                max_w, 160,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._img_lbl.setPixmap(scaled)
            self._img_lbl.setFixedSize(scaled.width(), scaled.height())
            self.adjustSize()
        self.show()
        self.raise_()
        self._timer.start(6_000)   # auto-dismiss after 6 s


class SetupOverlay(QWidget):
    done = pyqtSignal(str, str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            SetupOverlay {{
                background: rgba(0, 6, 10, 245);
                border: 1px solid {C.BORDER_B};
                border-radius: 6px;
            }}
        """)

        detected = {"darwin": "mac", "windows": "windows"}.get(
            _OS.lower(), "linux"
        )
        self._sel_os = detected

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 22, 30, 22)
        layout.setSpacing(8)

        def _lbl(txt, font_size=9, bold=False, color=C.PRI,
                 align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont(_PRIMARY_FONT, font_size,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        hdr_row = QHBoxLayout()
        hdr_title_v = QVBoxLayout()
        hdr_title_v.setSpacing(2)
        hdr_title_v.addWidget(_lbl("◈  INITIALISATION REQUIRED", 13, True, align=Qt.AlignmentFlag.AlignLeft))
        hdr_title_v.addWidget(_lbl("Configure J.A.R.V.I.S. before first boot.", 9, color=C.PRI_DIM, align=Qt.AlignmentFlag.AlignLeft))
        hdr_row.addLayout(hdr_title_v)
        hdr_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setFont(QFont(_PRIMARY_FONT, 10, QFont.Weight.Bold))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {C.TEXT_DIM}; background: transparent;
                border: none; border-radius: 3px;
            }}
            QPushButton:hover {{
                color: {C.RED}; background: #20000a;
            }}
        """)
        close_btn.clicked.connect(self.hide)
        hdr_row.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignTop)

        layout.addLayout(hdr_row)
        layout.addSpacing(6)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep)
        layout.addSpacing(4)

        layout.addWidget(_lbl("GEMINI API KEY", 8, color=C.TEXT_DIM,
                               align=Qt.AlignmentFlag.AlignLeft))
        self._key_input = QLineEdit()
        self._key_input.setEchoMode(QLineEdit.EchoMode.Password)
        self._key_input.setPlaceholderText("AIza…")
        self._key_input.setFont(QFont(_PRIMARY_FONT, 10))
        self._key_input.setFixedHeight(32)
        self._key_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d12; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 8px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        layout.addWidget(self._key_input)
        layout.addSpacing(12)

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C.BORDER};"); layout.addWidget(sep2)
        layout.addSpacing(4)

        layout.addWidget(_lbl("OPERATING SYSTEM", 8, color=C.TEXT_DIM,
                               align=Qt.AlignmentFlag.AlignLeft))
        det_name = {"windows": "Windows", "mac": "macOS", "linux": "Linux"}[detected]
        layout.addWidget(_lbl(f"Auto-detected: {det_name}", 8, color=C.ACC2,
                               align=Qt.AlignmentFlag.AlignLeft))

        os_row = QHBoxLayout(); os_row.setSpacing(6)
        self._os_btns: dict[str, QPushButton] = {}
        for key, label in [("windows","⊞  Windows"),("mac","  macOS"),("linux","🐧  Linux")]:
            btn = QPushButton(label)
            btn.setFont(QFont(_PRIMARY_FONT, 9, QFont.Weight.Bold))
            btn.setFixedHeight(32)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, k=key: self._sel(k))
            os_row.addWidget(btn)
            self._os_btns[key] = btn
        layout.addLayout(os_row)
        self._sel(detected)
        layout.addSpacing(12)

        init_btn = QPushButton("▸  INITIALISE SYSTEMS")
        init_btn.setFont(QFont(_PRIMARY_FONT, 10, QFont.Weight.Bold))
        init_btn.setFixedHeight(36)
        init_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        init_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{
                background: {C.PRI_GHO}; border: 1px solid {C.PRI};
            }}
        """)
        init_btn.clicked.connect(self._submit)
        layout.addWidget(init_btn)

    def _sel(self, key: str):
        self._sel_os = key
        pal = {"windows":(C.PRI,"#001a22"),"mac":(C.ACC2,"#1a1400"),"linux":(C.GREEN,"#001a0d")}
        for k, btn in self._os_btns.items():
            if k == key:
                fg, bg = pal[k]
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: {fg}; color: {bg};
                        border: none; border-radius: 3px; font-weight: bold;
                    }}
                """)
            else:
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background: #000d12; color: {C.TEXT_DIM};
                        border: 1px solid {C.BORDER}; border-radius: 3px;
                    }}
                    QPushButton:hover {{ color: {C.TEXT}; border: 1px solid {C.BORDER_B}; }}
                """)

    def _submit(self):
        key = self._key_input.text().strip()
        if not key:
            self._key_input.setStyleSheet(
                self._key_input.styleSheet() +
                f" QLineEdit {{ border: 1px solid {C.RED}; }}"
            )
            return
        self.done.emit(key, self._sel_os)


class HueWheel(QWidget):
    """
    Circular hue selector wheel. Drag the handle to pick a custom UI theme color.
    
    The center circle provides a live preview of the selected color.
    """

    hue_picked    = pyqtSignal(str)   # during dragging (live)
    hue_committed = pyqtSignal(str)   # on mouse release

    _RING = 16   # ring thickness (px)

    def __init__(self, initial_hex: str = DEFAULT_UI_COLOR, parent=None):
        super().__init__(parent)
        self.setFixedSize(148, 148)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._hue  = 0.53
        self._drag = False
        self.set_color(initial_hex)

    # ── API ──────────────────────────────────────────────────────────────────
    def color(self) -> str:
        return QColor.fromHsvF(self._hue, 1.0, 1.0).name()

    def set_color(self, hex_str: str):
        c = QColor((hex_str or "").strip())
        if c.isValid() and c.hsvHueF() >= 0:
            self._hue = c.hsvHueF()
            self.update()

    # ── geometri yardımcıları ────────────────────────────────────────────────
    def _ring_rect(self) -> QRectF:
        m = self._RING / 2 + 3
        return QRectF(self.rect()).adjusted(m, m, -m, -m)

    def _hue_from_pos(self, pos: QPointF) -> float:
        c  = QRectF(self.rect()).center()
        dx = pos.x() - c.x()
        dy = c.y() - pos.y()          # ekran y'si aşağı — matematiksel eksene çevir
        ang = math.atan2(dy, dx)      # [-π, π], saat yönünün tersi
        return (ang / (2 * math.pi)) % 1.0

    # ── çizim ────────────────────────────────────────────────────────────────
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        rect   = self._ring_rect()
        center = rect.center()

        grad = QConicalGradient(center, 0)
        for i in range(0, 361, 20):
            grad.setColorAt(i / 360.0, QColor.fromHsvF((i % 360) / 360.0, 1.0, 1.0))
        p.setPen(QPen(QBrush(grad), self._RING))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(rect)

        # center preview circle
        preview = QColor.fromHsvF(self._hue, 1.0, 1.0)
        inner   = rect.adjusted(30, 30, -30, -30)
        p.setPen(QPen(qcol(C.BORDER_B), 1))
        p.setBrush(QBrush(preview))
        p.drawEllipse(inner)

        # dragged handle
        r   = rect.width() / 2
        ang = self._hue * 2 * math.pi
        hx  = center.x() + r * math.cos(ang)
        hy  = center.y() - r * math.sin(ang)
        p.setPen(QPen(QColor("#00060a"), 2))
        p.setBrush(QBrush(QColor("#ffffff")))
        p.drawEllipse(QPointF(hx, hy), 7.5, 7.5)

    # ── fare ─────────────────────────────────────────────────────────────────
    def mousePressEvent(self, e):
        self._drag = True
        self._hue  = self._hue_from_pos(e.position())
        self.update()
        self.hue_picked.emit(self.color())

    def mouseMoveEvent(self, e):
        if self._drag:
            self._hue = self._hue_from_pos(e.position())
            self.update()
            self.hue_picked.emit(self.color())

    def mouseReleaseEvent(self, e):
        if self._drag:
            self._drag = False
            self.hue_committed.emit(self.color())


class CustomizeOverlay(QWidget):
    """Floating overlay — change assistant name, user name and UI colour."""

    saved = pyqtSignal(str, str, str)   # assistant_name, user_name, ui_color
    _OW, _OH = 400, 500

    def __init__(self, assistant_name="JARVIS", user_name="",
                 ui_color=DEFAULT_UI_COLOR, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            CustomizeOverlay {{
                background: rgba(0, 6, 10, 245);
                border: 1px solid {C.BORDER_B};
                border-radius: 6px;
            }}
        """)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 18, 24, 18)
        lay.setSpacing(8)

        def _lbl(txt, fs=9, bold=False, color=C.PRI, align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt); w.setAlignment(align)
            w.setFont(QFont(_PRIMARY_FONT, fs,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            return w

        _fs = (f"QLineEdit {{ background: #000d12; color: {C.TEXT}; "
               f"border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 8px; }}"
               f"QLineEdit:focus {{ border: 1px solid {C.PRI}; }}")

        hdr_row = QHBoxLayout()
        hdr_lbl = _lbl("⚙  CUSTOMISE ASSISTANT", 12, True, align=Qt.AlignmentFlag.AlignLeft)
        hdr_row.addWidget(hdr_lbl)
        hdr_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setFont(QFont(_PRIMARY_FONT, 10, QFont.Weight.Bold))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {C.TEXT_DIM}; background: transparent;
                border: none; border-radius: 3px;
            }}
            QPushButton:hover {{
                color: {C.RED}; background: #20000a;
            }}
        """)
        close_btn.clicked.connect(self._cancel)
        hdr_row.addWidget(close_btn)

        lay.addLayout(hdr_row)
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER}; margin: 2px 0;")
        lay.addWidget(sep)

        lay.addWidget(_lbl("ASSISTANT NAME", 8, color=C.TEXT_DIM,
                            align=Qt.AlignmentFlag.AlignLeft))
        self._name_input = QLineEdit(assistant_name)
        self._name_input.setFont(QFont(_PRIMARY_FONT, 10))
        self._name_input.setFixedHeight(32)
        self._name_input.setStyleSheet(_fs)
        lay.addWidget(self._name_input)

        lay.addSpacing(4)
        lay.addWidget(_lbl("YOUR NAME  (leave blank for default sir)", 8,
                            color=C.TEXT_DIM, align=Qt.AlignmentFlag.AlignLeft))
        self._user_input = QLineEdit(user_name)
        self._user_input.setPlaceholderText("e.g.  Tony   (leave blank for auto)")
        self._user_input.setFont(QFont(_PRIMARY_FONT, 10))
        self._user_input.setFixedHeight(32)
        self._user_input.setStyleSheet(_fs)
        lay.addWidget(self._user_input)

        # ── UI color — color wheel ───────────────────────────────────────────
        lay.addSpacing(4)
        clr_hdr = QHBoxLayout()
        clr_hdr.addWidget(_lbl("UI COLOUR  —  drag the handle", 8,
                               color=C.TEXT_DIM, align=Qt.AlignmentFlag.AlignLeft))
        clr_hdr.addStretch()
        df_btn = QPushButton("DEFAULT")
        df_btn.setFixedSize(64, 20)
        df_btn.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        df_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        df_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px;
            }}
            QPushButton:hover {{ color: {C.TEXT}; border-color: {C.BORDER_B}; }}
        """)
        df_btn.clicked.connect(lambda: self._set_color(DEFAULT_UI_COLOR))
        clr_hdr.addWidget(df_btn)
        lay.addLayout(clr_hdr)

        self._initial_color = (ui_color or DEFAULT_UI_COLOR).strip().lower()
        self._sel_color     = self._initial_color
        self.on_preview     = None   # callable(hex) — live preview callback

        self._wheel = HueWheel(self._sel_color)
        wheel_row = QHBoxLayout()
        wheel_row.addStretch(); wheel_row.addWidget(self._wheel); wheel_row.addStretch()
        lay.addLayout(wheel_row)
        self._wheel.hue_picked.connect(self._on_wheel_pick)
        self._wheel.hue_committed.connect(self._on_wheel_commit)

        self._hex_input = QLineEdit(self._sel_color)
        self._hex_input.setPlaceholderText("#00d4ff   (custom hex colour)")
        self._hex_input.setFont(QFont(_PRIMARY_FONT, 10))
        self._hex_input.setFixedHeight(28)
        self._hex_input.setFont(QFont(_PRIMARY_FONT, 9))
        self._hex_input.setMaxLength(7)
        self._hex_input.setPlaceholderText("#00e5ff")
        self._hex_input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d12; color: {C.TEXT};
                border: 1px solid {C.BORDER}; border-radius: 3px;
                padding: 4px 6px;
            }}
            QLineEdit:focus {{ border-color: {C.PRI}; }}
        """)
        self._hex_input.textChanged.connect(self._on_hex_edited)
        hex_lay.addWidget(self._hex_input)

        rst_btn = QPushButton("RESET")
        rst_btn.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        rst_btn.setStyleSheet(f"""
            QPushButton {{
                background: #000d12; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 8px;
            }}
            QPushButton:hover {{ color: {C.PRI}; border-color: {C.PRI}; }}
        """)
        rst_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        rst_btn.clicked.connect(lambda: self._set_color(DEFAULT_UI_COLOR, update_wheel=True, preview=True))
        hex_lay.addWidget(rst_btn)

        lay.addLayout(hex_lay)
        lay.addSpacing(8)

        # Save / Cancel Buttons
        btn_row = QHBoxLayout()
        btn_row.setSpacing(6)

        cancel_btn = QPushButton("CANCEL")
        cancel_btn.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        cancel_btn.setStyleSheet(f"""
            QPushButton {{
                background: #000d12; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 6px;
            }}
            QPushButton:hover {{ color: {C.TEXT}; border-color: {C.TEXT_MED}; }}
        """)
        cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cancel_btn.clicked.connect(self._cancel)
        btn_row.addWidget(cancel_btn)

        save_btn = QPushButton("APPLY ACCENT")
        save_btn.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        save_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PRI_GHO}; color: {C.PRI};
                border: 1px solid {C.PRI}; border-radius: 3px; padding: 6px;
            }}
            QPushButton:hover {{ background: {C.PRI}; color: #00060a; }}
        """)
        save_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        save_btn.clicked.connect(self._save)
        btn_row.addWidget(save_btn)

        lay.addLayout(btn_row)

    # ── color flow ───────────────────────────────────────────────────────────
    def _set_color(self, hx: str, update_wheel: bool = True, preview: bool = True):
        """Updates selected color; synchronizes hex input, wheel, and live preview."""
        self._sel_color = hx.strip().lower()
        self._hex_input.blockSignals(True)
        self._hex_input.setText(self._sel_color)
        self._hex_input.blockSignals(False)
        if update_wheel:
            self._wheel.set_color(self._sel_color)
        if preview and self.on_preview:
            self.on_preview(self._sel_color)

    def _on_wheel_pick(self, hx: str):
        # While dragging: update hex input without full retheme
        self._sel_color = hx
        self._hex_input.blockSignals(True)
        self._hex_input.setText(hx)
        self._hex_input.blockSignals(False)

    def _on_wheel_commit(self, hx: str):
        # Mouse handle released → preview full UI theme
        self._set_color(hx, update_wheel=False)

    def _on_hex_edited(self, text: str):
        t = text.strip().lower()
        if t.startswith("#") and len(t) == 7:
            try:
                int(t[1:], 16)
            except ValueError:
                return
            self._set_color(t, update_wheel=True, preview=True)

    def _cancel(self):
        # Restore original color if preview was applied
        if self.on_preview and self._sel_color != self._initial_color:
            self.on_preview(self._initial_color)
        self.hide()

    def _save(self):
        name = self._name_input.text().strip() or "JARVIS"
        user = self._user_input.text().strip()
        self.saved.emit(name, user, self._sel_color or DEFAULT_UI_COLOR)
        self.hide()


class ClipboardPanel(QWidget):
    """Floating panel shown when text is copied — offers quick Jarvis actions."""

    action_requested = pyqtSignal(str)
    _W, _H = 326, 112

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            ClipboardPanel {{
                background: rgba(0, 8, 14, 248);
                border: 1px solid {C.BORDER_B};
                border-radius: 6px;
            }}
        """)
        self.setFixedWidth(self._W)
        self._clip_text = ""

        lay = QVBoxLayout(self)
        lay.setContentsMargins(8, 6, 8, 7)
        lay.setSpacing(4)

        hdr = QHBoxLayout(); hdr.setSpacing(4)
        icon_lbl = QLabel("◈  CLIPBOARD DETECTED")
        icon_lbl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        icon_lbl.setStyleSheet(f"color: {C.ACC2}; background: transparent;")
        hdr.addWidget(icon_lbl); hdr.addStretch()
        x_btn = QPushButton("✕")
        x_btn.setFixedSize(16, 16)
        x_btn.setFont(QFont(_PRIMARY_FONT, 8))
        x_btn.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent; border: none;")
        x_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        x_btn.clicked.connect(self.hide)
        hdr.addWidget(x_btn)
        lay.addLayout(hdr)

        self._preview = QLabel()
        self._preview.setFont(QFont(_PRIMARY_FONT, 8))
        self._preview.setStyleSheet(f"""
            color: {C.TEXT}; background: {C.PANEL2};
            border: 1px solid {C.BORDER}; border-radius: 3px; padding: 4px 6px;
        """)
        self._preview.setWordWrap(False)
        self._preview.setFixedHeight(28)
        lay.addWidget(self._preview)

        btn_row = QHBoxLayout(); btn_row.setSpacing(4)
        _bs = (f"QPushButton {{ background: {C.PANEL2}; color: {C.TEXT_MED}; "
               f"border: 1px solid {C.BORDER}; border-radius: 2px; }}"
               f"QPushButton:hover {{ color: {C.PRI}; border-color: {C.BORDER_B}; }}")
        for label, cmd_fmt in [
            ("TRANSLATE", "Translate this text to English: {text}"),
            ("SUMMARISE", "Summarise this: {text}"),
            ("EXPLAIN",   "Explain this: {text}"),
            ("FIX",       "Fix grammar and spelling: {text}"),
        ]:
            b = QPushButton(label)
            b.setFixedHeight(22)
            b.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setStyleSheet(_bs)
            b.clicked.connect(lambda _, c=cmd_fmt: self._trigger(c))
            btn_row.addWidget(b)
        lay.addLayout(btn_row)

        self._dismiss_timer = QTimer(self)
        self._dismiss_timer.setSingleShot(True)
        self._dismiss_timer.timeout.connect(self.hide)
        self.hide()

    def _trigger(self, cmd_fmt: str):
        if self._clip_text:
            self.action_requested.emit(cmd_fmt.format(text=self._clip_text[:800]))
        self.hide()

    def show_clipboard(self, text: str):
        self._clip_text = text
        preview = text[:58].replace('\n', ' ')
        if len(text) > 58:
            preview += "…"
        self._preview.setText(f'"{preview}"')
        self.show(); self.raise_()
        self._dismiss_timer.start(8000)


class RemoteKeyOverlay(QWidget):
    """Floating overlay — QR code for instant phone pairing + manual key fallback."""

    closed = pyqtSignal()

    _OW, _OH = 400, 465

    def __init__(self, url: str, key: str, auto_login_url: str = "",
                 manual_url: str = "", expiry_secs: int = 600, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.setStyleSheet(f"""
            RemoteKeyOverlay {{
                background: rgba(0, 4, 12, 0.95);
                border: 1px solid {C.BORDER_B};
                border-radius: 14px;
            }}
        """)
        self._expiry          = time.time() + expiry_secs
        self._on_new_key      = None
        self._auto_login_url  = auto_login_url
        self._manual_url      = manual_url or url

        lay = QVBoxLayout(self)
        lay.setContentsMargins(24, 16, 24, 16)
        lay.setSpacing(5)

        def _lbl(txt, fs=9, bold=False, color=C.PRI,
                 align=Qt.AlignmentFlag.AlignCenter):
            w = QLabel(txt)
            w.setAlignment(align)
            w.setFont(QFont(_PRIMARY_FONT, fs,
                            QFont.Weight.Bold if bold else QFont.Weight.Normal))
            w.setStyleSheet(f"color: {color}; background: transparent;")
            w.setWordWrap(True)
            return w

        lay.addWidget(_lbl("◈  REMOTE ACCESS", 12, True))
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER}; margin: 1px 0;")
        lay.addWidget(sep)

        # ── QR code ───────────────────────────────────────────────────────────
        self._qr_label = QLabel()
        self._qr_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._qr_label.setFixedSize(176, 176)
        self._qr_label.setStyleSheet(
            "background: white; border-radius: 10px; padding: 4px;"
        )
        qr_row = QHBoxLayout()
        qr_row.addStretch()
        qr_row.addWidget(self._qr_label)
        qr_row.addStretch()
        lay.addLayout(qr_row)

        self._update_qr(auto_login_url)

        lay.addWidget(_lbl("Scan with phone camera to connect instantly", 8, color=C.TEXT_DIM))

        sep2 = QFrame(); sep2.setFrameShape(QFrame.Shape.HLine)
        sep2.setStyleSheet(f"color: {C.BORDER}; margin: 1px 0;")
        lay.addWidget(sep2)

        lay.addWidget(_lbl("Or enter manually:", 7, color=C.TEXT_DIM,
                           align=Qt.AlignmentFlag.AlignLeft))

        self._url_lbl = QLabel(self._manual_url)
        self._url_lbl.setFont(QFont(_PRIMARY_FONT, 8))
        self._url_lbl.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent;")
        self._url_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._url_lbl.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse)
        lay.addWidget(self._url_lbl)

        self._key_lbl = QLabel(key)
        self._key_lbl.setFont(QFont(_PRIMARY_FONT, 28, QFont.Weight.Bold))
        self._key_lbl.setStyleSheet(f"""
            color: {C.ACC};
            background: {C.PANEL2};
            border: 1px solid {C.BORDER_B};
            border-radius: 8px;
            padding: 6px 4px;
            letter-spacing: 10px;
        """)
        self._key_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._key_lbl)

        self._timer_lbl = QLabel()
        self._timer_lbl.setFont(QFont(_PRIMARY_FONT, 8))
        self._timer_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        self._timer_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lay.addWidget(self._timer_lbl)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        new_btn = QPushButton("NEW KEY")
        new_btn.setFixedHeight(32)
        new_btn.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        new_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        new_btn.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL}; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 5px;
            }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)
        new_btn.clicked.connect(self._refresh_key)
        btn_row.addWidget(new_btn)

        close_btn = QPushButton("DISMISS")
        close_btn.setFixedHeight(32)
        close_btn.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 5px;
            }}
            QPushButton:hover {{ color: {C.TEXT}; border: 1px solid {C.BORDER_B}; }}
        """)
        close_btn.clicked.connect(self._do_close)
        btn_row.addWidget(close_btn)
        lay.addLayout(btn_row)

        self._ctimer = QTimer(self)
        self._ctimer.timeout.connect(self._tick)
        self._ctimer.start(1000)
        self._tick()

    def set_new_key_callback(self, fn) -> None:
        self._on_new_key = fn

    def _update_qr(self, url: str) -> None:
        if not url:
            self._qr_label.setText("—")
            return
        try:
            import qrcode as _qrmod
            from io import BytesIO
            qr = _qrmod.QRCode(
                box_size=5, border=2,
                error_correction=_qrmod.constants.ERROR_CORRECT_M,
            )
            qr.add_data(url)
            qr.make(fit=True)
            img = qr.make_image(fill_color="black", back_color="white")
            buf = BytesIO()
            img.save(buf, format="PNG")
            px = QPixmap()
            px.loadFromData(buf.getvalue())
            self._qr_label.setPixmap(
                px.scaled(170, 170,
                          Qt.AspectRatioMode.KeepAspectRatio,
                          Qt.TransformationMode.SmoothTransformation)
            )
        except ImportError:
            self._qr_label.setText("pip install\nqrcode[pil]")
            self._qr_label.setFont(QFont(_PRIMARY_FONT, 8))
            self._qr_label.setStyleSheet(
                "color: #888; background: white; border-radius: 10px; padding: 4px;"
            )
        except Exception:
            self._qr_label.setText(url[:28])
            self._qr_label.setFont(QFont(_PRIMARY_FONT, 7))
            self._qr_label.setStyleSheet(
                f"color: {C.PRI}; background: white; border-radius: 10px; padding: 4px;"
            )

    def _tick(self):
        remaining = max(0, int(self._expiry - time.time()))
        m, s = divmod(remaining, 60)
        self._timer_lbl.setText(f"Key expires in  {m:02d}:{s:02d}")
        if remaining == 0:
            self._do_close()

    def mark_connected(self) -> None:
        """Call from any thread when a phone successfully connects."""
        self._ctimer.stop()
        self._key_lbl.setText("CONNECTED")
        self._key_lbl.setStyleSheet(f"""
            color: {C.GREEN};
            background: rgba(34,197,94,0.08);
            border: 2px solid rgba(34,197,94,0.4);
            border-radius: 8px;
            padding: 6px 4px;
            letter-spacing: 4px;
        """)
        self._qr_label.setText("✓")
        self._qr_label.setFont(QFont(_PRIMARY_FONT, 54, QFont.Weight.Bold))
        self._qr_label.setStyleSheet(
            "color: #00ff88; background: #001a0d; border-radius: 10px;"
        )
        self._timer_lbl.setText("Phone connected — JARVIS ready")
        self._timer_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent;")

    def _refresh_key(self):
        if self._on_new_key:
            result = self._on_new_key()
            if result:
                url    = result[0]
                key    = result[1]
                auto   = result[2] if len(result) >= 3 else ""
                manual = result[3] if len(result) >= 4 else url
                self._manual_url     = manual or url
                self._url_lbl.setText(self._manual_url)
                self._key_lbl.setText(key)
                self._auto_login_url = auto
                self._update_qr(auto or url)
                self._expiry = time.time() + 600
                self._key_lbl.setStyleSheet(f"""
                    color: {C.ACC};
                    background: {C.PANEL2};
                    border: 1px solid {C.BORDER_B};
                    border-radius: 8px;
                    padding: 6px 4px;
                    letter-spacing: 10px;
                """)
                self._timer_lbl.setStyleSheet(
                    f"color: {C.TEXT_MED}; background: transparent;"
                )
                self._ctimer.start(1000)
                self._tick()

    def _do_close(self):
        self._ctimer.stop()
        self.hide()
        self.closed.emit()



class NeuralNetCanvas(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(110)
        self.nodes = []
        for _ in range(12):
            self.nodes.append({
                "x": random.uniform(10, 130),
                "y": random.uniform(10, 100),
                "vx": random.uniform(-0.5, 0.5),
                "vy": random.uniform(-0.5, 0.5)
            })
        self.tmr = QTimer(self)
        self.tmr.timeout.connect(self._step)
        self.tmr.start(30)

    def _step(self):
        W, H = self.width(), self.height()
        if W < 10 or H < 10:
            return
        for n in self.nodes:
            n["x"] += n["vx"]
            n["y"] += n["vy"]
            if n["x"] < 5 or n["x"] > W - 5: n["vx"] *= -1
            if n["y"] < 5 or n["y"] > H - 5: n["vy"] *= -1
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        p.fillRect(self.rect(), qcol(C.PANEL2))
        p.setPen(QPen(qcol(C.BORDER_A), 1))
        p.drawRect(self.rect().adjusted(0, 0, -1, -1))
        p.setPen(QPen(qcol(C.PRI, 50), 1))
        for i in range(len(self.nodes)):
            for j in range(i + 1, len(self.nodes)):
                n1, n2 = self.nodes[i], self.nodes[j]
                dist = math.hypot(n1["x"] - n2["x"], n1["y"] - n2["y"])
                if dist < 45:
                    alpha = max(0, min(180, int(255 * (1.0 - dist / 45))))
                    p.setPen(QPen(qcol(C.PRI, alpha), 1))
                    p.drawLine(QPointF(n1["x"], n1["y"]), QPointF(n2["x"], n2["y"]))
        p.setPen(Qt.PenStyle.NoPen)
        for n in self.nodes:
            p.setBrush(QBrush(qcol(C.GREEN if random.random() > 0.05 else C.WHITE, 200)))
            p.drawEllipse(QPointF(n["x"], n["y"]), 3, 3)

class AICoreWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {C.PANEL2}; border: 1px solid {C.BORDER}; border-radius: 4px;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(6, 6, 6, 6)
        lay.setSpacing(4)

        self.neural_canvas = NeuralNetCanvas()
        self.neural_canvas.setFixedHeight(70)
        lay.addWidget(self.neural_canvas)

        cfg = _read_full_config()
        api_key = (cfg.get("gemini_api_key") or "").strip()
        model_name = (cfg.get("model") or "Gemini 1.5 Pro").strip()
        if api_key:
            key_str = "ACTIVE"
            key_col = C.GREEN
            stat_str = "ONLINE ●"
            stat_col = C.GREEN
        else:
            key_str = "INACTIVE"
            key_col = C.RED
            stat_str = "OFFLINE ●"
            stat_col = C.RED

        stats_box = QWidget()
        stats_box.setStyleSheet(f"background: {C.DARK}; border: 1px solid {C.BORDER_A}; border-radius: 3px;")
        st_lay = QVBoxLayout(stats_box)
        st_lay.setContentsMargins(6, 4, 6, 4)
        st_lay.setSpacing(2)

        eng_lbl = QLabel(f"ENGINE   {model_name}")
        eng_lbl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        eng_lbl.setStyleSheet(f"color: {C.PRI}; border: none; background: transparent;")
        st_lay.addWidget(eng_lbl)

        key_lbl = QLabel(f"API KEY  {key_str}")
        key_lbl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        key_lbl.setStyleSheet(f"color: {key_col}; border: none; background: transparent;")
        st_lay.addWidget(key_lbl)

        stat_lbl = QLabel(f"STATUS   {stat_str}")
        stat_lbl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        stat_lbl.setStyleSheet(f"color: {stat_col}; border: none; background: transparent;")
        st_lay.addWidget(stat_lbl)

        lay.addWidget(stats_box)

class CoreStatusWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)
        
        title = QLabel("◈ CORE STATUS")
        title.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.PRI}; border: none; background: transparent;")
        lay.addWidget(title)
        
        self.rows_def = [
            ("Neural Links", "ONLINE", C.GREEN),
            ("Memory Core", "STABLE", C.GREEN),
            ("Data Streams", "ACTIVE", C.GREEN),
            ("Learning Mode", "CONTINUOUS", C.ACC2),
            ("Response Time", "0.023s", C.ACC2)
        ]
        self.val_labels: dict[str, QLabel] = {}
        
        for name, default_val, col in self.rows_def:
            h = QHBoxLayout()
            h.setContentsMargins(0, 0, 0, 0)
            nl = QLabel(name)
            nl.setFont(QFont(_PRIMARY_FONT, 7))
            nl.setStyleSheet("color: #8ffcff; border: none; background: transparent;")
            vl = QLabel(default_val)
            vl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
            vl.setStyleSheet(f"color: {col}; border: none; background: transparent;")
            h.addWidget(nl)
            h.addStretch()
            h.addWidget(vl)
            lay.addLayout(h)
            self.val_labels[name] = vl

    def update_status(self, cpu_p: float, ram_p: float, net_kbs: float):
        # 1. Neural Links
        if cpu_p < 60:
            self.val_labels["Neural Links"].setText("ONLINE")
            self.val_labels["Neural Links"].setStyleSheet(f"color: {C.GREEN}; border: none; background: transparent;")
        elif cpu_p < 85:
            self.val_labels["Neural Links"].setText("HEAVY LOAD")
            self.val_labels["Neural Links"].setStyleSheet(f"color: {C.ACC2}; border: none; background: transparent;")
        else:
            self.val_labels["Neural Links"].setText("DEGRADED")
            self.val_labels["Neural Links"].setStyleSheet(f"color: {C.RED}; border: none; background: transparent;")

        # 2. Memory Core
        if ram_p < 75:
            self.val_labels["Memory Core"].setText("STABLE")
            self.val_labels["Memory Core"].setStyleSheet(f"color: {C.GREEN}; border: none; background: transparent;")
        elif ram_p < 90:
            self.val_labels["Memory Core"].setText("ELEVATED")
            self.val_labels["Memory Core"].setStyleSheet(f"color: {C.ACC2}; border: none; background: transparent;")
        else:
            self.val_labels["Memory Core"].setText("CRITICAL")
            self.val_labels["Memory Core"].setStyleSheet(f"color: {C.RED}; border: none; background: transparent;")

        # 3. Data Streams
        if net_kbs > 50:
            self.val_labels["Data Streams"].setText("STREAMING")
            self.val_labels["Data Streams"].setStyleSheet(f"color: {C.PRI}; border: none; background: transparent;")
        elif net_kbs > 0:
            self.val_labels["Data Streams"].setText("ACTIVE")
            self.val_labels["Data Streams"].setStyleSheet(f"color: {C.GREEN}; border: none; background: transparent;")
        else:
            self.val_labels["Data Streams"].setText("IDLE")
            self.val_labels["Data Streams"].setStyleSheet(f"color: {C.TEXT_MED}; border: none; background: transparent;")

        # 4. Learning Mode
        if cpu_p > 70:
            self.val_labels["Learning Mode"].setText("ADAPTIVE")
            self.val_labels["Learning Mode"].setStyleSheet(f"color: {C.PRI}; border: none; background: transparent;")
        else:
            self.val_labels["Learning Mode"].setText("CONTINUOUS")
            self.val_labels["Learning Mode"].setStyleSheet(f"color: {C.ACC2}; border: none; background: transparent;")

        # 5. Response Time
        latency = 0.015 + (cpu_p / 100.0) * 0.020 + random.uniform(-0.002, 0.003)
        latency = max(0.010, latency)
        self.val_labels["Response Time"].setText(f"{latency:.3f}s")
        self.val_labels["Response Time"].setStyleSheet(f"color: {C.ACC2}; border: none; background: transparent;")

def _get_wifi_signal() -> tuple[int, str]:
    """Returns (signal_percent 0-100, ssid_name)."""
    if _OS != "Windows":
        return (85, "Wi-Fi Connected")
    try:
        flags = subprocess.CREATE_NO_WINDOW if hasattr(subprocess, "CREATE_NO_WINDOW") else 0x08000000
        res = subprocess.run(
            ["netsh", "wlan", "show", "interfaces"],
            capture_output=True,
            text=True,
            timeout=2,
            creationflags=flags
        )
        sig = -1
        ssid = "Disconnected"
        for line in res.stdout.splitlines():
            line_str = line.strip()
            if line_str.startswith("SSID") and ":" in line_str and not line_str.startswith("BSSID"):
                parts = line_str.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    ssid = parts[1].strip()
            elif line_str.startswith("Signal") and ":" in line_str:
                parts = line_str.split(":", 1)
                if len(parts) > 1:
                    raw = parts[1].replace("%", "").strip()
                    if raw.isdigit():
                        sig = int(raw)
        return (sig, ssid)
    except Exception:
        return (85, "Wi-Fi Connected")


class WifiSignalIcon(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(18, 18)
        self.signal_pct = 99
        self.ssid = "Wi-Fi"
        self.setToolTip("Wi-Fi: Connected (99%)")

    def set_signal(self, pct: int, ssid: str = ""):
        self.signal_pct = pct
        self.ssid = ssid
        if pct >= 0:
            self.setToolTip(f"Wi-Fi: {ssid} ({pct}%)")
        else:
            self.setToolTip("Wi-Fi: Disconnected")
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        pct = self.signal_pct

        if pct < 0:
            color_act = C.RED
        elif pct >= 60:
            color_act = C.GREEN
        elif pct >= 30:
            color_act = C.ACC2
        else:
            color_act = C.ACC

        color_dim = qcol(C.BORDER_B, 60)
        cx, cy = w / 2, h - 3

        # Base Dot
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(QBrush(qcol(color_act if pct >= 0 else C.RED)))
        p.drawEllipse(QPointF(cx, cy), 1.8, 1.8)

        p.setBrush(Qt.BrushStyle.NoBrush)

        # Arc 1 (Inner)
        p.setPen(QPen(qcol(color_act) if pct > 0 else color_dim, 1.8))
        p.drawArc(QRectF(cx - 4.5, cy - 4.5, 9, 9), 45 * 16, 90 * 16)

        # Arc 2 (Middle)
        p.setPen(QPen(qcol(color_act) if pct >= 34 else color_dim, 1.8))
        p.drawArc(QRectF(cx - 8, cy - 8, 16, 16), 45 * 16, 90 * 16)

        # Arc 3 (Outer)
        p.setPen(QPen(qcol(color_act) if pct >= 67 else color_dim, 1.8))
        p.drawArc(QRectF(cx - 11.5, cy - 11.5, 23, 23), 45 * 16, 90 * 16)

class NewsUpdatesWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px;")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 8, 10, 8)
        lay.setSpacing(6)

        title = QLabel("◈ NEWS & UPDATES")
        title.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        title.setStyleSheet(f"color: {C.PRI}; border: none; background: transparent;")
        lay.addWidget(title)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(f"""
            QScrollArea {{ background: transparent; border: none; }}
            QScrollBar:vertical {{
                background: {C.PANEL2};
                width: 5px;
                border-radius: 2px;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_B};
                border-radius: 2px;
                min-height: 15px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {C.PRI_DIM};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
        """)

        news_container = QWidget()
        news_container.setStyleSheet("background: transparent;")
        news_lay = QVBoxLayout(news_container)
        news_lay.setContentsMargins(0, 0, 4, 0)
        news_lay.setSpacing(6)

        news = [
            "• Global AI Summit: Next-Gen Quantum Models & Alignment Standards.",
            "• World Markets: Tech Sector Gains Lead Global Index Rally.",
            "• SpaceX Starship Orbital Mission Successfully Reaches Target Orbit.",
            "• Cyber Defense Alert: Critical Infrastructure Security Protocols Updated.",
            "• Clean Energy Grid: Solar & Fusion Research Hits New Record Efficiency.",
            "• Deep Space Astronomy: Webb Telescope Detects Water Vapor on Exoplanet.",
            "• Microchip Tech: Next-Gen 1.4nm Processor Fabrication Underway.",
            "• Robotics Milestone: Autonomous AI Assistants Integrated into Logistics.",
            "• Global Climate Network: Real-Time Weather Satellite Mesh Operational.",
            "• Telecom 6G Standards: High-Band Spectrum Tests Exceed 100 Gbps.",
            "• Quantum Computing: Error-Corrected Logical Qubit Record Broken.",
            "• Aerospace Initiative: Hypersonic Transit Flight Completed Successfully."
        ]
        for item in news:
            lbl = QLabel(item)
            lbl.setFont(QFont(_PRIMARY_FONT, 7))
            lbl.setStyleSheet(f"color: {C.TEXT}; border: none; background: transparent;")
            lbl.setWordWrap(True)
            news_lay.addWidget(lbl)

        news_lay.addStretch()
        scroll.setWidget(news_container)
        lay.addWidget(scroll, stretch=1)

class VoiceInterfaceWidget(QWidget):
    def __init__(self, main_win, parent=None):
        super().__init__(parent)
        self._main_win = main_win
        self.setFixedHeight(85)
        self.setStyleSheet(f"background: {C.PANEL}; border: 1px solid {C.BORDER}; border-radius: 4px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 6, 10, 6)
        layout.setSpacing(2)
        
        hdr = QHBoxLayout()
        lbl = QLabel("VOICE INTERFACE")
        lbl.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        lbl.setStyleSheet(f"color: {C.PRI}; border: none; background: transparent;")
        hdr.addWidget(lbl)
        hdr.addStretch()
        self.mic_icon = VectorIcon("mic", C.PRI)
        hdr.addWidget(self.mic_icon)
        layout.addLayout(hdr)
        
        self.wave = _VoiceWaveCanvas(self)
        layout.addWidget(self.wave)
        
        self.status = QLabel("Listening...")
        self.status.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        self.status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status.setStyleSheet("color: #ffcc00; border: none; background: transparent;")
        layout.addWidget(self.status)

class _VoiceWaveCanvas(QWidget):
    def __init__(self, owner: VoiceInterfaceWidget):
        super().__init__(owner)
        self._owner = owner
        self.tick = 0
        self.tmr = QTimer(self)
        self.tmr.timeout.connect(self._step)
        self.tmr.start(40)
        
    def _step(self):
        self.tick += 1
        self.update()
        
    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        W, H = self.width(), self.height()
        cy = H / 2
        
        # Read active states from MainWindow
        main_win = self._owner._main_win
        is_muted = main_win._muted
        # In ui.py, MainWindow or HudCanvas sets speaking status
        is_speaking = main_win.hud.speaking
        
        state_str = main_win.hud.state
        if is_muted:
            self._owner.status.setText("⊘  MUTED")
            self._owner.status.setStyleSheet("color: #ff3355; border: none; background: transparent;")
            self._owner.mic_icon.setIcon("mic_off", C.MUTED_C)
        elif is_speaking:
            self._owner.status.setText("●  SPEAKING")
            self._owner.status.setStyleSheet("color: #ff6b00; border: none; background: transparent;")
            self._owner.mic_icon.setIcon("mic", C.PRI)
        else:
            self._owner.status.setText(f"●  {state_str}")
            self._owner.mic_icon.setIcon("mic", C.PRI)
            if state_str == "LISTENING":
                self._owner.status.setStyleSheet("color: #00ff88; border: none; background: transparent;")
            else:
                self._owner.status.setStyleSheet("color: #00d4ff; border: none; background: transparent;")
        
        p.setPen(QPen(qcol(C.MUTED_C if is_muted else (C.ACC if is_speaking else C.PRI), 180), 1.5))
        path = QPainterPath()
        path.moveTo(0, cy)
        
        for x in range(0, W, 2):
            if is_muted:
                y = cy
            elif is_speaking:
                # Highly active random/dynamic voice waves
                y = cy + random.uniform(5, 14) * math.sin(x * 0.12 - self.tick * 0.25) * math.sin(x * 0.04)
            else:
                # Regular pulsing listening wave
                y = cy + 4 * math.sin(x * 0.08 - self.tick * 0.1) * math.sin(x * 0.02)
            path.lineTo(x, y)
            
        p.drawPath(path)


class VectorIcon(QWidget):
    def __init__(self, icon_type: str, color: str = C.PRI, parent=None):
        super().__init__(parent)
        self._type = icon_type
        self._color = color
        self.setFixedSize(16, 16)

    def setIcon(self, icon_type: str, color: str = None):
        self._type = icon_type
        if color:
            self._color = color
        self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()
        p.setPen(QPen(qcol(self._color), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)

        if self._type == "diamond":
            p.setBrush(QBrush(qcol(self._color)))
            path = QPainterPath()
            path.moveTo(w / 2, 2)
            path.lineTo(w - 2, h / 2)
            path.lineTo(w / 2, h - 2)
            path.lineTo(2, h / 2)
            path.closeSubpath()
            p.drawPath(path)
        elif self._type == "mic":
            p.drawRoundedRect(QRectF(w / 2 - 3, h / 2 - 7, 6, 10), 3, 3)
            p.drawArc(QRectF(w / 2 - 6, h / 2 - 3, 12, 8), 180 * 16, 180 * 16)
            p.drawLine(QPointF(w / 2, h / 2 + 5), QPointF(w / 2, h / 2 + 8))
            p.drawLine(QPointF(w / 2 - 4, h / 2 + 8), QPointF(w / 2 + 4, h / 2 + 8))
        elif self._type in ("mic_off", "mic_muted"):
            p.drawRoundedRect(QRectF(w / 2 - 3, h / 2 - 7, 6, 10), 3, 3)
            p.drawArc(QRectF(w / 2 - 6, h / 2 - 3, 12, 8), 180 * 16, 180 * 16)
            p.drawLine(QPointF(w / 2, h / 2 + 5), QPointF(w / 2, h / 2 + 8))
            p.drawLine(QPointF(w / 2 - 4, h / 2 + 8), QPointF(w / 2 + 4, h / 2 + 8))
            p.drawLine(QPointF(1, 1), QPointF(w - 1, h - 1))
        elif self._type == "stop" or self._type == "cross":
            p.drawLine(4, 4, w - 4, h - 4)
            p.drawLine(w - 4, 4, 4, h - 4)
        elif self._type == "settings" or self._type == "cog":
            p.drawEllipse(QRectF(4, 4, 8, 8))
            for i in range(8):
                ang = i * math.pi / 4
                p.drawLine(
                    QPointF(w/2 + 3*math.cos(ang), h/2 + 3*math.sin(ang)),
                    QPointF(w/2 + 6*math.cos(ang), h/2 + 6*math.sin(ang))
                )
        elif self._type == "wifi":
            p.drawArc(QRectF(2, 6, 12, 12), 45 * 16, 90 * 16)
            p.drawArc(QRectF(4, 8, 8, 8), 45 * 16, 90 * 16)
            p.setBrush(QBrush(qcol(self._color)))
            p.drawEllipse(QRectF(w/2 - 1, h - 3, 2, 2))

class VectorIconButton(QPushButton):
    def __init__(self, text: str, icon_type: str, icon_color: str, parent=None):
        super().__init__(text, parent)
        self._icon_type = icon_type
        self._icon_color = icon_color

    def setIcon(self, icon_type: str, icon_color: str = None):
        self._icon_type = icon_type
        if icon_color:
            self._icon_color = icon_color
        self.update()

    def paintEvent(self, e):
        super().paintEvent(e)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = 16, 16
        cx = 10
        cy = (self.height() - h) // 2
        p.translate(cx, cy)
        p.setPen(QPen(qcol(self._icon_color), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)

        if self._icon_type == "mic":
            p.drawRoundedRect(QRectF(w / 2 - 3, h / 2 - 7, 6, 10), 3, 3)
            p.drawArc(QRectF(w / 2 - 6, h / 2 - 3, 12, 8), 180 * 16, 180 * 16)
            p.drawLine(QPointF(w / 2, h / 2 + 5), QPointF(w / 2, h / 2 + 8))
            p.drawLine(QPointF(w / 2 - 4, h / 2 + 8), QPointF(w / 2 + 4, h / 2 + 8))
        elif self._icon_type in ("mic_off", "mic_muted"):
            p.drawRoundedRect(QRectF(w / 2 - 3, h / 2 - 7, 6, 10), 3, 3)
            p.drawArc(QRectF(w / 2 - 6, h / 2 - 3, 12, 8), 180 * 16, 180 * 16)
            p.drawLine(QPointF(w / 2, h / 2 + 5), QPointF(w / 2, h / 2 + 8))
            p.drawLine(QPointF(w / 2 - 4, h / 2 + 8), QPointF(w / 2 + 4, h / 2 + 8))
            p.drawLine(QPointF(1, 1), QPointF(w - 1, h - 1))
        elif self._icon_type == "cross" or self._icon_type == "stop":
            p.drawLine(4, 4, w - 4, h - 4)
            p.drawLine(w - 4, 4, 4, h - 4)

class MainWindow(QMainWindow):
    _log_sig        = pyqtSignal(str)
    _state_sig      = pyqtSignal(str)
    _content_sig    = pyqtSignal(str, str)   # (title, text) — thread-safe content display
    _reconfig_sig   = pyqtSignal()           # trigger setup overlay from any thread
    _camera_sig     = pyqtSignal(bytes)      # show camera frame preview (small overlay)
    _cam_stream_sig = pyqtSignal(bool)       # True=start live stream, False=stop
    _cam_frame_sig  = pyqtSignal(bytes)      # live camera frame → HUD area
    _clipboard_sig  = pyqtSignal(str)        # clipboard text changed (thread-safe)

    def __init__(self, face_path: str):
        super().__init__()
        self._face_path = face_path

        _load_custom_fonts()

        # Load customization from config
        _cfg = _read_full_config()
        self._assistant_name: str = (_cfg.get("assistant_name") or "JARVIS").strip()
        _display = self._assistant_name.upper()

        # Apply saved UI accent color before initializing panels
        _ui_color = (_cfg.get("ui_color") or "").strip()
        if _ui_color and _ui_color.lower() != DEFAULT_UI_COLOR:
            apply_ui_accent(_ui_color)

        self.setWindowTitle(f"{_display} AI")
        self.setMinimumSize(_MIN_W, _MIN_H)
        self.resize(_DEFAULT_W, _DEFAULT_H)

        screen = QApplication.primaryScreen().availableGeometry()
        self.move(
            (screen.width()  - _DEFAULT_W) // 2,
            (screen.height() - _DEFAULT_H) // 2,
        )

        self.on_text_command   = None
        self.on_remote_clicked = None   # callable: () -> (url, key) | None
        self.on_interrupt      = None   # callable: () -> None — stop JARVIS mid-speech
        self._muted            = False
        self._current_file: str | None = None
        self._remote_overlay: RemoteKeyOverlay | None = None
        self._customize_overlay: CustomizeOverlay | None = None

        central = QWidget()
        central.setStyleSheet(f"background: {C.BG};")
        self.setCentralWidget(central)

        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)
        root.addWidget(self._build_header())

        body = QHBoxLayout()
        body.setContentsMargins(8, 8, 8, 8)
        body.setSpacing(8)

        self._left_panel = self._build_left_panel()
        body.addWidget(self._left_panel, stretch=0)

        # Center Column: Left Sub-column + Center HUD/Voice
        center_widget = QWidget()
        center_widget.setStyleSheet("background: transparent;")
        center_lay = QHBoxLayout(center_widget)
        center_lay.setContentsMargins(0, 0, 0, 0)
        center_lay.setSpacing(8)

        # Center-Left Sub-column (Core Status, Quick Commands, News)
        center_left_col = QWidget()
        center_left_col.setFixedWidth(200)
        center_left_col.setStyleSheet("background: transparent;")
        cl_lay = QVBoxLayout(center_left_col)
        cl_lay.setContentsMargins(0, 0, 0, 0)
        cl_lay.setSpacing(8)

        self.core_status_widget = CoreStatusWidget()
        cl_lay.addWidget(self.core_status_widget)

        # Relocated Activity Log (now at the bottom of the center-left column)
        # Adding log header to resemble the J.A.R.V.I.S activity log section
        log_hdr_lay = QHBoxLayout()
        log_hdr_lay.setContentsMargins(4, 0, 4, 0)
        log_hdr = QLabel("◈ ACTIVITY LOG")
        log_hdr.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        log_hdr.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        log_hdr_lay.addWidget(log_hdr)
        log_hdr_lay.addStretch()
        all_lbl = QLabel("ALL ▾ ☰")
        all_lbl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        all_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        log_hdr_lay.addWidget(all_lbl)
        cl_lay.addLayout(log_hdr_lay)

        self._log = LogWidget()
        cl_lay.addWidget(self._log, stretch=1)
        
        center_lay.addWidget(center_left_col)

        # Center-Right HUD & Voice Interface
        center_right_col = QWidget()
        center_right_lay = QVBoxLayout(center_right_col)
        center_right_lay.setContentsMargins(0, 0, 0, 0)
        center_right_lay.setSpacing(8)

        # Live camera container
        _cam_cont = QWidget()
        _cam_cont.setStyleSheet("background: #000308;")
        _cam_v = QVBoxLayout(_cam_cont)
        _cam_v.setContentsMargins(0, 0, 0, 0)
        _cam_v.setSpacing(0)
        _cam_hdr = QHBoxLayout()
        _cam_hdr.setContentsMargins(8, 5, 8, 5)
        _cam_title = QLabel("◈  CAMERA FEED")
        _cam_title.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        _cam_title.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        _cam_hdr.addWidget(_cam_title)
        _cam_hdr.addStretch()
        _cam_x = QPushButton("✕  CLOSE")
        _cam_x.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        _cam_x.setCursor(Qt.CursorShape.PointingHandCursor)
        _cam_x.setStyleSheet(f"""
            QPushButton {{
                color: {C.TEXT_DIM}; background: transparent;
                border: none; padding: 2px 6px;
            }}
            QPushButton:hover {{ color: {C.PRI}; }}
        """)
        _cam_x.clicked.connect(self.stop_camera_stream)
        _cam_hdr.addWidget(_cam_x)
        _cam_v.addLayout(_cam_hdr)
        self._cam_live_lbl = QLabel()
        self._cam_live_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._cam_live_lbl.setStyleSheet("background: transparent;")
        self._cam_live_lbl.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        _cam_v.addWidget(self._cam_live_lbl, stretch=1)

        self.hud = HudCanvas(face_path, _display)
        self.hud.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self._hud_cam_stack = QStackedWidget()
        self._hud_cam_stack.addWidget(self.hud)
        self._hud_cam_stack.addWidget(_cam_cont)

        # Overlay a Live Feed button on top right of HUD
        self.hud_container = QWidget()
        self.hud_container.setStyleSheet("background: transparent;")
        hud_container_lay = QVBoxLayout(self.hud_container)
        hud_container_lay.setContentsMargins(0, 0, 0, 0)
        hud_container_lay.setSpacing(0)
        
        hud_hdr = QHBoxLayout()
        hud_hdr.setContentsMargins(0, 4, 8, 0)
        hud_hdr.addStretch()
        self.live_feed_btn = QPushButton("● LIVE CAM FEED")
        self.live_feed_btn.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        self.live_feed_btn.setStyleSheet(f"""
            QPushButton {{
                color: {C.PRI}; background: {C.PANEL2};
                border: 1px solid {C.BORDER}; border-radius: 10px;
                padding: 3px 10px;
            }}
            QPushButton:hover {{
                border-color: {C.PRI}; background: {C.PRI_GHO};
            }}
        """)
        self.live_feed_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.live_feed_btn.clicked.connect(self.start_camera_stream)
        hud_hdr.addWidget(self.live_feed_btn)
        
        hud_container_lay.addLayout(hud_hdr)
        hud_container_lay.addWidget(self._hud_cam_stack, stretch=1)

        # Voice Interface waveform
        self.voice_interface = VoiceInterfaceWidget(self)
        
        # Splitter to allow resizing of content results
        self._content_panel = self._build_content_panel()
        self._center_split = QSplitter(Qt.Orientation.Vertical)
        self._center_split.setStyleSheet(f"""
            QSplitter::handle {{
                background: {C.BORDER};
                height: 4px;
            }}
            QSplitter::handle:hover {{
                background: {C.PRI_DIM};
            }}
        """)
        
        # Center right column widget containing HUD + Voice interface
        cr_hud_voice = QWidget()
        cr_hud_voice_lay = QVBoxLayout(cr_hud_voice)
        cr_hud_voice_lay.setContentsMargins(0, 0, 0, 0)
        cr_hud_voice_lay.setSpacing(8)
        cr_hud_voice_lay.addWidget(self.hud_container, stretch=1)
        cr_hud_voice_lay.addWidget(self.voice_interface, stretch=0)

        self._center_split.addWidget(cr_hud_voice)
        self._center_split.addWidget(self._content_panel)
        self._center_split.setStretchFactor(0, 3)
        self._center_split.setStretchFactor(1, 1)
        self._center_split.setCollapsible(0, False)
        
        center_right_lay.addWidget(self._center_split)
        center_lay.addWidget(center_right_col, stretch=1)

        body.addWidget(center_widget, stretch=1)

        self._right_panel = self._build_right_panel()
        body.addWidget(self._right_panel, stretch=0)

        root.addLayout(body, stretch=1)
        root.addWidget(self._build_footer())
        
        # Add helper function for quick command execution
        self.on_text_command_original = None

        self._quick_drawer = self._build_quick_drawer()
        self._update_autostart_btn(self._check_autostart())
        from memory.config_manager import get_brief_enabled as _gbe
        self._update_brief_btn(_gbe())

        self._clock_tmr = QTimer(self)
        self._clock_tmr.timeout.connect(self._tick_clock)
        self._clock_tmr.start(1000)
        self._tick_clock()

        # Metrik güncelleme timer'ı
        self._metric_tmr = QTimer(self)
        self._metric_tmr.timeout.connect(self._update_metrics)
        self._metric_tmr.start(2000)
        self._update_metrics()

        self._wifi_tmr = QTimer(self)
        self._wifi_tmr.timeout.connect(self._update_wifi_status)
        self._wifi_tmr.start(3000)
        self._update_wifi_status()

        self._log_sig.connect(self._log.append_log)
        self._state_sig.connect(self._apply_state)
        self._content_sig.connect(self._show_content)
        self._reconfig_sig.connect(self._show_setup)
        self._camera_sig.connect(self._show_camera_frame)
        self._cam_stream_sig.connect(self._on_cam_stream)
        self._cam_frame_sig.connect(self._on_cam_frame)
        self._clipboard_sig.connect(self._show_clipboard_panel)
        self._cam_stop = threading.Event()

        # Camera preview overlay (child of central widget, positioned in resizeEvent)
        self._cam_preview = _CameraPreview(self.centralWidget())

        # Clipboard panel (child of central widget, bottom-center)
        self._clipboard_panel = ClipboardPanel(self.centralWidget())
        self._clipboard_panel.action_requested.connect(self._on_clipboard_action)
        QApplication.clipboard().dataChanged.connect(self._on_clipboard_changed)

        self._overlay: SetupOverlay | None = None
        self._ready = self._check_config()
        if not self._ready:
            self._show_setup()

        sc_mute = QShortcut(QKeySequence("F4"), self)
        sc_mute.activated.connect(self._toggle_mute)
        sc_full = QShortcut(QKeySequence("F11"), self)
        sc_full.activated.connect(self._toggle_fullscreen)
        sc_intr = QShortcut(QKeySequence("Escape"), self)
        sc_intr.activated.connect(self._do_interrupt)

    def _trigger_text_command(self, text):
        if self.on_text_command:
            self.on_text_command(text)
        self._log.append_log(f"you: {text}")

    def _show_camera_frame(self, img_bytes: bytes):
        """Slot — display camera preview overlay (main thread)."""
        self._cam_preview.show_frame(img_bytes)
        cw = self.centralWidget()
        pw = _CameraPreview._W
        ph = self._cam_preview.height()
        self._cam_preview.setGeometry(
            cw.width() - _RIGHT_W - pw - 12,
            cw.height() - ph - 28,
            pw, ph,
        )

    # --- Live camera stream in HUD area ------------------------------------
    def _on_cam_stream(self, start: bool) -> None:
        if start:
            self._hud_cam_stack.setCurrentIndex(1)
        else:
            self._hud_cam_stack.setCurrentIndex(0)
            self._cam_live_lbl.clear()

    def _on_cam_frame(self, data: bytes) -> None:
        px = QPixmap()
        if px.loadFromData(data):
            w, h = self._cam_live_lbl.width(), self._cam_live_lbl.height()
            if w > 1 and h > 1 and (px.width() != w or px.height() != h):
                px = px.scaled(w, h,
                               Qt.AspectRatioMode.KeepAspectRatio,
                               Qt.TransformationMode.FastTransformation)
            self._cam_live_lbl.setPixmap(px)

    def get_latest_camera_frame(self) -> bytes | None:
        return getattr(self, "_latest_cam_frame_bytes", None)

    def start_camera_stream(self) -> None:
        self._cam_stop.clear()
        self._cam_stream_sig.emit(True)
        if hasattr(self, "_cam_thread") and self._cam_thread and self._cam_thread.is_alive():
            return
        self._cam_thread = threading.Thread(target=self._cam_loop, daemon=True, name="cam-stream")
        self._cam_thread.start()

    def _cam_loop(self) -> None:
        try:
            import cv2
            cam_idx = 0
            try:
                import json as _j
                cfg = _j.loads((CONFIG_DIR / "api_keys.json").read_text())
                cam_idx = int(cfg.get("camera_index", 0))
            except Exception:
                pass
            try:
                backend = cv2.CAP_DSHOW if _OS == "Windows" else cv2.CAP_ANY
            except AttributeError:
                backend = 0

            cap = None
            for try_idx in [cam_idx, 0, 1]:
                for try_backend in [backend, cv2.CAP_DSHOW, cv2.CAP_ANY, 0]:
                    try:
                        c = cv2.VideoCapture(try_idx, try_backend)
                        if c.isOpened():
                            c.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                            c.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                            r, f = c.read()
                            if r and f is not None and f.size > 0:
                                cap = c
                                break
                            c.release()
                    except Exception:
                        pass
                if cap and cap.isOpened():
                    break

            if not cap or not cap.isOpened():
                print("[Camera] ⚠️ Could not open any valid camera device")
                return

            # warm-up frames
            for _ in range(3):
                cap.read()

            fail_count = 0
            # 22 FPS (~0.045s) loop to keep GUI responsiveness crystal clear & low CPU/RAM
            while not self._cam_stop.wait(0.045) and cap.isOpened():
                ret, frame = cap.read()
                if ret and frame is not None and frame.size > 0:
                    fail_count = 0
                    _, buf = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 55])
                    data_bytes = buf.tobytes()
                    self._latest_cam_frame_bytes = data_bytes
                    self._cam_frame_sig.emit(data_bytes)
                else:
                    fail_count += 1
                    if fail_count > 30:
                        print("[Camera] ⚠️ Camera stream stopped returning frames")
                        break
                    time.sleep(0.02)
            cap.release()
        except Exception as e:
            print(f"[Camera] Stream error: {e}")
        finally:
            self._cam_stream_sig.emit(False)

    def stop_camera_stream(self) -> None:
        self._cam_stop.set()
        self._latest_cam_frame_bytes = None

    # ------------------------------------------------------------------
    # Icon generation — arc-reactor style, rendered with Pillow
    # ------------------------------------------------------------------
    @staticmethod
    def _build_jarvis_icon(out_path: Path) -> bool:
        """
        Render a JARVIS arc-reactor icon at 4× resolution and downsample
        for crisp results at all sizes. Saves a multi-res .ico to out_path.
        Returns True on success.
        """
        try:
            import math
            import PIL.Image
            import PIL.ImageDraw
            import PIL.ImageFilter
        except ImportError:
            return False

        CYAN   = (0, 212, 255)
        DIM    = (0, 100, 140)
        DARK   = (0, 6, 10)
        GLOW   = (0, 160, 200)
        WHITE  = (220, 240, 255)

        def _render(sz: int) -> PIL.Image.Image:
            S  = sz * 4                     # draw at 4× then downscale
            img = PIL.Image.new("RGBA", (S, S), (0, 0, 0, 0))
            d   = PIL.ImageDraw.Draw(img)
            cx = cy = S // 2

            # ── filled background circle ──────────────────────────────────
            R = S // 2 - 2
            d.ellipse([cx-R, cy-R, cx+R, cy+R], fill=(*DARK, 255))

            # ── outer border ring ─────────────────────────────────────────
            lw = max(2, S // 40)
            d.ellipse([cx-R, cy-R, cx+R, cy+R],
                      outline=(*CYAN, 220), width=lw)

            # ── mid decorative ring ───────────────────────────────────────
            R2 = int(R * 0.72)
            d.ellipse([cx-R2, cy-R2, cx+R2, cy+R2],
                      outline=(*DIM, 180), width=max(1, lw // 2))

            # ── 6 radial spokes (hex bolt) ────────────────────────────────
            R_inner = int(R * 0.30)
            R_outer = int(R * 0.62)
            spoke_w = max(1, S // 80)
            for i in range(6):
                angle = math.radians(i * 60 - 30)
                x1 = cx + int(R_inner * math.cos(angle))
                y1 = cy + int(R_inner * math.sin(angle))
                x2 = cx + int(R_outer * math.cos(angle))
                y2 = cy + int(R_outer * math.sin(angle))
                d.line([x1, y1, x2, y2], fill=(*GLOW, 200), width=spoke_w)

            # ── 6 tick marks on outer ring ────────────────────────────────
            for i in range(6):
                angle = math.radians(i * 60)
                for dr in range(lw * 2):
                    rx = (R - lw - dr)
                    d.point(
                        [cx + int(rx * math.cos(angle)),
                         cy + int(rx * math.sin(angle))],
                        fill=(*WHITE, 220),
                    )

            # ── inner glowing ring ────────────────────────────────────────
            Ri = int(R * 0.26)
            d.ellipse([cx-Ri, cy-Ri, cx+Ri, cy+Ri],
                      outline=(*CYAN, 255), width=max(2, lw))

            # ── bright glow soft blur applied before core ─────────────────
            # (draw a slightly larger cyan circle on a separate layer)
            glow_layer = PIL.Image.new("RGBA", (S, S), (0, 0, 0, 0))
            gd = PIL.ImageDraw.Draw(glow_layer)
            Rc = int(R * 0.13)
            gd.ellipse([cx-Rc*2, cy-Rc*2, cx+Rc*2, cy+Rc*2],
                       fill=(*CYAN, 110))
            glow_layer = glow_layer.filter(PIL.ImageFilter.GaussianBlur(S // 14))
            img = PIL.Image.alpha_composite(img, glow_layer)
            d   = PIL.ImageDraw.Draw(img)

            # ── core dot ──────────────────────────────────────────────────
            d.ellipse([cx-Rc, cy-Rc, cx+Rc, cy+Rc], fill=(*WHITE, 255))

            # ── downscale to target size ──────────────────────────────────
            return img.resize((sz, sz), PIL.Image.LANCZOS)

        try:
            sizes  = [256, 128, 64, 48, 32, 16]
            frames = [_render(s) for s in sizes]
            frames[0].save(
                out_path,
                format="ICO",
                append_images=frames[1:],
                sizes=[(s, s) for s in sizes],
            )
            return True
        except Exception as e:
            print(f"[Shortcut] ⚠️  Icon generation failed: {e}")
            return False

    @staticmethod
    def _get_desktop_dir() -> Path:
        """
        Resolve the user's REAL desktop directory instead of assuming
        ~/Desktop, which breaks when:
          • OneDrive "Known Folder Move" relocates the desktop
            (C:/Users/x/OneDrive/Desktop) — very common on Win 10/11;
          • the XDG desktop is localized on Linux (~/Masaüstü,
            ~/Schreibtisch, ~/Bureau, …).
        Falls back to ~/Desktop only as a last resort.
        """
        home = Path.home()
        _os = platform.system()

        if _os == "Windows":
            # ── 1) SHGetKnownFolderPath(FOLDERID_Desktop) — the canonical
            #       answer; follows OneDrive redirection. No dependencies. ──
            try:
                import ctypes
                from ctypes import wintypes

                class _GUID(ctypes.Structure):
                    _fields_ = [("Data1", wintypes.DWORD),
                                ("Data2", wintypes.WORD),
                                ("Data3", wintypes.WORD),
                                ("Data4", ctypes.c_ubyte * 8)]

                # FOLDERID_Desktop {B4BFCC3A-DB2C-424C-B029-7FE99A87C641}
                fid = _GUID(0xB4BFCC3A, 0xDB2C, 0x424C,
                            (ctypes.c_ubyte * 8)(0xB0, 0x29, 0x7F, 0xE9,
                                                 0x9A, 0x87, 0xC6, 0x41))
                buf = ctypes.c_wchar_p()
                if ctypes.windll.shell32.SHGetKnownFolderPath(
                        ctypes.byref(fid), 0, None, ctypes.byref(buf)) == 0:
                    p = Path(buf.value)
                    ctypes.windll.ole32.CoTaskMemFree(buf)
                    if p.is_dir():
                        return p
            except Exception:
                pass

            # ── 2) Registry: User Shell Folders (may contain %VARS%) ──────
            try:
                import winreg
                with winreg.OpenKey(
                        winreg.HKEY_CURRENT_USER,
                        r"Software\Microsoft\Windows\CurrentVersion"
                        r"\Explorer\User Shell Folders") as key:
                    val, _t = winreg.QueryValueEx(key, "Desktop")
                p = Path(os.path.expandvars(val))
                if p.is_dir():
                    return p
            except Exception:
                pass

        elif _os == "Linux":
            # ── xdg-user-dir honours localized names (~/Masaüstü, …) ──────
            try:
                out = subprocess.run(["xdg-user-dir", "DESKTOP"],
                                     capture_output=True, text=True, timeout=5)
                p = Path(out.stdout.strip())
                if out.stdout.strip() and p != home and p.is_dir():
                    return p
            except Exception:
                pass
            try:
                cfg = home / ".config" / "user-dirs.dirs"
                for line in cfg.read_text(encoding="utf-8").splitlines():
                    line = line.strip()
                    if line.startswith("XDG_DESKTOP_DIR"):
                        val = line.split("=", 1)[1].strip().strip('"')
                        p = Path(val.replace("$HOME", str(home)))
                        if p != home and p.is_dir():
                            return p
            except Exception:
                pass

        # macOS: ~/Desktop is always the real path (localization is
        # display-only). Everything else lands here as a last resort.
        return home / "Desktop"

    @staticmethod
    def _create_lnk_windows(lnk: str, target: str, args: str,
                             work_dir: str, icon_loc: str) -> None:
        """
        Create a Windows .lnk shortcut WITHOUT launching PowerShell or cmd.
        Tries win32com (pywin32) first; falls back to wscript.exe + VBScript.
        wscript.exe is a GUI-mode host — it never opens a console window.
        Raises on failure so the caller can log a useful error.
        """
        # ── Option 1: pywin32 (pure Python COM, zero subprocess) ──────────
        com_err: Exception | None = None
        try:
            from win32com.client import Dispatch   # type: ignore
            sh = Dispatch("WScript.Shell")
            sc = sh.CreateShortCut(lnk)
            sc.TargetPath       = target
            sc.Arguments        = f'"{args}"'
            sc.WorkingDirectory = work_dir
            sc.Description      = "J.A.R.V.I.S AI Assistant"
            sc.IconLocation     = icon_loc
            sc.save()
            return
        except ImportError:
            pass
        except Exception as e:            # COM error — still try VBScript
            com_err = e

        # ── Option 2: wscript.exe + VBScript (always available on Windows,
        #    GUI-mode executable — never opens a console window) ────────────
        def q(s: str) -> str:              # escape for a VBScript string literal
            return s.replace('"', '""')

        vbs = "\n".join([
            'On Error Resume Next',
            'Set ws = CreateObject("WScript.Shell")',
            f'Set sc = ws.CreateShortcut("{q(lnk)}")',
            f'sc.TargetPath = "{q(target)}"',
            f'sc.Arguments = Chr(34) & "{q(args)}" & Chr(34)',
            f'sc.WorkingDirectory = "{q(work_dir)}"',
            'sc.Description = "J.A.R.V.I.S AI Assistant"',
            f'sc.IconLocation = "{q(icon_loc)}"',
            'sc.Save',
            'If Err.Number <> 0 Then WScript.Quit 1',
        ])
        import tempfile
        fd, tmp = tempfile.mkstemp(suffix=".vbs")
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                f.write(vbs)
            proc = subprocess.Popen(
                ["wscript.exe", "/nologo", tmp],
                creationflags=subprocess.DETACHED_PROCESS | subprocess.CREATE_NO_WINDOW,
            )
            proc.wait(timeout=10)
        finally:
            try:
                os.unlink(tmp)
            except Exception:
                pass

        if not Path(lnk).exists():
            raise RuntimeError(
                f"could not create '{lnk}'"
                + (f" ({com_err})" if com_err else "")
            )

    def _create_desktop_shortcut(self):
        """
        Create a desktop shortcut on Windows / macOS / Linux.
        Never opens a terminal, console, or PowerShell window on any platform.
        """
        import stat as _stat
        script  = Path(__file__).resolve().parent / "main.py"
        python  = Path(sys.executable)
        desktop = self._get_desktop_dir()

        # Arc-reactor icon (.ico — also exported as .png for Linux/macOS)
        ico_path = Path(__file__).resolve().parent / "config" / "jarvis.ico"
        if not ico_path.exists():
            self._build_jarvis_icon(ico_path)

        try:
            _os = platform.system()
            desktop.mkdir(parents=True, exist_ok=True)

            # ── Windows ───────────────────────────────────────────────────────
            if _os == "Windows":
                pythonw  = python.parent / "pythonw.exe"
                target   = str(pythonw if pythonw.exists() else python)
                lnk      = str(desktop / "J.A.R.V.I.S.lnk")
                icon_loc = str(ico_path) if ico_path.exists() else f"{target},0"
                self._create_lnk_windows(lnk, target, str(script),
                                         str(script.parent), icon_loc)

            # ── macOS — proper .app bundle (no Terminal window) ───────────────
            elif _os == "Darwin":
                app     = desktop / "J.A.R.V.I.S.app"
                mac_dir = app / "Contents" / "MacOS"
                res_dir = app / "Contents" / "Resources"
                mac_dir.mkdir(parents=True, exist_ok=True)
                res_dir.mkdir(exist_ok=True)

                # Launcher executable (bash — runs as background process,
                # macOS does NOT open Terminal for executables inside .app bundles)
                launcher = mac_dir / "JARVIS"
                launcher.write_text(
                    "#!/usr/bin/env bash\n"
                    f'cd "{script.parent}"\n'
                    f'exec "{python}" "{script}"\n'
                )
                launcher.chmod(launcher.stat().st_mode
                               | _stat.S_IEXEC | _stat.S_IXGRP | _stat.S_IXOTH)

                # Minimal Info.plist (required for .app recognition)
                (app / "Contents" / "Info.plist").write_text(
                    '<?xml version="1.0" encoding="UTF-8"?>\n'
                    '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                    '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                    '<plist version="1.0"><dict>\n'
                    '  <key>CFBundleExecutable</key><string>JARVIS</string>\n'
                    '  <key>CFBundleIdentifier</key>'
                    '<string>com.jarvis.assistant</string>\n'
                    '  <key>CFBundleName</key><string>J.A.R.V.I.S</string>\n'
                    '  <key>CFBundlePackageType</key><string>APPL</string>\n'
                    '  <key>CFBundleVersion</key><string>1.0</string>\n'
                    '</dict></plist>\n'
                )

                # Optional: copy icon as .icns (skip silently if Pillow is missing)
                try:
                    import PIL.Image
                    icns = res_dir / "AppIcon.icns"
                    PIL.Image.open(ico_path).save(icns, format="ICNS")
                    # Inject icon reference into plist
                    plist = app / "Contents" / "Info.plist"
                    txt = plist.read_text()
                    plist.write_text(
                        txt.replace(
                            '</dict></plist>',
                            '  <key>CFBundleIconFile</key>'
                            '<string>AppIcon</string>\n</dict></plist>\n',
                        )
                    )
                except Exception:
                    pass  # icon is optional

            # ── Linux — .desktop file (Terminal=false, no console) ────────────
            else:
                # Export .ico → .png for better desktop integration
                png_path = ico_path.with_suffix(".png")
                if not png_path.exists() and ico_path.exists():
                    try:
                        import PIL.Image
                        PIL.Image.open(ico_path).resize(
                            (256, 256), PIL.Image.LANCZOS
                        ).save(png_path, format="PNG")
                    except Exception:
                        png_path = ico_path  # fallback to .ico

                icon_line = f"Icon={png_path}\n" if png_path.exists() else ""
                desk = desktop / "J.A.R.V.I.S.desktop"
                desk.write_text(
                    "[Desktop Entry]\n"
                    "Name=J.A.R.V.I.S\n"
                    f'Exec="{python}" "{script}"\n'
                    f"Path={script.parent}\n"
                    "Type=Application\n"
                    "Terminal=false\n"
                    "Categories=Utility;\n"
                    + icon_line
                )
                desk.chmod(desk.stat().st_mode | 0o755)
                # GNOME refuses to launch desktop files until they are
                # marked trusted ("Allow Launching") — do it automatically.
                try:
                    subprocess.run(
                        ["gio", "set", str(desk),
                         "metadata::trusted", "true"],
                        capture_output=True, timeout=5,
                    )
                except Exception:
                    pass  # non-GNOME desktops don't need (or have) gio

            self._log.append_log(f"SYS: Desktop shortcut created in '{desktop}'.")
        except Exception as e:
            self._log.append_log(
                f"ERR: Shortcut failed — {e} (desktop dir: '{desktop}')"
            )

    def _toggle_fullscreen(self):
        if self.isFullScreen():
            self.showNormal()
        else:
            self.showFullScreen()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cw = self.centralWidget()
        if self._overlay and self._overlay.isVisible():
            ow, oh = 460, 390
            self._overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )
        if self._remote_overlay and self._remote_overlay.isVisible():
            ow, oh = RemoteKeyOverlay._OW, RemoteKeyOverlay._OH
            self._remote_overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )
        if self._customize_overlay and self._customize_overlay.isVisible():
            ow, oh = CustomizeOverlay._OW, CustomizeOverlay._OH
            self._customize_overlay.setGeometry(
                (cw.width()  - ow) // 2,
                (cw.height() - oh) // 2,
                ow, oh,
            )
        # Camera preview — bottom-right corner of the center/HUD area
        pw = _CameraPreview._W
        ph = self._cam_preview.height() or _CameraPreview._H
        self._cam_preview.setGeometry(
            cw.width() - _RIGHT_W - pw - 12,
            cw.height() - ph - 28,
            pw, ph,
        )
        # Clipboard panel — bottom-center
        if hasattr(self, '_clipboard_panel') and self._clipboard_panel.isVisible():
            self._position_clipboard_panel()
        # Quick drawer — reposition if open
        if hasattr(self, '_quick_drawer') and self._quick_drawer.isVisible():
            self._position_quick_drawer()

    def _update_metrics(self):
        snap = _metrics.snapshot()
        now_t = time.time()

        # CPU
        cpu = snap["cpu"]
        self._bar_cpu.set_value(cpu, f"{cpu:.0f}%")

        # MEM
        mem = snap["mem"]
        self._bar_mem.set_value(mem, f"{mem:.0f}%")

        # NET
        net = snap["net"]
        if net < 1.0:
            net_str = f"{net*1024:.0f}KB/s"
        else:
            net_str = f"{net:.1f}MB/s"
        net_pct = min(100, net * 10)  # 10 MB/s = %100
        self._bar_net.set_value(net_pct, net_str)

        # GPU
        gpu = snap["gpu"]
        if gpu >= 0:
            self._bar_gpu.set_value(gpu, f"{gpu:.0f}%")
        else:
            gpu_calc = min(100.0, max(8.0, (cpu * 0.35) + (mem * 0.15) + (math.sin(now_t * 0.4) * 3.5 + 10.0)))
            self._bar_gpu.set_value(gpu_calc, f"{gpu_calc:.0f}%")

        # TMP
        tmp = snap["tmp"]
        if tmp >= 0:
            tmp_pct = min(100, (tmp / 100) * 100)
            self._bar_tmp.set_value(tmp_pct, f"{tmp:.0f}°C")
        else:
            tmp_calc = min(95.0, max(38.0, 42.0 + (cpu * 0.26) + (math.cos(now_t * 0.25) * 1.5)))
            self._bar_tmp.set_value(tmp_calc, f"{tmp_calc:.0f}°C")
            tmp = tmp_calc

        # Dynamic System Status update
        if hasattr(self, "_opt_lbl") and hasattr(self, "_opt_icon") and hasattr(self, "_sub_status"):
            if cpu > 85 or mem > 90 or tmp > 80:
                self._opt_icon.setText("🔴")
                self._opt_lbl.setText("HEAVY LOAD")
                self._opt_lbl.setStyleSheet(f"color: {C.RED}; border: none; background: transparent;")
                self._sub_status.setText("Resource Usage Elevated")
                self._sub_status.setStyleSheet(f"color: {C.RED}; border: none; background: transparent;")
            elif cpu > 65 or mem > 75:
                self._opt_icon.setText("🟡")
                self._opt_lbl.setText("MODERATE")
                self._opt_lbl.setStyleSheet(f"color: {C.ACC2}; border: none; background: transparent;")
                self._sub_status.setText("System Operating Normally")
                self._sub_status.setStyleSheet(f"color: {C.ACC2}; border: none; background: transparent;")
            else:
                self._opt_icon.setText("🟢")
                self._opt_lbl.setText("OPTIMAL")
                self._opt_lbl.setStyleSheet(f"color: {C.GREEN}; border: none; background: transparent;")
                self._sub_status.setText("All Systems Operational")
                self._sub_status.setStyleSheet(f"color: {C.GREEN_D}; border: none; background: transparent;")

        if hasattr(self, "core_status_widget") and self.core_status_widget:
            self.core_status_widget.update_status(cpu, mem, net * 1024.0)

        try:
            boot_t  = psutil.boot_time()
            elapsed = time.time() - boot_t
            h = int(elapsed // 3600)
            m = int((elapsed % 3600) // 60)
            self._uptime_lbl.setText(f"UP  {h:02d}:{m:02d}")
        except Exception:
            self._uptime_lbl.setText("UP  --:--")

        try:
            proc_count = len(psutil.pids())
            self._proc_lbl.setText(f"PROC  {proc_count}")
        except Exception:
            self._proc_lbl.setText("PROC  --")


    def _build_header(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(54)
        w.setStyleSheet(f"background: {C.DARK}; border-bottom: 1px solid {C.BORDER};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(16, 0, 16, 0)

        # Left Header Title — Only J.A.R.V.I.S. text
        logo = QLabel("J.A.R.V.I.S.")
        logo.setFont(QFont(_ETHNOCENTRIC_FONT, 14, QFont.Weight.Bold))
        logo.setStyleSheet(f"color: {C.PRI}; border: none; background: transparent; letter-spacing: 2px;")
        lay.addWidget(logo)
        lay.addStretch()

        # Clock & Date on the Right
        right_col = QVBoxLayout()
        right_col.setSpacing(1)
        right_col.setContentsMargins(0, 4, 0, 4)

        self._clock_lbl = QLabel("00:00:00")
        clock_font = QFont(_DS_DIGI_FONT, 18)
        clock_font.setItalic(True)
        self._clock_lbl.setFont(clock_font)
        self._clock_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent; border: none;")
        self._clock_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._clock_lbl)

        self._date_lbl = QLabel("")
        self._date_lbl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        self._date_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent; border: none;")
        self._date_lbl.setAlignment(Qt.AlignmentFlag.AlignRight)
        right_col.addWidget(self._date_lbl)

        lay.addLayout(right_col)

        self._title_lbl = QLabel()
        self._sub_lbl = QLabel()

        return w

    def _tick_clock(self):
        self._clock_lbl.setText(time.strftime("%H:%M:%S"))
        self._date_lbl.setText(time.strftime("%a %d %b %Y"))

    def _build_left_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(_LEFT_W)
        w.setStyleSheet(f"background: {C.DARK}; border-right: 1px solid {C.BORDER};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # 1. SYSTEM OVERVIEW
        hdr = QLabel("◈ SYSTEM OVERVIEW")
        hdr.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; "
                          f"border-bottom: 1px solid {C.BORDER}; padding-bottom: 4px;")
        lay.addWidget(hdr)
        lay.addSpacing(2)

        self._bar_cpu = MetricBar("CPU", C.PRI)
        self._bar_mem = MetricBar("MEMORY", C.ACC2)
        self._bar_net = MetricBar("NETWORK", C.GREEN)
        self._bar_gpu = MetricBar("GPU", C.ACC)
        self._bar_tmp = MetricBar("TEMP", "#ff3355")

        for bar in [self._bar_cpu, self._bar_mem, self._bar_net, self._bar_gpu, self._bar_tmp]:
            lay.addWidget(bar)

        lay.addSpacing(6)

        # 2. SYSTEM STATUS
        status_hdr = QLabel("◈ SYSTEM STATUS")
        status_hdr.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        status_hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; "
                                 f"border-bottom: 1px solid {C.BORDER}; padding-bottom: 4px;")
        lay.addWidget(status_hdr)

        status_box = QWidget()
        status_box.setStyleSheet(f"background: {C.PANEL2}; border: 1px solid {C.BORDER}; border-radius: 4px;")
        sb_lay = QVBoxLayout(status_box)
        sb_lay.setContentsMargins(8, 6, 8, 6)
        sb_lay.setSpacing(4)

        opt_lay = QHBoxLayout()
        opt_lay.setSpacing(4)
        self._opt_icon = QLabel("🟢")
        self._opt_icon.setFont(QFont("Segoe UI Emoji", 7))
        self._opt_icon.setStyleSheet("border: none; background: transparent;")
        self._opt_lbl = QLabel("OPTIMAL")
        self._opt_lbl.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        self._opt_lbl.setStyleSheet(f"color: {C.GREEN}; border: none; background: transparent;")
        opt_lay.addWidget(self._opt_icon)
        opt_lay.addWidget(self._opt_lbl)
        opt_lay.addStretch()
        sb_lay.addLayout(opt_lay)

        self._sub_status = QLabel("All Systems Operational")
        self._sub_status.setFont(QFont(_PRIMARY_FONT, 7))
        self._sub_status.setStyleSheet(f"color: {C.GREEN_D}; border: none; background: transparent;")
        sb_lay.addWidget(self._sub_status)

        self._uptime_lbl = QLabel("UPTIME  --:--")
        self._uptime_lbl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        self._uptime_lbl.setStyleSheet(f"color: {C.WHITE}; border: none; background: transparent; padding-top: 4px;")
        sb_lay.addWidget(self._uptime_lbl)

        self._proc_lbl = QLabel("PROCESSES  --")
        self._proc_lbl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        self._proc_lbl.setStyleSheet(f"color: {C.TEXT_MED}; border: none; background: transparent;")
        sb_lay.addWidget(self._proc_lbl)

        os_name = {"Windows": "Windows 11", "Darwin": "macOS", "Linux": "Linux"}.get(_OS, _OS)
        os_lbl = QLabel(f"OS      {os_name}")
        os_lbl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        os_lbl.setStyleSheet(f"color: {C.ACC2}; border: none; background: transparent;")
        sb_lay.addWidget(os_lbl)

        lay.addWidget(status_box)
        lay.addSpacing(6)

        # 3. AI CORE
        ai_hdr = QLabel("◈ AI CORE")
        ai_hdr.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        ai_hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; "
                             f"border-bottom: 1px solid {C.BORDER}; padding-bottom: 4px;")
        lay.addWidget(ai_hdr)
        
        self.ai_core_widget = AICoreWidget()
        lay.addWidget(self.ai_core_widget)

        # 4. SECURITY PROTOCOL
        sec_box = QWidget()
        sec_box.setStyleSheet(f"background: {C.PANEL2}; border: 1px solid {C.BORDER_A}; border-radius: 4px;")
        sec_lay = QVBoxLayout(sec_box)
        sec_lay.setContentsMargins(6, 6, 6, 6)
        sec_lay.setSpacing(2)
        
        sec_title = QLabel("🛡 SECURITY PROTOCOL")
        sec_title.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        sec_title.setStyleSheet(f"color: {C.TEXT_MED}; border: none; background: transparent;")
        sec_lay.addWidget(sec_title)
        
        sec_status = QLabel("MAXIMUM")
        sec_status.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        sec_status.setStyleSheet(f"color: {C.PRI}; border: none; background: transparent;")
        sec_lay.addWidget(sec_status)
        
        lay.addWidget(sec_box)
        return w

    def _build_right_panel(self) -> QWidget:
        w = QWidget()
        w.setFixedWidth(_RIGHT_W)
        w.setStyleSheet(f"background: {C.DARK}; border-left: 1px solid {C.BORDER};")
        lay = QVBoxLayout(w)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(8)

        # 1. LIVE NEWS & UPDATES (Visual feed)
        self.news_updates_widget = NewsUpdatesWidget()
        lay.addWidget(self.news_updates_widget, stretch=1)

        # 2. COMPACT FILE UPLOAD BUTTON
        self._drop_zone = FileDropZone()
        self._drop_zone.file_selected.connect(self._on_file_selected)
        lay.addWidget(self._drop_zone, stretch=0)

        # 2. COMMAND INPUT
        input_hdr = QLabel("◈ COMMAND INPUT")
        input_hdr.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        input_hdr.setStyleSheet(f"color: {C.PRI}; background: transparent; "
                                 f"border-bottom: 1px solid {C.BORDER}; padding-bottom: 4px;")
        lay.addWidget(input_hdr)
        
        lay.addLayout(self._build_input_row())

        voice_status_lay = QHBoxLayout()
        voice_status_lay.setContentsMargins(2, 0, 2, 0)
        
        self.rec_icon = VectorIcon("mic", C.TEXT_MED)
        voice_status_lay.addWidget(self.rec_icon)
        voice_rec_lbl = QLabel(" VOICE RECOGNITION")
        voice_rec_lbl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        voice_rec_lbl.setStyleSheet(f"color: {C.TEXT_MED}; background: transparent;")
        voice_status_lay.addWidget(voice_rec_lbl)
        
        voice_status_lbl = QLabel("ACTIVE")
        voice_status_lbl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        voice_status_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent;")
        voice_status_lay.addWidget(voice_status_lbl)
        voice_status_lay.addStretch()
        lay.addLayout(voice_status_lay)

        # Bottom operational buttons with VectorIconButton
        bot_btns = QHBoxLayout()
        bot_btns.setSpacing(6)
        
        self._interrupt_btn = VectorIconButton("   STOP", "stop", C.MUTED_C)
        self._interrupt_btn.setFixedHeight(24)
        self._interrupt_btn.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        self._interrupt_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._interrupt_btn.setStyleSheet(f"""
            QPushButton {{
                background: #140008; color: {C.MUTED_C};
                border: 1px solid {C.MUTED_C}; border-radius: 3px;
                padding-left: 20px;
            }}
            QPushButton:hover {{
                background: #200010;
            }}
        """)
        self._interrupt_btn.clicked.connect(self._do_interrupt)
        bot_btns.addWidget(self._interrupt_btn, stretch=1)

        self._mute_btn = VectorIconButton("   MUTE", "mic", C.GREEN)
        self._mute_btn.setFixedHeight(24)
        self._mute_btn.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        self._mute_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._mute_btn.clicked.connect(self._toggle_mute)
        self._style_mute_btn()
        bot_btns.addWidget(self._mute_btn, stretch=1)
        
        lay.addLayout(bot_btns)
        return w

    def _build_quick_drawer(self) -> QWidget:
        """Floating overlay panel for Settings / Controls, rendered centered."""
        _BTN_STYLE_PRI = f"""
            QPushButton {{
                background: #00091a; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
                text-align: left; padding: 0 8px;
            }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border-color: {C.PRI}; }}
        """
        _BTN_STYLE_DIM = f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_MED};
                border: 1px solid {C.BORDER}; border-radius: 3px;
                text-align: left; padding: 0 8px;
            }}
            QPushButton:hover {{ color: {C.PRI}; border-color: {C.BORDER_B}; }}
        """

        w = QWidget(self.centralWidget())
        w.setObjectName("QuickDrawer")
        w.setStyleSheet(f"""
            QWidget#QuickDrawer {{
                background: rgba(0, 6, 10, 245);
                border: 1px solid {C.BORDER_B};
                border-radius: 6px;
            }}
        """)
        w.hide()

        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 10, 12, 12)
        lay.setSpacing(6)

        hdr_row = QHBoxLayout()
        hdr = QLabel("◈ CONTROLS")
        hdr.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        hdr.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        hdr_row.addWidget(hdr)
        hdr_row.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(22, 22)
        close_btn.setFont(QFont(_PRIMARY_FONT, 9, QFont.Weight.Bold))
        close_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                color: {C.TEXT_DIM}; background: transparent;
                border: none; border-radius: 3px;
            }}
            QPushButton:hover {{
                color: {C.RED}; background: #20000a;
            }}
        """)
        close_btn.clicked.connect(w.hide)
        hdr_row.addWidget(close_btn)
        lay.addLayout(hdr_row)

        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER}; margin-bottom: 2px;"); lay.addWidget(sep)

        remote_btn = QPushButton("◉  REMOTE CONTROL")
        remote_btn.setFixedHeight(30)
        remote_btn.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        remote_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        remote_btn.setStyleSheet(_BTN_STYLE_PRI)
        remote_btn.clicked.connect(self._open_remote)
        lay.addWidget(remote_btn)

        fs_btn = QPushButton("⛶  FULLSCREEN  [F11]")
        fs_btn.setFixedHeight(26)
        fs_btn.setFont(QFont(_PRIMARY_FONT, 7))
        fs_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fs_btn.setStyleSheet(_BTN_STYLE_DIM)
        fs_btn.clicked.connect(self._toggle_fullscreen)
        lay.addWidget(fs_btn)

        sc_btn = QPushButton("⊞  CREATE DESKTOP SHORTCUT")
        sc_btn.setFixedHeight(26)
        sc_btn.setFont(QFont(_PRIMARY_FONT, 7))
        sc_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        sc_btn.setStyleSheet(_BTN_STYLE_DIM)
        sc_btn.clicked.connect(self._create_desktop_shortcut)
        lay.addWidget(sc_btn)

        self._autostart_btn = QPushButton("◉  AUTO-START: OFF")
        self._autostart_btn.setFixedHeight(26)
        self._autostart_btn.setFont(QFont(_PRIMARY_FONT, 7))
        self._autostart_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._autostart_btn.clicked.connect(self._toggle_autostart)
        lay.addWidget(self._autostart_btn)

        cust_btn = QPushButton("⚙  CUSTOMISE ASSISTANT")
        cust_btn.setFixedHeight(26)
        cust_btn.setFont(QFont(_PRIMARY_FONT, 7))
        cust_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        cust_btn.setStyleSheet(_BTN_STYLE_DIM)
        cust_btn.clicked.connect(self._open_customize)
        lay.addWidget(cust_btn)

        self._brief_btn = QPushButton()
        self._brief_btn.setFixedHeight(26)
        self._brief_btn.setFont(QFont(_PRIMARY_FONT, 7))
        self._brief_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._brief_btn.clicked.connect(self._toggle_brief)
        lay.addWidget(self._brief_btn)

        w.adjustSize()
        return w

    def _toggle_drawer(self, checked: bool = True):
        if not hasattr(self, '_quick_drawer'):
            return
        if self._quick_drawer.isVisible():
            self._quick_drawer.hide()
        else:
            self._position_quick_drawer()
            self._quick_drawer.show()
            self._quick_drawer.raise_()

    def _position_quick_drawer(self):
        if not hasattr(self, '_quick_drawer'):
            return
        _W = 260
        self._quick_drawer.setFixedWidth(_W)
        self._quick_drawer.adjustSize()
        parent_geo = self.centralWidget().geometry()
        h = self._quick_drawer.sizeHint().height()
        cx = max(0, (parent_geo.width() - _W) // 2)
        cy = max(0, (parent_geo.height() - h) // 2)
        self._quick_drawer.setGeometry(cx, cy, _W, h)

    def _build_input_row(self) -> QHBoxLayout:
        row = QHBoxLayout(); row.setSpacing(5)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Type a command or question…")
        self._input.setFont(QFont(_PRIMARY_FONT, 9))
        self._input.setFixedHeight(30)
        self._input.setStyleSheet(f"""
            QLineEdit {{
                background: #000d14; color: {C.WHITE};
                border: 1px solid {C.BORDER}; border-radius: 3px; padding: 3px 7px;
            }}
            QLineEdit:focus {{ border: 1px solid {C.PRI}; }}
        """)
        self._input.returnPressed.connect(self._send)
        row.addWidget(self._input)

        send = QPushButton("▸")
        send.setFixedSize(30, 30)
        send.setFont(QFont(_PRIMARY_FONT, 11, QFont.Weight.Bold))
        send.setCursor(Qt.CursorShape.PointingHandCursor)
        send.setStyleSheet(f"""
            QPushButton {{
                background: {C.PANEL}; color: {C.PRI};
                border: 1px solid {C.PRI_DIM}; border-radius: 3px;
            }}
            QPushButton:hover {{ background: {C.PRI_GHO}; border: 1px solid {C.PRI}; }}
        """)
        send.clicked.connect(self._send)
        row.addWidget(send)
        return row

    def _build_content_panel(self) -> QWidget:
        """
        Collapsible panel below the HUD — shows search results, news, briefings.
        Hidden by default; appears when show_content() is called.
        """
        w = QWidget()
        w.setObjectName("ContentPanel")
        w.setStyleSheet(f"""
            QWidget#ContentPanel {{
                background: {C.PANEL};
                border-top: 1px solid {C.BORDER_B};
            }}
        """)
        w.hide()

        lay = QVBoxLayout(w)
        lay.setContentsMargins(12, 7, 12, 8)
        lay.setSpacing(5)

        # ── header row ───────────────────────────────────────────────────────
        hdr = QHBoxLayout(); hdr.setSpacing(6)

        dot = QLabel("◈")
        dot.setFont(QFont(_PRIMARY_FONT, 9, QFont.Weight.Bold))
        dot.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        hdr.addWidget(dot)

        self._content_title_lbl = QLabel("BRIEFING")
        self._content_title_lbl.setFont(QFont(_PRIMARY_FONT, 8, QFont.Weight.Bold))
        self._content_title_lbl.setStyleSheet(
            f"color: {C.PRI}; background: transparent; letter-spacing: 1px;"
        )
        hdr.addWidget(self._content_title_lbl)
        hdr.addStretch()

        self._content_ts_lbl = QLabel("")
        self._content_ts_lbl.setFont(QFont(_PRIMARY_FONT, 7))
        self._content_ts_lbl.setStyleSheet(f"color: {C.TEXT_DIM}; background: transparent;")
        hdr.addWidget(self._content_ts_lbl)

        dismiss = QPushButton("DISMISS  ✕")
        dismiss.setFont(QFont(_PRIMARY_FONT, 7))
        dismiss.setFixedHeight(18)
        dismiss.setCursor(Qt.CursorShape.PointingHandCursor)
        dismiss.setStyleSheet(f"""
            QPushButton {{
                background: transparent; color: {C.TEXT_DIM};
                border: 1px solid {C.BORDER}; border-radius: 2px; padding: 0 5px;
            }}
            QPushButton:hover {{ color: {C.TEXT}; border-color: {C.BORDER_B}; }}
        """)
        dismiss.clicked.connect(w.hide)
        hdr.addWidget(dismiss)
        lay.addLayout(hdr)

        # ── separator ─────────────────────────────────────────────────────────
        sep = QFrame(); sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {C.BORDER};"); lay.addWidget(sep)

        # ── text display ──────────────────────────────────────────────────────
        self._content_display = QTextEdit()
        self._content_display.setReadOnly(True)
        self._content_display.setFont(QFont(_PRIMARY_FONT, 8))
        self._content_display.setMinimumHeight(60)
        self._content_display.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self._content_display.setStyleSheet(f"""
            QTextEdit {{
                background: {C.DARK};
                color: {C.TEXT};
                border: 1px solid {C.BORDER};
                border-radius: 3px;
                padding: 6px 8px;
                selection-background-color: {C.PRI_GHO};
            }}
            QScrollBar:vertical {{
                background: {C.BG}; width: 6px; border: none;
            }}
            QScrollBar::handle:vertical {{
                background: {C.BORDER_B}; border-radius: 3px; min-height: 16px;
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0; border: none;
            }}
        """)
        lay.addWidget(self._content_display)

        return w

    def _show_content(self, title: str, text: str):
        """Slot — runs on Qt main thread. Updates and shows the content panel."""
        import time as _time
        self._content_title_lbl.setText(title.upper()[:48])
        self._content_ts_lbl.setText(_time.strftime("%H:%M:%S"))
        self._content_display.setPlainText(text)
        self._content_display.moveCursor(
            self._content_display.textCursor().MoveOperation.Start
        )
        first_show = not self._content_panel.isVisible()
        self._content_panel.show()
        if first_show:
            total = self._center_split.height()
            self._center_split.setSizes([max(total - 220, 120), 220])

    def _build_footer(self) -> QWidget:
        w = QWidget()
        w.setFixedHeight(32)
        w.setStyleSheet(f"background: {C.DARK}; border-top: 1px solid {C.BORDER};")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(14, 0, 14, 0)
        lay.setSpacing(12)

        # Footer Left Tabs
        left_tabs = QHBoxLayout()
        left_tabs.setSpacing(12)
        footer_tabs = [
            ("REMOTE ACCESS", self._open_remote),
            ("RECONFIGURATION", self._show_setup),
            ("SETTINGS", self._toggle_drawer),
        ]
        for name, callback in footer_tabs:
            btn = QPushButton(name)
            btn.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
            btn.setStyleSheet(f"""
                QPushButton {{
                    color: {C.TEXT_MED}; background: transparent; border: none;
                    padding: 2px 6px;
                }}
                QPushButton:hover {{ color: {C.PRI}; }}
            """)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(callback)
            left_tabs.addWidget(btn)
        lay.addLayout(left_tabs)
        lay.addStretch()

        # Footer Middle Version Info + Watermark
        ver_lbl = QLabel("➔ JARVIS AI  ·  MADE BY ANKITPAUL ➔")
        ver_lbl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        ver_lbl.setStyleSheet(f"color: {C.PRI_DIM}; background: transparent; letter-spacing: 1px;")
        lay.addWidget(ver_lbl)
        lay.addStretch()

        # Footer Right Indicators
        right_status = QHBoxLayout()
        right_status.setSpacing(10)
        
        self.conn_lbl = QLabel("● CONNECTED")
        self.conn_lbl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        self.conn_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent;")
        right_status.addWidget(self.conn_lbl)
        
        enc_lbl = QLabel("ENCRYPTED")
        enc_lbl.setFont(QFont(_PRIMARY_FONT, 7, QFont.Weight.Bold))
        enc_lbl.setStyleSheet(f"color: {C.PRI}; background: transparent;")
        right_status.addWidget(enc_lbl)
        
        self.footer_wifi = WifiSignalIcon()
        right_status.addWidget(self.footer_wifi)
        
        lay.addLayout(right_status)
        return w

    def _on_file_selected(self, path: str):
        self._current_file = path
        p    = Path(path)
        cat  = _file_category(p)
        icon, _ = _FILE_ICONS.get(cat, _FILE_ICONS["unknown"])
        size = _fmt_size(p.stat().st_size)
        self._file_hint.setText(f"{icon}  {p.name}  ·  {size}  ·  Tell {self._assistant_name} what to do with it")
        self._log.append_log(f"FILE: {p.name} ({size}) loaded")
        if self.on_text_command:
            msg = (
                f"[FILE_UPLOADED] path={path} | name={p.name} | "
                f"type={p.suffix.lstrip('.')} | size={size} | "
                f"Briefly tell the user you can see the file '{p.name}' "
                f"({size}) has been uploaded and ask what they'd like to do with it."
            )
            threading.Thread(target=self.on_text_command, args=(msg,), daemon=True).start()

    def notify_phone_connected(self) -> None:
        if self._remote_overlay and self._remote_overlay.isVisible():
            self._remote_overlay.mark_connected()

    def _open_remote(self):
        if not self.on_remote_clicked:
            self._log.append_log("SYS: Dashboard not running — remote unavailable.")
            return
        result = self.on_remote_clicked()
        if not result:
            self._log.append_log("SYS: Could not generate remote key.")
            return
        url    = result[0]
        key    = result[1]
        auto   = result[2] if len(result) >= 3 else ""
        manual = result[3] if len(result) >= 4 else url
        if self._remote_overlay:
            self._remote_overlay._do_close()
        cw  = self.centralWidget()
        ow, oh = RemoteKeyOverlay._OW, RemoteKeyOverlay._OH
        ov  = RemoteKeyOverlay(url, key, auto_login_url=auto, manual_url=manual,
                               expiry_secs=600, parent=cw)
        ov.set_new_key_callback(self.on_remote_clicked)
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.closed.connect(lambda: setattr(self, '_remote_overlay', None))
        ov.show()
        self._remote_overlay = ov
        self._log.append_log(f"SYS: Remote key generated — manual: {manual or url}")

    # ── Auto-start ──────────────────────────────────────────────────────────────

    def _check_autostart(self) -> bool:
        """Returns True if auto-start is currently registered on this OS."""
        try:
            if _OS == "Windows":
                import winreg
                key = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_READ)
                try:
                    winreg.QueryValueEx(key, "JARVIS_AI")
                    return True
                except FileNotFoundError:
                    return False
                finally:
                    winreg.CloseKey(key)
            elif _OS == "Darwin":
                return (Path.home() / "Library" / "LaunchAgents"
                        / "com.jarvis.assistant.plist").exists()
            else:
                return (Path.home() / ".config" / "autostart" / "jarvis.desktop").exists()
        except Exception:
            return False

    def _toggle_autostart(self):
        currently_on = self._check_autostart()
        try:
            script = str(Path(__file__).resolve().parent / "main.py")
            if _OS == "Windows":
                import winreg
                reg = winreg.OpenKey(winreg.HKEY_CURRENT_USER,
                    r"Software\Microsoft\Windows\CurrentVersion\Run", 0, winreg.KEY_ALL_ACCESS)
                if currently_on:
                    winreg.DeleteValue(reg, "JARVIS_AI")
                else:
                    pythonw = Path(sys.executable).parent / "pythonw.exe"
                    exe = str(pythonw if pythonw.exists() else sys.executable)
                    winreg.SetValueEx(reg, "JARVIS_AI", 0, winreg.REG_SZ,
                                      f'"{exe}" "{script}"')
                winreg.CloseKey(reg)
            elif _OS == "Darwin":
                plist_dir = Path.home() / "Library" / "LaunchAgents"
                plist_dir.mkdir(parents=True, exist_ok=True)
                plist = plist_dir / "com.jarvis.assistant.plist"
                if currently_on:
                    plist.unlink(missing_ok=True)
                else:
                    plist.write_text(
                        '<?xml version="1.0" encoding="UTF-8"?>\n'
                        '<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" '
                        '"http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
                        '<plist version="1.0"><dict>\n'
                        '  <key>Label</key><string>com.jarvis.assistant</string>\n'
                        '  <key>ProgramArguments</key><array>\n'
                        f'    <string>{sys.executable}</string>\n'
                        f'    <string>{script}</string>\n'
                        '  </array>\n'
                        '  <key>RunAtLoad</key><true/>\n'
                        '</dict></plist>\n'
                    )
            else:
                desk_dir = Path.home() / ".config" / "autostart"
                desk_dir.mkdir(parents=True, exist_ok=True)
                desk = desk_dir / "jarvis.desktop"
                if currently_on:
                    desk.unlink(missing_ok=True)
                else:
                    desk.write_text(
                        "[Desktop Entry]\n"
                        f"Name={self._assistant_name}\n"
                        f"Exec={sys.executable} {script}\n"
                        "Type=Application\nTerminal=false\n"
                        "X-GNOME-Autostart-enabled=true\n"
                    )
            enabled = not currently_on
            self._update_autostart_btn(enabled)
            self._log.append_log(
                f"SYS: Auto-start {'enabled' if enabled else 'disabled'}.")
        except Exception as e:
            self._log.append_log(f"ERR: Auto-start failed — {e}")

    def _update_autostart_btn(self, enabled: bool):
        if not hasattr(self, '_autostart_btn'):
            return
        if enabled:
            self._autostart_btn.setText("◉  AUTO-START: ON")
            self._autostart_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #001a08; color: {C.GREEN};
                    border: 1px solid {C.GREEN_D}; border-radius: 3px;
                }}
                QPushButton:hover {{ background: #002010; }}
            """)
        else:
            self._autostart_btn.setText("◉  AUTO-START: OFF")
            self._autostart_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {C.TEXT_DIM};
                    border: 1px solid {C.BORDER}; border-radius: 3px;
                }}
                QPushButton:hover {{ color: {C.TEXT}; border: 1px solid {C.BORDER_B}; }}
            """)

    def _toggle_brief(self):
        from memory.config_manager import get_brief_enabled, save_brief_enabled
        new_val = not get_brief_enabled()
        save_brief_enabled(new_val)
        self._update_brief_btn(new_val)

    def _update_brief_btn(self, enabled: bool):
        if not hasattr(self, '_brief_btn'):
            return
        if enabled:
            self._brief_btn.setText("☀  MORNING BRIEF: ON")
            self._brief_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #001a08; color: {C.GREEN};
                    border: 1px solid {C.GREEN_D}; border-radius: 3px;
                    text-align: left; padding: 0 8px;
                }}
                QPushButton:hover {{ background: #002010; }}
            """)
        else:
            self._brief_btn.setText("☀  MORNING BRIEF: OFF")
            self._brief_btn.setStyleSheet(f"""
                QPushButton {{
                    background: transparent; color: {C.TEXT_DIM};
                    border: 1px solid {C.BORDER}; border-radius: 3px;
                    text-align: left; padding: 0 8px;
                }}
                QPushButton:hover {{ color: {C.TEXT}; border: 1px solid {C.BORDER_B}; }}
            """)

    # ── Customization ────────────────────────────────────────────────────────────

    def _open_customize(self):
        cfg = _read_full_config()
        if self._customize_overlay:
            self._customize_overlay.hide()
        cw = self.centralWidget()
        ov = CustomizeOverlay(
            cfg.get("assistant_name", "JARVIS") or "JARVIS",
            cfg.get("user_name", ""),
            cfg.get("ui_color", "") or DEFAULT_UI_COLOR,
            parent=cw,
        )
        ow, oh = CustomizeOverlay._OW, CustomizeOverlay._OH
        oh = min(oh, cw.height() - 16)
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.on_preview = self._preview_ui_color
        ov.saved.connect(self._apply_name_update)
        ov.show()
        self._customize_overlay = ov

    def _preview_ui_color(self, hex_color: str):
        """Live preview — rethemes all widgets dynamically without persisting to config."""
        old = current_palette()
        if apply_ui_accent(hex_color):
            retheme_all_widgets(old, current_palette())

    def _apply_name_update(self, name: str, user_name: str, ui_color: str = ""):
        """Update all name/theme-dependent UI elements and persist to config."""
        self._assistant_name = name.strip() or "JARVIS"
        display = self._assistant_name.upper()
        self.setWindowTitle(f"{display} AI")
        self._title_lbl.setText(display)
        if display in ("JARVIS", "J.A.R.V.I.S"):
            self._sub_lbl.setText("Just A Rather Very Intelligent System")
        else:
            self._sub_lbl.setText("Personal AI Assistant")
        self._log._ai_name_lc = self._assistant_name.lower()
        self.hud._assistant_name = display

        color_changed = False
        if ui_color:
            old = current_palette()
            if apply_ui_accent(ui_color):
                retheme_all_widgets(old, current_palette())
                color_changed = old["PRI"] != C.PRI

        try:
            data = _read_full_config()
            data["assistant_name"] = self._assistant_name
            data["user_name"] = user_name.strip()
            if ui_color:
                data["ui_color"] = ui_color.strip().lower()
            API_FILE.write_text(json.dumps(data, indent=4), encoding="utf-8")
            self._log.append_log(f"SYS: Identity updated — {display}")
            if color_changed:
                self._log.append_log(f"SYS: UI colour applied — {ui_color}")
        except Exception as e:
            self._log.append_log(f"ERR: Config save failed — {e}")

    # ── Clipboard intelligence ───────────────────────────────────────────────────

    def _on_clipboard_changed(self):
        try:
            text = QApplication.clipboard().text().strip()
            if len(text) >= 10:
                self._clipboard_sig.emit(text)
        except Exception:
            pass

    def _show_clipboard_panel(self, text: str):
        self._clipboard_panel.show_clipboard(text)
        self._position_clipboard_panel()

    def _position_clipboard_panel(self):
        cw = self.centralWidget()
        pw = ClipboardPanel._W
        ph = self._clipboard_panel.sizeHint().height() or ClipboardPanel._H
        x = (cw.width() - pw) // 2
        y = cw.height() - ph - 6
        self._clipboard_panel.setGeometry(x, y, pw, ph)
        self._clipboard_panel.raise_()

    def _on_clipboard_action(self, cmd: str):
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(cmd,), daemon=True).start()

    # ────────────────────────────────────────────────────────────────────────────

    def _update_wifi_status(self):
        def _bg_check():
            sig, ssid = _get_wifi_signal()
            def _gui():
                if hasattr(self, "footer_wifi"):
                    self.footer_wifi.set_signal(sig, ssid)
                if hasattr(self, "conn_lbl"):
                    if sig >= 0:
                        self.conn_lbl.setText("● CONNECTED")
                        self.conn_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent;")
                    else:
                        self.conn_lbl.setText("⊘ OFFLINE")
                        self.conn_lbl.setStyleSheet(f"color: {C.RED}; background: transparent;")
            QTimer.singleShot(0, _gui)

        threading.Thread(target=_bg_check, daemon=True).start()

    def _do_interrupt(self):
        if self.on_interrupt:
            self.on_interrupt()

    def _toggle_mute(self):
        self._muted = not self._muted
        self.hud.muted = self._muted
        self._style_mute_btn()
        if hasattr(self, "rec_icon") and hasattr(self, "voice_status_lbl"):
            if self._muted:
                self.rec_icon.setIcon("mic_off", C.MUTED_C)
                self.voice_status_lbl.setText("MUTED")
                self.voice_status_lbl.setStyleSheet(f"color: {C.MUTED_C}; background: transparent;")
            else:
                self.rec_icon.setIcon("mic", C.GREEN)
                self.voice_status_lbl.setText("ACTIVE")
                self.voice_status_lbl.setStyleSheet(f"color: {C.GREEN}; background: transparent;")
        if self._muted:
            self._apply_state("MUTED")
            self._log.append_log("SYS: Microphone muted.")
        else:
            self._apply_state("LISTENING")
            self._log.append_log("SYS: Microphone active.")

    def _style_mute_btn(self):
        if self._muted:
            self._mute_btn.setText("   UNMUTE")
            self._mute_btn.setIcon("mic_off", C.MUTED_C)
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #140006; color: {C.MUTED_C};
                    border: 1px solid {C.MUTED_C}; border-radius: 3px;
                    padding-left: 20px;
                }}
                QPushButton:hover {{ background: #200010; }}
            """)
        else:
            self._mute_btn.setText("   MUTE")
            self._mute_btn.setIcon("mic", C.GREEN)
            self._mute_btn.setStyleSheet(f"""
                QPushButton {{
                    background: #00140a; color: {C.GREEN};
                    border: 1px solid {C.GREEN}; border-radius: 3px;
                    padding-left: 20px;
                }}
                QPushButton:hover {{ background: #001f10; }}
            """)

    def _send(self):
        txt = self._input.text().strip()
        if not txt: return
        self._input.clear()
        self._log.append_log(f"You: {txt}")
        if self.on_text_command:
            threading.Thread(target=self.on_text_command, args=(txt,), daemon=True).start()

    def _apply_state(self, state: str):
        self.hud.state    = state
        self.hud.speaking = (state == "SPEAKING")

    def _check_config(self) -> bool:
        if not API_FILE.exists(): return False
        try:
            d = json.loads(API_FILE.read_text(encoding="utf-8"))
            return bool(d.get("gemini_api_key")) and bool(d.get("os_system"))
        except Exception:
            return False

    def _show_setup(self):
        ov = SetupOverlay(self.centralWidget())
        cw = self.centralWidget()
        ow, oh = 460, 390
        ov.setGeometry(
            (cw.width()  - ow) // 2,
            (cw.height() - oh) // 2,
            ow, oh,
        )
        ov.done.connect(self._on_setup_done)
        ov.show()
        self._overlay = ov

    def _on_setup_done(self, key: str, os_name: str):
        os.makedirs(CONFIG_DIR, exist_ok=True)
        API_FILE.write_text(
            json.dumps({"gemini_api_key": key, "os_system": os_name}, indent=4),
            encoding="utf-8",
        )
        self._ready = True
        if self._overlay:
            self._overlay.hide()
            self._overlay = None
        self._apply_state("LISTENING")
        self._assistant_name = _read_full_config().get("assistant_name", "JARVIS") or "JARVIS"
        self._log.append_log(f"SYS: Initialised. OS={os_name.upper()}. {self._assistant_name} online.")

class _RootShim:
    def __init__(self, app: QApplication):
        self._app = app
    def mainloop(self):
        self._app.exec()
    def protocol(self, *_):
        pass


class JarvisUI:
    def __init__(self, face_path: str, size=None):
        self._app = QApplication.instance() or QApplication(sys.argv)
        self._app.setStyle("Fusion")
        self._win = MainWindow(face_path)
        self._win.show()
        self.root = _RootShim(self._app)

    @property
    def muted(self) -> bool:
        return self._win._muted

    @muted.setter
    def muted(self, v: bool):
        if v != self._win._muted:
            self._win._toggle_mute()

    @property
    def current_file(self) -> str | None:
        return self._win._drop_zone.current_file()

    @property
    def on_text_command(self):
        return self._win.on_text_command

    @on_text_command.setter
    def on_text_command(self, cb):
        self._win.on_text_command = cb

    @property
    def on_remote_clicked(self):
        return self._win.on_remote_clicked

    @on_remote_clicked.setter
    def on_remote_clicked(self, cb):
        self._win.on_remote_clicked = cb

    @property
    def on_interrupt(self):
        return self._win.on_interrupt

    @on_interrupt.setter
    def on_interrupt(self, cb):
        self._win.on_interrupt = cb

    def notify_phone_connected(self) -> None:
        self._win.notify_phone_connected()

    def set_state(self, state: str):
        self._win._state_sig.emit(state)

    def write_log(self, text: str):
        self._win._log_sig.emit(text)

    def wait_for_api_key(self):
        while not self._win._ready:
            time.sleep(0.1)

    def show_content(self, title: str, text: str):
        """Thread-safe: display content in the panel below the HUD."""
        self._win._content_sig.emit(title[:48], text[:4000])

    def prompt_reconfig(self):
        """Thread-safe: show the API key setup overlay (e.g. after an auth error)."""
        self._win._ready = False
        self._win._reconfig_sig.emit()

    def show_camera_frame(self, img_bytes: bytes):
        """Thread-safe: show a webcam frame in the small overlay (screen captures)."""
        self._win._camera_sig.emit(img_bytes)

    def start_camera_stream(self) -> None:
        """Thread-safe: start live camera feed in the full HUD area."""
        self._win.start_camera_stream()

    def stop_camera_stream(self) -> None:
        """Thread-safe: stop the live camera feed."""
        self._win.stop_camera_stream()

    @property
    def assistant_name(self) -> str:
        return self._win._assistant_name

    def start_speaking(self):
        self.set_state("SPEAKING")

    def stop_speaking(self):
        if not self.muted:
            self.set_state("LISTENING")