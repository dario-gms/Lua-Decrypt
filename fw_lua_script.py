#!/usr/bin/env python3
"""
FW LUA Script — Forsaken World Lua 5.1 Bytecode Tool
Backends: unluac.jar (decrypt) + luac (encrypt)
"""

import sys, os, subprocess, tempfile, shutil, argparse, re
from pathlib import Path

# Suppress CMD window flash on Windows when spawning subprocesses
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

APP_NAME    = "FW LUA Script"
APP_VERSION = "2.0"
APP_YEAR    = "2026"

UNLUAC_JAR  = "unluac.jar"
LUAC_NAMES  = ["luac.exe", "luac5.1.exe", "luac", "luac5.1"]

LANG = {
    'en': {
        'tools': 'Tools:',
        'language': 'Language:',
        'decrypt_frame': '  Decrypt  (bytecode → source)',
        'encrypt_frame': '  Encrypt  (source → bytecode)',
        'input': 'Input:',
        'output': 'Output:',
        'browse': 'Browse',
        'preview': 'Preview',
        'close': 'Close',
        'decrypt_btn': '🔓  Decrypt',
        'batch_decrypt_btn': '📂  Batch Decrypt',
        'encrypt_btn': '🔒  Encrypt',
        'batch_encrypt_btn': '📂  Batch Encrypt',
        'clear_log': 'Clear log',
        'warning': 'Warning',
        'select_input': 'Please select an input file.',
        'preview_error': 'Preview Error',
        'preview_title': 'Preview — {filename}',
        'select_bytecode': 'Select bytecode file',
        'save_decrypted_as': 'Save decrypted file as',
        'select_source': 'Select source file',
        'save_encrypted_as': 'Save encrypted file as',
        'select_batch_input_decrypt': 'Select folder to batch decrypt',
        'select_batch_output_decrypt': 'Select output folder for decrypted files',
        'select_batch_input_encrypt': 'Select folder to batch encrypt',
        'select_batch_output_encrypt': 'Select output folder for encrypted files',
        'lua_files': 'Lua files',
        'all_files': 'All files',
        'decrypted_ok': '✓  Decrypted → {name}',
        'encrypted_ok': '✓  Encrypted → {name}  ({size} bytes)',
        'batch_decrypt_done': '✓  Batch decrypt finished: {success} succeeded, {fail} failed',
        'batch_encrypt_done': '✓  Batch encrypt finished: {success} succeeded, {fail} failed',
        'batch_more_errors': '… {count} more errors not shown',
        'missing_tools': '⚠  Missing tools — place them in the same folder as the program:',
        'all_tools_ok': '✓  All tools found. Ready to use.',
        'lines': 'lines',
        'drop_hint': 'Drag files here is supported',
        'drag_unavailable': 'Drag-and-drop unavailable (install tkinterdnd2 for support)',
    },
    'zh': {
        'tools': '工具:',
        'language': '语言:',
        'decrypt_frame': '  解密  （字节码 → 源码）',
        'encrypt_frame': '  加密  （源码 → 字节码）',
        'input': '输入:',
        'output': '输出:',
        'browse': '浏览',
        'preview': '预览',
        'close': '关闭',
        'decrypt_btn': '🔓  解密',
        'batch_decrypt_btn': '📂  批量解密',
        'encrypt_btn': '🔒  加密',
        'batch_encrypt_btn': '📂  批量加密',
        'clear_log': '清空日志',
        'warning': '提示',
        'select_input': '请选择输入文件。',
        'preview_error': '预览错误',
        'preview_title': '预览 — {filename}',
        'select_bytecode': '选择字节码文件',
        'save_decrypted_as': '另存解密文件为',
        'select_source': '选择源码文件',
        'save_encrypted_as': '另存加密文件为',
        'select_batch_input_decrypt': '选择要批量解密的文件夹',
        'select_batch_output_decrypt': '选择解密输出文件夹',
        'select_batch_input_encrypt': '选择要批量加密的文件夹',
        'select_batch_output_encrypt': '选择加密输出文件夹',
        'lua_files': 'Lua 文件',
        'all_files': '所有文件',
        'decrypted_ok': '✓  解密完成 → {name}',
        'encrypted_ok': '✓  加密完成 → {name}  （{size} 字节）',
        'batch_decrypt_done': '✓  批量解密完成：成功 {success} 个，失败 {fail} 个',
        'batch_encrypt_done': '✓  批量加密完成：成功 {success} 个，失败 {fail} 个',
        'batch_more_errors': '… 其余 {count} 个错误未显示',
        'missing_tools': '⚠  缺少工具 —— 请将它们放在程序同目录下：',
        'all_tools_ok': '✓  已找到所有工具，程序可以正常使用。',
        'lines': '行',
        'drop_hint': '支持拖拽文件到输入框',
        'drag_unavailable': '拖拽功能不可用（安装 tkinterdnd2 后可用）',
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL RESOLUTION
# ─────────────────────────────────────────────────────────────────────────────

def _search_dirs() -> list:
    """Return all candidate directories to search for bundled tools."""
    dirs = []
    meipass = getattr(sys, '_MEIPASS', None)
    if meipass:
        dirs.append(Path(meipass))
    if getattr(sys, 'frozen', False):
        dirs.append(Path(sys.executable).parent)
    dirs.append(Path(__file__).parent)
    dirs.append(Path(os.getcwd()))
    return dirs


def find_unluac() -> str | None:
    for folder in _search_dirs():
        p = folder / UNLUAC_JAR
        if p.is_file():
            return str(p)
    return None


def find_luac() -> str | None:
    for name in LUAC_NAMES:
        for folder in _search_dirs():
            p = folder / name
            if p.is_file():
                return str(p)
        found = shutil.which(name)
        if found:
            return found
    return None


def find_java() -> str | None:
    return shutil.which("java")


def tools_status() -> dict:
    return {
        "java":   find_java(),
        "unluac": find_unluac(),
        "luac":   find_luac(),
    }


# ─────────────────────────────────────────────────────────────────────────────
# AUTO OUTPUT PATH HELPERS
# ─────────────────────────────────────────────────────────────────────────────

def auto_decrypt_output(input_path: str) -> str:
    p = Path(input_path)
    return str(p.parent / f"{p.stem}_decrypted.lua")


def auto_encrypt_output(input_path: str) -> str:
    p = Path(input_path)
    stem = p.stem
    if stem.endswith('_decrypted'):
        stem = stem[:-len('_decrypted')]
    return str(p.parent / f"{stem}_encrypted.lua")


def decode_lua_escaped_utf8(text: str) -> str:
    pattern = re.compile(r'(?:\\\d{1,3})+')

    def repl(match):
        seq = match.group(0)
        nums = re.findall(r'\\(\d{1,3})', seq)
        try:
            values = [int(n) for n in nums]
            if any(v < 0 or v > 255 for v in values):
                return seq
            data = bytes(values)
            return data.decode('utf-8')
        except Exception:
            return seq

    return pattern.sub(repl, text)


# ─────────────────────────────────────────────────────────────────────────────
# CORE OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

def decrypt(input_path: str, output_path: str) -> str:
    st = tools_status()

    if not st["java"]:
        raise RuntimeError(
            "Java not found.\n"
            "Install Java (JRE 8+) and make sure it is on the system PATH.\n"
            "Download: https://adoptium.net"
        )
    if not st["unluac"]:
        raise RuntimeError(
            f"'{UNLUAC_JAR}' not found.\n"
            f"Place it in the same folder as this program.\n"
            f"Download: https://github.com/HansWessels/unluac/releases"
        )

    cmd = [st["java"], "-jar", st["unluac"], input_path]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30, creationflags=_NO_WINDOW)
    except subprocess.TimeoutExpired:
        raise RuntimeError("unluac timed out after 30 seconds — file may be corrupted.")
    except FileNotFoundError as e:
        raise RuntimeError(f"Failed to run java: {e}")

    if result.returncode != 0:
        err = result.stderr.decode('utf-8', errors='replace').strip()
        raise RuntimeError(
            f"unluac failed (code {result.returncode}).\n\n"
            f"Details:\n{err or '(no error message)'}\n\n"
            f"Possible cause: file is not valid Lua 5.1 bytecode."
        )

    source = result.stdout.decode('utf-8', errors='replace')
    source = decode_lua_escaped_utf8(source)
    Path(output_path).write_text(source, encoding='utf-8')
    return source


def encrypt(input_path: str, output_path: str) -> int:
    st = tools_status()

    if not st["luac"]:
        raise RuntimeError(
            "luac not found.\n"
            f"Place one of the following in the program folder: {', '.join(LUAC_NAMES)}\n\n"
            f"Download (Windows): https://luabinaries.sourceforge.net\n"
            f"Download (Linux):   sudo apt install lua5.1"
        )

    cmd = [st["luac"], "-o", output_path, input_path]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30, creationflags=_NO_WINDOW)
    except subprocess.TimeoutExpired:
        raise RuntimeError("luac timed out after 30 seconds.")
    except FileNotFoundError as e:
        raise RuntimeError(f"Failed to run luac: {e}")

    if result.returncode != 0:
        err = result.stderr.decode('utf-8', errors='replace').strip()
        raise RuntimeError(
            f"luac failed (code {result.returncode}).\n\n"
            f"Syntax error in source file:\n{err}"
        )

    return Path(output_path).stat().st_size


def batch_decrypt(input_dir: str, output_dir: str) -> tuple[int, int, list[str]]:
    in_root = Path(input_dir)
    out_root = Path(output_dir)

    if not in_root.exists() or not in_root.is_dir():
        raise RuntimeError("Input folder does not exist or is not a folder.")

    out_root.mkdir(parents=True, exist_ok=True)

    success = 0
    fail = 0
    errors = []

    for file in in_root.rglob("*"):
        if not file.is_file():
            continue
        if file.suffix.lower() not in [".lua", ".luac"]:
            continue

        rel_path = file.relative_to(in_root)
        out_dir = out_root / rel_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{file.stem}_decrypted.lua"

        try:
            decrypt(str(file), str(out_file))
            success += 1
        except Exception as e:
            fail += 1
            errors.append(f"{file}: {e}")

    return success, fail, errors


def batch_encrypt(input_dir: str, output_dir: str) -> tuple[int, int, list[str]]:
    in_root = Path(input_dir)
    out_root = Path(output_dir)

    if not in_root.exists() or not in_root.is_dir():
        raise RuntimeError("Input folder does not exist or is not a folder.")

    out_root.mkdir(parents=True, exist_ok=True)

    success = 0
    fail = 0
    errors = []

    for file in in_root.rglob("*"):
        if not file.is_file():
            continue
        if file.suffix.lower() != ".lua":
            continue

        rel_path = file.relative_to(in_root)
        out_dir = out_root / rel_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        stem = file.stem
        if stem.endswith('_decrypted'):
            stem = stem[:-len('_decrypted')]
        out_file = out_dir / f"{stem}_encrypted.lua"

        try:
            encrypt(str(file), str(out_file))
            success += 1
        except Exception as e:
            fail += 1
            errors.append(f"{file}: {e}")

    return success, fail, errors


# ─────────────────────────────────────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────────────────────────────────────

def gui_main():
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, scrolledtext
    except ImportError:
        print("tkinter not available. Use CLI instead.")
        return

    # optional drag and drop
    try:
        from tkinterdnd2 import TkinterDnD, DND_FILES
        RootClass = TkinterDnD.Tk
        drag_supported = True
    except Exception:
        RootClass = tk.Tk
        DND_FILES = None
        drag_supported = False

    def get_icon_path() -> str | None:
        for c in [Path(sys.executable).parent / 'icon.ico',
                  Path(__file__).parent / 'icon.ico',
                  Path(os.getcwd()) / 'icon.ico']:
            if c.exists():
                return str(c)
        return None

    root = RootClass()
    lang_var = tk.StringVar(value='zh')

    def tr(key: str, **kwargs) -> str:
        text = LANG[lang_var.get()][key]
        return text.format(**kwargs) if kwargs else text

    root.title(f"{APP_NAME}  v{APP_VERSION}")
    root.resizable(False, False)

    icon = get_icon_path()
    if icon:
        try:
            root.iconbitmap(icon)
        except Exception:
            pass

    try:
        w, h = 920, 560
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')
    except Exception:
        pass

    BG   = '#1e1e2e'
    FG   = '#cdd6f4'
    ACC  = '#89b4fa'
    PURP = '#cba6f7'
    SUB  = '#45475a'
    DARK = '#181825'
    OK   = '#a6e3a1'
    ERR  = '#f38ba8'
    WARN = '#fab387'
    MUTE = '#6c7086'
    TEAL = '#94e2d5'
    ORANGE = '#f9a826'

    root.configure(bg=BG)

    frm_title = tk.Frame(root, bg=DARK, pady=10)
    frm_title.pack(fill='x')

    if icon:
        try:
            from PIL import Image, ImageTk
            img = Image.open(icon).resize((28, 28))
            _img = ImageTk.PhotoImage(img)
            lbl_ico = tk.Label(frm_title, image=_img, bg=DARK)
            lbl_ico.image = _img
            lbl_ico.pack(side='left', padx=(16, 6))
        except Exception:
            pass

    tk.Label(frm_title, text=APP_NAME, bg=DARK, fg=ACC,
             font=('Segoe UI', 15, 'bold')).pack(side='left', padx=(16, 4))
    tk.Label(frm_title, text=f'v{APP_VERSION}', bg=DARK, fg=MUTE,
             font=('Segoe UI', 10)).pack(side='left', pady=4)

    tk.Label(frm_title, text='   ', bg=DARK).pack(side='left')

    lbl_lang = tk.Label(frm_title, text=tr('language'), bg=DARK, fg=FG,
                        font=('Segoe UI', 9))
    lbl_lang.pack(side='left', padx=(12, 4))

    lang_menu = tk.OptionMenu(frm_title, lang_var, 'en', 'zh')
    lang_menu.config(bg=SUB, fg=FG, activebackground=ACC, activeforeground=DARK,
                     relief='flat', highlightthickness=0, font=('Segoe UI', 8))
    lang_menu['menu'].config(bg=SUB, fg=FG, activebackground=ACC, activeforeground=DARK,
                             font=('Segoe UI', 8))
    lang_menu.pack(side='left')

    frm_tools = tk.Frame(root, bg='#12121c', pady=6, padx=16)
    frm_tools.pack(fill='x')

    lbl_tools = tk.Label(frm_tools, text=tr('tools'), bg='#12121c', fg=MUTE,
                         font=('Segoe UI', 8, 'bold'))
    lbl_tools.pack(side='left', padx=(0, 10))

    tool_dots = {}

    for name, display in [('java', 'Java'), ('unluac', 'unluac.jar'), ('luac', 'luac')]:
        frm = tk.Frame(frm_tools, bg='#12121c')
        frm.pack(side='left', padx=8)
        dot = tk.Label(frm, text='●', bg='#12121c', fg=MUTE, font=('Segoe UI', 9))
        dot.pack(side='left')
        tk.Label(frm, text=display, bg='#12121c', fg=FG,
                 font=('Segoe UI', 8)).pack(side='left', padx=(2, 0))
        tool_dots[name] = dot

    lbl_drop_hint = tk.Label(frm_tools,
                             text=tr('drop_hint') if drag_supported else tr('drag_unavailable'),
                             bg='#12121c', fg=MUTE, font=('Segoe UI', 8))
    lbl_drop_hint.pack(side='right')

    def refresh_tools():
        st = tools_status()
        for name, dot in tool_dots.items():
            dot.configure(fg=OK if st.get(name) else ERR)
        root.after(4000, refresh_tools)

    def parse_drop_path(data: str) -> str:
        if not data:
            return ''
        data = data.strip()
        if data.startswith('{') and data.endswith('}'):
            return data[1:-1]
        return data.split()[0]

    def register_drop(widget, setter, output_setter=None, mode='decrypt'):
        if not drag_supported:
            return
        try:
            widget.drop_target_register(DND_FILES)
            def on_drop(event):
                path = parse_drop_path(event.data)
                if not path:
                    return
                setter(path)
                p = Path(path)
                if output_setter and p.is_file():
                    if mode == 'decrypt':
                        output_setter(auto_decrypt_output(path))
                    elif mode == 'encrypt':
                        output_setter(auto_encrypt_output(path))
            widget.dnd_bind('<<Drop>>', on_drop)
        except Exception:
            pass

    def make_row(parent, label_key, var, browse_cmd, mode=None, output_var=None):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill='x', pady=3)

        lbl = tk.Label(row, text=tr(label_key), bg=BG, fg=FG, width=10,
                       font=('Segoe UI', 9), anchor='w')
        lbl.pack(side='left')

        ent = tk.Entry(row, textvariable=var, bg='#313244', fg=FG,
                       insertbackground=FG, relief='flat',
                       font=('Consolas', 9), bd=0, highlightthickness=1,
                       highlightbackground=SUB, highlightcolor=ACC)
        ent.pack(side='left', fill='x', expand=True, padx=(0, 4), ipady=4)

        btn = tk.Button(row, text=tr('browse'), bg=SUB, fg=FG, relief='flat',
                        font=('Segoe UI', 8), cursor='hand2',
                        activebackground=ACC, activeforeground=DARK,
                        command=browse_cmd)
        btn.pack(side='left', ipadx=6, ipady=3)

        if mode and output_var is not None:
            register_drop(ent, var.set, output_var.set, mode=mode)

        return {'label': lbl, 'entry': ent, 'button': btn}

    def open_preview(source: str, filename: str):
        win = tk.Toplevel(root)
        win.title(tr('preview_title', filename=filename))
        win.configure(bg='#181825')

        if icon:
            try:
                win.iconbitmap(icon)
            except Exception:
                pass

        try:
            pw, ph = 860, 660
            sw2, sh2 = win.winfo_screenwidth(), win.winfo_screenheight()
            win.geometry(f'{pw}x{ph}+{(sw2-pw)//2}+{(sh2-ph)//2}')
        except Exception:
            pass

        bar = tk.Frame(win, bg='#313244', pady=6, padx=10)
        bar.pack(fill='x')
        tk.Label(bar, text=f'  {filename}', bg='#313244', fg=FG,
                 font=('Segoe UI', 9, 'bold')).pack(side='left')
        tk.Label(bar, text=f'{source.count(chr(10)) + 1} {tr("lines")}',
                 bg='#313244', fg=MUTE, font=('Segoe UI', 8)).pack(side='left', padx=12)

        btn_close_preview = tk.Button(bar, text=tr('close'), bg=SUB, fg=FG, relief='flat',
                                      font=('Segoe UI', 8), cursor='hand2',
                                      command=win.destroy)
        btn_close_preview.pack(side='right', ipadx=8, ipady=2)

        txt = scrolledtext.ScrolledText(win, bg='#1e1e2e', fg=FG,
                                        font=('Microsoft YaHei UI', 10), relief='flat',
                                        wrap='none', bd=0,
                                        insertbackground=FG,
                                        selectbackground='#45475a')
        txt.pack(fill='both', expand=True)

        txt.tag_config('kw',  foreground='#cba6f7')
        txt.tag_config('str', foreground='#a6e3a1')
        txt.tag_config('num', foreground='#fab387')
        txt.tag_config('com', foreground='#6c7086')

        keywords = {'function','end','return','local','if','then','else','elseif',
                    'for','while','do','repeat','until','break','not','and','or',
                    'true','false','nil','in'}

        def highlight(code: str):
            i = 0
            n = len(code)
            while i < n:
                c = code[i]
                if code[i:i+2] == '--':
                    j = code.find('\n', i)
                    j = j if j != -1 else n
                    txt.insert('end', code[i:j], 'com')
                    i = j
                    continue
                if c in ('"', "'"):
                    j = i + 1
                    while j < n:
                        if code[j] == '\\':
                            j += 2
                            continue
                        if code[j] == c:
                            break
                        j += 1
                    txt.insert('end', code[i:j+1], 'str')
                    i = j + 1
                    continue
                if c.isdigit():
                    j = i
                    while j < n and (code[j].isdigit() or code[j] in '.eExX'):
                        j += 1
                    txt.insert('end', code[i:j], 'num')
                    i = j
                    continue
                if c.isalpha() or c == '_':
                    j = i
                    while j < n and (code[j].isalnum() or code[j] == '_'):
                        j += 1
                    word = code[i:j]
                    txt.insert('end', word, 'kw' if word in keywords else '')
                    i = j
                    continue
                txt.insert('end', c)
                i += 1

        highlight(source)
        txt.configure(state='disabled')

    frm_dec = tk.LabelFrame(root, text=tr('decrypt_frame'),
                            bg=BG, fg=ACC, font=('Segoe UI', 9, 'bold'),
                            padx=14, pady=10, bd=1, relief='groove')
    frm_dec.pack(fill='x', padx=16, pady=(12, 6))

    var_dec_in  = tk.StringVar()
    var_dec_out = tk.StringVar()

    def browse_dec_in():
        path = filedialog.askopenfilename(
            title=tr('select_bytecode'),
            filetypes=[(tr('lua_files'), '*.lua *.luac'), (tr('all_files'), '*.*')])
        if path:
            var_dec_in.set(path)
            var_dec_out.set(auto_decrypt_output(path))

    def browse_dec_out():
        path = filedialog.asksaveasfilename(
            title=tr('save_decrypted_as'),
            defaultextension='.lua',
            filetypes=[(tr('lua_files'), '*.lua')])
        if path:
            var_dec_out.set(path)

    dec_row_in = make_row(frm_dec, 'input', var_dec_in, browse_dec_in, mode='decrypt', output_var=var_dec_out)
    dec_row_out = make_row(frm_dec, 'output', var_dec_out, browse_dec_out)

    def do_preview():
        inp = var_dec_in.get().strip()
        if not inp:
            messagebox.showwarning(tr('warning'), tr('select_input'), parent=root)
            return
        try:
            with tempfile.NamedTemporaryFile(suffix='.lua', delete=False) as tmp:
                tmp_path = tmp.name
            source = decrypt(inp, tmp_path)
            Path(tmp_path).unlink(missing_ok=True)
            open_preview(source, Path(inp).name)
        except Exception as e:
            messagebox.showerror(tr('preview_error'), str(e), parent=root)

    btn_preview = tk.Button(frm_dec, text=tr('preview'), bg=SUB, fg=FG,
                            relief='flat', font=('Segoe UI', 8), cursor='hand2',
                            activebackground=ACC, activeforeground=DARK,
                            command=do_preview)
    btn_preview.pack(anchor='e', ipadx=8, ipady=3, pady=(4, 0))

    frm_enc = tk.LabelFrame(root, text=tr('encrypt_frame'),
                            bg=BG, fg=PURP, font=('Segoe UI', 9, 'bold'),
                            padx=14, pady=10, bd=1, relief='groove')
    frm_enc.pack(fill='x', padx=16, pady=(6, 6))

    var_enc_in  = tk.StringVar()
    var_enc_out = tk.StringVar()

    def browse_enc_in():
        path = filedialog.askopenfilename(
            title=tr('select_source'),
            filetypes=[(tr('lua_files'), '*.lua'), (tr('all_files'), '*.*')])
        if path:
            var_enc_in.set(path)
            var_enc_out.set(auto_encrypt_output(path))

    def browse_enc_out():
        path = filedialog.asksaveasfilename(
            title=tr('save_encrypted_as'),
            defaultextension='.lua',
            filetypes=[(tr('lua_files'), '*.lua')])
        if path:
            var_enc_out.set(path)

    enc_row_in = make_row(frm_enc, 'input', var_enc_in, browse_enc_in, mode='encrypt', output_var=var_enc_out)
    enc_row_out = make_row(frm_enc, 'output', var_enc_out, browse_enc_out)

    frm_btn = tk.Frame(root, bg=BG)
    frm_btn.pack(fill='x', padx=16, pady=8)

    log = scrolledtext.ScrolledText(root, height=6, bg=DARK, fg=FG,
                                    font=('Consolas', 9), relief='flat',
                                    state='disabled', bd=0)
    log.pack(fill='both', expand=True, padx=16, pady=(0, 4))
    log.tag_config('ok',   foreground=OK)
    log.tag_config('err',  foreground=ERR)
    log.tag_config('inf',  foreground=ACC)
    log.tag_config('warn', foreground=WARN)

    def log_write(msg, tag='inf'):
        log.configure(state='normal')
        log.insert('end', msg + '\n', tag)
        log.see('end')
        log.configure(state='disabled')

    def do_decrypt():
        inp = var_dec_in.get().strip()
        out = var_dec_out.get().strip()
        if not inp:
            messagebox.showwarning(tr('warning'), tr('select_input'), parent=root)
            return
        if not out:
            out = auto_decrypt_output(inp)
            var_dec_out.set(out)
        try:
            decrypt(inp, out)
            log_write(tr('decrypted_ok', name=Path(out).name), 'ok')
        except Exception as e:
            log_write(f'✗  {e}', 'err')

    def do_batch_decrypt():
        input_dir = filedialog.askdirectory(title=tr('select_batch_input_decrypt'))
        if not input_dir:
            return
        output_dir = filedialog.askdirectory(title=tr('select_batch_output_decrypt'))
        if not output_dir:
            return

        try:
            success, fail, errors = batch_decrypt(input_dir, output_dir)
            log_write(tr('batch_decrypt_done', success=success, fail=fail), 'ok')
            for err in errors[:10]:
                log_write(f'✗  {err}', 'err')
            if len(errors) > 10:
                log_write(tr('batch_more_errors', count=len(errors) - 10), 'warn')
        except Exception as e:
            log_write(f'✗  {e}', 'err')

    def do_encrypt():
        inp = var_enc_in.get().strip()
        out = var_enc_out.get().strip()
        if not inp:
            messagebox.showwarning(tr('warning'), tr('select_input'), parent=root)
            return
        if not out:
            out = auto_encrypt_output(inp)
            var_enc_out.set(out)
        try:
            size = encrypt(inp, out)
            log_write(tr('encrypted_ok', name=Path(out).name, size=size), 'ok')
        except Exception as e:
            log_write(f'✗  {e}', 'err')

    def do_batch_encrypt():
        input_dir = filedialog.askdirectory(title=tr('select_batch_input_encrypt'))
        if not input_dir:
            return
        output_dir = filedialog.askdirectory(title=tr('select_batch_output_encrypt'))
        if not output_dir:
            return

        try:
            success, fail, errors = batch_encrypt(input_dir, output_dir)
            log_write(tr('batch_encrypt_done', success=success, fail=fail), 'ok')
            for err in errors[:10]:
                log_write(f'✗  {err}', 'err')
            if len(errors) > 10:
                log_write(tr('batch_more_errors', count=len(errors) - 10), 'warn')
        except Exception as e:
            log_write(f'✗  {e}', 'err')

    btn_cfg = dict(relief='flat', cursor='hand2',
                   font=('Segoe UI', 10, 'bold'), pady=6, padx=16)

    btn_decrypt = tk.Button(frm_btn, text=tr('decrypt_btn'), bg=ACC, fg=DARK,
                            activebackground='#74c7ec', activeforeground=DARK,
                            command=do_decrypt, **btn_cfg)
    btn_decrypt.pack(side='left', padx=(0, 10))

    btn_batch_decrypt = tk.Button(frm_btn, text=tr('batch_decrypt_btn'), bg=TEAL, fg=DARK,
                                  activebackground='#74c7ec', activeforeground=DARK,
                                  command=do_batch_decrypt, **btn_cfg)
    btn_batch_decrypt.pack(side='left', padx=(0, 10))

    btn_encrypt = tk.Button(frm_btn, text=tr('encrypt_btn'), bg=PURP, fg=DARK,
                            activebackground='#b4befe', activeforeground=DARK,
                            command=do_encrypt, **btn_cfg)
    btn_encrypt.pack(side='left', padx=(0, 10))

    btn_batch_encrypt = tk.Button(frm_btn, text=tr('batch_encrypt_btn'), bg=ORANGE, fg=DARK,
                                  activebackground='#fab387', activeforeground=DARK,
                                  command=do_batch_encrypt, **btn_cfg)
    btn_batch_encrypt.pack(side='left')

    def clear_log():
        log.configure(state='normal')
        log.delete('1.0', 'end')
        log.configure(state='disabled')

    btn_clear = tk.Button(frm_btn, text=tr('clear_log'), bg=SUB, fg=FG,
                          activebackground='#585b70', activeforeground=FG,
                          relief='flat', cursor='hand2', font=('Segoe UI', 9),
                          command=clear_log)
    btn_clear.pack(side='right')

    def startup_check():
        refresh_tools()
        st = tools_status()
        missing = []

        if lang_var.get() == 'zh':
            if not st['java']:
                missing.append("  • Java（JRE 8+）   →  https://adoptium.net")
            if not st['unluac']:
                missing.append(f"  • {UNLUAC_JAR}  →  https://github.com/HansWessels/unluac/releases")
            if not st['luac']:
                missing.append("  • luac.exe         →  https://luabinaries.sourceforge.net  （Windows）")
                missing.append("                        sudo apt install lua5.1               （Linux）")
        else:
            if not st['java']:
                missing.append("  • Java (JRE 8+)    →  https://adoptium.net")
            if not st['unluac']:
                missing.append(f"  • {UNLUAC_JAR}  →  https://github.com/HansWessels/unluac/releases")
            if not st['luac']:
                missing.append("  • luac.exe          →  https://luabinaries.sourceforge.net  (Windows)")
                missing.append("                          sudo apt install lua5.1              (Linux)")

        clear_log()
        if missing:
            log_write(tr('missing_tools'), 'warn')
            for line in missing:
                log_write(line, 'warn')
        else:
            log_write(tr('all_tools_ok'), 'ok')

    def refresh_language(*args):
        lbl_tools.config(text=tr('tools'))
        lbl_lang.config(text=tr('language'))
        lbl_drop_hint.config(text=tr('drop_hint') if drag_supported else tr('drag_unavailable'))

        frm_dec.config(text=tr('decrypt_frame'))
        frm_enc.config(text=tr('encrypt_frame'))

        dec_row_in['label'].config(text=tr('input'))
        dec_row_out['label'].config(text=tr('output'))
        enc_row_in['label'].config(text=tr('input'))
        enc_row_out['label'].config(text=tr('output'))

        dec_row_in['button'].config(text=tr('browse'))
        dec_row_out['button'].config(text=tr('browse'))
        enc_row_in['button'].config(text=tr('browse'))
        enc_row_out['button'].config(text=tr('browse'))

        btn_preview.config(text=tr('preview'))
        btn_decrypt.config(text=tr('decrypt_btn'))
        btn_batch_decrypt.config(text=tr('batch_decrypt_btn'))
        btn_encrypt.config(text=tr('encrypt_btn'))
        btn_batch_encrypt.config(text=tr('batch_encrypt_btn'))
        btn_clear.config(text=tr('clear_log'))

        startup_check()

    lang_var.trace_add('write', refresh_language)

    tk.Label(root, text=f'{APP_NAME}  v{APP_VERSION}  •  {APP_YEAR}',
             bg=DARK, fg=MUTE, font=('Segoe UI', 8)).pack(
             fill='x', pady=4, side='bottom')

    root.after(150, startup_check)
    root.mainloop()


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────

def main():
    if len(sys.argv) == 1:
        gui_main()
        return

    p = argparse.ArgumentParser(
        description=f'{APP_NAME} v{APP_VERSION} — Forsaken World Lua 5.1 Bytecode Tool\n'
                    f'Decrypt: unluac.jar   |   Encrypt: luac',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest='cmd')

    d = sub.add_parser('decrypt', help='Bytecode -> readable source  (uses unluac.jar)')
    d.add_argument('input')
    d.add_argument('-o', '--output', default=None)

    e = sub.add_parser('encrypt', help='Readable source -> bytecode  (uses luac)')
    e.add_argument('input')
    e.add_argument('-o', '--output', default=None)

    sub.add_parser('status', help='Check if all required tools are available')

    args = p.parse_args()

    if args.cmd == 'status':
        st = tools_status()
        for name, path in st.items():
            print(f"  {name:10s}  {'OK  -> ' + path if path else 'NOT FOUND'}")
        sys.exit(0 if all(st.values()) else 1)

    elif args.cmd == 'decrypt':
        out = args.output or auto_decrypt_output(args.input)
        try:
            decrypt(args.input, out)
            print(f'[OK] Decrypted -> {out}')
        except RuntimeError as e:
            print(f'[ERROR] {e}', file=sys.stderr)
            sys.exit(1)

    elif args.cmd == 'encrypt':
        out = args.output or auto_encrypt_output(args.input)
        try:
            size = encrypt(args.input, out)
            print(f'[OK] Encrypted -> {out}  ({size} bytes)')
        except RuntimeError as e:
            print(f'[ERROR] {e}', file=sys.stderr)
            sys.exit(1)

    else:
        p.print_help()


if __name__ == '__main__':
    main()
