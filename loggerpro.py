import os
import sys
import gc
import shutil
import hashlib
import time
import re
import ctypes
import threading
import subprocess
import webbrowser
from datetime import datetime
from pathlib import Path
from tkinter import filedialog, messagebox
import tkinter as tk
import psutil
from PIL import Image, ImageDraw, ImageFilter, ImageTk
import customtkinter as ctk

# Registra o AppUserModelID para exibir o ícone próprio na Barra de Tarefas do Windows
if os.name == "nt":
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("souzfilmes.loggerpro.ingest.v2")
    except Exception:
        pass

ctk.set_appearance_mode("dark")

C_BG = "#0B0A09"
C_SURFACE = "#141210"
C_CARD = "#1B1815"
C_CARD_INNER = "#110F0D"
C_BORDER = "#33291F"
C_BORDER_GLOW = "#E87A24"
C_ACCENT = "#E87A24"
C_ACCENT_HOVER = "#C86416"
C_GOLD = "#D4A74A"
C_GOLD_BRIGHT = "#F5C869"
C_GOLD_DARK = "#8A6621"
C_SUCCESS = "#2EA043"
C_SUCCESS_BG = "#0F2415"
C_WARNING = "#D29922"
C_DANGER = "#C93C37"
C_TEXT = "#F0ECE6"
C_MUTED = "#8A8279"
C_PHOTO = "#388BFD"
C_AUDIO = "#A371F7"
C_PROXY = "#2EA89C"

VIDEO_EXTENSIONS = {".mp4", ".mov", ".mxf", ".avi", ".braw", ".r3d", ".insv", ".mts"}
RAW_PHOTO_EXTENSIONS = {".arw", ".cr2", ".cr3", ".nef", ".dng", ".raf", ".orf", ".rw2"}
STD_PHOTO_EXTENSIONS = {".jpg", ".jpeg", ".heif", ".heic", ".png"}
AUDIO_EXTENSIONS = {".wav", ".bwf", ".mp3", ".aac", ".flac", ".m4a", ".ogg"}

BLOCKED_DIRS = {
    "thmbnl", "avf_info", "iisv", "canonmsc", "misc",
    "trashes", ".trashes", "system volume information", "$recycle.bin"
}
PROXY_DIRS = {"sub", "proxy", "proxies"}
IGNORED_XML_NAMES = {"mediapro.xml", "cueup.xml", "sonycard.xml", "index.xml", "status.xml"}
SONY_THUMB_REGEX = re.compile(r"^.+T\d{2}\.JPE?G$", re.IGNORECASE)
SONY_PROXY_REGEX = re.compile(r"^.+S\d{2}\.MP4$", re.IGNORECASE)


def truncate_middle(text: str, max_len: int = 48) -> str:
    if len(text) <= max_len:
        return text
    half = (max_len - 5) // 2
    return f"{text[:half]} ... {text[-half:]}"


class IconFactory:
    """Renderizador vetorial supersampled (1024x1024 -> Lanczos) para o ícone do app e ícones da UI."""

    @classmethod
    def build_master_app_icon(cls) -> Image.Image:
        S = 1024
        base = Image.new("RGBA", (S, S), (0, 0, 0, 0))

        sq_mask = Image.new("L", (S, S), 0)
        sq_draw = ImageDraw.Draw(sq_mask)
        sq_draw.rounded_rectangle([56, 56, 968, 968], radius=215, fill=255)

        sq_grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        sq_gdraw = ImageDraw.Draw(sq_grad)
        for y in range(56, 969):
            t = (y - 56) / 912.0
            r = int(28 * (1 - t) + 11 * t)
            g = int(23 * (1 - t) + 10 * t)
            b = int(19 * (1 - t) + 9 * t)
            sq_gdraw.line([(56, y), (968, y)], fill=(r, g, b, 255))

        base.paste(sq_grad, (0, 0), sq_mask)

        b_draw = ImageDraw.Draw(base)
        b_draw.rounded_rectangle([56, 56, 968, 968], radius=215, outline=(66, 50, 36, 255), width=8)

        glow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        g_draw = ImageDraw.Draw(glow)
        g_draw.ellipse([200, 160, 824, 860], fill=(232, 122, 36, 95))
        glow = glow.filter(ImageFilter.GaussianBlur(85))
        base = Image.alpha_composite(base, glow)

        sd_mask_raw = Image.new("L", (S, S), 0)
        sd_mdraw = ImageDraw.Draw(sd_mask_raw)
        sd_pts = [(265, 175), (585, 175), (755, 345), (755, 835), (265, 835)]
        sd_mdraw.polygon(sd_pts, fill=255)
        sd_blurred = sd_mask_raw.filter(ImageFilter.GaussianBlur(22))
        sd_mask = sd_blurred.point(lambda p: max(0, min(255, int((p - 112) * 9))))

        sd_grad = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        sd_gdraw = ImageDraw.Draw(sd_grad)
        for y in range(160, 850):
            t = (y - 160) / 690.0
            r = int(255 * (1 - t) + 190 * t)
            g = int(158 * (1 - t) + 82 * t)
            b = int(64 * (1 - t) + 14 * t)
            sd_gdraw.line([(240, y), (780, y)], fill=(r, g, b, 255))

        sd_shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        sd_shadow.paste((0, 0, 0, 150), (0, 22), sd_mask)
        sd_shadow = sd_shadow.filter(ImageFilter.GaussianBlur(28))
        base = Image.alpha_composite(base, sd_shadow)
        base.paste(sd_grad, (0, 0), sd_mask)

        ui_draw = ImageDraw.Draw(base)
        for sx in [335, 425, 515]:
            ui_draw.rounded_rectangle([sx, 235, sx + 50, 360], radius=18, fill=(24, 18, 14, 220))
            ui_draw.rounded_rectangle([sx + 8, 245, sx + 42, 330], radius=12, fill=(248, 206, 118, 255))

        arrow_layer = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        ad = ImageDraw.Draw(arrow_layer)
        cx = 510
        ad.rounded_rectangle([cx - 30, 435, cx + 30, 650], radius=22, fill=(255, 248, 240, 255))
        ad.line([(cx - 115, 575), (cx, 690), (cx + 115, 575)], fill=(255, 248, 240, 255), width=56, joint="curve")
        ad.ellipse([cx - 143, 547, cx - 87, 603], fill=(255, 248, 240, 255))
        ad.ellipse([cx + 87, 547, cx + 143, 603], fill=(255, 248, 240, 255))
        ad.ellipse([cx - 28, 662, cx + 28, 718], fill=(255, 248, 240, 255))

        a_shadow = Image.new("RGBA", (S, S), (0, 0, 0, 0))
        a_shadow.paste((80, 30, 0, 120), (0, 12), arrow_layer.split()[3])
        a_shadow = a_shadow.filter(ImageFilter.GaussianBlur(14))
        base = Image.alpha_composite(base, a_shadow)
        base = Image.alpha_composite(base, arrow_layer)

        bx, by, br = 735, 760, 125
        ui_draw = ImageDraw.Draw(base)
        ui_draw.ellipse([bx - br - 20, by - br - 20, bx + br + 20, by + br + 20], fill=(14, 12, 10, 255))
        ui_draw.ellipse([bx - br, by - br, bx + br, by + br], fill=(46, 168, 68, 255), outline=(92, 214, 112, 255), width=6)
        ui_draw.line([(bx - 52, by + 4), (bx - 14, by + 44), (bx + 60, by - 38)], fill=(255, 255, 255, 255), width=28, joint="curve")

        return base

    @classmethod
    def ensure_ico_file(cls) -> str:
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd())
        ico_path = os.path.join(base_dir, "loggerpro_icon.ico")
        if os.path.exists(ico_path):
            return ico_path
        try:
            master = cls.build_master_app_icon()
            sizes = [(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)]
            master.save(ico_path, format="ICO", sizes=sizes)
        except Exception:
            ico_path = os.path.abspath("loggerpro_icon.ico")
            master = cls.build_master_app_icon()
            master.save(ico_path, format="ICO", sizes=[(256, 256), (128, 128), (64, 64), (48, 48), (32, 32), (16, 16)])
        return ico_path

    @classmethod
    def ensure_mac_icns(cls, icns_path: str = "loggerpro_icon.icns") -> str:
        base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)) if "__file__" in globals() else os.getcwd())
        target_path = os.path.join(base_dir, icns_path) if not os.path.isabs(icns_path) else icns_path
        master = cls.build_master_app_icon()
        master.save(target_path, format="ICNS")
        return target_path

    @classmethod
    def app_ctk_icon(cls, size=(20, 20)):
        master = cls.build_master_app_icon().resize((128, 128), Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=master, dark_image=master, size=size)

    @staticmethod
    def _new_canvas(size=128):
        img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
        return img, ImageDraw.Draw(img)

    @classmethod
    def ssd_icon(cls, color=C_ACCENT, size=(22, 22)):
        img, d = cls._new_canvas(128)
        d.rounded_rectangle([16, 28, 112, 100], radius=16, outline=color, width=8)
        d.line([32, 52, 72, 52], fill=color, width=8)
        d.ellipse([88, 72, 100, 84], fill=color)
        img = img.resize((64, 64), Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)

    @classmethod
    def video_icon(cls, color=C_ACCENT, size=(18, 18)):
        img, d = cls._new_canvas(128)
        d.rounded_rectangle([12, 28, 88, 100], radius=12, outline=color, width=8)
        d.polygon([(88, 48), (116, 32), (116, 96), (88, 80)], outline=color, width=8)
        img = img.resize((64, 64), Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)

    @classmethod
    def proxy_icon(cls, color=C_PROXY, size=(18, 18)):
        img, d = cls._new_canvas(128)
        d.rounded_rectangle([14, 30, 84, 98], radius=12, outline=color, width=8)
        d.line([36, 64, 64, 64], fill=color, width=8)
        d.polygon([(84, 50), (114, 34), (114, 94), (84, 78)], outline=color, width=8)
        img = img.resize((64, 64), Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)

    @classmethod
    def photo_icon(cls, color=C_PHOTO, size=(18, 18)):
        img, d = cls._new_canvas(128)
        d.rounded_rectangle([12, 32, 116, 104], radius=12, outline=color, width=8)
        d.polygon([(40, 32), (52, 16), (76, 16), (88, 32)], outline=color, width=6)
        d.ellipse([46, 50, 82, 86], outline=color, width=8)
        img = img.resize((64, 64), Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)

    @classmethod
    def audio_icon(cls, color=C_AUDIO, size=(18, 18)):
        img, d = cls._new_canvas(128)
        d.rounded_rectangle([48, 16, 80, 72], radius=16, outline=color, width=8)
        d.arc([28, 36, 100, 92], start=0, end=180, fill=color, width=8)
        d.line([64, 92, 64, 112], fill=color, width=8)
        d.line([44, 112, 84, 112], fill=color, width=8)
        img = img.resize((64, 64), Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)

    @classmethod
    def check_circle(cls, color=C_SUCCESS, size=(42, 42)):
        img, d = cls._new_canvas(192)
        d.ellipse([12, 12, 180, 180], fill=color)
        d.line([(56, 100), (84, 128), (136, 68)], fill="#0B0A09", width=16, joint="curve")
        img = img.resize((96, 96), Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)

    @classmethod
    def report_icon(cls, color=C_TEXT, size=(18, 18)):
        img, d = cls._new_canvas(128)
        d.rounded_rectangle([24, 16, 104, 112], radius=12, outline=color, width=8)
        d.line([40, 44, 88, 44], fill=color, width=8)
        d.line([40, 68, 88, 68], fill=color, width=8)
        d.line([40, 92, 68, 92], fill=color, width=8)
        img = img.resize((64, 64), Image.Resampling.LANCZOS)
        return ctk.CTkImage(light_image=img, dark_image=img, size=size)


class NextCardModal(ctk.CTkToplevel):
    def __init__(self, parent, current_cam, next_cam, was_only_audio_or_photo=False):
        super().__init__(parent)
        self.title("LoggerPro • Cartão Verificado")
        self.geometry("500x370")
        self.configure(fg_color=C_CARD)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.result = "finish"

        box = ctk.CTkFrame(self, fg_color=C_SUCCESS_BG, corner_radius=10, border_width=1, border_color=C_SUCCESS)
        box.pack(fill="x", padx=28, pady=(20, 12))
        ctk.CTkLabel(box, text="✓  BACKUP CONFERIDO E CARTÃO EJETADO", font=("Segoe UI", 13, "bold"), text_color=C_SUCCESS).pack(pady=10)

        ctk.CTkLabel(
            self, text="Retire o cartão atual do leitor.\nExiste mais algum cartão para descarregar neste projeto?",
            font=("Segoe UI", 13), text_color=C_TEXT, justify="center"
        ).pack(pady=(2, 14))

        if was_only_audio_or_photo:
            ctk.CTkButton(
                self, text=f"🎥   Sim, próximo cartão é de vídeo ({current_cam})",
                fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER, text_color="#0B0A09",
                height=40, corner_radius=8, font=("Segoe UI", 13, "bold"),
                command=lambda: self._end("keep_cam")
            ).pack(fill="x", padx=32, pady=4)

        ctk.CTkButton(
            self, text=f"🎥   Sim, criar pasta {next_cam} (Nova Câmera)",
            fg_color=C_ACCENT if not was_only_audio_or_photo else C_SURFACE,
            hover_color=C_ACCENT_HOVER if not was_only_audio_or_photo else "#26211B",
            text_color="#0B0A09" if not was_only_audio_or_photo else C_TEXT,
            border_width=0 if not was_only_audio_or_photo else 1, border_color=C_ACCENT,
            height=40, corner_radius=8, font=("Segoe UI", 13, "bold"),
            command=lambda: self._end("new_cam")
        ).pack(fill="x", padx=32, pady=4)

        ctk.CTkButton(
            self, text=f"🔄   Sim, continuação da {current_cam} ou Gravador/Fotos",
            fg_color=C_SURFACE, hover_color="#26211B", border_width=1, border_color=C_BORDER_GLOW,
            height=40, corner_radius=8, font=("Segoe UI", 13, "bold"),
            command=lambda: self._end("continue_cam")
        ).pack(fill="x", padx=32, pady=4)

        ctk.CTkButton(
            self, text="🏁   Não, finalizar e abrir relatório",
            fg_color="transparent", hover_color="#221E1A", text_color=C_MUTED,
            height=34, font=("Segoe UI", 12),
            command=lambda: self._end("finish")
        ).pack(fill="x", padx=32, pady=(6, 10))

        self.protocol("WM_DELETE_WINDOW", lambda: self._end("finish"))

    def _end(self, choice):
        self.result = choice
        self.grab_release()
        self.destroy()


class ProjectSetupModal(ctk.CTkToplevel):
    def __init__(self, parent, default_name=""):
        super().__init__(parent)
        self.title("LoggerPro • Novo Projeto")
        self.geometry("490x320")
        self.configure(fg_color=C_CARD)
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()

        self.project_name = default_name or time.strftime("%Y-%m-%d EVENTO")
        self.multi_card = True
        self.confirmed = False

        ctk.CTkLabel(self, text="⚡ CONFIGURAR PROJETO • LOGGERPRO", font=("Segoe UI", 14, "bold"), text_color=C_ACCENT).pack(pady=(22, 12))
        ctk.CTkLabel(self, text="Qual foi o nome do projeto / gravação?", font=("Segoe UI", 13, "bold"), text_color=C_TEXT).pack(anchor="w", padx=35)

        self.entry = ctk.CTkEntry(
            self, width=420, height=40, font=("Segoe UI", 14, "bold"),
            fg_color=C_CARD_INNER, border_color=C_BORDER_GLOW, text_color=C_TEXT
        )
        self.entry.pack(padx=35, pady=(6, 4))
        self.entry.insert(0, self.project_name)

        ctk.CTkLabel(
            self, text="Automático: BRUTO/CAM A (+ Proxies e XML) • FOTOS • GRAVADOR",
            font=("Consolas", 11), text_color=C_MUTED
        ).pack(anchor="w", padx=35, pady=(0, 14))

        self.var_multi = ctk.BooleanVar(value=True)
        ctk.CTkSwitch(
            self, text="Existe mais de 1 cartão para descarregar?",
            variable=self.var_multi, progress_color=C_ACCENT, font=("Segoe UI", 13, "bold")
        ).pack(anchor="w", padx=35, pady=8)

        ctk.CTkButton(
            self, text="CONFIRMAR PROJETO",
            fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER, text_color="#0B0A09",
            height=42, corner_radius=8, font=("Segoe UI", 13, "bold"),
            command=self._ok
        ).pack(fill="x", padx=35, pady=(18, 12))

    def _ok(self):
        name = self.entry.get().strip()
        if not name:
            messagebox.showwarning("Atenção", "Digite o nome do projeto.")
            return
        self.project_name = name
        self.multi_card = self.var_multi.get()
        self.confirmed = True
        self.grab_release()
        self.destroy()


class LoggerProApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("LoggerPro • Ingest & Backup Verificado")
        self.geometry("1160x780")
        self.minsize(1100, 740)
        self.configure(fg_color=C_BG)

        try:
            master_pil = IconFactory.build_master_app_icon().resize((128, 128), Image.Resampling.LANCZOS)
            self._tk_icon = ImageTk.PhotoImage(master_pil)
            self.wm_iconphoto(True, self._tk_icon)
            if os.name == "nt":
                ico_file = IconFactory.ensure_ico_file()
                self.iconbitmap(ico_file)
        except Exception:
            pass

        self.project_name = ctk.StringVar(value=time.strftime("%Y-%m-%d EVENTO"))
        self.has_multiple_cards = ctk.BooleanVar(value=True)
        self.cam_index = 0
        self.card_counter_in_cam = 1
        self.total_cards_offloaded = 0

        self.report_cards = []
        self.last_report_path = None

        self.source_path = ctk.StringVar(value="")
        self.dest1_path = ctk.StringVar(value="")
        self.dest2_path = ctk.StringVar(value="")
        self.use_dest2 = ctk.BooleanVar(value=False)

        self.auto_mode = ctk.BooleanVar(value=True)
        self.copy_xml_sidecars = ctk.BooleanVar(value=True)
        self.flatten_to_folder = ctk.BooleanVar(value=True)
        self.auto_eject = ctk.BooleanVar(value=True)

        self.is_copying = False
        self.copy_finished_ok = False
        self.stop_requested = False
        self.polling_paused = False
        self.detected_camera = "Aguardando leitura..."

        self.found_files = []
        self.video_count = 0
        self.xml_count = 0
        self.video_bytes = 0
        self.proxy_count = 0
        self.proxy_bytes = 0
        self.photo_count = 0
        self.photo_bytes = 0
        self.audio_count = 0
        self.audio_bytes = 0
        self.total_bytes = 0

        self.anim_phase = 0.0
        self.known_mounts = self._get_mounts()

        self.ico_sd = IconFactory.app_ctk_icon((20, 20))
        self.ico_ssd = IconFactory.ssd_icon(C_ACCENT)
        self.ico_video = IconFactory.video_icon(C_ACCENT)
        self.ico_proxy = IconFactory.proxy_icon(C_PROXY)
        self.ico_photo = IconFactory.photo_icon(C_PHOTO)
        self.ico_audio = IconFactory.audio_icon(C_AUDIO)
        self.ico_check = IconFactory.check_circle(C_SUCCESS)
        self.ico_report = IconFactory.report_icon(C_TEXT)

        self._build_ui()
        self._update_header_badges()

        self.after(300, self.open_wizard)
        self.after(1500, self._poll_usb)
        self.after(50, self._animate_loop)

    def _cam_name(self, idx=None):
        i = self.cam_index if idx is None else idx
        return f"CAM {chr(ord('A') + (i % 26))}"

    def _build_ui(self):
        # 1. BARRA SUPERIOR
        topbar = ctk.CTkFrame(self, fg_color=C_SURFACE, corner_radius=10, border_width=1, border_color=C_BORDER)
        topbar.pack(fill="x", padx=22, pady=(14, 6))

        self.lbl_pulse = ctk.CTkLabel(topbar, text="●", font=("Segoe UI", 16, "bold"), text_color=C_ACCENT)
        self.lbl_pulse.pack(side="left", padx=(16, 6), pady=8)

        ctk.CTkSwitch(
            topbar, text="Modo automático ligado: detecta Vídeos, Proxies, XML, Fotos e Áudio sozinho",
            variable=self.auto_mode, progress_color=C_ACCENT, font=("Segoe UI", 12, "bold"), text_color=C_TEXT
        ).pack(side="left", padx=6, pady=10)

        ctk.CTkButton(
            topbar, text="+ NOVO PROJETO", width=140, height=32, corner_radius=6,
            fg_color=C_CARD, hover_color="#29231D", border_width=1, border_color=C_ACCENT,
            text_color=C_TEXT, font=("Segoe UI", 11, "bold"), command=self.open_wizard
        ).pack(side="right", padx=16, pady=8)

        # 2. BARRA DO PROJETO ATUAL
        projbar = ctk.CTkFrame(self, fg_color=C_CARD, corner_radius=10, border_width=1, border_color=C_BORDER)
        projbar.pack(fill="x", padx=22, pady=6)

        p_left = ctk.CTkFrame(projbar, fg_color="transparent")
        p_left.pack(side="left", fill="x", expand=True, padx=18, pady=10)

        ctk.CTkLabel(p_left, text="PROJETO ATUAL", font=("Segoe UI", 10, "bold"), text_color=C_MUTED).pack(anchor="w")
        self.ent_proj = ctk.CTkEntry(
            p_left, textvariable=self.project_name, width=380, height=34,
            font=("Segoe UI", 15, "bold"), fg_color=C_CARD_INNER, border_color=C_BORDER, text_color=C_TEXT
        )
        self.ent_proj.pack(anchor="w", pady=(3, 5))
        self.ent_proj.bind("<KeyRelease>", lambda e: self._update_header_badges())

        self.lbl_path_pill = ctk.CTkLabel(
            p_left, text="Roteamento: BRUTO/CAM A (+ Proxies e XML)  •  FOTOS  •  GRAVADOR",
            font=("Consolas", 11, "bold"), text_color=C_ACCENT
        )
        self.lbl_path_pill.pack(anchor="w")

        p_right = ctk.CTkFrame(projbar, fg_color="transparent")
        p_right.pack(side="right", padx=18, pady=10)

        ctk.CTkLabel(p_right, text="DESTINO DE VÍDEO ATIVO", font=("Segoe UI", 10, "bold"), text_color=C_MUTED).pack(anchor="e")
        self.lbl_cam_pill = ctk.CTkLabel(
            p_right, text="  🎥  CAM A · CARTÃO 1  ",
            fg_color=C_CARD_INNER, corner_radius=6, font=("Segoe UI", 13, "bold"), text_color=C_ACCENT
        )
        self.lbl_cam_pill.pack(anchor="e", pady=(4, 6), ipadx=8, ipady=3)

        ctk.CTkCheckBox(
            p_right, text="Perguntar sobre próximo cartão ao finalizar",
            variable=self.has_multiple_cards, fg_color=C_ACCENT, font=("Segoe UI", 11), text_color=C_MUTED
        ).pack(anchor="e")

        # 3. ÁREA CENTRAL DE TRABALHO
        self.workspace = ctk.CTkFrame(self, fg_color=C_BG)
        self.workspace.pack(fill="both", expand=True, padx=22, pady=6)

        self.circuit_canvas = tk.Canvas(self.workspace, bg=C_BG, highlightthickness=0)
        self.circuit_canvas.place(relx=0, rely=0, relwidth=1, relheight=1)
        self.workspace.bind("<Configure>", lambda e: self._draw_circuit_lines())

        self.workspace.grid_columnconfigure(0, weight=11, minsize=360)
        self.workspace.grid_columnconfigure(1, weight=7, minsize=260)
        self.workspace.grid_columnconfigure(2, weight=11, minsize=360)
        self.workspace.grid_rowconfigure(0, weight=1)

        # --- COLUNA 1: CARTÃO SD UHS-II V90 ---
        self.card_src = ctk.CTkFrame(self.workspace, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER_GLOW)
        self.card_src.grid(row=0, column=0, sticky="nsew", padx=(0, 14), pady=4)

        self.pins_canvas = tk.Canvas(self.card_src, height=62, bg=C_CARD, highlightthickness=0)
        self.pins_canvas.pack(fill="x", padx=2, pady=(2, 4))
        self.pins_canvas.bind("<Configure>", lambda e: self._draw_sd_v90_header())

        src_head = ctk.CTkFrame(self.card_src, fg_color="transparent")
        src_head.pack(fill="x", padx=18, pady=(2, 6))

        ctk.CTkLabel(src_head, text="SOURCE · O CARTÃO", font=("Segoe UI", 10, "bold"), text_color=C_MUTED).pack(anchor="w")
        self.lbl_card_name = ctk.CTkLabel(src_head, text="AGUARDANDO CARTÃO", font=("Segoe UI", 17, "bold"), text_color=C_TEXT)
        self.lbl_card_name.pack(anchor="w", pady=(1, 1))
        self.lbl_cam_meta = ctk.CTkLabel(src_head, text="Dispositivo: aguardando...", font=("Segoe UI", 11, "bold"), text_color=C_MUTED)
        self.lbl_cam_meta.pack(anchor="w")

        ctk.CTkButton(
            self.card_src, image=self.ico_sd, text="  ⚡ DETECTAR SD CARD", compound="left",
            height=38, corner_radius=8, fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER,
            text_color="#0B0A09", font=("Segoe UI", 12, "bold"),
            command=self.detect_sd_card_now
        ).pack(fill="x", padx=18, pady=(4, 6))

        btn_row = ctk.CTkFrame(self.card_src, fg_color="transparent")
        btn_row.pack(fill="x", padx=18, pady=(0, 6))

        ctk.CTkButton(
            btn_row, text="📁 Pasta Manual", height=30, corner_radius=6,
            fg_color=C_CARD_INNER, hover_color="#29231D", border_width=1, border_color=C_BORDER,
            text_color=C_TEXT, font=("Segoe UI", 11, "bold"), command=self.select_source_manual
        ).pack(side="left", fill="x", expand=True, padx=(0, 5))

        ctk.CTkButton(
            btn_row, text="⏏ Ejetar", width=88, height=30, corner_radius=6,
            fg_color=C_CARD_INNER, hover_color="#29231D", border_width=1, border_color=C_BORDER,
            text_color=C_TEXT, font=("Segoe UI", 11, "bold"), command=self.manual_eject_card
        ).pack(side="right", padx=(5, 0))

        ctk.CTkLabel(self.card_src, text="SEPARAÇÃO AUTOMÁTICA DE PASTAS", font=("Segoe UI", 10, "bold"), text_color=C_MUTED).pack(anchor="w", padx=18, pady=(4, 2))

        self.box_video = ctk.CTkFrame(self.card_src, fg_color=C_CARD_INNER, corner_radius=6, border_width=1, border_color=C_BORDER)
        self.box_video.pack(fill="x", padx=18, pady=2)
        self.lbl_video_row = ctk.CTkLabel(
            self.box_video, image=self.ico_video, text="  Vídeos: 0 arq + 0 XML (0.0 GB) ➔ BRUTO/CAM A",
            compound="left", font=("Segoe UI", 11, "bold"), text_color=C_MUTED
        )
        self.lbl_video_row.pack(anchor="w", padx=10, pady=4)

        self.box_proxy = ctk.CTkFrame(self.card_src, fg_color=C_CARD_INNER, corner_radius=6, border_width=1, border_color=C_BORDER)
        self.box_proxy.pack(fill="x", padx=18, pady=2)
        self.lbl_proxy_row = ctk.CTkLabel(
            self.box_proxy, image=self.ico_proxy, text="  Proxies: 0 arq (0.0 GB) ➔ BRUTO/CAM A/Proxies",
            compound="left", font=("Segoe UI", 11, "bold"), text_color=C_MUTED
        )
        self.lbl_proxy_row.pack(anchor="w", padx=10, pady=4)

        self.box_photo = ctk.CTkFrame(self.card_src, fg_color=C_CARD_INNER, corner_radius=6, border_width=1, border_color=C_BORDER)
        self.box_photo.pack(fill="x", padx=18, pady=2)
        self.lbl_photo_row = ctk.CTkLabel(
            self.box_photo, image=self.ico_photo, text="  Fotos (RAW/JPG): 0 arq (0.0 GB) ➔ FOTOS",
            compound="left", font=("Segoe UI", 11, "bold"), text_color=C_MUTED
        )
        self.lbl_photo_row.pack(anchor="w", padx=10, pady=4)

        self.box_audio = ctk.CTkFrame(self.card_src, fg_color=C_CARD_INNER, corner_radius=6, border_width=1, border_color=C_BORDER)
        self.box_audio.pack(fill="x", padx=18, pady=2)
        self.lbl_audio_row = ctk.CTkLabel(
            self.box_audio, image=self.ico_audio, text="  Gravador: 0 arq (0.0 GB) ➔ GRAVADOR",
            compound="left", font=("Segoe UI", 11, "bold"), text_color=C_MUTED
        )
        self.lbl_audio_row.pack(anchor="w", padx=10, pady=4)

        self.lbl_will_copy = ctk.CTkLabel(self.card_src, text="Total: 0 arquivos · 0.00 GB", font=("Segoe UI", 12, "bold"), text_color=C_TEXT)
        self.lbl_will_copy.pack(anchor="w", padx=18, pady=(6, 2))

        ctk.CTkCheckBox(self.card_src, text="Puxar XML dos clipes (Giroscópio / Metadados)", variable=self.copy_xml_sidecars, fg_color=C_ACCENT, font=("Segoe UI", 11), command=self.scan_source).pack(anchor="w", padx=18, pady=2)
        ctk.CTkCheckBox(self.card_src, text="Ejetar cartão automaticamente ao conferir", variable=self.auto_eject, fg_color=C_ACCENT, font=("Segoe UI", 11)).pack(anchor="w", padx=18, pady=(2, 8))

        # --- COLUNA 2: HUD CENTRAL ---
        center_wrap = ctk.CTkFrame(self.workspace, fg_color="transparent")
        center_wrap.grid(row=0, column=1, sticky="nsew", padx=6, pady=4)

        self.hud_node = ctk.CTkFrame(center_wrap, fg_color=C_CARD, corner_radius=14, border_width=2, border_color=C_ACCENT, width=248, height=270)
        self.hud_node.place(relx=0.5, rely=0.5, anchor="center")
        self.hud_node.pack_propagate(False)

        self.lbl_phase_badge = ctk.CTkLabel(
            self.hud_node, text="AGUARDANDO",
            fg_color=C_CARD_INNER, corner_radius=6, font=("Segoe UI", 11, "bold"), text_color=C_ACCENT,
            width=170, height=26
        )
        self.lbl_phase_badge.pack(pady=(22, 8))

        self.lbl_pct = ctk.CTkLabel(self.hud_node, text="0%", font=("Segoe UI", 42, "bold"), text_color=C_TEXT)
        self.lbl_pct.pack(pady=0)

        self.prog_bar = ctk.CTkProgressBar(self.hud_node, progress_color=C_ACCENT, fg_color=C_CARD_INNER, height=8, corner_radius=4)
        self.prog_bar.pack(fill="x", padx=26, pady=(10, 10))
        self.prog_bar.set(0)

        self.lbl_file_counter = ctk.CTkLabel(self.hud_node, text="0 arquivos na fila", font=("Segoe UI", 12, "bold"), text_color=C_TEXT)
        self.lbl_file_counter.pack(padx=16, pady=1)

        self.lbl_speed_eta = ctk.CTkLabel(self.hud_node, text="Hash BLAKE2b ativo", font=("Segoe UI", 11), text_color=C_MUTED)
        self.lbl_speed_eta.pack(padx=16, pady=(0, 12))

        self.btn_action = ctk.CTkButton(
            self.hud_node, text="INICIAR", height=40, corner_radius=8,
            fg_color=C_ACCENT, hover_color=C_ACCENT_HOVER, text_color="#0B0A09",
            font=("Segoe UI", 13, "bold"), command=self.toggle_copy
        )
        self.btn_action.pack(fill="x", padx=28, pady=(4, 18))

        # --- COLUNA 3: DESTINOS ---
        right_stack = ctk.CTkFrame(self.workspace, fg_color="transparent")
        right_stack.grid(row=0, column=2, sticky="nsew", padx=(14, 0), pady=4)
        right_stack.grid_rowconfigure((0, 1), weight=1)
        right_stack.grid_columnconfigure(0, weight=1)

        self.card_d1 = ctk.CTkFrame(right_stack, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER_GLOW)
        self.card_d1.grid(row=0, column=0, sticky="nsew", pady=(0, 8))

        d1_top = ctk.CTkFrame(self.card_d1, fg_color="transparent")
        d1_top.pack(fill="x", padx=18, pady=(14, 6))
        ctk.CTkLabel(d1_top, image=self.ico_ssd, text="  DELIVERY · CÓPIA 1 (PRINCIPAL)", compound="left", font=("Segoe UI", 11, "bold"), text_color=C_ACCENT).pack(side="left")
        ctk.CTkButton(d1_top, text="Escolher SSD/HD", width=116, height=28, corner_radius=6, fg_color=C_CARD_INNER, hover_color="#29231D", border_width=1, border_color=C_ACCENT, font=("Segoe UI", 11, "bold"), command=self.select_dest1).pack(side="right")

        self.lbl_d1_name = ctk.CTkLabel(self.card_d1, text="Selecione o SSD / HD Principal", font=("Segoe UI", 16, "bold"), text_color=C_TEXT, anchor="w")
        self.lbl_d1_name.pack(fill="x", padx=18, pady=(2, 2))

        self.lbl_d1_sub = ctk.CTkLabel(self.card_d1, text="Pasta destino ainda não selecionada", font=("Consolas", 11), text_color=C_MUTED, anchor="w")
        self.lbl_d1_sub.pack(fill="x", padx=18, pady=(0, 8))

        self.bar_d1_space = ctk.CTkProgressBar(self.card_d1, progress_color=C_ACCENT, fg_color=C_CARD_INNER, height=8, corner_radius=4)
        self.bar_d1_space.pack(fill="x", padx=18, pady=4)
        self.bar_d1_space.set(0)

        self.lbl_d1_space = ctk.CTkLabel(self.card_d1, text="-- GB livres · depois deste cartão: -- GB", font=("Segoe UI", 11), text_color=C_MUTED, anchor="w")
        self.lbl_d1_space.pack(fill="x", padx=18, pady=(2, 6))

        ctk.CTkButton(
            self.card_d1, text="📂 ABRIR PASTA DO PROJETO", height=32, corner_radius=6,
            fg_color=C_CARD_INNER, hover_color="#29231D", border_width=1, border_color=C_BORDER,
            font=("Segoe UI", 11, "bold"), command=self.open_project_folder
        ).pack(anchor="w", padx=18, pady=(6, 14))

        self.card_d2 = ctk.CTkFrame(right_stack, fg_color=C_CARD, corner_radius=12, border_width=1, border_color=C_BORDER)
        self.card_d2.grid(row=1, column=0, sticky="nsew", pady=(8, 0))

        d2_top = ctk.CTkFrame(self.card_d2, fg_color="transparent")
        d2_top.pack(fill="x", padx=18, pady=(14, 6))
        ctk.CTkSwitch(
            d2_top, text="DELIVERY · CÓPIA 2 (2º HD / DRIVE)",
            variable=self.use_dest2, progress_color=C_ACCENT, font=("Segoe UI", 11, "bold"),
            command=self._toggle_d2
        ).pack(side="left")
        self.btn_d2_pick = ctk.CTkButton(d2_top, text="Escolher 2º HD", width=116, height=28, corner_radius=6, fg_color=C_CARD_INNER, hover_color="#29231D", state="disabled", font=("Segoe UI", 11, "bold"), command=self.select_dest2)
        self.btn_d2_pick.pack(side="right")

        self.lbl_d2_name = ctk.CTkLabel(self.card_d2, text="2º Backup Opcional Desativado", font=("Segoe UI", 15, "bold"), text_color=C_MUTED, anchor="w")
        self.lbl_d2_name.pack(fill="x", padx=18, pady=(2, 4))

        self.bar_d2_space = ctk.CTkProgressBar(self.card_d2, progress_color=C_ACCENT, fg_color=C_CARD_INNER, height=8, corner_radius=4)
        self.bar_d2_space.pack(fill="x", padx=18, pady=4)
        self.bar_d2_space.set(0)

        self.lbl_d2_space = ctk.CTkLabel(self.card_d2, text="Ative a chave acima para gravar em 2 destinos simultâneos", font=("Segoe UI", 11), text_color=C_MUTED, anchor="w")
        self.lbl_d2_space.pack(fill="x", padx=18, pady=(2, 8))

        ctk.CTkButton(
            self.card_d2, image=self.ico_report, text="  ABRIR RELATÓRIOS DE AUDITORIA", compound="left",
            height=34, corner_radius=6, fg_color=C_CARD_INNER, hover_color="#29231D",
            border_width=1, border_color=C_SUCCESS, text_color=C_TEXT, font=("Segoe UI", 11, "bold"),
            command=self.open_reports
        ).pack(fill="x", padx=18, pady=(8, 14))

        # 4. BARRA DE STATUS INFERIOR
        self.log_bar = ctk.CTkLabel(
            self, text="LoggerPro pronto. Ejeção nativa Win32 (Lock + Dismount) ativa.",
            anchor="w", fg_color=C_SURFACE, corner_radius=6, font=("Consolas", 11), text_color=C_MUTED
        )
        self.log_bar.pack(fill="x", padx=22, pady=(4, 12), ipadx=12, ipady=5)

    # ---------------- CABEÇALHO SD CARD V90 (UHS-II) ---------------- #
    def _draw_sd_v90_header(self):
        c = self.pins_canvas
        c.delete("all")
        w = c.winfo_width()
        h = c.winfo_height()
        if w < 60:
            return

        chamfer = 26
        c.create_polygon(0, 0, w - chamfer, 0, w, chamfer, w, h, 0, h, fill="#15120F", outline="")
        c.create_polygon(w - chamfer, 0, w, 0, w, chamfer, fill=C_BG, outline="")
        c.create_line(w - chamfer, 0, w, chamfer, fill=C_BORDER_GLOW, width=2)

        c.create_line(0, h - 2, w, h - 2, fill=C_BORDER_GLOW, width=1)
        c.create_line(14, h - 6, w - 14, h - 6, fill="#2A221B", width=1)

        left_margin = 16
        badge_space = 86
        usable_w = max(w - left_margin - badge_space, 160)
        num_top = 9
        gap = 5
        pin_w = max(int((usable_w - (num_top - 1) * gap) / num_top), 12)

        for i in range(num_top):
            x0 = left_margin + i * (pin_w + gap)
            y0 = 10 if i == 0 else 6
            y1 = 27
            active = self.is_copying and ((int(self.anim_phase * 10) + i) % 3 == 0)
            col = C_GOLD_BRIGHT if active else C_GOLD
            c.create_rectangle(x0, y0, x0 + pin_w, y1, fill=col, outline=C_GOLD_DARK, width=1)
            c.create_line(x0 + 2, y0 + 2, x0 + pin_w - 2, y0 + 2, fill="#FCE3A6")

        num_bot = 8
        bot_pin_w = max(int(pin_w * 0.82), 10)
        total_bot_w = num_bot * bot_pin_w + (num_bot - 1) * gap
        bot_start_x = left_margin + max((usable_w - total_bot_w) // 2, 0)

        for j in range(num_bot):
            bx0 = bot_start_x + j * (bot_pin_w + gap)
            by0 = 32
            by1 = 49
            active = self.is_copying and ((int(self.anim_phase * 12) + j) % 3 == 1)
            col = C_GOLD_BRIGHT if active else "#C49538"
            c.create_rectangle(bx0, by0, bx0 + bot_pin_w, by1, fill=col, outline=C_GOLD_DARK, width=1)

        bx = w - badge_space + 8
        c.create_rectangle(bx, 10, w - 18, 32, fill="#241E18", outline=C_GOLD_DARK, width=1)
        c.create_text((bx + w - 18) // 2, 21, text="V90", fill=C_GOLD_BRIGHT, font=("Segoe UI", 10, "bold"))
        c.create_text((bx + w - 18) // 2, 42, text="UHS-II", fill=C_MUTED, font=("Consolas", 8, "bold"))

    def _draw_circuit_lines(self):
        cv = self.circuit_canvas
        cv.delete("all")
        w, h = cv.winfo_width(), cv.winfo_height()
        if w < 100 or h < 100:
            return

        x_src = int(w * 0.33)
        x_mid_l = int(w * 0.40)
        x_mid_r = int(w * 0.60)
        x_dst = int(w * 0.67)

        y_mid = int(h * 0.50)
        y_d1 = int(h * 0.26)
        y_d2 = int(h * 0.74)

        main_color = C_SUCCESS if self.copy_finished_ok else (C_ACCENT if self.is_copying else "#3A2E23")
        d2_color = main_color if self.use_dest2.get() else "#221D18"

        cv.create_line(x_src, y_mid, x_mid_l, y_mid, fill=main_color, width=2)
        knee_x = int((x_mid_r + x_dst) / 2)
        cv.create_line(x_mid_r, y_mid - 18, knee_x, y_mid - 18, knee_x, y_d1, x_dst, y_d1, fill=main_color, width=2)
        cv.create_line(x_mid_r, y_mid + 18, knee_x, y_mid + 18, knee_x, y_d2, x_dst, y_d2, fill=d2_color, width=2)

        if self.is_copying:
            t = self.anim_phase % 1.0
            px1 = x_src + (x_mid_l - x_src) * t
            cv.create_oval(px1 - 4, y_mid - 4, px1 + 4, y_mid + 4, fill="#FFF0D0", outline=C_ACCENT)
            py_d1 = (y_mid - 18) + (y_d1 - (y_mid - 18)) * t
            cv.create_oval(knee_x - 4, py_d1 - 4, knee_x + 4, py_d1 + 4, fill="#FFF0D0", outline=C_ACCENT)
            if self.use_dest2.get():
                py_d2 = (y_mid + 18) + (y_d2 - (y_mid + 18)) * t
                cv.create_oval(knee_x - 4, py_d2 - 4, knee_x + 4, py_d2 + 4, fill="#FFF0D0", outline=C_ACCENT)

    def _animate_loop(self):
        self.anim_phase += 0.08
        if self.auto_mode.get() and not self.polling_paused:
            pulse_col = C_ACCENT if int(self.anim_phase * 2) % 2 == 0 else "#7A4012"
            self.lbl_pulse.configure(text_color=pulse_col)
        else:
            self.lbl_pulse.configure(text_color=C_MUTED)

        if self.is_copying:
            self._draw_sd_v90_header()
            self._draw_circuit_lines()

        self.after(70, self._animate_loop)

    def log(self, msg):
        self.log_bar.configure(text=f"[{time.strftime('%H:%M:%S')}]  {msg}")

    # ---------------- GERENCIAMENTO E DETECÇÃO DO CARTÃO ---------------- #
    def open_wizard(self):
        if self.is_copying:
            return
        m = ProjectSetupModal(self, self.project_name.get())
        self.wait_window(m)
        if m.confirmed:
            self.project_name.set(m.project_name)
            self.has_multiple_cards.set(m.multi_card)
            self.cam_index = 0
            self.card_counter_in_cam = 1
            self.total_cards_offloaded = 0
            self.report_cards = []
            self.copy_finished_ok = False
            self.polling_paused = False
            self.known_mounts = self._get_mounts()
            self._reset_hud_to_idle()
            self._update_header_badges()
            self.log(f"Projeto '{m.project_name}' iniciado no LoggerPro.")

    def _update_header_badges(self):
        proj = self.project_name.get().strip() or "PROJETO"
        cam = self._cam_name()
        self.lbl_path_pill.configure(text=f"Roteamento: {proj}  ➔  BRUTO/{cam} (+ Proxies e XML)  •  FOTOS  •  GRAVADOR")
        self.lbl_cam_pill.configure(text=f"  🎥  {cam} · CARTÃO {self.card_counter_in_cam}  ")
        self._refresh_storage_bars()

    def _toggle_d2(self):
        if self.use_dest2.get():
            self.btn_d2_pick.configure(state="normal", border_width=1, border_color=C_ACCENT)
            self.card_d2.configure(border_color=C_BORDER_GLOW)
            self.lbl_d2_name.configure(text=self.dest2_path.get() or "Selecione o 2º HD ou Google Drive", text_color=C_TEXT)
        else:
            self.btn_d2_pick.configure(state="disabled", border_width=0)
            self.card_d2.configure(border_color=C_BORDER)
            self.lbl_d2_name.configure(text="2º Backup Opcional Desativado", text_color=C_MUTED)
        self._refresh_storage_bars()
        self._draw_circuit_lines()

    def _get_mounts(self):
        try:
            return {p.mountpoint for p in psutil.disk_partitions(all=False)}
        except Exception:
            return set()

    def _poll_usb(self):
        # Só sonda as portas USB se não estiver copiando e se o cartão não tiver acabado de ser ejetado!
        if not self.is_copying and not self.polling_paused:
            cur = self._get_mounts()
            new = cur - self.known_mounts
            if new:
                drive = list(new)[0]
                self.known_mounts = cur
                self.log(f"⚡ Cartão SD detectado automaticamente em {drive}")
                self._load_card(drive)
                if self.auto_mode.get() and self.dest1_path.get() and self.found_files:
                    self.toggle_copy()
            else:
                self.known_mounts = cur
        self.after(1500, self._poll_usb)

    def detect_sd_card_now(self):
        # Ao clicar manualmente em Detectar SD Card, reativa o detector
        self.polling_paused = False
        candidates = []
        camera_signatures = ("PRIVATE", "DCIM", "M4ROOT", "XDROOT", "ZOOM", "TASCAM", "RODE", "CANONMSC", "BPAV")

        try:
            for p in psutil.disk_partitions(all=False):
                mp = p.mountpoint
                if os.name == "nt" and mp.upper().startswith("C:"):
                    continue
                if sys.platform == "darwin" and (mp == "/" or not mp.startswith("/Volumes")):
                    continue

                score = 0
                if "removable" in p.opts.lower():
                    score += 50

                try:
                    root_items = {item.upper() for item in os.listdir(mp)}
                    if any(sig in root_items for sig in camera_signatures):
                        score += 100
                except Exception:
                    continue

                if score > 0:
                    candidates.append((score, mp))
        except Exception:
            pass

        if candidates:
            candidates.sort(key=lambda x: x[0], reverse=True)
            best_drive = candidates[0][1]
            self.known_mounts = self._get_mounts()
            self.log(f"⚡ Cartão SD localizado com sucesso em: {best_drive}")
            self._load_card(best_drive)
        else:
            self.log("Nenhum cartão SD removível detectado no momento.")
            messagebox.showinfo(
                "LoggerPro • Detectar SD Card",
                "Nenhum cartão SD ou gravador foi encontrado nas portas USB.\n\n"
                "Se você acabou de ejetar o cartão, remova-o e insira novamente no leitor."
            )

    def select_source_manual(self):
        f = filedialog.askdirectory(title="Selecione o Cartão SD ou Pasta Manualmente")
        if f:
            try:
                os.chdir(os.path.expanduser("~"))
            except Exception:
                pass
            self.polling_paused = False
            self._load_card(f)

    def _read_device_metadata(self, root_path):
        try:
            for r, dirs, files in os.walk(root_path):
                upper_dirs = {d.upper() for d in dirs}
                if upper_dirs & {"ZOOM", "TASCAM", "STEREO", "MULTI", "RODE", "DJI_AUDIO"}:
                    return "Gravador de Áudio Externo"
                for f in files:
                    if f.upper().endswith(".XML"):
                        with open(os.path.join(r, f), "r", encoding="utf-8", errors="ignore") as fp:
                            m = re.search(r'modelName\s*=\s*"([^"]+)"', fp.read(8192), re.I)
                            if m:
                                return m.group(1)
            if os.path.exists(os.path.join(root_path, "PRIVATE", "M4ROOT")):
                return "Sony Cinema / Alpha"
        except Exception:
            pass
        return "Cartão SD V90"

    def _load_card(self, folder):
        self.copy_finished_ok = False
        self._reset_hud_to_idle()
        self.source_path.set(folder)
        self.detected_camera = self._read_device_metadata(folder)
        self.scan_source()

    def scan_source(self):
        src = self.source_path.get()
        if not src or not os.path.exists(src):
            return

        self.found_files = []
        self.video_count = self.xml_count = self.video_bytes = 0
        self.proxy_count = self.proxy_bytes = 0
        self.photo_count = self.photo_bytes = 0
        self.audio_count = self.audio_bytes = 0
        self.total_bytes = 0

        candidates = []
        raw_stems = set()
        video_stems = set()

        for r, dirs, files in os.walk(src):
            dirs[:] = [d for d in dirs if d.lower() not in BLOCKED_DIRS and not d.startswith(".")]

            rel_parts_upper = {p.upper() for p in Path(r).relative_to(src).parts}
            rel_parts_lower = {p.lower() for p in Path(r).relative_to(src).parts}

            for f in files:
                if f.startswith(".") or f.startswith("._"):
                    continue
                ext = os.path.splitext(f)[1].lower()
                stem_upper = os.path.splitext(f)[0].upper()
                fp = os.path.join(r, f)

                try:
                    sz = os.path.getsize(fp)
                except OSError:
                    continue

                if ext in RAW_PHOTO_EXTENSIONS:
                    raw_stems.add(stem_upper)
                elif ext in VIDEO_EXTENSIONS and not (rel_parts_lower & PROXY_DIRS):
                    video_stems.add(stem_upper)

                candidates.append((fp, f, ext, stem_upper, sz, rel_parts_upper, rel_parts_lower))

        include_xml = self.copy_xml_sidecars.get()

        for fp, fname, ext, stem_upper, sz, rel_parts_upper, rel_parts_lower in candidates:
            in_proxy_folder = bool(rel_parts_lower & PROXY_DIRS)
            in_video_tree = bool(rel_parts_upper & {"PRIVATE", "M4ROOT", "CLIP", "XDROOT", "BDMV", "STREAM"})
            in_dcim = "DCIM" in rel_parts_upper

            if ext in VIDEO_EXTENSIONS and (in_proxy_folder or SONY_PROXY_REGEX.match(fname)):
                self.found_files.append((fp, sz, "PROXY"))
                self.proxy_count += 1
                self.proxy_bytes += sz
                self.total_bytes += sz

            elif ext in VIDEO_EXTENSIONS:
                self.found_files.append((fp, sz, "VIDEO"))
                self.video_count += 1
                self.video_bytes += sz
                self.total_bytes += sz

            elif ext == ".xml" and include_xml and not in_proxy_folder:
                if fname.lower() in IGNORED_XML_NAMES:
                    continue
                is_clip_xml = (
                    "CLIP" in rel_parts_upper
                    or stem_upper.endswith("M01")
                    or any(stem_upper.startswith(vs) for vs in video_stems)
                )
                if is_clip_xml:
                    self.found_files.append((fp, sz, "VIDEO_XML"))
                    self.xml_count += 1
                    self.video_bytes += sz
                    self.total_bytes += sz

            elif ext in RAW_PHOTO_EXTENSIONS:
                self.found_files.append((fp, sz, "PHOTO"))
                self.photo_count += 1
                self.photo_bytes += sz
                self.total_bytes += sz

            elif ext in STD_PHOTO_EXTENSIONS:
                if SONY_THUMB_REGEX.match(fname) or in_video_tree or in_proxy_folder:
                    continue
                if in_dcim or (stem_upper in raw_stems) or not in_video_tree:
                    self.found_files.append((fp, sz, "PHOTO"))
                    self.photo_count += 1
                    self.photo_bytes += sz
                    self.total_bytes += sz

            elif ext in AUDIO_EXTENSIONS:
                if (in_video_tree or in_proxy_folder) and "CLIP" not in rel_parts_upper:
                    continue
                self.found_files.append((fp, sz, "AUDIO"))
                self.audio_count += 1
                self.audio_bytes += sz
                self.total_bytes += sz

        short_src = truncate_middle(src, 22)
        if self.audio_count > 0 and self.video_count == 0 and self.photo_count == 0:
            self.detected_camera = "Gravador de Áudio"
            self.lbl_card_name.configure(text=f"GRAVADOR ({short_src})")
        elif self.photo_count > 0 and self.video_count == 0 and self.audio_count == 0:
            self.lbl_card_name.configure(text=f"FOTOS ({short_src})")
        else:
            self.lbl_card_name.configure(text=f"CARD {self.card_counter_in_cam} ({short_src})")

        self.lbl_cam_meta.configure(text=f"Dispositivo: {self.detected_camera}", text_color=C_ACCENT)

        cam = self._cam_name()
        v_gb = self.video_bytes / (1024 ** 3)
        prx_gb = self.proxy_bytes / (1024 ** 3)
        p_gb = self.photo_bytes / (1024 ** 3)
        a_gb = self.audio_bytes / (1024 ** 3)
        tot_gb = self.total_bytes / (1024 ** 3)

        xml_tag = f" + {self.xml_count} XML" if self.xml_count > 0 else ""
        self.lbl_video_row.configure(
            text=f"  Vídeos: {self.video_count} arq{xml_tag} ({v_gb:.2f} GB) ➔ BRUTO/{cam}",
            text_color=C_TEXT if (self.video_count + self.xml_count) > 0 else C_MUTED
        )
        self.box_video.configure(border_color=C_ACCENT if self.video_count > 0 else C_BORDER)

        self.lbl_proxy_row.configure(
            text=f"  Proxies: {self.proxy_count} arq ({prx_gb:.2f} GB) ➔ BRUTO/{cam}/Proxies",
            text_color=C_TEXT if self.proxy_count > 0 else C_MUTED
        )
        self.box_proxy.configure(border_color=C_PROXY if self.proxy_count > 0 else C_BORDER)

        self.lbl_photo_row.configure(
            text=f"  Fotos (RAW/JPG): {self.photo_count} arq ({p_gb:.2f} GB) ➔ FOTOS",
            text_color=C_TEXT if self.photo_count > 0 else C_MUTED
        )
        self.box_photo.configure(border_color=C_PHOTO if self.photo_count > 0 else C_BORDER)

        self.lbl_audio_row.configure(
            text=f"  Gravador: {self.audio_count} arq ({a_gb:.2f} GB) ➔ GRAVADOR",
            text_color=C_TEXT if self.audio_count > 0 else C_MUTED
        )
        self.box_audio.configure(border_color=C_AUDIO if self.audio_count > 0 else C_BORDER)

        self.lbl_will_copy.configure(text=f"Total: {len(self.found_files)} arquivos · {tot_gb:.2f} GB")
        self.lbl_file_counter.configure(text=f"{len(self.found_files)} arquivos prontos")
        self._refresh_storage_bars()
        self._draw_circuit_lines()

    def select_dest1(self):
        f = filedialog.askdirectory(title="Selecione a Pasta Principal (SSD/HD)")
        if f:
            try:
                os.chdir(os.path.expanduser("~"))
            except Exception:
                pass
            self.dest1_path.set(os.path.normpath(f))
            self._refresh_storage_bars()

    def select_dest2(self):
        f = filedialog.askdirectory(title="Selecione o 2º HD ou Pasta do Google Drive")
        if f:
            try:
                os.chdir(os.path.expanduser("~"))
            except Exception:
                pass
            self.dest2_path.set(os.path.normpath(f))
            self._refresh_storage_bars()

    def _refresh_storage_bars(self):
        card_gb = self.total_bytes / (1024 ** 3)
        proj = self.project_name.get().strip() or "PROJETO"

        if self.dest1_path.get() and os.path.exists(self.dest1_path.get()):
            p1 = os.path.normpath(self.dest1_path.get())
            u1 = shutil.disk_usage(p1)
            free_gb = u1.free / (1024 ** 3)
            tot_gb = u1.total / (1024 ** 3)
            after_gb = max(free_gb - card_gb, 0)
            used_ratio = min((u1.used + self.total_bytes) / max(u1.total, 1), 1.0)
            full_target = os.path.join(p1, proj)
            self.lbl_d1_name.configure(text=Path(p1).name or p1)
            self.lbl_d1_sub.configure(text=truncate_middle(full_target, 46))
            self.bar_d1_space.set(used_ratio)
            self.lbl_d1_space.configure(text=f"{free_gb:.1f} GB livres de {tot_gb:.0f} GB · depois: {after_gb:.1f} GB")

        if self.use_dest2.get() and self.dest2_path.get() and os.path.exists(self.dest2_path.get()):
            p2 = os.path.normpath(self.dest2_path.get())
            u2 = shutil.disk_usage(p2)
            free_gb = u2.free / (1024 ** 3)
            tot_gb = u2.total / (1024 ** 3)
            after_gb = max(free_gb - card_gb, 0)
            used_ratio = min((u2.used + self.total_bytes) / max(u2.total, 1), 1.0)
            self.lbl_d2_name.configure(text=truncate_middle(p2, 38), text_color=C_TEXT)
            self.bar_d2_space.set(used_ratio)
            self.lbl_d2_space.configure(text=f"{free_gb:.1f} GB livres de {tot_gb:.0f} GB · depois: {after_gb:.1f} GB")

    def _reset_hud_to_idle(self):
        self.hud_node.configure(fg_color=C_CARD, border_color=C_ACCENT)
        self.lbl_phase_badge.configure(text="AGUARDANDO", fg_color=C_CARD_INNER, text_color=C_ACCENT)
        self.lbl_pct.configure(text="0%", font=("Segoe UI", 42, "bold"), text_color=C_TEXT)
        self.prog_bar.configure(progress_color=C_ACCENT)
        self.prog_bar.set(0)
        self.lbl_file_counter.configure(text=f"{len(self.found_files)} arquivos na fila")
        self.lbl_speed_eta.configure(text="Hash BLAKE2b ativo", text_color=C_MUTED)
        self.btn_action.configure(text="INICIAR", fg_color=C_ACCENT, text_color="#0B0A09")

    # ---------------- MOTOR DE CÓPIA E VERIFICAÇÃO ---------------- #
    def toggle_copy(self):
        if self.is_copying:
            self.stop_requested = True
            return
        if not self.source_path.get() or not self.dest1_path.get():
            messagebox.showwarning("Atenção", "Selecione o cartão SD e a pasta do Destino 1.")
            return
        if self.use_dest2.get() and not self.dest2_path.get():
            messagebox.showwarning("Atenção", "Selecione a pasta do 2º Destino ou desative a chave Cópia 2.")
            return
        if not self.found_files:
            messagebox.showwarning("Atenção", "Nenhum arquivo válido encontrado no cartão.")
            return

        self.is_copying = True
        self.copy_finished_ok = False
        self.stop_requested = False
        self._reset_hud_to_idle()
        self.btn_action.configure(text="PARAR", fg_color=C_CARD_INNER, text_color=C_ACCENT)
        threading.Thread(target=self._worker, daemon=True).start()

    def _safe_dest(self, folder: Path, name: str) -> Path:
        cand = folder / name
        if not cand.exists():
            return cand
        return folder / f"{cand.stem}_CARD{self.card_counter_in_cam}{cand.suffix}"

    def _get_category_subfolder(self, proj_root: Path, category: str, cam_name: str) -> tuple[Path, str]:
        if category == "PHOTO":
            return proj_root / "FOTOS", "FOTOS"
        elif category == "AUDIO":
            return proj_root / "GRAVADOR", "GRAVADOR"
        elif category == "PROXY":
            return proj_root / "BRUTO" / cam_name / "Proxies", f"BRUTO/{cam_name}/Proxies"
        else:
            return proj_root / "BRUTO" / cam_name, f"BRUTO/{cam_name}"

    def _worker(self):
        src_root = Path(self.source_path.get())
        proj = self.project_name.get().strip() or "PROJETO"
        cam = self._cam_name()

        proj_root1 = Path(self.dest1_path.get()) / proj
        proj_root2 = (Path(self.dest2_path.get()) / proj) if self.use_dest2.get() else None

        proj_root1.mkdir(parents=True, exist_ok=True)
        if proj_root2:
            proj_root2.mkdir(parents=True, exist_ok=True)

        corrupted, file_records = [], []
        copied = 0
        t0 = time.time()
        total = len(self.found_files)

        for idx, (fpath, sz, cat) in enumerate(self.found_files, 1):
            if self.stop_requested:
                break

            src_f = Path(fpath)
            target_dir1, folder_label = self._get_category_subfolder(proj_root1, cat, cam)
            target_dir2, _ = self._get_category_subfolder(proj_root2, cat, cam) if proj_root2 else (None, "")

            target_dir1.mkdir(parents=True, exist_ok=True)
            if target_dir2:
                target_dir2.mkdir(parents=True, exist_ok=True)

            if self.flatten_to_folder.get() or cat == "PROXY":
                d1 = self._safe_dest(target_dir1, src_f.name)
                d2 = self._safe_dest(target_dir2, src_f.name) if target_dir2 else None
            else:
                rel = src_f.relative_to(src_root)
                d1 = target_dir1 / rel
                d2 = (target_dir2 / rel) if target_dir2 else None
                d1.parent.mkdir(parents=True, exist_ok=True)
                if d2:
                    d2.parent.mkdir(parents=True, exist_ok=True)

            if sz == 0:
                corrupted.append(f"{src_f.name} (0 bytes)")

            h_src = hashlib.blake2b()
            status = "OK"
            try:
                with open(src_f, "rb") as fin, open(d1, "wb") as fo1:
                    fo2 = open(d2, "wb") if d2 else None
                    try:
                        while chunk := fin.read(4 * 1024 * 1024):
                            if self.stop_requested:
                                break
                            h_src.update(chunk)
                            fo1.write(chunk)
                            if fo2:
                                fo2.write(chunk)
                            copied += len(chunk)
                            self._ui_prog("COPIANDO", idx, total, copied, t0)
                    finally:
                        if fo2:
                            fo2.close()

                if self.stop_requested:
                    break

                shutil.copystat(src_f, d1)
                if d2:
                    shutil.copystat(src_f, d2)

                self._ui_prog("CONFERINDO", idx, total, copied, t0)
                digest = h_src.hexdigest()
                if not self._check_hash(d1, digest) or (d2 and not self._check_hash(d2, digest)):
                    status = "ERRO HASH"
                    corrupted.append(f"{src_f.name} (Hash Divergente)")
            except Exception as e:
                status = f"ERRO ({e})"
                corrupted.append(f"{src_f.name} ({e})")

            file_records.append({
                "name": d1.name,
                "dest_folder": folder_label,
                "size_mb": sz / (1024 * 1024),
                "hash": h_src.hexdigest()[:16],
                "status": status if sz > 0 else "CORROMPIDO"
            })

        card_label = "GRAVADOR" if (self.audio_count > 0 and self.video_count == 0) else (
            "FOTOS" if (self.photo_count > 0 and self.video_count == 0) else f"{cam} (Cartão {self.card_counter_in_cam})"
        )

        self.report_cards.append({
            "card_title": card_label,
            "model": self.detected_camera,
            "finished_at": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "total_files": len(file_records),
            "total_gb": self.total_bytes / (1024 ** 3),
            "files": file_records
        })
        self._write_reports(proj_root1, proj_root2)
        was_only_aux = (self.video_count == 0 and self.proxy_count == 0)
        self.after(0, lambda: self._finish(corrupted, total, was_only_aux))

    def _check_hash(self, p: Path, exp: str) -> bool:
        h = hashlib.blake2b()
        with open(p, "rb") as f:
            while c := f.read(4 * 1024 * 1024):
                h.update(c)
        return h.hexdigest() == exp

    def _ui_prog(self, phase, idx, total, copied, t0):
        el = max(time.time() - t0, 0.1)
        spd = (copied / (1024 * 1024)) / el
        rem = max(self.total_bytes - copied, 0)
        eta = int(rem / max(copied / el, 1))
        pct = copied / self.total_bytes if self.total_bytes > 0 else 1.0
        self.after(0, lambda: (
            self.lbl_phase_badge.configure(text=phase),
            self.lbl_pct.configure(text=f"{int(pct * 100)}%"),
            self.prog_bar.set(pct),
            self.lbl_file_counter.configure(text=f"Arquivo {idx} de {total}"),
            self.lbl_speed_eta.configure(text=f"{spd:.0f} MB/s · {eta // 60}m {eta % 60}s")
        ))

    def _finish(self, corrupted, total, was_only_aux):
        self.is_copying = False
        if self.stop_requested:
            self.lbl_phase_badge.configure(text="PAUSADO", text_color=C_WARNING)
            self.btn_action.configure(text="INICIAR", fg_color=C_ACCENT, text_color="#0B0A09")
            self._draw_circuit_lines()
            return

        if corrupted:
            self.lbl_phase_badge.configure(text="ERRO DETECTADO", text_color=C_WARNING)
            messagebox.showwarning("Atenção", "Problemas:\n\n" + "\n".join(corrupted[:8]))
            return

        self.copy_finished_ok = True
        self.total_cards_offloaded += 1
        dest_count = "nos 2 HDs" if self.use_dest2.get() else "no SSD/HD"

        self.hud_node.configure(fg_color=C_SUCCESS_BG, border_color=C_SUCCESS)
        self.lbl_phase_badge.configure(text="✓ CONFERIDO", fg_color="#14331C", text_color=C_SUCCESS)
        self.lbl_pct.configure(text="100%", font=("Segoe UI", 38, "bold"), text_color=C_SUCCESS)
        self.prog_bar.configure(progress_color=C_SUCCESS)
        self.prog_bar.set(1.0)
        self.lbl_file_counter.configure(text=f"{total} arq · {dest_count}")
        self.lbl_speed_eta.configure(text="Pode remover do leitor", text_color=C_SUCCESS)
        self.btn_action.configure(text="EJETADO", fg_color=C_SUCCESS, text_color="#0B0A09")

        self._draw_sd_v90_header()
        self._draw_circuit_lines()
        self.bell()

        card_to_eject = self.source_path.get()
        self.source_path.set("")
        self.found_files = []
        self.lbl_card_name.configure(text="CARTÃO EJETADO")

        if self.auto_eject.get():
            self._eject(card_to_eject)

        if self.has_multiple_cards.get():
            m = NextCardModal(self, self._cam_name(self.cam_index), self._cam_name(self.cam_index + 1), was_only_aux)
            self.wait_window(m)
            if m.result == "new_cam":
                self.cam_index += 1
                self.card_counter_in_cam = 1
                self._update_header_badges()
                self._resume_polling_after_swap()
            elif m.result == "continue_cam":
                if not was_only_aux:
                    self.card_counter_in_cam += 1
                self._update_header_badges()
                self._resume_polling_after_swap()
            elif m.result == "keep_cam":
                self._update_header_badges()
                self._resume_polling_after_swap()
            else:
                self.open_reports()

    def _resume_polling_after_swap(self):
        """Reativa a busca automática após o usuário confirmar que vai inserir o próximo cartão."""
        self.known_mounts = self._get_mounts()
        self.polling_paused = False
        self.log("Aguardando conexão do próximo cartão SD...")

    # ---------------- RELATÓRIOS ---------------- #
    def _write_reports(self, proj_root1: Path, proj_root2: Path | None):
        proj = self.project_name.get().strip() or "PROJETO"
        txt_lines = [
            f"RELATÓRIO DE AUDITORIA E INGEST - LOGGERPRO",
            f"Projeto: {proj}",
            f"Gerado em: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}",
            f"Destino 1: {proj_root1}",
            f"Destino 2: {proj_root2 if proj_root2 else 'Desativado'}",
            "=" * 78
        ]
        html_cards = ""
        for c in self.report_cards:
            txt_lines.append(f"\n[{c['card_title']}] Dispositivo: {c['model']} | {c['total_files']} arq ({c['total_gb']:.2f} GB) | {c['finished_at']}")
            rows = ""
            for f in c["files"]:
                txt_lines.append(f"  - [{f['dest_folder']}] {f['name']} | {f['size_mb']:.2f} MB | Hash: {f['hash']} | {f['status']}")
                col = C_SUCCESS if f["status"] == "OK" else C_WARNING
                rows += f"<tr><td><b>{f['dest_folder']}</b></td><td>{f['name']}</td><td>{f['size_mb']:.2f} MB</td><td><code>{f['hash']}</code></td><td style='color:{col};font-weight:bold'>{f['status']}</td></tr>"
            html_cards += f"<h3>📁 {c['card_title']} · {c['model']} · {c['total_files']} arquivos ({c['total_gb']:.2f} GB)</h3><table><tr><th>Pasta Destino</th><th>Arquivo</th><th>Tamanho</th><th>Hash BLAKE2b</th><th>Status</th></tr>{rows}</table>"

        html = f"""<!DOCTYPE html><html lang='pt-BR'><head><meta charset='utf-8'><title>Relatório LoggerPro - {proj}</title>
        <style>body{{background:#0B0A09;color:#F0ECE6;font-family:Segoe UI,sans-serif;padding:32px}}
        h1,h3{{color:#E87A24}}table{{width:100%;border-collapse:collapse;margin-bottom:28px;background:#1B1815;border-radius:8px;overflow:hidden}}
        th,td{{border:1px solid #33291F;padding:10px 14px;text-align:left}}th{{background:#141210;color:#8A8279}}</style></head>
        <body><h1>✓ LoggerPro • Relatório de Backup e Conferência</h1><p><b>Projeto:</b> {proj} | <b>Caminho:</b> {proj_root1}</p>{html_cards}</body></html>"""

        for root_folder in [proj_root1, proj_root2]:
            if root_folder and root_folder.exists():
                (root_folder / "RELATORIO_BACKUP.txt").write_text("\n".join(txt_lines), encoding="utf-8")
                hp = root_folder / "RELATORIO_BACKUP.html"
                hp.write_text(html, encoding="utf-8")
                bruto_dir = root_folder / "BRUTO"
                if bruto_dir.exists():
                    (bruto_dir / "RELATORIO_BACKUP.txt").write_text("\n".join(txt_lines), encoding="utf-8")
                    (bruto_dir / "RELATORIO_BACKUP.html").write_text(html, encoding="utf-8")
                if root_folder == proj_root1:
                    self.last_report_path = hp

    def open_reports(self):
        if self.last_report_path and self.last_report_path.exists():
            webbrowser.open(self.last_report_path.as_uri())
        else:
            messagebox.showinfo("LoggerPro • Relatórios", "O relatório é gerado na pasta do projeto após a conferência do primeiro cartão.")

    def open_project_folder(self):
        if not self.dest1_path.get():
            return
        p = Path(self.dest1_path.get()) / self.project_name.get().strip()
        target = p if p.exists() else Path(self.dest1_path.get())
        if os.name == "nt":
            os.startfile(target)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(target)])

    # ---------------- EJEÇÃO NATIVA WIN32 SEM REMONTAR ---------------- #
    def manual_eject_card(self):
        path_str = self.source_path.get()
        if not path_str:
            messagebox.showinfo("LoggerPro • Ejetar", "Nenhum cartão selecionado para ejetar.")
            return
        self.source_path.set("")
        self.found_files = []
        self.lbl_card_name.configure(text="CARTÃO EJETADO")
        self.lbl_cam_meta.configure(text="Pode remover o cartão do leitor", text_color=C_SUCCESS)
        self.lbl_phase_badge.configure(text="EJETADO", text_color=C_SUCCESS)
        self._eject(path_str)

    def _eject(self, path_str):
        if not path_str:
            return
        # Pausa imediatamente o _poll_usb para não sondar o drive e forçar o Windows a remontá-lo
        self.polling_paused = True
        try:
            os.chdir(os.path.expanduser("~"))
        except Exception:
            pass

        if os.name == "nt":
            drv = os.path.splitdrive(path_str)[0]
            if drv:
                threading.Thread(target=self._win32_safe_eject, args=(drv,), daemon=True).start()
        elif sys.platform == "darwin":
            parts = Path(path_str).parts
            if len(parts) >= 3 and parts[1] == "Volumes":
                vol_name = parts[2]
                subprocess.Popen(["diskutil", "eject", f"/Volumes/{vol_name}"])
                self.after(0, lambda: self.log(f"⏏ Cartão ({vol_name}) ejetado com segurança. Pode retirar do leitor."))

    def _win32_safe_eject(self, drv: str):
        """Executa Flush -> Lock -> Dismount -> Eject Media direto na API kernel32 do Windows."""
        gc.collect()

        GENERIC_READ = 0x80000000
        GENERIC_WRITE = 0x40000000
        FILE_SHARE_READ = 0x00000001
        FILE_SHARE_WRITE = 0x00000002
        OPEN_EXISTING = 3

        FSCTL_LOCK_VOLUME = 0x00090018
        FSCTL_DISMOUNT_VOLUME = 0x00090020
        IOCTL_STORAGE_MEDIA_REMOVAL = 0x002D4804
        IOCTL_STORAGE_EJECT_MEDIA = 0x002D4808

        vol_path = f"\\\\.\\{drv}"
        k32 = ctypes.windll.kernel32

        handle = k32.CreateFileW(
            vol_path,
            GENERIC_READ | GENERIC_WRITE,
            FILE_SHARE_READ | FILE_SHARE_WRITE,
            None,
            OPEN_EXISTING,
            0,
            None
        )
        if handle in (-1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
            handle = k32.CreateFileW(
                vol_path,
                GENERIC_READ,
                FILE_SHARE_READ | FILE_SHARE_WRITE,
                None,
                OPEN_EXISTING,
                0,
                None
            )

        if handle not in (-1, 0xFFFFFFFF, 0xFFFFFFFFFFFFFFFF):
            try:
                bytes_ret = ctypes.c_ulong(0)
                k32.FlushFileBuffers(handle)

                for _ in range(6):
                    if k32.DeviceIoControl(handle, FSCTL_LOCK_VOLUME, None, 0, None, 0, ctypes.byref(bytes_ret), None):
                        break
                    time.sleep(0.15)

                k32.DeviceIoControl(handle, FSCTL_DISMOUNT_VOLUME, None, 0, None, 0, ctypes.byref(bytes_ret), None)

                pmr = ctypes.c_byte(0)
                k32.DeviceIoControl(handle, IOCTL_STORAGE_MEDIA_REMOVAL, ctypes.byref(pmr), 1, None, 0, ctypes.byref(bytes_ret), None)
                k32.DeviceIoControl(handle, IOCTL_STORAGE_EJECT_MEDIA, None, 0, None, 0, ctypes.byref(bytes_ret), None)
            finally:
                k32.CloseHandle(handle)

        self.after(0, lambda: self.log(f"⏏ Cartão ({drv}) desmontado e ejetado com segurança. Pode retirar do leitor."))


if __name__ == "__main__":
    app = LoggerProApp()
    app.mainloop()
