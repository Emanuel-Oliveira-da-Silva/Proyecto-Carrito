import tkinter as tk
from tkinter import ttk, messagebox
import re
import uuid
import sqlite3
import hashlib
import sys
sys.path.append("/home/pi/pc_stock_project/hardware")
import Carrito


from datetime import datetime

DB_PATH = "control.db"

# Toggle to enable a cleaner visual style quickly (reversible)
CLEAN_UI = True

# ---------- UI constants ----------
BG_GRAD_TOP = "#c7d2fe"
BG_GRAD_BOT = "#93c5fd"
BG_OUT      = "#eaf1fb"
CARD_BG     = "#ffffff"
CARD_INNER  = "#f7f9fc"
INK         = "#0f172a"
INK_SOFT    = "#6b7280"
PRIMARY     = "#2563eb"
PRIMARY_DK  = "#1f4fd4"
SUCCESS_BG  = "#dcfce7"
SUCCESS_TX  = "#166534"
WARN_BG     = "#fee2e2"
WARN_TX     = "#991b1b"
INFO_BG     = "#e0f2fe"
INFO_TX     = "#075985"
DIVIDER     = "#e5e7eb"

if CLEAN_UI:
    # Neutral, flat palette (no gradient feel, softer primary)
    BG_GRAD_TOP = "#f8fafc"   # almost white
    BG_GRAD_BOT = "#f8fafc"
    BG_OUT      = "#f3f4f6"   # light gray background
    CARD_BG     = "#ffffff"
    CARD_INNER  = "#fafafa"
    INK         = "#111827"
    INK_SOFT    = "#6b7280"
    PRIMARY     = "#3b82f6"   # softer blue
    PRIMARY_DK  = "#2563eb"
    SUCCESS_BG  = "#ecfdf5"
    SUCCESS_TX  = "#065f46"
    WARN_BG     = "#fef2f2"
    WARN_TX     = "#991b1b"
    INFO_BG     = "#eff6ff"
    INFO_TX     = "#1d4ed8"
    DIVIDER     = "#e5e7eb"

FONT        = ("Segoe UI", 10)
FONT_BOLD   = ("Segoe UI Semibold", 10)
FONT_TITLE  = ("Segoe UI", 16, "bold")
FONT_SUB    = ("Segoe UI", 9)

# ---------- util: vertical gradient ----------
def vertical_gradient(canvas, w, h, top=BG_GRAD_TOP, bottom=BG_GRAD_BOT):
    canvas.delete("grad")
    steps = max(120, h // 3)
    r1, g1, b1 = canvas.winfo_rgb(top)
    r2, g2, b2 = canvas.winfo_rgb(bottom)
    for i in range(steps):
        t = i/(steps-1)
        r = int(r1 + (r2-r1)*t); g = int(g1 + (g2-g1)*t); b = int(b1 + (b2-b1)*t)
        color = f"#{r//256:02x}{g//256:02x}{b//256:02x}"
        y0 = int(h*i/steps); y1 = int(h*(i+1)/steps)
        canvas.create_rectangle(0, y0, w, y1, outline="", fill=color, tags="grad")

# ---------- PrimaryButton ----------
class PrimaryButton(tk.Button):
    def __init__(self, master, **kwargs):
        base = dict(
            font=FONT_BOLD, fg="#ffffff", bg=PRIMARY,
            activeforeground="#ffffff", activebackground=PRIMARY_DK,
            bd=0, relief="flat", cursor="hand2", padx=14, pady=10
        )
        base.update(kwargs)
        super().__init__(master, **base)
        self._bg = base["bg"]
        self._hover = PRIMARY_DK
        self.bind("<Enter>", lambda e: self.config(bg=self._hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))

# ---------- IconButton (bigger, with text) ----------
class IconButton(tk.Button):
    COLORS = {
        "edit":  ("#2563eb", "#1f4fd4"),
        "del":   ("#dc2626", "#b91c1c"),
        "ghost": ("#f3f4f6", "#e5e7eb"),
    }
    def __init__(self, master, text_label, kind="edit", command=None, tooltip=None):
        fg, fg_hover = "#ffffff", "#ffffff"
        bg, bg_hover = self.COLORS.get(kind, self.COLORS["ghost"])
        super().__init__(
            master,
            text=text_label,
            font=("Segoe UI", 11, "bold"),
            fg=fg, bg=bg, activeforeground=fg_hover, activebackground=bg_hover,
            bd=0, relief="flat", cursor="hand2", padx=10, pady=6, command=command
        )
        self._bg, self._hover = bg, bg_hover
        self.bind("<Enter>", lambda e: self.config(bg=self._hover))
        self.bind("<Leave>", lambda e: self.config(bg=self._bg))
        if tooltip:
            self._add_tooltip(tooltip)

    def _add_tooltip(self, text):
        tip = tk.Toplevel(self, bg="#000000"); tip.overrideredirect(True); tip.withdraw()
        lbl = tk.Label(tip, text=text, fg="#ffffff", bg="#111827", font=("Segoe UI", 9), padx=8, pady=4); lbl.pack()
        def enter(_):
            tip.deiconify()
            x = self.winfo_rootx() + self.winfo_width() + 6
            y = self.winfo_rooty() - 2
            tip.geometry(f"+{x}+{y}")
        def leave(_): tip.withdraw()
        self.bind("<Enter>", enter, add="+"); self.bind("<Leave>", leave, add="+")

# ---------- LabeledEntry ----------
class LabeledEntry(ttk.Frame):
    def __init__(self, master, label, icon="", password=False, width=24):
        super().__init__(master, style="Card.TFrame")
        self.icon = tk.Label(self, text=icon, font=("Segoe UI Emoji", 12), fg=INK, bg=CARD_BG, width=2, anchor="e")
        self.icon.grid(row=0, column=0, sticky="w", padx=(0,6))
        self.entry = ttk.Entry(self, style="G.TEntry", show="*" if password else "", width=width)
        self.entry.grid(row=0, column=1, sticky="ew")
        self.grid_columnconfigure(1, weight=1)
        self.placeholder = label
        self.entry.insert(0, self.placeholder)
        self.entry.configure(foreground=INK_SOFT)
        self.entry.bind("<FocusIn>", self._on_in)
        self.entry.bind("<FocusOut>", self._on_out)
    def _on_in(self, *_):
        if self.entry.get() == self.placeholder:
            self.entry.delete(0, "end"); self.entry.configure(foreground=INK)
    def _on_out(self, *_):
        if not self.entry.get():
            self.entry.insert(0, self.placeholder); self.entry.configure(foreground=INK_SOFT)
    def value(self):
        v = self.entry.get().strip()
        return "" if v == self.placeholder else v

# ---------- badge ----------
def badge(parent, text, kind="ok"):
    if kind == "ok": bg, fg = SUCCESS_BG, SUCCESS_TX
    elif kind == "warn": bg, fg = WARN_BG, WARN_TX
    else: bg, fg = INFO_BG, INFO_TX
    return tk.Label(parent, text=text, font=FONT_BOLD, bg=bg, fg=fg, padx=8, pady=3)

# ---------- DB helpers (safe connections + WAL) ----------
def sha256_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()

def get_conn():
    conn = sqlite3.connect(DB_PATH, timeout=30, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.execute("PRAGMA foreign_keys = ON;")
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
    except Exception:
        pass
    return conn

def init_db():
    # barcode fijo que pediste para admin
    admin_barcode = "BS'1DUSB"
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.executescript("""
        CREATE TABLE IF NOT EXISTS users (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          email TEXT UNIQUE NOT NULL,
          name TEXT NOT NULL,
          password_hash TEXT NOT NULL,
          barcode TEXT UNIQUE,
          is_admin INTEGER DEFAULT 0
        );
        CREATE TABLE IF NOT EXISTS pcs (
          id INTEGER PRIMARY KEY,
          available INTEGER DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS loans (
          id INTEGER PRIMARY KEY AUTOINCREMENT,
          user_id INTEGER NOT NULL,
          pc_id INTEGER NOT NULL,
          loaned_at TEXT NOT NULL,
          returned_at TEXT,
          active INTEGER DEFAULT 1,
          FOREIGN KEY(user_id) REFERENCES users(id),
          FOREIGN KEY(pc_id) REFERENCES pcs(id)
        );
        """)
        # populate pcs if empty
        cur.execute("SELECT COUNT(*) FROM pcs;")
        if cur.fetchone()[0] == 0:
            cur.executemany("INSERT INTO pcs (id, available) VALUES (?, 1);", [(i,) for i in range(1, 16)])

        # ensure admin user exists and has the specified barcode
        cur.execute("SELECT id, barcode FROM users WHERE email = ?", ("admin@gmail.com",))
        r = cur.fetchone()
        if not r:
            cur.execute(
                "INSERT INTO users (email, name, password_hash, barcode, is_admin) VALUES (?, ?, ?, ?, 1)",
                ("admin@gmail.com", "Administrador", sha256_hash("abcd"), admin_barcode)
            )
        else:
            # force the admin barcode to the requested value
            cur.execute("UPDATE users SET barcode = ? WHERE email = ?", (admin_barcode, "admin@gmail.com"))

        # ensure demo user exists (non-admin)
        cur.execute("SELECT id FROM users WHERE email = ?", ("usuario.demo@gmail.com",))
        r_demo = cur.fetchone()
        if not r_demo:
            cur.execute(
                "INSERT INTO users (email, name, password_hash, barcode, is_admin) VALUES (?, ?, ?, ?, 0)",
                ("usuario.demo@gmail.com", "Usuario Demo", sha256_hash("1234"), None)
            )

        cur.execute("SELECT id FROM users WHERE email = ?", ("pedro@gmail.com",))
        r_pedro = cur.fetchone()
        if not r_pedro:
            cur.execute(
                "INSERT INTO users (email, name, password_hash, barcode, is_admin) VALUES (?, ?, ?, ?, 0)",
                ("pedro@gmail.com", "Pedro", sha256_hash("asdasd"), None)
            )

        # remove the user 'hola@gmail.com' if it exists (delete loans first)
        cur.execute("SELECT id FROM users WHERE email = ?", ("hola@gmail.com",))
        r_hola = cur.fetchone()
        if r_hola:
            hola_id = r_hola[0]
            # delete loans for that user (to avoid FK or 'locked' issues)
            cur.execute("DELETE FROM loans WHERE user_id = ?", (hola_id,))
            # delete the user itself
            cur.execute("DELETE FROM users WHERE id = ?", (hola_id,))

        conn.commit()
    finally:
        conn.close()

# DB actions
def find_user_by_barcode(code: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, email, name, is_admin, barcode FROM users WHERE barcode = ?", (code,))
        r = cur.fetchone()
        if not r: return None
        return {"id": r[0], "email": r[1], "name": r[2], "is_admin": bool(r[3]), "barcode": r[4]}
    finally:
        conn.close()

def list_users():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, email, name, barcode, is_admin FROM users ORDER BY name COLLATE NOCASE")
        rows = cur.fetchall()
        result = [{"id": r[0], "email": r[1], "name": r[2], "barcode": r[3], "is_admin": bool(r[4])} for r in rows]
        return result
    finally:
        conn.close()

def create_user_db(email, name, password, barcode=None, is_admin=0):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("INSERT INTO users (email, name, password_hash, barcode, is_admin) VALUES (?, ?, ?, ?, ?)",
                    (email, name, sha256_hash(password), barcode, is_admin))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def update_user_db(user_id, email, name, password, barcode, is_admin):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE users SET email=?, name=?, password_hash=?, barcode=?, is_admin=? WHERE id=?",
                    (email, name, sha256_hash(password), barcode, int(is_admin), user_id))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def delete_user_db(user_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM loans WHERE user_id = ? AND active = 1", (user_id,))
        if cur.fetchone()[0] > 0:
            raise Exception("El usuario tiene préstamos activos")
        cur.execute("DELETE FROM users WHERE id = ?", (user_id,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def get_available_pcs():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id FROM pcs WHERE available = 1 ORDER BY id")
        rows = [r[0] for r in cur.fetchall()]
        return rows
    finally:
        conn.close()

def get_user_loans(user_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT pc_id FROM loans WHERE user_id = ? AND active = 1 ORDER BY pc_id", (user_id,))
        rows = [r[0] for r in cur.fetchall()]
        return rows
    finally:
        conn.close()

def loan_pcs_to_user(user_id, pc_list):
    conn = get_conn()
    try:
        cur = conn.cursor()
        for pc in pc_list:
            cur.execute("SELECT available FROM pcs WHERE id = ?", (pc,))
            r = cur.fetchone()
            if not r or r[0] == 0:
                raise Exception(f"PC {pc} no disponible")
            cur.execute("UPDATE pcs SET available = 0 WHERE id = ?", (pc,))
            cur.execute("INSERT INTO loans (user_id, pc_id, loaned_at, active) VALUES (?, ?, ?, 1)",
                        (user_id, pc, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

def return_pcs_for_user(user_id, pc_list):
    conn = get_conn()
    try:
        cur = conn.cursor()
        for pc in pc_list:
            cur.execute("SELECT id FROM loans WHERE pc_id = ? AND user_id = ? AND active = 1", (pc, user_id))
            if not cur.fetchone():
                raise Exception(f"PC {pc} no fue prestada por este usuario")
            cur.execute("UPDATE loans SET active = 0, returned_at = ? WHERE pc_id = ? AND user_id = ? AND active = 1",
                        (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), pc, user_id))
            cur.execute("UPDATE pcs SET available = 1 WHERE id = ?", (pc,))
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()

# Lista de préstamos activos con fecha/hora
def list_active_loans_with_times(user_id):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT pc_id, loaned_at FROM loans WHERE user_id = ? AND active = 1 ORDER BY pc_id",
            (user_id,)
        )
        rows = cur.fetchall()
        return [{"pc_id": r[0], "loaned_at": r[1]} for r in rows]
    finally:
        conn.close()

# ---- extra DB helpers for PCs management ----
def list_all_pcs():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, available FROM pcs ORDER BY id")
        rows = cur.fetchall()
        return [{"id": r[0], "available": bool(r[1])} for r in rows]
    finally:
        conn.close()

def add_pc_db():
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COALESCE(MAX(id), 0) FROM pcs")
        next_id = (cur.fetchone()[0] or 0) + 1
        cur.execute("INSERT INTO pcs (id, available) VALUES (?, 1)", (next_id,))
        conn.commit()
        return next_id
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()

def remove_pc_db(pc_id: int):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT COUNT(*) FROM loans WHERE pc_id = ? AND active = 1", (pc_id,))
        if cur.fetchone()[0] > 0:
            raise Exception(f"PC {pc_id} tiene un préstamo activo")
        cur.execute("DELETE FROM pcs WHERE id = ?", (pc_id,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()

def set_pc_available_db(pc_id: int, available: bool):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("UPDATE pcs SET available = ? WHERE id = ?", (1 if available else 0, pc_id))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()

def free_pc_db(pc_id: int):
    """Finaliza el préstamo activo de esa PC (si existe) y la marca disponible."""
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute("SELECT id, user_id FROM loans WHERE pc_id = ? AND active = 1", (pc_id,))
        loan = cur.fetchone()
        if loan:
            cur.execute(
                "UPDATE loans SET active = 0, returned_at = ? WHERE id = ?",
                (datetime.now().strftime("%Y-%m-%d %H:%M:%S"), loan[0])
            )
        cur.execute("UPDATE pcs SET available = 1 WHERE id = ?", (pc_id,))
        conn.commit()
    except Exception:
        conn.rollback(); raise
    finally:
        conn.close()

def authenticate_admin(email: str, password: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, name, is_admin, barcode FROM users WHERE email = ? AND password_hash = ? AND is_admin = 1",
            (email, sha256_hash(password))
        )
        r = cur.fetchone()
        if not r: return None
        return {"id": r[0], "email": r[1], "name": r[2], "is_admin": bool(r[3]), "barcode": r[4]}
    finally:
        conn.close()

def authenticate_user(email: str, password: str):
    conn = get_conn()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT id, email, name, is_admin, barcode FROM users WHERE email = ? AND password_hash = ?",
            (email, sha256_hash(password))
        )
        r = cur.fetchone()
        if not r: return None
        return {"id": r[0], "email": r[1], "name": r[2], "is_admin": bool(r[3]), "barcode": r[4]}
    finally:
        conn.close()

# ---------- App ----------
class App(tk.Tk):
    def __init__(self):
        super().__init__()
        # Configuración de pantalla completa
        self.title("Stock de Computadoras — Demo (SQLite)")
        self.state('zoomed')  # Pantalla completa en Windows
        self.configure(bg=BG_OUT)
        
        # Ocultar barra de menú y hacer ventana no redimensionable
        self.attributes('-fullscreen', True)
        self.resizable(False, False)

        init_db()

        st = ttk.Style(self)
        try: st.theme_use("clam")
        except tk.TclError: pass
        st.configure("G.TEntry", padding=8, relief="flat", borderwidth=0, foreground=INK)
        st.map("G.TEntry", fieldbackground=[("!disabled", CARD_INNER)], background=[("!disabled", CARD_INNER)])
        st.configure("Card.TFrame", background=CARD_BG)
        st.configure("TLabel", background=CARD_BG, foreground=INK, font=FONT)
        st.configure("Soft.TLabel", background=CARD_BG, foreground=INK_SOFT, font=FONT_SUB)
        st.configure("Title.TLabel", background=CARD_BG, foreground=INK, font=FONT_TITLE)

        self.bg = tk.Canvas(self, highlightthickness=0, bd=0, bg=BG_OUT)
        self.bg.pack(fill="both", expand=True)
        self.bg.bind("<Configure>", self._on_resize)

        # center frame that will host content; allow it to expand
        self.center = tk.Frame(self.bg, bg=BG_OUT)
        self.center_id = self.bg.create_window(0, 0, window=self.center, anchor="center")
        # let center expand
        self.center.grid_columnconfigure(0, weight=1)
        self.center.grid_rowconfigure(0, weight=1)

        self.scan_entry = None
        self.current_user = None
        
        # Frame principal para todas las pantallas
        self.main_frame = tk.Frame(self.bg, bg=BG_OUT)
        self.main_frame.pack(fill="both", expand=True)
        
        # Botón de salida de pantalla completa
        self.exit_fullscreen_btn = tk.Button(
            self.bg, text="⛌", font=("Segoe UI", 16), 
            bg=BG_OUT, fg=INK, bd=0, cursor="hand2",
            command=self._toggle_fullscreen
        )
        self.exit_fullscreen_btn.place(x=10, y=10)

        self._build_login()

        # Pila de modales para soportar anidación (captura de código, etc.)
        self._modal_stack = []
        
        # === Inicializar hardware (Arduino) ===
        try:
            Carrito.start_hardware()
            print("[Hardware] Conexión con Arduino iniciada correctamente.")
            if not Carrito.is_hardware_connected():
                # Si el hardware no se conectó, mostrar un indicador visual
                sim_label = tk.Label(
                    self.bg, text="SIMULACIÓN", font=("Segoe UI", 10, "bold"),
                    bg=WARN_BG, fg=WARN_TX, padx=10, pady=4
                )
                sim_label.place(relx=1.0, x=-10, y=10, anchor="ne")
        except Exception as e:
            print("[Error] No se pudo iniciar hardware:", e)

    def _gen_barcode(self) -> str:
        token = uuid.uuid4().hex[:8].upper()
        return f"{token[:4]}-{token[4:]}"
    def _gen_unique_barcode(self) -> str:
        existing = {u["barcode"] for u in list_users() if u["barcode"]}
        code = self._gen_barcode()
        while code in existing:
            code = self._gen_barcode()
        return code
    
    def _toggle_fullscreen(self):
        """Alternar entre pantalla completa y ventana normal"""
        if self.attributes('-fullscreen'):
            self.attributes('-fullscreen', False)
            self.state('normal')
            self.geometry("1300x760")
        else:
            self.attributes('-fullscreen', True)
            self.state('zoomed')
    
    def _show_modal(self, content_frame, title="Modal"):
        """Mostrar un modal sobre el contenido principal"""
        # Crear overlay
        # Fondo del contenedor igual al fondo general (sin oscurecer)
        overlay = tk.Frame(self.main_frame, bg=BG_OUT)
        overlay.place(x=0, y=0, relwidth=1, relheight=1)
        
        # Crear modal
        modal_frame = tk.Frame(overlay, bg=CARD_BG, relief="raised", bd=2)
        modal_frame.place(relx=0.5, rely=0.5, anchor="center")
        
        # Título del modal
        title_frame = tk.Frame(modal_frame, bg=CARD_BG)
        title_frame.pack(fill="x", padx=20, pady=(20, 10))
        tk.Label(title_frame, text=title, font=FONT_TITLE, bg=CARD_BG, fg=INK).pack(side="left")
        
        # Contenido del modal
        content_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # Push a la pila y bind Escape para cerrar el tope
        self._modal_stack.append(overlay)
        overlay.bind_all("<Escape>", lambda _e: self._close_modal(), add="+")
    
    def _close_modal(self):
        """Cerrar el modal actual"""
        if hasattr(self, '_modal_stack') and self._modal_stack:
            top = self._modal_stack.pop()
            try:
                top.destroy()
            except Exception:
                pass

    # ---------- login ----------
    def _build_login(self):
        # Limpiar frame principal
        for w in self.main_frame.winfo_children(): w.destroy()
        
        # Crear contenedor centrado
        container = tk.Frame(self.main_frame, bg=BG_OUT)
        container.pack(expand=True, fill="both")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        card = tk.Frame(container, bg=CARD_BG, bd=0, highlightthickness=0)
        card.grid(row=0, column=0, sticky="nsew", padx=50, pady=50)
        card.grid_columnconfigure(0, weight=1)

        header = tk.Frame(card, bg=CARD_BG); header.pack(fill="x", pady=(10,6), padx=16)
        tk.Label(header, text="🔐", font=("Segoe UI Emoji", 22), bg=CARD_BG, fg=INK).pack(side="left")
        ttk.Label(header, text="Acceso al sistema", style="Title.TLabel").pack(side="left", padx=(8,0))
        ttk.Label(card, text="Escaneá tu código de barras para entrar (usuarios y administradores).", style="Soft.TLabel").pack(fill="x", padx=16)
        tk.Frame(card, bg=DIVIDER, height=1).pack(fill="x", padx=16, pady=8)

        # scan block
        scan = ttk.Frame(card, style="Card.TFrame"); scan.pack(fill="x", padx=16, pady=(6,10))
        tk.Label(scan, text="🏷️", font=("Segoe UI Emoji", 14), bg=CARD_BG, fg=INK, width=2, anchor="e").grid(row=0, column=0, padx=(0,6))
        self.scan_entry = ttk.Entry(scan, style="G.TEntry", width=40)
        self.scan_entry.grid(row=0, column=1, sticky="ew")
        scan.grid_columnconfigure(1, weight=1)
        ttk.Label(card, text="Escaneá tu código y presioná Enter (la mayoría de lectores lo envían solo).", style="Soft.TLabel").pack(fill="x", padx=16, pady=(0,6))
        self.scan_entry.bind("<Return>", self._do_scan_login)
        self.after(250, lambda: self.scan_entry.focus_set())
        tk.Frame(card, bg=DIVIDER, height=1).pack(fill="x", padx=16, pady=8)

        # Acceso alternativo para administrador con email/contraseña
        alt = tk.Frame(card, bg=CARD_BG); alt.pack(fill="x", padx=16, pady=(4,10))
        ttk.Label(alt, text="¿Sos administrador?", style="Soft.TLabel").pack(side="left")
        ttk.Button(alt, text="Entrar con contraseña", command=self._admin_password_login_page).pack(side="left", padx=10)

        alt2 = tk.Frame(card, bg=CARD_BG); alt2.pack(fill="x", padx=16, pady=(0,6))
        ttk.Label(alt2, text="¿Sos usuario?", style="Soft.TLabel").pack(side="left")
        ttk.Button(alt2, text="Entrar como usuario", command=self._user_password_login_page).pack(side="left", padx=10)

    def _do_scan_login(self, event=None):
        code = (self.scan_entry.get() or "").strip()
        if not code:
            messagebox.showwarning("Escaneo", "Escaneá un código válido."); return
        user = find_user_by_barcode(code)
        self.scan_entry.delete(0, "end"); self.scan_entry.focus_set()
        if not user:
            messagebox.showerror("No encontrado", f"Código '{code}' no está asignado a ningún usuario."); return
        # allow admin login via barcode too
        self.current_user = user
        if user["is_admin"]:
            self._build_admin()
        else:
            self._build_menu_user()
        
        try:
            Carrito.Open_cart()
            print("[Hardware] Carrito abierto por login de usuario.")
        except Exception as e:
            print("[Error] No se pudo abrir carrito:", e)

        if user["is_admin"]:
            self._build_admin()
        else:
            self._build_menu_user()

    # ---------- user menu ----------
    def _build_menu_user(self):
        # Limpiar frame principal
        for w in self.main_frame.winfo_children(): w.destroy()
        
        # Crear contenedor centrado
        container = tk.Frame(self.main_frame, bg=BG_OUT)
        container.pack(expand=True, fill="both")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        card = tk.Frame(container, bg=CARD_BG)
        card.grid(row=0, column=0, sticky="nsew", padx=30, pady=30)
        card.grid_columnconfigure(0, weight=1)
        header = tk.Frame(card, bg=CARD_BG); header.pack(fill="x", pady=(10,2), padx=16)
        tk.Label(header, text="🖥️", font=("Segoe UI Emoji", 20), bg=CARD_BG, fg=INK).pack(side="left")
        name = self.current_user["name"]
        ttk.Label(header, text=f"Menú — {name}", style="Title.TLabel").pack(side="left", padx=(8,0))
        ttk.Label(card, text=f"Usuario: {self.current_user['email']}", style="Soft.TLabel").pack(fill="x", padx=16)
        badges = tk.Frame(card, bg=CARD_BG); badges.pack(fill="x", padx=16, pady=(8,8))
        self.badge_avail = badge(badges, "", "ok"); self.badge_avail.pack(side="left")
        self.badge_mine  = badge(badges, "", "info"); self.badge_mine.pack(side="left", padx=(8,0))
        self._update_badges_user()
        tk.Frame(card, bg=DIVIDER, height=1).pack(fill="x", padx=16, pady=8)
        actions = tk.Frame(card, bg=CARD_BG); actions.pack(fill="x", padx=16)
        # Abrir modal unificado para retirar/devolver
        PrimaryButton(actions, text="RETIRAR O DEVOLVER", command=self._retirar_devolver_modal).pack(fill="x", pady=6)
        detail = tk.Frame(card, bg=CARD_BG); detail.pack(fill="x", padx=16, pady=(8,6))
        tk.Label(detail, text="Disponibilidad actual", font=FONT_BOLD, bg=CARD_BG, fg=INK).pack(anchor="w")
        self.lbl_avail = ttk.Label(detail, text=self._disp_text(), style="TLabel", anchor="w", justify="left"); self.lbl_avail.pack(fill="x")
        tk.Label(detail, text="Tus retiradas", font=FONT_BOLD, bg=CARD_BG, fg=INK).pack(anchor="w", pady=(8,0))
        self.lbl_mine = ttk.Label(detail, text=self._mine_text(), style="TLabel", anchor="w", justify="left"); self.lbl_mine.pack(fill="x")
        tk.Frame(card, bg=DIVIDER, height=1).pack(fill="x", padx=16, pady=8)
        footer = tk.Frame(card, bg=CARD_BG); footer.pack(fill="x", padx=16, pady=(0,8))
        tk.Button(footer, text="Cerrar sesión", font=FONT, fg=INK, bg=CARD_BG, activebackground=CARD_BG, bd=0, cursor="hand2", command=self._logout).pack(side="right")

    def _logout(self):
        try:
            Carrito.Close_cart()
            print("[Hardware] Carrito cerrado al cerrar sesión.")
        except Exception as e:
            print("[Error] No se pudo cerrar carrito:", e)

        self.current_user = None
        self._build_login()


    def _disp_text(self):
        disp = get_available_pcs()
        nums = "— (no hay disponibles)" if not disp else ", ".join(map(str, disp))
        return f"Disponibles: {len(disp)}\nNúmeros: {nums}"

    def _mine_text(self):
        mine = get_user_loans(self.current_user["id"])
        nums = "— (no retiraste nada)" if not mine else ", ".join(map(str, mine))
        return f"Retiradas por vos: {len(mine)}\nNúmeros: {nums}"

    def _update_badges_user(self):
        count_av = len(get_available_pcs())
        mine = get_user_loans(self.current_user["id"])
        self.badge_avail.config(text=f"{count_av} disponibles", bg=SUCCESS_BG if count_av else WARN_BG, fg=SUCCESS_TX if count_av else WARN_TX)
        self.badge_mine.config(text=f"{len(mine)} tuyas", bg=INFO_BG, fg=INFO_TX)

    def _refresh_menu_user(self):
        if hasattr(self, "lbl_avail"): self.lbl_avail.config(text=self._disp_text())
        if hasattr(self, "lbl_mine"):  self.lbl_mine.config(text=self._mine_text())
        self._update_badges_user()

    # ---------- unified retirar/devolver modal ----------
    def _retirar_devolver_modal(self):
        # Render como página (no modal)
        for w in self.main_frame.winfo_children(): w.destroy()

        page = tk.Frame(self.main_frame, bg=CARD_BG)
        page.pack(fill="both", expand=True, padx=20, pady=16)

        header = tk.Frame(page, bg=CARD_BG); header.pack(fill="x", padx=4, pady=(8,10))
        ttk.Label(header, text="Gestionar computadoras", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Volver", command=self._build_menu_user).pack(side="right")

        # --- Panel de Estado de Sensores (Simulación) ---
        status_frame = tk.Frame(page, bg=CARD_INNER, highlightthickness=1, highlightbackground=DIVIDER)
        status_frame.pack(fill="x", padx=4, pady=10)
        tk.Label(status_frame, text="Estado de Sensores (Simulado)", font=FONT_BOLD, bg=CARD_INNER, fg=INK).pack(pady=(4,2))
        
        pc1_frame = tk.Frame(status_frame, bg=CARD_INNER)
        pc1_frame.pack(fill="x", padx=10)
        tk.Label(pc1_frame, text="Computadora 1:", font=FONT, bg=CARD_INNER, fg=INK_SOFT).pack(side="left")
        pc1_status_label = tk.Label(pc1_frame, text="...", font=FONT_BOLD, bg=CARD_INNER, padx=8)
        pc1_status_label.pack(side="left")

        pc2_frame = tk.Frame(status_frame, bg=CARD_INNER)
        pc2_frame.pack(fill="x", padx=10, pady=(0, 4))
        tk.Label(pc2_frame, text="Computadora 2:", font=FONT, bg=CARD_INNER, fg=INK_SOFT).pack(side="left")
        pc2_status_label = tk.Label(pc2_frame, text="...", font=FONT_BOLD, bg=CARD_INNER, padx=8)
        pc2_status_label.pack(side="left")

        def update_status_labels():
            pc1_presente = Carrito.Computer_state(0)
            pc1_status_label.config(text="Presente" if pc1_presente else "Ausente", bg=SUCCESS_BG if pc1_presente else WARN_BG, fg=SUCCESS_TX if pc1_presente else WARN_TX)
            pc2_presente = Carrito.Computer_state(1)
            pc2_status_label.config(text="Presente" if pc2_presente else "Ausente", bg=SUCCESS_BG if pc2_presente else WARN_BG, fg=SUCCESS_TX if pc2_presente else WARN_TX)
            page.after(1000, update_status_labels) # Actualizar cada segundo

        update_status_labels() # Iniciar la actualización

        # Secciones
        body = tk.Frame(page, bg=CARD_BG); body.pack(fill="both", expand=True, padx=4, pady=10)
        # Subtítulos
        ttk.Label(body, text="Disponibles para retirar", style="TLabel").grid(row=0, column=0, sticky="w", pady=(0,6))
        ttk.Label(body, text="Tus retiradas", style="TLabel").grid(row=0, column=1, sticky="w", pady=(0,6))

        # Listas
        left_wrap = tk.Frame(body, bg=CARD_BG); left_wrap.grid(row=1, column=0, sticky="nsew", padx=(0,10))
        right_wrap = tk.Frame(body, bg=CARD_BG); right_wrap.grid(row=1, column=1, sticky="nsew", padx=(10,0))
        body.grid_rowconfigure(1, weight=1); body.grid_columnconfigure(0, weight=1); body.grid_columnconfigure(1, weight=1)

        sbL = ttk.Scrollbar(left_wrap, orient="vertical")
        lbL = tk.Listbox(left_wrap, selectmode="extended", activestyle="none", bd=0, relief="flat",
                         highlightthickness=1, highlightbackground=DIVIDER, highlightcolor=PRIMARY,
                         font=FONT, fg=INK, bg=CARD_INNER, height=14)
        lbL.grid(row=0, column=0, sticky="nsew"); sbL.grid(row=0, column=1, sticky="ns")
        left_wrap.grid_rowconfigure(0, weight=1); left_wrap.grid_columnconfigure(0, weight=1)
        lbL.config(yscrollcommand=sbL.set); sbL.config(command=lbL.yview)

        sbR = ttk.Scrollbar(right_wrap, orient="vertical")
        lbR = tk.Listbox(right_wrap, selectmode="extended", activestyle="none", bd=0, relief="flat",
                         highlightthickness=1, highlightbackground=DIVIDER, highlightcolor=PRIMARY,
                         font=FONT, fg=INK, bg=CARD_INNER, height=14)
        lbR.grid(row=0, column=0, sticky="nsew"); sbR.grid(row=0, column=1, sticky="ns")
        right_wrap.grid_rowconfigure(0, weight=1); right_wrap.grid_columnconfigure(0, weight=1)
        lbR.config(yscrollcommand=sbR.set); sbR.config(command=lbR.yview)

        def refresh_lists():
            lbL.delete(0, "end"); lbR.delete(0, "end")
            
            # Obtener PCs disponibles de la DB
            pcs_disponibles_db = get_available_pcs()
            
            # Filtrar la lista de disponibles basándose en el estado del sensor
            for n in pcs_disponibles_db:
                # Para las PCs 1 y 2, verificamos el sensor.
                if n in [1, 2]:
                    # El sensor para PC 'n' es el índice 'n-1'
                    try:
                        if Carrito.Computer_state(n - 1):
                            lbL.insert("end", f"💻 Computadora {n}")
                    except IndexError:
                        # Si hay un error (ej: el array de sensores es más pequeño), no la mostramos para estar seguros.
                        pass
                else: # Para el resto de PCs (3 en adelante), si están en la DB, se muestran.
                    lbL.insert("end", f"💻 Computadora {n}")
            
            for n in get_user_loans(self.current_user["id"]): lbR.insert("end", f"💻 Computadora {n}")

        refresh_lists(); lbL.focus_set()

        # Botones en cada sección
        # Mensaje discreto inline
        feedback = tk.StringVar(value="")
        fb_label = ttk.Label(body, textvariable=feedback, style="Soft.TLabel")
        fb_label.grid(row=3, column=0, columnspan=2, sticky="w", pady=(6,0))

        def _flash(msg):
            feedback.set(msg)
            fb_label.after(2500, lambda: feedback.set(""))

        def confirmar_retiro():
            idx = lbL.curselection()
            if not idx: _flash("Seleccioná al menos una computadora para retirar."); return
            sel = [int(lbL.get(i).split()[-1]) for i in idx]
            try:
                loan_pcs_to_user(self.current_user["id"], sel)
            except Exception as e:
                _flash(str(e)); return
            # Actualizar listas en vivo
            # (la PC retirada ya no estará disponible, por lo que desaparecerá de la lista)
            refresh_lists(); self._refresh_menu_user()
            _flash(f"Retiraste: {', '.join(map(str, sorted(sel)))}")

        def confirmar_devolucion():
            idx = lbR.curselection()
            if not idx:
                _flash("Seleccioná al menos una computadora para devolver.")
                return
            sel = [int(lbR.get(i).split()[-1]) for i in idx]

            # Revisión por sensor antes de permitir devolución
            for pc_id in sel:
                sensor_ok = False
                try:
                    # Asumimos que el ID de la PC se corresponde con el índice del sensor.
                    # Por ejemplo, PC 1 -> sensor 0, PC 2 -> sensor 1, etc.
                    # ¡Ajusta esta lógica si tu mapeo es diferente!
                    sensor_index = pc_id - 1
                    if sensor_index >= 0:
                        sensor_ok = Carrito.Computer_state(sensor_index)
                    else:
                        # Si el ID de la PC no es válido para un sensor, lo marcamos como no OK.
                        sensor_ok = False
                except Exception as e:
                    print(f"[Error sensor] No se pudo verificar el estado de la PC {pc_id}:", e)
                    # Si hay un error de hardware, no permitimos la devolución para estar seguros.
                    sensor_ok = False

                if not sensor_ok:
                    Carrito.Turn_on_alarm()
                    messagebox.showerror(
                        "Devolución fallida",
                        f"La computadora {pc_id} no fue detectada en el carrito.\n"
                        "Por favor, colócala correctamente en su lugar y vuelve a intentarlo."
                    )
                    return  # Detiene el proceso de devolución

            # Si todas las computadoras seleccionadas fueron detectadas, apaga la alarma y procesa la devolución.
            Carrito.Turn_off_alarm()
            try:
                return_pcs_for_user(self.current_user["id"], sel)
                refresh_lists()
                self._refresh_menu_user()
                _flash(f"Devolviste: {', '.join(map(str, sorted(sel)))}")
            except Exception as e:
                _flash(str(e))

        # Botones de acción
        btn_retiro = PrimaryButton(body, text="Confirmar retiro", command=confirmar_retiro)
        btn_retiro.grid(row=2, column=0, sticky="ew", pady=(8,0), padx=(0,10))
        btn_devolucion = PrimaryButton(body, text="Confirmar devolución", command=confirmar_devolucion)
        btn_devolucion.grid(row=2, column=1, sticky="ew", pady=(8,0), padx=(10,0))

    # ---------- common dialog builder ----------
    def _list_dialog(self, title_icon, title_text, items, confirm_text, on_confirm, switch_btn_text=None, switch_btn_command=None):
        # Crear frame para el modal
        modal_content = tk.Frame(self.main_frame, bg=CARD_BG)
        modal_content.configure(width=600, height=500)
        
        # Header del modal
        header = tk.Frame(modal_content, bg=CARD_BG)
        header.pack(fill="x", padx=20, pady=(20, 10))
        tk.Label(header, text=title_icon, font=("Segoe UI Emoji", 20), bg=CARD_BG, fg=INK).pack(side="left")
        ttk.Label(header, text=title_text, style="Title.TLabel").pack(side="left", padx=(6,0))
        if switch_btn_text and switch_btn_command:
            def _switch_from_header():
                self._close_modal(); self.after(50, switch_btn_command)
            ttk.Button(header, text=switch_btn_text, command=_switch_from_header).pack(side="right")
        
        # Línea divisoria sutil
        tk.Frame(modal_content, bg=DIVIDER, height=1).pack(fill="x", padx=20)
        
        # Body con lista
        body = tk.Frame(modal_content, bg=CARD_BG)
        body.pack(fill="both", expand=True, padx=20, pady=20)
        
        frame = tk.Frame(body, bg=CARD_BG)
        frame.pack(fill="both", expand=True)
        
        sb = ttk.Scrollbar(frame, orient="vertical")
        listbox = tk.Listbox(frame, selectmode="multiple", activestyle="none", bd=0, relief="flat", 
                           highlightthickness=1, highlightbackground=DIVIDER, highlightcolor=PRIMARY, 
                           font=FONT, fg=INK, bg=CARD_INNER, height=12)
        listbox.grid(row=0, column=0, sticky="nsew")
        sb.grid(row=0, column=1, sticky="ns")
        frame.grid_rowconfigure(0, weight=1)
        frame.grid_columnconfigure(0, weight=1)
        listbox.config(yscrollcommand=sb.set)
        sb.config(command=listbox.yview)
        # Asegurar que se pueda seleccionar de inmediato
        listbox.focus_set()
        
        for n in items: 
            listbox.insert("end", f"💻 Computadora {n}")
        
        # Footer con botones
        footer = tk.Frame(modal_content, bg=CARD_BG)
        footer.pack(fill="x", padx=20, pady=(0, 20))
        
        def on_confirm_wrapper():
            on_confirm(modal_content, listbox)
        
        PrimaryButton(footer, text=confirm_text, command=on_confirm_wrapper).pack(side="left")
        def _cancel():
            self._close_modal(); self._refresh_menu_user()
        ttk.Button(footer, text="Cancelar", command=_cancel).pack(side="left", padx=8)
        
        # Mostrar modal
        self._show_modal(modal_content, f"{title_icon} {title_text}")
        return modal_content, listbox

    def _retirar_pcs_dialog(self):
        items = get_available_pcs()
        def on_confirm(modal, listbox):
            idx = listbox.curselection()
            if not idx:
                messagebox.showwarning("Selección", "Seleccioná al menos una computadora."); return
            sel = [int(listbox.get(i).split()[-1]) for i in idx]
            try:
                loan_pcs_to_user(self.current_user["id"], sel)
            except Exception as e:
                messagebox.showerror("Disponibilidad", str(e)); return
            messagebox.showinfo("Retiro OK", f"Retiraste: {', '.join(map(str, sorted(sel)))}")
            # Quitar ítems seleccionados del listbox para que no se puedan volver a seleccionar
            for i in sorted(idx, reverse=True):
                listbox.delete(i)
            self._refresh_menu_user()
        # Construir siempre el modal, aunque no haya items (botón confirmar deshabilitado)
        modal, listbox = self._list_dialog("📦", "Retirar computadoras", items, "Confirmar retiro", on_confirm,
                                           switch_btn_text="Ir a Devolver", switch_btn_command=self._devolver_pcs_dialog)
        if not items:
            # Mostrar aviso dentro del modal y deshabilitar confirmación
            info = ttk.Label(modal, text="No hay computadoras disponibles para retirar.", style="Soft.TLabel")
            info.pack(fill="x", padx=20, pady=(0, 10))
            # Deshabilitar el primer botón (Confirmar) en el footer
            try:
                footer = modal.winfo_children()[-2]
                footer.winfo_children()[0]["state"] = "disabled"
            except Exception:
                pass

    def _devolver_pcs_dialog(self):
        mine_items = get_user_loans(self.current_user["id"])
        def on_confirm(modal, listbox):
            idx = listbox.curselection()
            if not idx:
                messagebox.showwarning("Selección", "Seleccioná al menos una computadora."); return
            sel = [int(listbox.get(i).split()[-1]) for i in idx]
            try:
                return_pcs_for_user(self.current_user["id"], sel)
            except Exception as e:
                messagebox.showerror("Permisos", str(e)); return
            messagebox.showinfo("Devolución OK", f"Devolviste: {', '.join(map(str, sorted(sel)))}")
            # Quitar ítems ya devueltos del listbox para que desaparezcan
            for i in sorted(idx, reverse=True):
                listbox.delete(i)
            self._refresh_menu_user()
        # Construir siempre el modal, aunque no haya items (botón confirmar deshabilitado)
        modal, listbox = self._list_dialog("↩️", "Devolver computadoras (tuyas)", mine_items, "Confirmar devolución", on_confirm,
                                           switch_btn_text="Ir a Retirar", switch_btn_command=self._retirar_pcs_dialog)
        if not mine_items:
            info = ttk.Label(modal, text="No tenés computadoras retiradas actualmente.", style="Soft.TLabel")
            info.pack(fill="x", padx=20, pady=(0, 10))
            try:
                footer = modal.winfo_children()[-2]
                footer.winfo_children()[0]["state"] = "disabled"
            except Exception:
                pass

    # ---------- admin ----------
    def _build_admin(self):
        # Limpiar frame principal
        for w in self.main_frame.winfo_children(): w.destroy()
        
        # Crear contenedor centrado
        container = tk.Frame(self.main_frame, bg=BG_OUT)
        container.pack(expand=True, fill="both")
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1)
        
        card = tk.Frame(container, bg=CARD_BG)
        card.grid(row=0, column=0, sticky="nsew", padx=40, pady=40)
        card.grid_columnconfigure(0, weight=1)
        header = tk.Frame(card, bg=CARD_BG); header.pack(fill="x", pady=(10,6), padx=16)
        tk.Label(header, text="🛠️", font=("Segoe UI Emoji", 22), bg=CARD_BG, fg=INK).pack(side="left")
        ttk.Label(header, text="Administrador — Usuarios", style="Title.TLabel").pack(side="left", padx=(8,0))
        tools = tk.Frame(card, bg=CARD_BG); tools.pack(fill="x", padx=16, pady=(8,6))
        ttk.Label(tools, text="🔎", style="TLabel").pack(side="left")
        self.var_search = tk.StringVar()
        ent = ttk.Entry(tools, textvariable=self.var_search, width=40, style="G.TEntry"); ent.pack(side="left", padx=(6,10))
        # Botones de acciones a la derecha (navegan a páginas internas)
        PrimaryButton(tools, text="⚙️ Administrar computadoras", command=self._admin_manage_pcs_page).pack(side="right", padx=(8,0))
        PrimaryButton(tools, text="＋ Agregar usuario", command=self._admin_add_user_page).pack(side="right")
        self.var_search.trace_add("write", lambda *_: self._admin_render_user_list())
        tk.Frame(card, bg=DIVIDER, height=1).pack(fill="x", padx=16, pady=6)
        # list container consumes available width
        self.list_container = tk.Frame(card, bg=CARD_BG); self.list_container.pack(fill="both", expand=True, padx=8, pady=(2,10))
        tk.Frame(card, bg=DIVIDER, height=1).pack(fill="x", padx=16, pady=(6,8))
        footer = tk.Frame(card, bg=CARD_BG); footer.pack(fill="x", padx=16, pady=(0,8))
        tk.Button(footer, text="Cerrar sesión", font=FONT, fg=INK, bg=CARD_BG, activebackground=CARD_BG, bd=0, cursor="hand2", command=self._logout).pack(side="right")
        self._admin_render_user_list()

    def _admin_render_user_list(self):
        # clear
        for w in self.list_container.winfo_children(): w.destroy()
        head = tk.Frame(self.list_container, bg=CARD_BG); head.pack(fill="x", pady=(6,0), padx=6)
        ttk.Label(head, text="Lista de usuarios", style="TLabel").pack(side="left")
        users = list_users()
        ttk.Label(head, text=f"({len(users)})", style="Soft.TLabel").pack(side="left", padx=(6,0))
        tk.Frame(self.list_container, height=6, bg=CARD_BG).pack(fill="x")
        q = (self.var_search.get() if hasattr(self, "var_search") else "").strip().lower()

        # scroll area that fills horizontal space and supports horizontal scrolling
        body = tk.Frame(self.list_container, bg=CARD_BG); body.pack(fill="both", expand=True)
        canvas = tk.Canvas(body, bg=CARD_BG, highlightthickness=0)
        vs = ttk.Scrollbar(body, orient="vertical", command=canvas.yview)
        hs = ttk.Scrollbar(body, orient="horizontal", command=canvas.xview)  # horizontal scrollbar
        inner = tk.Frame(canvas, bg=CARD_BG)

        # place inner frame in canvas
        canvas_window = canvas.create_window((0,0), window=inner, anchor="nw")

        # configure scrolling
        canvas.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)

        # layout: canvas (fill both), vertical scrollbar on right, horizontal scrollbar at bottom
        canvas.pack(side="top", fill="both", expand=True)
        vs.pack(side="right", fill="y")
        hs.pack(side="bottom", fill="x")

        # update scrollregion when inner changes
        def _on_inner_config(event=None):
            canvas.configure(scrollregion=canvas.bbox("all"))
        inner.bind("<Configure>", _on_inner_config)

        def _on_canvas_config(event):
            canvas.configure(scrollregion=canvas.bbox("all"))
        canvas.bind("<Configure>", _on_canvas_config)

        # populate rows
        for u in users:
            if q and q not in u["name"].lower(): continue
            deuda = len(get_user_loans(u["id"]))
            # row uses full width; reduce inner paddings for more horizontal space
            row = tk.Frame(inner, bg=CARD_BG, highlightthickness=1, highlightbackground=DIVIDER, padx=6, pady=8)
            row.pack(fill="x", pady=6)
            row.grid_columnconfigure(0, weight=1)
            left = tk.Frame(row, bg=CARD_BG); left.pack(side="left", fill="both", expand=True, padx=6)
            avatar = tk.Label(left, text=u["name"][:1].upper(), font=("Segoe UI", 16, "bold"), fg="#ffffff", bg="#64748b", width=3, height=1, padx=8, pady=6)
            avatar.pack(side="left", padx=(0,12))
            info = tk.Frame(left, bg=CARD_BG); info.pack(side="left", fill="x", expand=True)
            ttk.Label(info, text=u["name"], style="TLabel", font=FONT_BOLD).pack(anchor="w")
            ttk.Label(info, text=u["email"], style="Soft.TLabel").pack(anchor="w")
            barcode_txt = u["barcode"] if not u["is_admin"] else (u["barcode"] or "—")
            ttk.Label(info, text=f"Código: {barcode_txt}", style="Soft.TLabel").pack(anchor="w")
            mid = tk.Frame(row, bg=CARD_BG); mid.pack(side="left", padx=8)
            badge(mid, f"Debe {deuda}", "ok" if deuda == 0 else "warn").pack(padx=8, pady=8)
            right = tk.Frame(row, bg=CARD_BG); right.pack(side="right", padx=12, pady=6)
            IconButton(right, "✏️  Editar", "edit", command=lambda e=u: self._admin_edit_user_dialog(e), tooltip="Editar usuario").pack(side="left", padx=6)
            if not u["is_admin"]:
                IconButton(right, "🗑️  Borrar", "del", command=lambda e=u: self._admin_delete_user(e), tooltip="Borrar usuario").pack(side="left", padx=6)

        # final update of scrollregion
        inner.update_idletasks()
        canvas.configure(scrollregion=canvas.bbox("all"))

    def _is_valid_gmail(self, email: str) -> bool:
        return bool(re.match(r"^[A-Za-z0-9._%+-]+@gmail\.com$", email or ""))

    # --- add user (barcode editable) ---
    def _admin_add_user_page(self):
        for w in self.main_frame.winfo_children(): w.destroy()
        page = tk.Frame(self.main_frame, bg=CARD_BG)
        page.pack(fill="both", expand=True, padx=20, pady=16)
        header = tk.Frame(page, bg=CARD_BG); header.pack(fill="x", padx=4, pady=(12,8))
        ttk.Label(header, text="Agregar usuario", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Volver", command=self._build_admin).pack(side="right")
        frm = tk.Frame(page, bg=CARD_BG)
        frm.pack(fill="both", expand=True, padx=10, pady=10)
        name = LabeledEntry(frm, "Nombre", "👤"); name.pack(fill="x", pady=6)
        email = LabeledEntry(frm, "Email (@gmail.com)", "📧"); email.pack(fill="x", pady=6)
        pwd   = LabeledEntry(frm, "Password", "🔒", password=True); pwd.pack(fill="x", pady=6)
        is_admin_var = tk.IntVar(value=0)
        admin_checkbox = ttk.Checkbutton(frm, text="Es administrador", variable=is_admin_var)
        admin_checkbox.pack(anchor="w", pady=(4,6), padx=2)
        bc_frame = tk.Frame(frm, bg=CARD_BG); bc_frame.pack(fill="x", pady=(6,2))
        tk.Label(bc_frame, text="🏷️ Código de barras:", font=FONT, bg=CARD_BG, fg=INK).pack(side="left")
        bc_var = tk.StringVar(value=self._gen_unique_barcode())
        bc_entry = ttk.Entry(bc_frame, textvariable=bc_var, style="G.TEntry", width=36); bc_entry.pack(side="left", padx=8)
        def capture_scan():
            # Inline: enfocar el campo de código para permitir escaneo directo
            bc_entry.focus_set()
        ttk.Button(bc_frame, text="Capturar por escaneo", command=capture_scan).pack(side="left", padx=8)
        ttk.Button(bc_frame, text="Regenerar", command=lambda: bc_var.set(self._gen_unique_barcode())).pack(side="left", padx=8)
        btns = tk.Frame(frm, bg=CARD_BG); btns.pack(pady=10)
        def do_add():
            n = name.value(); e = (email.value() or "").lower(); p = pwd.value(); bc = (bc_var.get() or "").strip(); is_admin = is_admin_var.get()
            if not (n and e and p): messagebox.showwarning("Datos", "Completá nombre, email y password."); return
            if not self._is_valid_gmail(e): messagebox.showerror("Email inválido", "El email debe ser @gmail.com."); return
            users = list_users()
            if any(u["email"] == e for u in users): messagebox.showerror("Duplicado", "Ese email ya existe."); return
            if bc and any(u["barcode"] == bc for u in users): messagebox.showerror("Duplicado", "El código ya está en uso. Regeneralo o usá otro."); return
            try:
                create_user_db(e, n, p, bc or None, int(is_admin))
            except Exception as ex:
                messagebox.showerror("Error", str(ex)); return
            messagebox.showinfo("OK", f"Usuario creado.\nCódigo: {bc}")
            self._close_modal(); self._admin_render_user_list()
        PrimaryButton(btns, text="Crear", command=do_add).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancelar", command=self._close_modal).pack(side="left", padx=6)
        
        # No modal: página inline

    # --- edit user (as page, no popups) ---
    def _admin_edit_user_dialog(self, user):
        meta = user
        for w in self.main_frame.winfo_children(): w.destroy()
        page = tk.Frame(self.main_frame, bg=CARD_BG)
        page.pack(fill="both", expand=True, padx=20, pady=16)
        header = tk.Frame(page, bg=CARD_BG); header.pack(fill="x", padx=4, pady=(12,8))
        ttk.Label(header, text="Editar usuario", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Volver", command=self._build_admin).pack(side="right")

        frm = tk.Frame(page, bg=CARD_BG); frm.pack(fill="both", expand=True, padx=10, pady=10)
        name = LabeledEntry(frm, "Nombre", "👤"); name.pack(fill="x", pady=6); name.entry.delete(0,"end"); name.entry.insert(0, meta["name"])
        mail = LabeledEntry(frm, "Email (@gmail.com)", "📧"); mail.pack(fill="x", pady=6); mail.entry.delete(0,"end"); mail.entry.insert(0, meta["email"])
        pwd  = LabeledEntry(frm, "Password", "🔒", password=True); pwd.pack(fill="x", pady=6); pwd.entry.delete(0,"end"); pwd.entry.insert(0, "*****")
        bc_var = tk.StringVar(value=meta.get("barcode","") or "")
        is_admin_var = tk.IntVar(value=1 if meta.get("is_admin") else 0)
        ttk.Checkbutton(frm, text="Es administrador", variable=is_admin_var).pack(anchor="w", pady=(4,6), padx=2)

        bc_frame = tk.Frame(frm, bg=CARD_BG); bc_frame.pack(fill="x", pady=(6,2))
        tk.Label(bc_frame, text="🏷️ Código de barras:", font=FONT, bg=CARD_BG, fg=INK).pack(side="left")
        bc_entry = ttk.Entry(bc_frame, textvariable=bc_var, style="G.TEntry", width=36); bc_entry.pack(side="left", padx=8)
        def capture_scan():
            bc_entry.focus_set()
        ttk.Button(bc_frame, text="Capturar por escaneo", command=capture_scan).pack(side="left", padx=8)
        ttk.Button(bc_frame, text="Regenerar", command=lambda: bc_var.set(self._gen_unique_barcode())).pack(side="left", padx=8)

        # Loans with time
        loans_wrap = tk.Frame(frm, bg=CARD_BG); loans_wrap.pack(fill="both", expand=True, pady=(8,6))
        tk.Label(loans_wrap, text="Préstamos activos", font=FONT_BOLD, bg=CARD_BG, fg=INK).pack(anchor="w")
        loans_list = tk.Listbox(loans_wrap, activestyle="none", bd=0, relief="flat",
                                highlightthickness=1, highlightbackground=DIVIDER, highlightcolor=PRIMARY,
                                font=FONT, fg=INK, bg=CARD_INNER, height=6)
        loans_list.pack(fill="both", expand=True, pady=(4,0))
        for r in list_active_loans_with_times(meta["id"]):
            loans_list.insert("end", f"💻 PC {r['pc_id']} — retirado: {r['loaned_at']}")

        btns = tk.Frame(frm, bg=CARD_BG); btns.pack(pady=10)
        def do_save():
            new_name = name.value(); new_email = (mail.value() or "").lower(); new_pwd = pwd.value(); new_bc = (bc_var.get() or "").strip()
            new_is_admin = is_admin_var.get()
            if not (new_name and new_email and new_pwd):
                messagebox.showwarning("Datos", "Completá todos los campos."); return
            if not self._is_valid_gmail(new_email):
                messagebox.showerror("Email inválido", "El email debe ser @gmail.com."); return
            users = list_users()
            if any((u["email"] == new_email and u["id"] != meta["id"]) for u in users):
                messagebox.showerror("Duplicado", "Ese nuevo email ya existe."); return
            if not new_bc:
                messagebox.showerror("Código", "El usuario debe tener un código de barras asignado."); return
            if any((u["barcode"] == new_bc and u["id"] != meta["id"]) for u in users):
                messagebox.showerror("Duplicado", "Ese código ya está asignado a otro usuario."); return
            try:
                if new_pwd == "*****":
                    conn = get_conn(); cur = conn.cursor()
                    cur.execute("UPDATE users SET email=?, name=?, barcode=?, is_admin=? WHERE id=?", (new_email, new_name, new_bc, int(new_is_admin), meta["id"]))
                    conn.commit(); conn.close()
                else:
                    update_user_db(meta["id"], new_email, new_name, new_pwd, new_bc, int(new_is_admin))
            except Exception as ex:
                messagebox.showerror("Error", str(ex)); return
            messagebox.showinfo("OK", "Usuario actualizado.")
            self._build_admin()
        PrimaryButton(btns, text="Guardar", command=do_save).pack(side="left", padx=6)
        ttk.Button(btns, text="Cancelar", command=self._build_admin).pack(side="left", padx=6)

    def _admin_delete_user(self, user):
        try:
            if user["is_admin"]:
                messagebox.showwarning("Bloqueado", "No se puede borrar la cuenta admin."); return
            if not messagebox.askyesno("Confirmar", f"¿Borrar usuario {user['email']}?"): return
            delete_user_db(user["id"])
            messagebox.showinfo("OK", "Usuario eliminado."); self._admin_render_user_list()
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ---------- admin: manage PCs ----------
    def _admin_manage_pcs_page(self):
        for w in self.main_frame.winfo_children(): w.destroy()
        page = tk.Frame(self.main_frame, bg=CARD_BG)
        page.pack(fill="both", expand=True, padx=20, pady=16)

        header = tk.Frame(page, bg=CARD_BG)
        header.pack(fill="x", padx=4, pady=(12, 10))
        ttk.Label(header, text="Administración de computadoras", style="Title.TLabel").pack(side="left")
        ttk.Button(header, text="Volver", command=self._build_admin).pack(side="right")

        body = tk.Frame(page, bg=CARD_BG)
        body.pack(fill="both", expand=True, padx=4, pady=10)

        list_frame = tk.Frame(body, bg=CARD_BG)
        list_frame.pack(fill="both", expand=True)

        sb = ttk.Scrollbar(list_frame, orient="vertical")
        lb = tk.Listbox(list_frame, selectmode="extended", activestyle="none", bd=0, relief="flat",
                        highlightthickness=1, highlightbackground=DIVIDER, highlightcolor=PRIMARY,
                        font=FONT, fg=INK, bg=CARD_INNER, height=14)
        lb.grid(row=0, column=0, sticky="nsew"); sb.grid(row=0, column=1, sticky="ns")
        list_frame.grid_rowconfigure(0, weight=1); list_frame.grid_columnconfigure(0, weight=1)
        lb.config(yscrollcommand=sb.set); sb.config(command=lb.yview)

        def refresh_list():
            lb.delete(0, "end")
            for pc in list_all_pcs():
                state = "Disponible" if pc["available"] else "En uso/bloqueada"
                icon = "✅" if pc["available"] else "⛔"
                lb.insert("end", f"💻 PC {pc['id']} — {icon} {state}")

        # acciones
        actions = tk.Frame(body, bg=CARD_BG)
        actions.pack(fill="x", pady=(8,0))

        def get_selected_ids():
            sel = []
            for i in lb.curselection():
                txt = lb.get(i)
                try:
                    sel.append(int(txt.split()[1]))
                except Exception:
                    pass
            return sel

        def add_pc():
            new_id = add_pc_db()
            messagebox.showinfo("OK", f"PC {new_id} agregada")
            refresh_list()

        def remove_pc():
            ids = get_selected_ids()
            if not ids:
                messagebox.showwarning("Selección", "Seleccioná al menos una PC"); return
            for pid in ids:
                try:
                    remove_pc_db(pid)
                except Exception as e:
                    messagebox.showerror("Error", str(e)); return
            messagebox.showinfo("OK", "PCs eliminadas")
            refresh_list()

        def bloquear():
            ids = get_selected_ids()
            if not ids:
                messagebox.showwarning("Selección", "Seleccioná al menos una PC"); return
            for pid in ids:
                try:
                    set_pc_available_db(pid, False)
                except Exception as e:
                    messagebox.showerror("Error", str(e)); return
            refresh_list()

        def desbloquear():
            ids = get_selected_ids()
            if not ids:
                messagebox.showwarning("Selección", "Seleccioná al menos una PC"); return
            for pid in ids:
                try:
                    set_pc_available_db(pid, True)
                except Exception as e:
                    messagebox.showerror("Error", str(e)); return
            refresh_list()

        def liberar():
            ids = get_selected_ids()
            if not ids:
                messagebox.showwarning("Selección", "Seleccioná al menos una PC"); return
            for pid in ids:
                try:
                    free_pc_db(pid)
                except Exception as e:
                    messagebox.showerror("Error", str(e)); return
            refresh_list()

        # Se quita agregar/eliminar PCs según requerimiento
        ttk.Button(actions, text="⛔ Bloquear", command=bloquear).pack(side="left", padx=6)
        ttk.Button(actions, text="✅ Desbloquear", command=desbloquear).pack(side="left", padx=6)
        ttk.Button(actions, text="↩️ Liberar selección", command=liberar).pack(side="left", padx=6)

        # footer
        footer = tk.Frame(page, bg=CARD_BG)
        footer.pack(fill="x", padx=4, pady=(6, 8))
        ttk.Button(footer, text="Volver", command=self._build_admin).pack(side="right")

        refresh_list()

    # ---------- admin: password login ----------
    def _admin_password_login_page(self):
        for w in self.main_frame.winfo_children(): w.destroy()
        wrap = tk.Frame(self.main_frame, bg=CARD_BG)
        wrap.pack(fill="both", expand=True, padx=40, pady=40)
        header = tk.Frame(wrap, bg=CARD_BG); header.pack(fill="x", pady=(10,6))
        ttk.Label(header, text="🔐 Acceso administrador", style="Title.TLabel").pack(side="left")
        frm = tk.Frame(wrap, bg=CARD_BG); frm.pack(fill="x")
        mail = LabeledEntry(frm, "Email (@gmail.com)", "📧"); mail.pack(fill="x", pady=6)
        pwd  = LabeledEntry(frm, "Password", "🔒", password=True); pwd.pack(fill="x", pady=6)
        btns = tk.Frame(wrap, bg=CARD_BG); btns.pack(pady=10, fill="x")
        def do_login():
            e = (mail.value() or "").lower(); p = pwd.value()
            if not (e and p):
                messagebox.showwarning("Datos", "Completá email y password"); return
            u = authenticate_admin(e, p)
            if not u:
                messagebox.showerror("Acceso", "Credenciales inválidas o no sos admin"); return
            self.current_user = u; self._build_admin()
        PrimaryButton(btns, text="Entrar", command=do_login).pack(side="left")
        ttk.Button(btns, text="Volver", command=self._build_login).pack(side="left", padx=8)

    # ---------- user: password login ----------
    def _user_password_login_page(self):
        for w in self.main_frame.winfo_children(): w.destroy()
        wrap = tk.Frame(self.main_frame, bg=CARD_BG)
        wrap.pack(fill="both", expand=True, padx=40, pady=40)
        header = tk.Frame(wrap, bg=CARD_BG); header.pack(fill="x", pady=(10,6))
        ttk.Label(header, text="🔐 Acceso usuario", style="Title.TLabel").pack(side="left")
        frm = tk.Frame(wrap, bg=CARD_BG); frm.pack(fill="x")
        mail = LabeledEntry(frm, "Email (@gmail.com)", "📧"); mail.pack(fill="x", pady=6)
        pwd  = LabeledEntry(frm, "Password", "🔒", password=True); pwd.pack(fill="x", pady=6)
        btns = tk.Frame(wrap, bg=CARD_BG); btns.pack(pady=10, fill="x")
        def do_login():
            e = (mail.value() or "").lower(); p = pwd.value()
            if not (e and p):
                messagebox.showwarning("Datos", "Completá email y password"); return
            u = authenticate_user(e, p)
            if not u:
                messagebox.showerror("Acceso", "Credenciales inválidas"); return
            self.current_user = u
            if u["is_admin"]:
                self._build_admin()
            else:
                self._build_menu_user()
        PrimaryButton(btns, text="Entrar", command=do_login).pack(side="left")
        ttk.Button(btns, text="Volver", command=self._build_login).pack(side="left", padx=8)

    # ---------- resizing background ----------
    def _on_resize(self, event):
        vertical_gradient(self.bg, event.width, event.height)
        # Ya no necesitamos el center_id porque usamos main_frame

if __name__ == "__main__":
    App().mainloop()
