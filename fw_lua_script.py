#!/usr/bin/env python3
"""
FW LUA Script — Lua Bytecode Tool (multi-version)
Backends: unluac.jar (decrypt) + luac (encrypt)
Supported: Lua 1.0 – 5.5  (auto-detect via bytecode header)

Version notes:
  • Lua 1.x / 2.x / 3.x  — very old formats; unluac support is limited/absent.
    Use version-specific decompilers (e.g. luadec) for those.
  • Lua 4.0               — unluac has partial support.
  • Lua 5.0 – 5.4         — fully supported by unluac.
  • Lua 5.5               — in development; support depends on unluac version.
"""

import sys, os, subprocess, tempfile, shutil, argparse, re
from pathlib import Path

# Suppress CMD window flash on Windows when spawning subprocesses
_NO_WINDOW = subprocess.CREATE_NO_WINDOW if sys.platform == 'win32' else 0


# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTS
# ─────────────────────────────────────────────────────────────────────────────

APP_NAME    = "FW LUA Script"
APP_VERSION = "3.0"
APP_YEAR    = "2026"

UNLUAC_JAR  = "unluac.jar"

# ── All Lua versions this tool exposes ───────────────────────────────────────
# Versions 1.x / 2.x / 3.x have very different bytecode formats and may not
# be supported by unluac; they are included so the user can select them and
# attempt decryption with a compatible unluac build or external tool.
LUA_VERSIONS = [
    '1.0', '1.1',
    '2.1', '2.2', '2.4', '2.5',
    '3.0', '3.1', '3.2',
    '4.0',
    '5.0', '5.1', '5.2', '5.3', '5.4', '5.5',
]
LUA_VERSIONS_DECRYPT = ['auto'] + LUA_VERSIONS   # 'auto' = let unluac detect
LUA_DEFAULT_ENCRYPT  = '5.1'
LUA_DEFAULT_DECRYPT  = 'auto'

# Versions that unluac.jar is known to handle well
LUA_UNLUAC_SUPPORTED = {'5.0', '5.1', '5.2', '5.3', '5.4'}
# Versions with partial / experimental unluac support
LUA_UNLUAC_PARTIAL   = {'4.0', '5.5'}

# ── Bytecode magic bytes ──────────────────────────────────────────────────────
# All Lua versions since 1.0 start with the 4-byte signature \x1bLua.
# The 5th byte encodes the version (major*16 + minor in hex):
#   0x10 = 1.0,  0x11 = 1.1
#   0x21 = 2.1,  0x22 = 2.2,  0x24 = 2.4,  0x25 = 2.5
#   0x30 = 3.0,  0x31 = 3.1,  0x32 = 3.2
#   0x40 = 4.0
#   0x50 = 5.0,  0x51 = 5.1 … 0x55 = 5.5
# Note: Lua 1.x/2.x/3.x also used \x1bLua but their overall chunk format
# is very different from 5.x.  Detection still works off byte 4.
LUA_MAGIC = b'\x1bLua'
LUA_VERSION_BYTES: dict[int, str] = {
    0x10: '1.0',
    0x11: '1.1',
    0x21: '2.1',
    0x22: '2.2',
    0x24: '2.4',
    0x25: '2.5',
    0x30: '3.0',
    0x31: '3.1',
    0x32: '3.2',
    0x40: '4.0',
    0x50: '5.0',
    0x51: '5.1',
    0x52: '5.2',
    0x53: '5.3',
    0x54: '5.4',
    0x55: '5.5',
}

def _luac_names_for(version: str) -> list[str]:
    """
    Return candidate luac binary names for a given Lua version string.
    Handles all versions from 1.0 to 5.5, including unusual ones like 2.4.
    """
    v = version.replace('.', '')   # "5.1" → "51",  "2.4" → "24"
    return [
        f"luac{version}.exe",      # luac5.1.exe  / luac2.4.exe
        f"luac{v}.exe",            # luac51.exe   / luac24.exe
        f"luac{version}",          # luac5.1      / luac2.4
        f"luac{v}",                # luac51       / luac24
        "luac.exe",                # generic fallback
        "luac",
    ]

def _unluac_support_note(version: str) -> str:
    """Return a human-readable note about unluac support for the given version."""
    if version in LUA_UNLUAC_SUPPORTED:
        return ""
    if version in LUA_UNLUAC_PARTIAL:
        return (
            f"\nNote: Lua {version} has partial unluac support. "
            "Results may be incomplete."
        )
    major = version.split('.')[0]
    if int(major) < 5:
        return (
            f"\nNote: Lua {version} predates unluac's supported range. "
            "unluac may fail. Consider using luadec or a version-specific tool."
        )
    return ""

LANG = {
    'en': {
        'tools': 'Tools:',
        'language': 'Language:',
        'lua_version': 'Lua Version:',
        'version_auto': 'Auto-detect',
        'detect_btn': 'Detect',
        'detected_ver': '● Detected Lua {version}',
        'unknown_ver': '● Version unknown (not Lua bytecode?)',
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
        'decrypted_ok': '✓  Decrypted → {name}  [Lua {version}]',
        'encrypted_ok': '✓  Encrypted → {name}  ({size} bytes)  [Lua {version}]',
        'batch_decrypt_done': '✓  Batch decrypt finished: {success} succeeded, {fail} failed',
        'batch_encrypt_done': '✓  Batch encrypt finished: {success} succeeded, {fail} failed',
        'batch_more_errors': '… {count} more errors not shown',
        'missing_tools': '⚠  Missing tools — place them in the same folder as the program:',
        'all_tools_ok': '✓  All tools found. Ready to use.',
        'lines': 'lines',
        'drop_hint': 'Drag files here is supported',
        'drag_unavailable': 'Drag-and-drop unavailable (install tkinterdnd2 for support)',
        'luac_not_found_ver': (
            'luac not found for Lua {version}.\n'
            'Place one of these in the program folder: {names}\n\n'
            'Download (Windows): https://luabinaries.sourceforge.net\n'
            'Download (Linux):   sudo apt install lua{version}'
        ),
        'decrypt_version_note': (
            'Possible cause: file is not valid Lua bytecode, or\n'
            'unluac does not support this Lua version.\n'
            'Try a different version in the dropdown.'
        ),
    },
    'zh': {
        'tools': '工具:',
        'language': '语言:',
        'lua_version': 'Lua 版本:',
        'version_auto': '自动检测',
        'detect_btn': '检测',
        'detected_ver': '● 检测到 Lua {version}',
        'unknown_ver': '● 版本未知（不是 Lua 字节码？）',
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
        'decrypted_ok': '✓  解密完成 → {name}  [Lua {version}]',
        'encrypted_ok': '✓  加密完成 → {name}  （{size} 字节）  [Lua {version}]',
        'batch_decrypt_done': '✓  批量解密完成：成功 {success} 个，失败 {fail} 个',
        'batch_encrypt_done': '✓  批量加密完成：成功 {success} 个，失败 {fail} 个',
        'batch_more_errors': '… 其余 {count} 个错误未显示',
        'missing_tools': '⚠  缺少工具 —— 请将它们放在程序同目录下：',
        'all_tools_ok': '✓  已找到所有工具，程序可以正常使用。',
        'lines': '行',
        'drop_hint': '支持拖拽文件到输入框',
        'drag_unavailable': '拖拽功能不可用（安装 tkinterdnd2 后可用）',
        'luac_not_found_ver': (
            '未找到 Lua {version} 的 luac。\n'
            '请将以下文件之一放在程序目录：{names}\n\n'
            '下载（Windows）：https://luabinaries.sourceforge.net\n'
            '下载（Linux）：  sudo apt install lua{version}'
        ),
        'decrypt_version_note': (
            '可能原因：文件不是有效的 Lua 字节码，或\n'
            'unluac 不支持该 Lua 版本。\n'
            '请在下拉菜单中尝试其他版本。'
        ),
    }
}


# ─────────────────────────────────────────────────────────────────────────────
# TOOL RESOLUTION
# ─────────────────────────────────────────────────────────────────────────────

def _search_dirs() -> list[Path]:
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


def find_luac(version: str = LUA_DEFAULT_ENCRYPT) -> str | None:
    """
    Search for a luac binary matching the requested Lua version.

    Search order (per candidate name):
      1. All _search_dirs() — bundled / portable binaries
      2. System PATH via shutil.which
    Returns the first match found, or None.
    """
    for name in _luac_names_for(version):
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


def tools_status(lua_version: str = LUA_DEFAULT_ENCRYPT) -> dict:
    return {
        "java":   find_java(),
        "unluac": find_unluac(),
        "luac":   find_luac(lua_version),
    }


# ─────────────────────────────────────────────────────────────────────────────
# VERSION DETECTION
# ─────────────────────────────────────────────────────────────────────────────

def detect_lua_version(path: str) -> str | None:
    """
    Read the first 5 bytes of a file and return the Lua version string
    (e.g. '5.1') if it looks like valid Lua bytecode, or None otherwise.
    """
    try:
        with open(path, 'rb') as f:
            header = f.read(5)
        if len(header) >= 5 and header[:4] == LUA_MAGIC:
            return LUA_VERSION_BYTES.get(header[4])
    except Exception:
        pass
    return None


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
    pattern = re.compile(r'(?:\\\\d{1,3})+')

    def repl(match):
        seq = match.group(0)
        nums = re.findall(r'\\(\\d{1,3})', seq)
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
# UNLUAC CAPABILITY PROBE
# ─────────────────────────────────────────────────────────────────────────────

_unluac_version_flag_cache: dict[str, bool] = {}

def _unluac_supports_version_flag(java: str, jar: str) -> bool:
    """
    Return True if this unluac build accepts a --version <ver> flag.

    Some older builds (e.g. v1.2.2.155) only auto-detect the version from
    the bytecode header and do not accept --version at all.  We probe by
    passing '--version 5.1' with no input file and checking whether the error
    output contains 'unrecognized option' (flag unsupported) vs something else
    (flag accepted but file missing — meaning it IS supported).
    """
    key = jar
    if key in _unluac_version_flag_cache:
        return _unluac_version_flag_cache[key]

    try:
        probe = subprocess.run(
            [java, "-jar", jar, "--version", "5.1"],
            capture_output=True, timeout=10,
            creationflags=_NO_WINDOW,
        )
        stderr = probe.stderr.decode('utf-8', errors='replace').lower()
        stdout = probe.stdout.decode('utf-8', errors='replace').lower()
        combined = stderr + stdout
        supported = 'unrecognized option' not in combined
    except Exception:
        supported = False

    _unluac_version_flag_cache[key] = supported
    return supported


# ─────────────────────────────────────────────────────────────────────────────
# CORE OPERATIONS
# ─────────────────────────────────────────────────────────────────────────────

def decrypt(input_path: str, output_path: str,
            lua_version: str = LUA_DEFAULT_DECRYPT) -> tuple[str, str]:
    """
    Decompile Lua bytecode to source using unluac.jar.

    Parameters
    ----------
    lua_version : 'auto' or a version string like '5.1', '5.3', etc.
        When 'auto', unluac detects the version from the bytecode header.
        When explicit, passes --version <lua_version> to unluac.

    Returns
    -------
    (source_text, resolved_version)
        resolved_version is the detected or requested version string.
    """
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

    # Detect version from header for reporting, even in auto mode
    detected = detect_lua_version(input_path)
    resolved_version = detected or lua_version

    # unluac auto-detects the Lua version from the bytecode header.
    # Older builds (e.g. v1.2.2.155) do not accept a --version flag at all,
    # so we probe support once and cache the result.
    cmd = [st["java"], "-jar", st["unluac"]]
    if lua_version != 'auto' and _unluac_supports_version_flag(st["java"], st["unluac"]):
        cmd += ["--version", lua_version]
    cmd.append(input_path)

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30,
                                creationflags=_NO_WINDOW)
    except subprocess.TimeoutExpired:
        raise RuntimeError("unluac timed out after 30 seconds — file may be corrupted.")
    except FileNotFoundError as e:
        raise RuntimeError(f"Failed to run java: {e}")

    if result.returncode != 0:
        err  = result.stderr.decode('utf-8', errors='replace').strip()
        note = _unluac_support_note(resolved_version if resolved_version != 'unknown' else lua_version)
        raise RuntimeError(
            f"unluac failed (code {result.returncode}).\n\n"
            f"Details:\n{err or '(no error message)'}\n\n"
            f"Possible cause: file is not valid Lua bytecode, or\n"
            f"unluac does not support Lua {resolved_version}.\n"
            f"Try a different version in the dropdown."
            + note
        )

    source = result.stdout.decode('utf-8', errors='replace')
    source = decode_lua_escaped_utf8(source)
    Path(output_path).write_text(source, encoding='utf-8')
    return source, resolved_version or 'unknown'


def encrypt(input_path: str, output_path: str,
            lua_version: str = LUA_DEFAULT_ENCRYPT) -> tuple[int, str]:
    """
    Compile Lua source to bytecode using luac.

    Returns (file_size_bytes, lua_version_used).
    """
    luac = find_luac(lua_version)

    if not luac:
        names_str = ', '.join(_luac_names_for(lua_version)[:4])
        raise RuntimeError(
            f"luac not found for Lua {lua_version}.\n"
            f"Place one of these in the program folder: {names_str}\n\n"
            f"Download (Windows): https://luabinaries.sourceforge.net\n"
            f"Download (Linux):   sudo apt install lua{lua_version}"
        )

    cmd = [luac, "-o", output_path, input_path]

    try:
        result = subprocess.run(cmd, capture_output=True, timeout=30,
                                creationflags=_NO_WINDOW)
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

    return Path(output_path).stat().st_size, lua_version


def batch_decrypt(input_dir: str, output_dir: str,
                  lua_version: str = LUA_DEFAULT_DECRYPT) -> tuple[int, int, list[str]]:
    in_root  = Path(input_dir)
    out_root = Path(output_dir)

    if not in_root.exists() or not in_root.is_dir():
        raise RuntimeError("Input folder does not exist or is not a folder.")

    out_root.mkdir(parents=True, exist_ok=True)

    success = fail = 0
    errors: list[str] = []

    for file in in_root.rglob("*"):
        if not file.is_file():
            continue
        if file.suffix.lower() not in [".lua", ".luac"]:
            continue

        rel_path = file.relative_to(in_root)
        out_dir  = out_root / rel_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)
        out_file = out_dir / f"{file.stem}_decrypted.lua"

        try:
            decrypt(str(file), str(out_file), lua_version)
            success += 1
        except Exception as e:
            fail += 1
            errors.append(f"{file}: {e}")

    return success, fail, errors


def batch_encrypt(input_dir: str, output_dir: str,
                  lua_version: str = LUA_DEFAULT_ENCRYPT) -> tuple[int, int, list[str]]:
    in_root  = Path(input_dir)
    out_root = Path(output_dir)

    if not in_root.exists() or not in_root.is_dir():
        raise RuntimeError("Input folder does not exist or is not a folder.")

    out_root.mkdir(parents=True, exist_ok=True)

    success = fail = 0
    errors: list[str] = []

    for file in in_root.rglob("*"):
        if not file.is_file():
            continue
        if file.suffix.lower() != ".lua":
            continue

        rel_path = file.relative_to(in_root)
        out_dir  = out_root / rel_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        stem = file.stem
        if stem.endswith('_decrypted'):
            stem = stem[:-len('_decrypted')]
        out_file = out_dir / f"{stem}_encrypted.lua"

        try:
            encrypt(str(file), str(out_file), lua_version)
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
        RootClass    = TkinterDnD.Tk
        drag_supported = True
    except Exception:
        RootClass    = tk.Tk
        DND_FILES    = None
        drag_supported = False

    def get_icon_path() -> str | None:
        for c in [Path(sys.executable).parent / 'icon.ico',
                  Path(__file__).parent / 'icon.ico',
                  Path(os.getcwd()) / 'icon.ico']:
            if c.exists():
                return str(c)
        return None

    root = RootClass()
    lang_var = tk.StringVar(value='en')

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
        w, h = 960, 620
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f'{w}x{h}+{(sw-w)//2}+{(sh-h)//2}')
    except Exception:
        pass

    BG     = '#1e1e2e'
    FG     = '#cdd6f4'
    ACC    = '#89b4fa'
    PURP   = '#cba6f7'
    SUB    = '#45475a'
    DARK   = '#181825'
    OK     = '#a6e3a1'
    ERR    = '#f38ba8'
    WARN   = '#fab387'
    MUTE   = '#6c7086'
    TEAL   = '#94e2d5'
    ORANGE = '#f9a826'
    PINK   = '#f5c2e7'

    root.configure(bg=BG)

    # ── Title bar ────────────────────────────────────────────────────────────
    frm_title = tk.Frame(root, bg=DARK, pady=10)
    frm_title.pack(fill='x')

    if icon:
        try:
            from PIL import Image, ImageTk
            img  = Image.open(icon).resize((28, 28))
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

    # ── Tool status bar ───────────────────────────────────────────────────────
    frm_tools = tk.Frame(root, bg='#12121c', pady=6, padx=16)
    frm_tools.pack(fill='x')

    lbl_tools = tk.Label(frm_tools, text=tr('tools'), bg='#12121c', fg=MUTE,
                         font=('Segoe UI', 8, 'bold'))
    lbl_tools.pack(side='left', padx=(0, 10))

    tool_dots: dict[str, tk.Label] = {}

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

    # version variable for luac status check
    _enc_ver_for_status = [LUA_DEFAULT_ENCRYPT]

    def refresh_tools():
        ver = _enc_ver_for_status[0]
        st  = tools_status(ver)
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

    def make_version_row(parent, label_key, ver_var, choices,
                         accent_color, show_detect=False, detect_input_var=None):
        """Create a Lua Version selector row with optional Detect button."""
        row = tk.Frame(parent, bg=BG)
        row.pack(fill='x', pady=(2, 4))

        lbl = tk.Label(row, text=tr(label_key), bg=BG, fg=FG, width=10,
                       font=('Segoe UI', 9), anchor='w')
        lbl.pack(side='left')

        # Build display labels: 'auto' → 'Auto-detect', others unchanged
        def display_for(v):
            return tr('version_auto') if v == 'auto' else f'Lua {v}'

        display_var = tk.StringVar(value=display_for(ver_var.get()))

        def on_display_change(*_):
            raw = display_var.get()
            if raw == tr('version_auto'):
                ver_var.set('auto')
            else:
                ver_var.set(raw.replace('Lua ', ''))
            # update luac status if this is the encrypt row
            if not show_detect:
                _enc_ver_for_status[0] = ver_var.get()

        display_var.trace_add('write', on_display_change)

        display_choices = [display_for(c) for c in choices]
        om = tk.OptionMenu(row, display_var, *display_choices)
        om.config(bg='#313244', fg=accent_color, activebackground=accent_color,
                  activeforeground=DARK, relief='flat', highlightthickness=1,
                  highlightbackground=SUB, font=('Segoe UI', 9), width=12)
        om['menu'].config(bg='#313244', fg=accent_color,
                          activebackground=accent_color, activeforeground=DARK,
                          font=('Segoe UI', 9))
        om.pack(side='left', padx=(0, 6))

        detect_lbl = None
        if show_detect and detect_input_var is not None:
            btn_detect = tk.Button(
                row, text=tr('detect_btn'), bg=SUB, fg=FG, relief='flat',
                font=('Segoe UI', 8), cursor='hand2',
                activebackground=TEAL, activeforeground=DARK)
            btn_detect.pack(side='left', ipadx=6, ipady=2, padx=(0, 8))

            detect_lbl = tk.Label(row, text='', bg=BG, fg=TEAL,
                                  font=('Segoe UI', 8))
            detect_lbl.pack(side='left')

            def do_detect():
                path = detect_input_var.get().strip()
                if not path:
                    detect_lbl.config(text=tr('select_input'), fg=WARN)
                    return
                ver = detect_lua_version(path)
                if ver:
                    detect_lbl.config(
                        text=tr('detected_ver', version=ver), fg=TEAL)
                    display_var.set(display_for(ver))
                else:
                    detect_lbl.config(
                        text=tr('unknown_ver'), fg=WARN)

            btn_detect.config(command=do_detect)

        return {'label': lbl, 'om': om, 'display_var': display_var,
                'detect_lbl': detect_lbl, 'detect_btn': btn_detect if show_detect else None}

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

        btn_close_preview = tk.Button(bar, text=tr('close'), bg=SUB, fg=FG,
                                      relief='flat', font=('Segoe UI', 8),
                                      cursor='hand2', command=win.destroy)
        btn_close_preview.pack(side='right', ipadx=8, ipady=2)

        txt = scrolledtext.ScrolledText(win, bg='#1e1e2e', fg=FG,
                                        font=('Microsoft YaHei UI', 10),
                                        relief='flat', wrap='none', bd=0,
                                        insertbackground=FG,
                                        selectbackground='#45475a')
        txt.pack(fill='both', expand=True)

        txt.tag_config('kw',  foreground='#cba6f7')
        txt.tag_config('str', foreground='#a6e3a1')
        txt.tag_config('num', foreground='#fab387')
        txt.tag_config('com', foreground='#6c7086')

        keywords = {'function','end','return','local','if','then','else','elseif',
                    'for','while','do','repeat','until','break','not','and','or',
                    'true','false','nil','in','goto'}     # 'goto' added in Lua 5.2

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
                    while j < n and (code[j].isdigit() or code[j] in '.eExXabcdefABCDEF_'):
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

    # ── Decrypt frame ─────────────────────────────────────────────────────────
    frm_dec = tk.LabelFrame(root, text=tr('decrypt_frame'),
                            bg=BG, fg=ACC, font=('Segoe UI', 9, 'bold'),
                            padx=14, pady=10, bd=1, relief='groove')
    frm_dec.pack(fill='x', padx=16, pady=(12, 6))

    var_dec_in  = tk.StringVar()
    var_dec_out = tk.StringVar()
    ver_dec_var = tk.StringVar(value=LUA_DEFAULT_DECRYPT)

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

    dec_row_in  = make_row(frm_dec, 'input',  var_dec_in,  browse_dec_in,
                           mode='decrypt', output_var=var_dec_out)
    dec_row_out = make_row(frm_dec, 'output', var_dec_out, browse_dec_out)
    dec_ver_row = make_version_row(frm_dec, 'lua_version', ver_dec_var,
                                   LUA_VERSIONS_DECRYPT, ACC,
                                   show_detect=True, detect_input_var=var_dec_in)

    def do_preview():
        inp = var_dec_in.get().strip()
        if not inp:
            messagebox.showwarning(tr('warning'), tr('select_input'), parent=root)
            return
        try:
            with tempfile.NamedTemporaryFile(suffix='.lua', delete=False) as tmp:
                tmp_path = tmp.name
            source, _ = decrypt(inp, tmp_path, ver_dec_var.get())
            Path(tmp_path).unlink(missing_ok=True)
            open_preview(source, Path(inp).name)
        except Exception as e:
            messagebox.showerror(tr('preview_error'), str(e), parent=root)

    btn_preview = tk.Button(frm_dec, text=tr('preview'), bg=SUB, fg=FG,
                            relief='flat', font=('Segoe UI', 8), cursor='hand2',
                            activebackground=ACC, activeforeground=DARK,
                            command=do_preview)
    btn_preview.pack(anchor='e', ipadx=8, ipady=3, pady=(4, 0))

    # ── Encrypt frame ─────────────────────────────────────────────────────────
    frm_enc = tk.LabelFrame(root, text=tr('encrypt_frame'),
                            bg=BG, fg=PURP, font=('Segoe UI', 9, 'bold'),
                            padx=14, pady=10, bd=1, relief='groove')
    frm_enc.pack(fill='x', padx=16, pady=(6, 6))

    var_enc_in  = tk.StringVar()
    var_enc_out = tk.StringVar()
    ver_enc_var = tk.StringVar(value=LUA_DEFAULT_ENCRYPT)
    _enc_ver_for_status[0] = LUA_DEFAULT_ENCRYPT

    def on_enc_ver_change(*_):
        _enc_ver_for_status[0] = ver_enc_var.get()

    ver_enc_var.trace_add('write', on_enc_ver_change)

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

    enc_row_in  = make_row(frm_enc, 'input',  var_enc_in,  browse_enc_in,
                           mode='encrypt', output_var=var_enc_out)
    enc_row_out = make_row(frm_enc, 'output', var_enc_out, browse_enc_out)
    enc_ver_row = make_version_row(frm_enc, 'lua_version', ver_enc_var,
                                   LUA_VERSIONS, PURP)

    # ── Action buttons ────────────────────────────────────────────────────────
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
            _, ver = decrypt(inp, out, ver_dec_var.get())
            log_write(tr('decrypted_ok', name=Path(out).name, version=ver), 'ok')
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
            success, fail, errors = batch_decrypt(input_dir, output_dir, ver_dec_var.get())
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
            size, ver = encrypt(inp, out, ver_enc_var.get())
            log_write(tr('encrypted_ok', name=Path(out).name, size=size, version=ver), 'ok')
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
            success, fail, errors = batch_encrypt(input_dir, output_dir, ver_enc_var.get())
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

    # ── Startup & language refresh ────────────────────────────────────────────
    def startup_check():
        refresh_tools()
        st      = tools_status(_enc_ver_for_status[0])
        missing = []
        lang    = lang_var.get()

        if lang == 'zh':
            if not st['java']:
                missing.append("  • Java（JRE 8+）   →  https://adoptium.net")
            if not st['unluac']:
                missing.append(f"  • {UNLUAC_JAR}  →  https://github.com/HansWessels/unluac/releases")
            if not st['luac']:
                ver = _enc_ver_for_status[0]
                missing.append(f"  • luac{ver}.exe     →  https://luabinaries.sourceforge.net  （Windows）")
                missing.append(f"                          sudo apt install lua{ver}              （Linux）")
        else:
            if not st['java']:
                missing.append("  • Java (JRE 8+)    →  https://adoptium.net")
            if not st['unluac']:
                missing.append(f"  • {UNLUAC_JAR}  →  https://github.com/HansWessels/unluac/releases")
            if not st['luac']:
                ver = _enc_ver_for_status[0]
                missing.append(f"  • luac{ver}.exe      →  https://luabinaries.sourceforge.net  (Windows)")
                missing.append(f"                          sudo apt install lua{ver}             (Linux)")

        clear_log()
        if missing:
            log_write(tr('missing_tools'), 'warn')
            for line in missing:
                log_write(line, 'warn')
        else:
            log_write(tr('all_tools_ok'), 'ok')

    def refresh_language(*_args):
        lbl_tools.config(text=tr('tools'))
        lbl_lang.config(text=tr('language'))
        lbl_drop_hint.config(
            text=tr('drop_hint') if drag_supported else tr('drag_unavailable'))

        frm_dec.config(text=tr('decrypt_frame'))
        frm_enc.config(text=tr('encrypt_frame'))

        for row in [dec_row_in, dec_row_out, enc_row_in, enc_row_out]:
            row['button'].config(text=tr('browse'))

        dec_row_in['label'].config(text=tr('input'))
        dec_row_out['label'].config(text=tr('output'))
        enc_row_in['label'].config(text=tr('input'))
        enc_row_out['label'].config(text=tr('output'))

        dec_ver_row['label'].config(text=tr('lua_version'))
        enc_ver_row['label'].config(text=tr('lua_version'))

        if dec_ver_row.get('detect_btn'):
            dec_ver_row['detect_btn'].config(text=tr('detect_btn'))
        if dec_ver_row.get('detect_lbl') and dec_ver_row['detect_lbl'].cget('text'):
            # clear stale translated text from the detect label
            current = dec_ver_row['detect_lbl'].cget('text')
            if current == LANG['en']['unknown_ver'] or current == LANG['zh']['unknown_ver']:
                dec_ver_row['detect_lbl'].config(text=tr('unknown_ver'))

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
        description=(
            f'{APP_NAME} v{APP_VERSION} — Lua Bytecode Tool\n'
            f'Supported Lua versions: {", ".join(LUA_VERSIONS)}\n'
            f'Decrypt backend: unluac.jar   |   Encrypt backend: luac\n'
            f'unluac fully supports: {", ".join(sorted(LUA_UNLUAC_SUPPORTED))}\n'
            f'unluac partial support: {", ".join(sorted(LUA_UNLUAC_PARTIAL))}'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = p.add_subparsers(dest='cmd')

    d = sub.add_parser('decrypt', help='Bytecode → source  (uses unluac.jar)')
    d.add_argument('input')
    d.add_argument('-o', '--output', default=None)
    d.add_argument('--lua-version', default=LUA_DEFAULT_DECRYPT,
                   choices=LUA_VERSIONS_DECRYPT, metavar='VERSION',
                   help=f'Lua version for unluac (default: auto). '
                        f'Choices: {", ".join(LUA_VERSIONS_DECRYPT)}')

    e = sub.add_parser('encrypt', help='Source → bytecode  (uses luac)')
    e.add_argument('input')
    e.add_argument('-o', '--output', default=None)
    e.add_argument('--lua-version', default=LUA_DEFAULT_ENCRYPT,
                   choices=LUA_VERSIONS, metavar='VERSION',
                   help=f'Lua version for luac (default: {LUA_DEFAULT_ENCRYPT}). '
                        f'Choices: {", ".join(LUA_VERSIONS)}')

    detect_p = sub.add_parser('detect', help='Detect Lua version from bytecode header')
    detect_p.add_argument('input')

    sub.add_parser('status', help='Check if all required tools are available')
    sub.add_parser('versions', help='List supported Lua versions')

    args = p.parse_args()

    if args.cmd == 'status':
        st = tools_status()
        for name, path in st.items():
            print(f"  {name:10s}  {'OK  -> ' + path if path else 'NOT FOUND'}")
        sys.exit(0 if all(st.values()) else 1)

    elif args.cmd == 'versions':
        print("Supported Lua versions:\n")
        print(f"  {'Version':<10} {'luac':<30} {'unluac support'}")
        print(f"  {'-'*7:<10} {'-'*27:<30} {'-'*20}")
        for v in LUA_VERSIONS:
            luac   = find_luac(v)
            luac_s = f"found: {luac}" if luac else "NOT found"
            if v in LUA_UNLUAC_SUPPORTED:
                ul = "✓ full"
            elif v in LUA_UNLUAC_PARTIAL:
                ul = "~ partial"
            else:
                ul = "✗ limited (use luadec)"
            print(f"  Lua {v:<7} {luac_s:<30} {ul}")
        sys.exit(0)

    elif args.cmd == 'detect':
        ver = detect_lua_version(args.input)
        if ver:
            print(f"Lua {ver}")
            sys.exit(0)
        else:
            print("Unknown — not Lua bytecode or unsupported version.", file=sys.stderr)
            sys.exit(1)

    elif args.cmd == 'decrypt':
        out = args.output or auto_decrypt_output(args.input)
        try:
            _, ver = decrypt(args.input, out, args.lua_version)
            print(f'[OK] Decrypted -> {out}  [Lua {ver}]')
        except RuntimeError as e:
            print(f'[ERROR] {e}', file=sys.stderr)
            sys.exit(1)

    elif args.cmd == 'encrypt':
        out = args.output or auto_encrypt_output(args.input)
        try:
            size, ver = encrypt(args.input, out, args.lua_version)
            print(f'[OK] Encrypted -> {out}  ({size} bytes)  [Lua {ver}]')
        except RuntimeError as e:
            print(f'[ERROR] {e}', file=sys.stderr)
            sys.exit(1)

    else:
        p.print_help()


if __name__ == '__main__':
    main()
