# FW LUA Script v2.1

A tool for decrypting and encrypting Lua 5.1 bytecode files from Forsaken World (and other Lua 5.1 games).

---

## Requirements

| Tool | Purpose | Download |
|------|---------|----------|
| **Java JRE 8+** | Required to run unluac | [adoptium.net](https://adoptium.net) |
| **unluac.jar** | Decompiles bytecode → source | [github.com/HansWessels/unluac](https://github.com/HansWessels/unluac/releases) |
| **luac.exe** | Compiles source → bytecode | [luabinaries.sourceforge.net](https://luabinaries.sourceforge.net) — `lua-5.1.5_Win64_bin.zip` |

> **Note:** If using the standalone `.exe` build, all tools are already bundled — no extra files needed.

### Optional

| Package | Purpose |
|---------|---------|
| **tkinterdnd2** | Enables drag-and-drop support in the GUI (`pip install tkinterdnd2`) |
| **Pillow** | Displays the icon in the title bar when running from source (`pip install pillow`) |

---

## Folder Structure

If running from source or using the unbundled `.exe`:

```
FW LUA Script.exe
unluac.jar
luac.exe
lua51.dll        ← include if luac.exe requires it
icon.ico
```

---

## Usage

### GUI

Double-click `FW LUA Script.exe`. The status bar at the top shows whether each required tool was found (green = OK, red = missing).

**Single file:**
- **Decrypt** — select a `.lua` bytecode file and click **Decrypt**. Use **Preview** to inspect the source before saving.
- **Encrypt** — select a decrypted `.lua` source file and click **Encrypt** to recompile it to bytecode.

**Batch processing:**
- **Batch Decrypt** — select an input folder and an output folder. All `.lua` / `.luac` files are decrypted recursively, preserving the subfolder structure.
- **Batch Encrypt** — select an input folder and an output folder. All `.lua` source files are compiled recursively.

**Drag-and-drop** (requires `tkinterdnd2`):
- Drop a file onto the input field to set the path. The output path is auto-filled.
- A hint in the top bar indicates whether drag-and-drop is available.

**Language:**
- Use the language selector in the title bar to switch between **English** and **Chinese (中文)**. All UI labels update instantly.

Output filenames are auto-generated:
- `file.lua` → `file_decrypted.lua`
- `file_decrypted.lua` → `file_encrypted.lua`

### CLI

```bash
# Decrypt
python fw_lua_script.py decrypt input.lua
python fw_lua_script.py decrypt input.lua -o output.lua

# Encrypt
python fw_lua_script.py encrypt input.lua
python fw_lua_script.py encrypt input.lua -o output.lua

# Check tool availability
python fw_lua_script.py status
```

---

## Building from Source

**Requirements:** Python 3.10+, PyInstaller

```bash
# Build the .exe
build.bat
```

Output: `dist\FW LUA Script.exe`

The build embeds `unluac.jar`, `luac.exe`, `lua51.dll`, `lua5.1.dll`, and `icon.ico` directly into the `.exe`.

---

## CI / CD

This repository uses GitHub Actions to build the `.exe` automatically.

| Event | Result |
|-------|--------|
| Push / PR to `main` | Builds the `.exe` and uploads it as a workflow artifact (kept 30 days) |
| Tag `v*` (e.g. `v2.1`) | Builds the `.exe` and creates a GitHub Release with it attached |

The workflow file is located at `.github/workflows/build.yml`.

---

## Notes

- Only **Lua 5.1** bytecode is supported.
- The decrypt → encrypt cycle is **functionally faithful**: all logic, loops, functions, and tables are preserved. Variable names in stripped bytecode may be replaced with generic names (e.g. `local0`) — this is normal and does not affect behavior.
- Comments from the original source are not recoverable (they are not stored in bytecode).
- Batch decrypt accepts both `.lua` and `.luac` extensions. Batch encrypt only processes `.lua` source files.
