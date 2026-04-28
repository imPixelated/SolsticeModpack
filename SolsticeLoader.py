import minecraft_launcher_lib
import subprocess
import tkinter as tk
from tkinter import messagebox, filedialog
import os
import json
import time
import urllib.request
import urllib.parse
import urllib.error
import ssl
import uuid
import hashlib
import shutil

# ─────────────────────────────────────────────────────────────────────────────
# CONFIGURAÇÕES
# ─────────────────────────────────────────────────────────────────────────────

MSA_CLIENT_ID     = "c36a9fb6-4f2a-41ff-90bd-ae7cc92031eb"
ACCOUNT_FILE      = "save.json"
MINECRAFT_VERSION = "1.21.1"
LOADER_TYPE       = "neoforge"   # vanilla | forge | neoforge | fabric
MODPACK_MODS_DIR = "mods"

# ─────────────────────────────────────────────────────────────────────────────
# PALETA DARK MODE
# ─────────────────────────────────────────────────────────────────────────────

BG       = "#1f1d1c"   # fundo principal
BG2      = "#2a2a3e"   # fundo secundário (listbox, entry, frames internos)
BG3      = "#45475a"   # hover / active
FG       = "#cdd6f4"   # texto principal
FG_MUTED = "#6c7086"   # texto secundário / hints
SEL_BG   = "#585b70"   # seleção na listbox
ACCENT   = "#f0c040"   # dourado — botão primário
ACCENT_H = "#ffd966"   # dourado hover
DANGER   = "#f38ba8"   # vermelho — ações destrutivas

# ─────────────────────────────────────────────────────────────────────────────
# SISTEMA DE JANELAS
# ─────────────────────────────────────────────────────────────────────────────

def make_window(title: str, parent=None) -> "tk.Tk | tk.Toplevel":
    import os
    import tkinter as tk

    if parent is None:
        win = tk.Tk()
    else:
        win = tk.Toplevel(parent)
        win.transient(parent)

    win.withdraw()          # esconde imediatamente, antes de qualquer desenho
    win.title(title)
    win.resizable(False, False)

    # resolve o caminho do ícone corretamente
    base_dir = os.path.dirname(os.path.abspath(__file__))
    icon_path = os.path.join(base_dir, "resources", "icon.ico")
    try:
        win.iconbitmap(icon_path)
    except Exception as e:
        print(f"Erro ao carregar ícone: {e}")

    win.configure(bg=BG)

    # Dark mode para todos os widgets criados nesta janela
    win.option_add("*Background",               BG)
    win.option_add("*Foreground",               FG)
    win.option_add("*activeBackground",         BG3)
    win.option_add("*activeForeground",         FG)
    win.option_add("*disabledForeground",       FG_MUTED)

    win.option_add("*Label.Background",         BG)
    win.option_add("*Label.Foreground",         FG)

    win.option_add("*Frame.Background",         BG)

    win.option_add("*Button.Background",        BG2)
    win.option_add("*Button.Foreground",        FG)
    win.option_add("*Button.activeBackground",  BG3)
    win.option_add("*Button.activeForeground",  FG)
    win.option_add("*Button.relief",            "flat")
    win.option_add("*Button.padx",              10)
    win.option_add("*Button.pady",              5)
    win.option_add("*Button.cursor",            "hand2")

    win.option_add("*Entry.Background",         BG2)
    win.option_add("*Entry.Foreground",         FG)
    win.option_add("*Entry.insertBackground",   FG)
    win.option_add("*Entry.selectBackground",   SEL_BG)
    win.option_add("*Entry.selectForeground",   FG)
    win.option_add("*Entry.relief",             "flat")

    win.option_add("*Listbox.Background",       BG2)
    win.option_add("*Listbox.Foreground",       FG)
    win.option_add("*Listbox.selectBackground", SEL_BG)
    win.option_add("*Listbox.selectForeground", FG)
    win.option_add("*Listbox.relief",           "flat")
    win.option_add("*Listbox.borderWidth",      0)

    return win


def show_window(win: "tk.Tk | tk.Toplevel") -> None:
    """
    Centra a janela na tela usando o tamanho real dos widgets (reqwidth/reqheight)
    e depois exibe. Deve ser chamado APÓS todos os widgets estarem criados.
    """
    win.update_idletasks()
    w  = win.winfo_reqwidth()
    h  = win.winfo_reqheight()
    sw = win.winfo_screenwidth()
    sh = win.winfo_screenheight()
    win.geometry(f"+{(sw - w) // 2}+{(sh - h) // 2}")
    win.deiconify()
    apply_dark_titlebar(win)


def apply_dark_titlebar(win: "tk.Tk | tk.Toplevel") -> None:
    """
    Aplica barra de título dark mode seguindo a paleta do launcher.
    Funciona no Windows 10 (build 17763+) e Windows 11.
    No macOS/Linux é silenciosamente ignorado.
    """
    try:
        import sys
        if sys.platform != "win32":
            return

        import ctypes

        HWND = ctypes.windll.user32.GetParent(win.winfo_id())
        if not HWND:
            HWND = win.winfo_id()

        # Windows 11 — atributo DWMWA_CAPTION_COLOR (35) para cor da paleta exata
        # Windows 10 — atributo DWMWA_USE_IMMERSIVE_DARK_MODE (20) para modo escuro
        DWMWA_USE_IMMERSIVE_DARK_MODE = 20
        DWMWA_CAPTION_COLOR           = 35

        # Converte hex "#1f1d1c" → COLORREF (0x00BBGGRR)
        hex_color = BG.lstrip("#")
        r, g, b   = int(hex_color[0:2], 16), int(hex_color[2:4], 16), int(hex_color[4:6], 16)
        colorref  = ctypes.c_uint32(b << 16 | g << 8 | r)

        dwm = ctypes.windll.dwmapi

        # Tenta Win11 primeiro (cor exata da paleta)
        result = dwm.DwmSetWindowAttribute(
            HWND, DWMWA_CAPTION_COLOR,
            ctypes.byref(colorref), ctypes.sizeof(colorref),
        )

        # Fallback Win10: ativa só o modo escuro genérico
        if result != 0:
            dark = ctypes.c_int(1)
            dwm.DwmSetWindowAttribute(
                HWND, DWMWA_USE_IMMERSIVE_DARK_MODE,
                ctypes.byref(dark), ctypes.sizeof(dark),
            )

    except Exception as e:
        print(f"[titlebar] Não foi possível aplicar dark mode: {e}")


# ─────────────────────────────────────────────────────────────────────────────
# HELPERS DE WIDGETS
# ─────────────────────────────────────────────────────────────────────────────

def btn_primary(parent, text: str, command, width: int = 18) -> tk.Button:
    return tk.Button(
        parent, text=text, command=command, width=width,
        bg=BG2, fg=FG, activebackground=BG3, activeforeground=FG,
        font=("Arial", 10), relief="flat", cursor="hand2",
        padx=4, pady=3,
    )


def btn_danger(parent, text: str, command, width: int = 18) -> tk.Button:
    """Botão destrutivo — vermelho."""
    return tk.Button(
        parent, text=text, command=command, width=width,
        bg="#3b1e2b", fg=DANGER, activebackground="#5c2a3a", activeforeground=DANGER,
        font=("Arial", 10), relief="flat", cursor="hand2",
        padx=4, pady=3,
    )


def separator(parent) -> tk.Frame:
    """Linha horizontal decorativa."""
    return tk.Frame(parent, height=1, bg=BG3)


def ask_string_dark(title: str, prompt: str, parent, initial: str = "") -> "str | None":
    """
    Substitui simpledialog.askstring com um diálogo 100% dark-mode.
    Retorna a string digitada ou None se cancelado / vazio.
    """
    result = {"value": None}

    win = make_window(title, parent=parent)

    tk.Label(win, text=prompt, font=("Arial", 10)).pack(padx=24, pady=(18, 6))

    var   = tk.StringVar(value=initial)
    entry = tk.Entry(win, textvariable=var, width=34, font=("Arial", 10))
    entry.pack(padx=24, pady=(0, 12))

    def on_ok(_event=None):
        val = var.get().strip()
        if val:
            result["value"] = val
        win.destroy()

    def on_cancel(_event=None):
        win.destroy()

    entry.bind("<Return>", on_ok)
    entry.bind("<Escape>", on_cancel)

    row = tk.Frame(win)
    row.pack(pady=(0, 16))
    btn_primary(row, "OK",       on_ok,     width=10).pack(side=tk.LEFT, padx=6)
    btn_primary(row, "Cancelar", on_cancel, width=10).pack(side=tk.LEFT, padx=6)

    show_window(win)
    entry.focus_set()
    win.grab_set()
    win.wait_window()

    return result["value"]


# ─────────────────────────────────────────────────────────────────────────────
# SSL
# ─────────────────────────────────────────────────────────────────────────────

ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode    = ssl.CERT_NONE


# ─────────────────────────────────────────────────────────────────────────────
# UTILITÁRIOS DE REDE
# ─────────────────────────────────────────────────────────────────────────────

def _post(url, data=None, headers=None):
    if headers is None:
        headers = {}
    if "Accept" not in headers:
        headers["Accept"] = "application/json"
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, context=ssl_context) as r:
        return json.loads(r.read())


def _get(url, headers=None):
    if headers is None:
        headers = {}
    req = urllib.request.Request(url, headers=headers, method="GET")
    with urllib.request.urlopen(req, context=ssl_context) as r:
        return json.loads(r.read())


# ─────────────────────────────────────────────────────────────────────────────
# AUTENTICAÇÃO MICROSOFT
# nao me pergunte como isso funciona eu so copiei do prism e deus nos abencoe
# ─────────────────────────────────────────────────────────────────────────────

def microsoft_device_code_login() -> "dict | None":
    try:
        print("Obtendo código de autenticação...")
        device = _post(
            "https://login.microsoftonline.com/consumers/oauth2/v2.0/devicecode",
            data=urllib.parse.urlencode({
                "client_id": MSA_CLIENT_ID,
                "scope":     "XboxLive.SignIn XboxLive.offline_access",
            }).encode(),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )

        print(f"\n{'='*45}")
        print(f"ACESSE: {device['verification_uri']}")
        print(f"CÓDIGO: {device['user_code']}")
        print(f"{'='*45}\n")

        messagebox.showinfo(
            "Autenticação Solstice",
            f"1. Aceda ao site: {device['verification_uri']}\n"
            f"2. Digite o código: {device['user_code']}\n\n"
            "O launcher continuará automaticamente após a confirmação no navegador.",
        )

        interval   = device.get("interval", 5)
        expires_in = device.get("expires_in", 900)
        start_time = time.time()
        ms_token   = None

        print("Aguardando autorização no navegador...")
        while (time.time() - start_time) < expires_in:
            time.sleep(interval)
            try:
                ms_token = _post(
                    "https://login.microsoftonline.com/consumers/oauth2/v2.0/token",
                    data=urllib.parse.urlencode({
                        "client_id":   MSA_CLIENT_ID,
                        "grant_type":  "urn:ietf:params:oauth:grant-type:device_code",
                        "device_code": device["device_code"],
                    }).encode(),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                )
                print("Autorização concedida!")
                break
            except urllib.error.HTTPError as e:
                body  = json.loads(e.read())
                error = body.get("error")
                if error == "authorization_pending":
                    continue
                elif error == "slow_down":
                    interval += 5
                    continue
                else:
                    raise Exception(f"Erro na Microsoft: {error}")

        if not ms_token:
            return None

        print("Autenticando no Xbox Live...")
        xbl = _post(
            "https://user.auth.xboxlive.com/user/authenticate",
            data=json.dumps({
                "Properties": {
                    "AuthMethod": "RPS",
                    "SiteName":   "user.auth.xboxlive.com",
                    "RpsTicket":  f"d={ms_token['access_token']}",
                },
                "RelyingParty": "http://auth.xboxlive.com",
                "TokenType":    "JWT",
            }).encode(),
            headers={"Content-Type": "application/json"},
        )

        xbl_token = xbl["Token"]
        userhash  = xbl["DisplayClaims"]["xui"][0]["uhs"]

        print("Obtendo tokens XSTS...")
        xsts = _post(
            "https://xsts.auth.xboxlive.com/xsts/authorize",
            data=json.dumps({
                "Properties":   {"SandboxId": "RETAIL", "UserTokens": [xbl_token]},
                "RelyingParty": "rp://api.minecraftservices.com/",
                "TokenType":    "JWT",
            }).encode(),
            headers={"Content-Type": "application/json"},
        )

        print("Finalizando login no Minecraft...")
        mc_auth = _post(
            "https://api.minecraftservices.com/authentication/login_with_xbox",
            data=json.dumps({"identityToken": f"XBL3.0 x={userhash};{xsts['Token']}"}).encode(),
            headers={"Content-Type": "application/json"},
        )

        profile = _get(
            "https://api.minecraftservices.com/minecraft/profile",
            headers={"Authorization": f"Bearer {mc_auth['access_token']}"},
        )

        return {
            "username":      profile["name"],
            "uuid":          profile["id"],
            "access_token":  mc_auth["access_token"],
            "refresh_token": ms_token.get("refresh_token"),
        }

    except Exception as e:
        print(f"Erro no processo de login: {e}")
        messagebox.showerror("Erro de Login", str(e))
        return None


def offline_login() -> "dict | None":
    """Login offline com nome personalizado."""
    result = {"value": None}

    win = make_window("Login Offline")

    tk.Label(win, text="Nome de utilizador:", font=("Arial", 10, "bold")).pack(
        padx=30, pady=(22, 6))

    var   = tk.StringVar()
    entry = tk.Entry(win, textvariable=var, width=28, font=("Arial", 10))
    entry.pack(padx=30, pady=(0, 16))

    def on_ok(_event=None):
        username = var.get().strip()
        if not username:
            messagebox.showwarning("Aviso", "Digite um nome de utilizador.", parent=win)
            return
        result["value"] = username
        win.destroy()

    def on_cancel(_event=None):
        win.destroy()

    entry.bind("<Return>", on_ok)
    entry.bind("<Escape>", on_cancel)

    row = tk.Frame(win)
    row.pack(pady=(0, 20))
    btn_primary(row, "Entrar",   on_ok,     width=10).pack(side=tk.LEFT, padx=6)
    btn_primary(row, "Cancelar", on_cancel, width=10).pack(side=tk.LEFT, padx=6)

    show_window(win)
    entry.focus_set()
    win.mainloop()

    username = result["value"]
    if username:
        offline_uuid = str(uuid.UUID(
            hashlib.md5(f"OfflinePlayer:{username}".encode()).hexdigest()
        ))
        return {
            "username":     username,
            "uuid":         offline_uuid,
            "access_token": "",
            "type":         "offline",
        }
    return None


# ─────────────────────────────────────────────────────────────────────────────
# PERSISTÊNCIA
# ─────────────────────────────────────────────────────────────────────────────

def save_data(accounts: list, instances: list, launcher_dir: str) -> None:
    path = os.path.join(launcher_dir, ACCOUNT_FILE)
    with open(path, "w") as f:
        json.dump({"accounts": accounts, "instances": instances}, f, indent=2)


def load_data(launcher_dir: str) -> tuple:
    path = os.path.join(launcher_dir, ACCOUNT_FILE)
    if not os.path.exists(path):
        return [], []
    try:
        with open(path, "r") as f:
            data = json.load(f)

        if isinstance(data, dict) and "account" in data:
            # Formato antigo — single account
            account = data.get("account")
            if account and "type" not in account:
                account["type"] = "microsoft"
            accounts  = [account] if account else []
            instances = []
            for i, p in enumerate(data.get("instances", [])):
                instances.append({
                    "name":    f"Instância {i+1}",
                    "path":    p,
                    "version": MINECRAFT_VERSION,
                    "loader":  LOADER_TYPE,
                })

        elif isinstance(data, dict) and "accounts" in data:
            accounts  = data.get("accounts", [])
            instances = []
            for item in data.get("instances", []):
                if isinstance(item, str):
                    instances.append({
                        "name":    os.path.basename(item) or "Instância",
                        "path":    item,
                        "version": MINECRAFT_VERSION,
                        "loader":  LOADER_TYPE,
                    })
                else:
                    item["version"] = MINECRAFT_VERSION
                    item["loader"]  = LOADER_TYPE
                    instances.append(item)

        else:
            if data and "type" not in data:
                data["type"] = "microsoft"
            accounts  = [data] if data else []
            instances = []

        # Corrigir UUIDs vazios em contas offline antigas
        for acc in accounts:
            if acc.get("type") == "offline" and not acc.get("uuid"):
                acc["uuid"] = str(uuid.UUID(
                    hashlib.md5(
                        f"OfflinePlayer:{acc.get('username', 'Player')}".encode()
                    ).hexdigest()
                ))

        return accounts, instances
    except Exception:
        return [], []


# ─────────────────────────────────────────────────────────────────────────────
# UTILITÁRIOS GUI
# ─────────────────────────────────────────────────────────────────────────────

def account_icon(account: dict) -> str:
    return "☀" if account.get("type", "microsoft") == "microsoft" else "☽"

def account_display_name(account: dict) -> str:
    return f"{account_icon(account)}  {account.get('username', 'Conta')}"

def instance_display_name(instance: dict) -> str:
    return f"☸ {instance.get('name', 'Sem Nome')}  (v{instance.get('version', '?')})"

def open_folder_path(folder_path: str) -> None:
    if folder_path and os.path.isdir(folder_path):
        os.startfile(folder_path)
    else:
        messagebox.showinfo("Pasta", "Esta pasta não existe ou não foi encontrada.")


# ─────────────────────────────────────────────────────────────────────────────
# TELA INICIAL
# ─────────────────────────────────────────────────────────────────────────────

def show_welcome_screen() -> bool:
    entered = {"value": False}

    win = make_window("Solstice Loader")

    # Logo
    logo_path = os.path.expanduser("resources/logo.png")
    try:
        try:
            from PIL import Image, ImageTk
            img = Image.open(logo_path)
            # Preserve aspect ratio, fit within 300x300
            img.thumbnail((300, 300), Image.LANCZOS)
            photo = ImageTk.PhotoImage(img)
        except ImportError:
            from tkinter import PhotoImage
            photo = PhotoImage(file=logo_path)
            w, h = photo.width(), photo.height()
            # subsample using integer factor so the largest dimension <= 300
            factor = max(1, max(w, h) // 300)
            if factor > 1:
                photo = photo.subsample(factor, factor)

        lbl       = tk.Label(win, image=photo, bg=BG, bd=0)
        lbl.image = photo   # manter referência
        lbl.pack(pady=(30, 8))
    except Exception:
        tk.Label(win, text="SOLSTICE",
                 font=("Georgia", 34, "bold"), fg=ACCENT, bg=BG).pack(pady=(50, 8))
    def on_enter():
        entered["value"] = True
        win.destroy()

    btn_primary(win, "Adentrar o solstício", on_enter, width=26).pack(pady=(0, 38))

    show_window(win)
    win.mainloop()
    return entered["value"]


# ─────────────────────────────────────────────────────────────────────────────
# ESCOLHA DE TIPO DE CONTA
# ─────────────────────────────────────────────────────────────────────────────

def gui_choose_account_type() -> "str | None":
    result = {"value": None}

    win = make_window("Solstice — Nova Conta")

    tk.Label(win, text="Qual tipo de conta?", font=("Arial", 12, "bold")).pack(pady=(26, 16))
    separator(win).pack(fill=tk.X, padx=24, pady=(0, 16))

    col = tk.Frame(win)
    col.pack()

    def pick(v):
        result["value"] = v
        win.destroy()

    btn_primary(col, "Microsoft", lambda: pick("microsoft"), width=17).pack(pady=3)
    btn_primary(col, "Offline", lambda: pick("offline"), width=17).pack(pady=3)
    btn_primary(col, "Cancelar", win.destroy, width=17).pack(pady=(14, 0))

    tk.Frame(win, height=18, bg=BG).pack()
    show_window(win)
    win.mainloop()
    return result["value"]


# ─────────────────────────────────────────────────────────────────────────────
# SELEÇÃO DE CONTA
# ─────────────────────────────────────────────────────────────────────────────

def gui_select_account(accounts: list, instances: list, launcher_dir: str):
    result        = {"value": None}
    selected_acct = {"value": None}

    win = make_window("Solstice — Contas")

    tk.Label(win, text="Selecione uma conta:", font=("Arial", 12, "bold")).pack(
        padx=22, pady=(22, 4), anchor=tk.W)
    separator(win).pack(fill=tk.X, padx=22, pady=(0, 8))

    frame   = tk.Frame(win, bg=BG2, padx=2, pady=2)
    frame.pack(fill=tk.BOTH, expand=True, padx=22, pady=(0, 10))
    listbox = tk.Listbox(frame, height=10, font=("Arial", 10),
                         activestyle="none", selectmode=tk.SINGLE)
    listbox.pack(fill=tk.BOTH, expand=True)

    account_map: dict = {}

    def refresh():
        listbox.delete(0, tk.END)
        account_map.clear()
        for idx, acc in enumerate(accounts):
            listbox.insert(tk.END, f" {account_display_name(acc)}")
            account_map[idx] = acc
        listbox.insert(tk.END,"  +  Nova Conta")

    def get_sel() -> "dict | None":
        s = listbox.curselection()
        return account_map.get(s[0]) if s else None

    # ── Opções de conta ──────────────────────────────────────────────────────
    def open_account_options():
        account = get_sel()
        if account is None:
            messagebox.showwarning("Aviso", "Selecione uma conta primeiro.", parent=win)
            return

        opt = make_window("Opções da Conta", parent=win)
        opt.minsize(200, 250)

        tk.Label(opt, text=account_display_name(account),
                 font=("Arial", 11, "bold")).pack(padx=26, pady=(22, 2))
        tk.Label(opt, text=account.get("type", "microsoft").capitalize(),
                 font=("Arial", 9), fg=FG_MUTED).pack()
        separator(opt).pack(fill=tk.X, padx=22, pady=14)

        col = tk.Frame(opt)
        col.pack()

        def on_rename():
            new_name = ask_string_dark(
                "Alterar Nome",
                "Novo nome de utilizador:",
                parent=opt,
                initial=account.get("username", ""),
            )
            if new_name:
                account["username"] = new_name
                save_data(accounts, instances, launcher_dir)
                refresh()
                opt.destroy()

        def on_delete():
            if not messagebox.askyesno(
                "Apagar Conta",
                f"Apagar '{account.get('username', 'esta conta')}'?",
                parent=opt,
            ):
                return
            if not messagebox.askyesno(
                "Confirmar", "Esta ação remove a conta guardada. Tem a certeza?", parent=opt,
            ):
                return
            if account in accounts:
                accounts.remove(account)
                save_data(accounts, instances, launcher_dir)
                refresh()
            opt.destroy()

        btn_primary(col, "Alterar Nome", on_rename, width=10).pack(pady=5)
        btn_danger(col, "Apagar Conta", on_delete, width=10).pack(pady=5)
        btn_primary(col, "Fechar", opt.destroy, width=10).pack(pady=(14, 0))

        tk.Frame(opt, height=16, bg=BG).pack()
        show_window(opt)

    # ── Botões principais ────────────────────────────────────────────────────
    refresh()
    separator(win).pack(fill=tk.X, padx=22, pady=(0, 10))

    row = tk.Frame(win)
    row.pack(pady=(0, 20))

    def on_select():
        s = listbox.curselection()
        if not s:
            messagebox.showwarning("Aviso", "Selecione uma conta.", parent=win)
            return
        idx = s[0]
        if idx in account_map:
            selected_acct["value"] = account_map[idx]
            result["value"] = "selected"
        else:
            result["value"] = "new"
        win.destroy()

    btn_primary(row, "Confirmar", on_select,            width=12).pack(side=tk.LEFT, padx=5)
    btn_primary(row, "Opções", open_account_options, width=12).pack(side=tk.LEFT, padx=5)
    btn_primary(row, "Cancelar", win.destroy, width=12).pack(side=tk.LEFT, padx=5)

    listbox.bind("<Double-Button-1>", lambda _e: on_select())

    show_window(win)
    win.mainloop()

    if result["value"] == "selected":
        return selected_acct["value"]
    if result["value"] == "new":
        return "__NEW__"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# OBTER / CRIAR CONTA
# ─────────────────────────────────────────────────────────────────────────────

def get_account(launcher_dir: str, accounts: list, instances: list) -> "dict | None":
    if accounts:
        selected = gui_select_account(accounts, instances, launcher_dir)
        if selected is None:
            return None
        if selected != "__NEW__":
            return selected

    account_type = gui_choose_account_type()
    if account_type is None:
        return None

    account = microsoft_device_code_login() if account_type == "microsoft" else offline_login()
    if account:
        account["type"] = account_type
        accounts.append(account)
        save_data(accounts, instances, launcher_dir)
    return account


# ─────────────────────────────────────────────────────────────────────────────
# SELEÇÃO DE INSTÂNCIA
# ─────────────────────────────────────────────────────────────────────────────

def gui_choose_instance(instances: list, accounts: list, launcher_dir: str):
    result        = {"value": None}
    selected_inst = {"value": None}

    win = make_window("Solstice — Instâncias")

    tk.Label(win, text="Selecione uma instância", font=("Arial", 12, "bold")).pack(
        padx=22, pady=(22, 4), anchor=tk.W)
    separator(win).pack(fill=tk.X, padx=22, pady=(0, 8))

    frame   = tk.Frame(win, bg=BG2, padx=2, pady=2)
    frame.pack(fill=tk.BOTH, expand=True, padx=22, pady=(0, 10))
    listbox = tk.Listbox(frame, height=10, font=("Arial", 10),
                         activestyle="none", selectmode=tk.SINGLE)
    listbox.pack(fill=tk.BOTH, expand=True)

    instance_map: dict = {}

    def refresh():
        listbox.delete(0, tk.END)
        instance_map.clear()
        for idx, inst in enumerate(instances):
            listbox.insert(tk.END, f"{instance_display_name(inst)}")
            instance_map[idx] = inst
        listbox.insert(tk.END, " + Nova Instância")

    def get_sel() -> "dict | None":
        s = listbox.curselection()
        return instance_map.get(s[0]) if s else None

    # ── Opções de instância ──────────────────────────────────────────────────
    def open_instance_options():
        instance = get_sel()
        if instance is None:
            messagebox.showwarning("Aviso", "Selecione uma instância primeiro.", parent=win)
            return

        opt = make_window("Opções da Instância", parent=win)

        tk.Label(opt, text=instance.get("name", "Instância"),
                 font=("Arial", 11, "bold")).pack(padx=26, pady=(22, 2))
        tk.Label(opt, text=instance.get("path", ""),
                 font=("Arial", 8), fg=FG_MUTED, wraplength=310).pack(padx=22)
        separator(opt).pack(fill=tk.X, padx=22, pady=14)

        col = tk.Frame(opt)
        col.pack()

        def on_open_folder():
            open_folder_path(instance.get("path"))

        def on_rename():
            new_name = ask_string_dark(
                "Renomear Instância", "Novo nome:",
                parent=opt, initial=instance.get("name", ""),
            )
            if new_name:
                instance["name"] = new_name
                save_data(accounts, instances, launcher_dir)
                refresh()
                opt.destroy()

        def on_java_args():
            jw = make_window("Argumentos Java", parent=opt)

            tk.Label(jw, text="Argumentos JVM", font=("Arial", 11, "bold")).pack(
                padx=26, pady=(22, 4))
            tk.Label(
                jw,
                text="Exemplos:  -Xmx4G -Xms2G  →  4 GB RAM\n"
                     "           -Xmx8G -Xms4G  →  8 GB RAM",
                font=("Arial", 9), fg=FG_MUTED,
            ).pack(padx=26, pady=(0, 10))

            var   = tk.StringVar(value=instance.get("jvm_args", "-Xmx4G -Xms2G"))
            entry = tk.Entry(jw, textvariable=var, width=42, font=("Arial", 10))
            entry.pack(padx=26, pady=(0, 14))

            def on_save(_e=None):
                raw = var.get().strip()
                instance["jvm_args"] = raw if raw else "-Xmx4G -Xms2G"
                save_data(accounts, instances, launcher_dir)
                jw.destroy()
                messagebox.showinfo("Salvo", "Argumentos Java salvos!", parent=opt)

            entry.bind("<Return>", on_save)
            entry.bind("<Escape>", lambda _e: jw.destroy())

            row = tk.Frame(jw)
            row.pack(pady=(0, 20))
            btn_primary(row, "Salvar", on_save, width=10).pack(side=tk.LEFT, padx=6)
            btn_primary(row, "Cancelar", jw.destroy, width=10).pack(side=tk.LEFT, padx=6)

            show_window(jw)
            entry.focus_set()

        def on_delete():
            if not messagebox.askyesno(
                "Apagar Instância",
                f"Apagar '{instance.get('name', 'esta instância')}'?\n\n"
                "Os ficheiros na pasta NÃO serão apagados.",
                parent=opt,
            ):
                return
            if instance in instances:
                instances.remove(instance)
                save_data(accounts, instances, launcher_dir)
                refresh()
            opt.destroy()

        btn_primary(col, "Abrir Pasta", on_open_folder, width=24).pack(pady=5)
        btn_primary(col, "Renomear", on_rename, width=24).pack(pady=5)
        btn_primary(col, "Argumentos Java", on_java_args, width=24).pack(pady=5)
        btn_danger(col, "Apagar Instância", on_delete, width=24).pack(pady=5)
        btn_primary(col, "Fechar", opt.destroy, width=24).pack(pady=(14, 0))

        tk.Frame(opt, height=16, bg=BG).pack()
        show_window(opt)

    # ── Botões principais ────────────────────────────────────────────────────
    refresh()
    separator(win).pack(fill=tk.X, padx=22, pady=(0, 10))

    row = tk.Frame(win)
    row.pack(pady=(0, 20))

    def on_select():
        s = listbox.curselection()
        if not s:
            messagebox.showwarning("Aviso", "Selecione uma instância.", parent=win)
            return
        idx = s[0]
        if idx in instance_map:
            selected_inst["value"] = instance_map[idx]
            result["value"] = "selected"
        else:
            result["value"] = "new"
        win.destroy()

    btn_primary(row,"Confirmar", on_select, width=12).pack(side=tk.LEFT, padx=5)
    btn_primary(row, "Opções", open_instance_options, width=12).pack(side=tk.LEFT, padx=5)
    btn_primary(row, "Cancelar", win.destroy, width=12).pack(side=tk.LEFT, padx=5)

    listbox.bind("<Double-Button-1>", lambda _e: on_select())

    show_window(win)
    win.mainloop()

    if result["value"] == "selected":
        return selected_inst["value"]
    if result["value"] == "new":
        return "__NEW__"
    return None


# ─────────────────────────────────────────────────────────────────────────────
# CRIAR INSTÂNCIA
# ─────────────────────────────────────────────────────────────────────────────

def gui_choose_folder_type() -> "str | None":
    result = {"value": None}

    win = make_window("Diretório da Instância")

    tk.Label(win, text="Onde deseja instalar?", font=("Arial", 12, "bold")).pack(pady=(26, 16))
    separator(win).pack(fill=tk.X, padx=24, pady=(0, 16))
    tk.Label(win, text="<Recomendado>", font=("Arial", 7, "italic")).pack(pady=(0, 1))

    col = tk.Frame(win)
    col.pack()

    def pick(v):
        result["value"] = v
        win.destroy()

    btn_primary(col, "Pasta Padrão (.minecraft)", lambda: pick("default"), width=28).pack(pady=5)
    btn_primary(col, "Pasta Personalizada", lambda: pick("custom"), width=28).pack(pady=5)
    btn_primary(col, "Cancelar", win.destroy, width=28).pack(pady=(14, 0))

    tk.Frame(win, height=20, bg=BG).pack()
    show_window(win)
    win.mainloop()
    return result["value"]


def create_new_instance(instances: list) -> "dict | None":
    # Janela raiz temporária e invisível para servir de parent ao ask_string_dark
    tmp = tk.Tk()
    tmp.withdraw()

    instance_name = ask_string_dark(
        "Nova Instância",
        "Nome da nova instância:",
        parent=tmp,
        initial=f"Instância {len(instances) + 1}",
    )
    tmp.destroy()

    if not instance_name:
        return None

    folder_type = gui_choose_folder_type()
    if folder_type is None:
        return None

    if folder_type == "default":
        minecraft_directory = minecraft_launcher_lib.utils.get_minecraft_directory()
    else:
        minecraft_directory = filedialog.askdirectory(title="Selecione o Diretório")
        if not minecraft_directory:
            return None

    return {
        "name":    instance_name,
        "path":    minecraft_directory,
        "version": MINECRAFT_VERSION,
        "loader":  LOADER_TYPE,
    }

# ─────────────────────────────────────────────────────────────────────────────
# CRIAR MODPACK
# ─────────────────────────────────────────────────────────────────────────────

def instance_files_exist(instance):
    path = instance.get("path", "")
    return bool(path) and os.path.isdir(path)


def validate_and_clean_instances(instances, launcher_dir, accounts):
    valid   = [inst for inst in instances if instance_files_exist(inst)]
    removed = len(instances) - len(valid)

    if removed > 0:
        print(f"[validate] {removed} instancia(s) removida(s) por pasta inexistente.")
        save_data(accounts, valid, launcher_dir)

    return valid


def copy_modpack_mods(instance_path, launcher_dir):
    src_dir = os.path.join(launcher_dir, MODPACK_MODS_DIR)

    if not os.path.isdir(src_dir):
        print(f"[mods] Pasta de mods nao encontrada: {src_dir}")
        return

    dst_dir = os.path.join(instance_path, "mods")
    os.makedirs(dst_dir, exist_ok=True)

    copied = 0
    for filename in os.listdir(src_dir):
        src_file = os.path.join(src_dir, filename)

        if os.path.isfile(src_file):
            shutil.copy2(src_file, os.path.join(dst_dir, filename))
            copied += 1

    print(f"[mods] {copied} mod(s) copiado(s) para {dst_dir}")


def install_neoforge(minecraft_directory):
    loaders = minecraft_launcher_lib.mod_loader.list_mod_loader()

    # procurar o neoforge
    neoforge_id = None
    for l in loaders:
        loader = minecraft_launcher_lib.mod_loader.get_mod_loader(l)
        if "neo" in loader.get_name().lower():
            neoforge_id = l
            break

    if not neoforge_id:
        raise Exception("NeoForge não encontrado na lista de mod loaders.")

    loader = minecraft_launcher_lib.mod_loader.get_mod_loader(neoforge_id)

    # pegar versões compatíveis
    versions = loader.get_minecraft_versions(True)

    if MINECRAFT_VERSION not in versions:
        raise Exception(f"NeoForge não suporta {MINECRAFT_VERSION}")

    print(f"[neoforge] Instalando para MC {MINECRAFT_VERSION}")

    installed_version = loader.install(
        MINECRAFT_VERSION,
        minecraft_directory,
        callback={"setStatus": print}
    )

    print(f"[neoforge] Instalado como: {installed_version}")

    return installed_version

# ─────────────────────────────────────────────────────────────────────────────
# LANÇAMENTO
# ─────────────────────────────────────────────────────────────────────────────

def launch_minecraft(minecraft_directory, installed_version, java_executable,
                     account, jvm_args_str=None) -> None:
    raw_args = jvm_args_str if jvm_args_str else "-Xmx4G -Xms2G"
    jvm_list = [a for a in raw_args.split() if a]

    options = {
        "jvmArguments": jvm_list,
        "username":     account["username"],
        "uuid":         account["uuid"],
        "token":        account["access_token"],
    }
    if java_executable:
        options["executablePath"] = java_executable

    print(f"Iniciando Minecraft como: {account['username']} | JVM: {jvm_list}")
    command = minecraft_launcher_lib.command.get_minecraft_command(
        installed_version, minecraft_directory, options
    )
    subprocess.run(command, cwd=minecraft_directory)


# ─────────────────────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────────────────────

def main():
    launcher_dir = os.path.dirname(os.path.abspath(__file__))

    # Tela de boas-vindas (se fechar aqui, o app encerra)
    if not show_welcome_screen():
        return

    while True:
        accounts, instances = load_data(launcher_dir)
        instances = validate_and_clean_instances(instances, launcher_dir, accounts)

        # 1. Fluxo de Conta
        account = get_account(launcher_dir, accounts, instances)
        if not account:
            # Se o usuário cancelou na seleção de conta, volta para a Welcome Screen ou encerra
            if not show_welcome_screen():
                break
            continue

        while True:  # Loop interno para permitir voltar da instância para a conta
            # 2. Fluxo de Instância
            instances = validate_and_clean_instances(instances, launcher_dir, accounts)
            if instances:
                choice = gui_choose_instance(instances, accounts, launcher_dir)
                if choice is None:
                    # Clicou em cancelar na instância? Volta para a seleção de conta
                    break 
                
                if choice == "__NEW__":
                    new_instance = create_new_instance(instances)
                    if new_instance is None:
                        continue # Volta para a lista de instâncias
                    instances.append(new_instance)
                    save_data(accounts, instances, launcher_dir)
                    instance = new_instance
                else:
                    instance = choice
            else:
                # Se não há instâncias, força a criação de uma
                new_instance = create_new_instance(instances)
                if new_instance is None:
                    break # Volta para a seleção de conta
                instances.append(new_instance)
                save_data(accounts, instances, launcher_dir)
                instance = new_instance

            # 3. Lançamento do Jogo
            minecraft_directory = instance["path"]
            minecraft_version   = instance["version"]

            print(f"Verificando instalação do jogo (v{minecraft_version})...")
            try:
                # Instala o Minecraft base
                minecraft_launcher_lib.install.install_minecraft_version(
                    MINECRAFT_VERSION,
                    minecraft_directory
                )

                # Instala NeoForge
                neoforge_id = install_neoforge(minecraft_directory)

                # Copia mods do modpack
                copy_modpack_mods(minecraft_directory, launcher_dir)

                # Inicia o jogo com NeoForge
                launch_minecraft(
                    minecraft_directory,
                    neoforge_id,
                    None,
                    account,
                    instance.get("jvm_args")
                )
                
                return
            except Exception as e:
                messagebox.showerror("Erro no Jogo", str(e))
                continue

if __name__ == "__main__":
    main()