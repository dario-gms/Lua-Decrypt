# FW LUA Script v3.0

A tool for decrypting and encrypting Lua bytecode files from Forsaken World (and other Lua-based games).  
Supports Lua 1.0 through 5.5, with native Lua 5.1 support bundled out of the box.

---

## What's New in v3.0

- **Multi-version Lua support** — decrypt and encrypt bytecode for Lua 1.0 through 5.5
- **Auto-detect** — the tool reads the bytecode header and automatically identifies the Lua version; no manual selection needed
- **Broader file support** — accepts both `.lua` and `.luac` extensions for decryption (batch and single file)
- **Smarter unluac integration** — probes the bundled `unluac.jar` at startup to detect which flags it supports, avoiding compatibility errors with different jar versions
- **Version dropdown** — manually override the detected version if needed, or leave it on Auto

---

## Requirements

| Tool | Purpose | Download |
|------|---------|----------|
| **Java 8+** | Required to run unluac | [adoptium.net](https://adoptium.net) |
| **unluac.jar** | Decompiles bytecode → source | [github.com/HansWessels/unluac](https://github.com/HansWessels/unluac/releases) |
| **luac.exe** *(or luac binary)* | Compiles source → bytecode | See [Lua Binaries](#lua-binaries) below |

> **Note:** If using the standalone `.exe` build, Java and `unluac.jar` are already bundled — `luac.exe` for Lua 5.1 is also included.

### Optional

| Package | Purpose |
|---------|---------|
| **tkinterdnd2** | Enables drag-and-drop support in the GUI (`pip install tkinterdnd2`) |
| **Pillow** | Displays the icon in the title bar when running from source (`pip install pillow`) |

---

## Lua Binaries

The tool requires a `luac` binary matching the Lua version you want to **encrypt** (compile source → bytecode).  
Decryption (bytecode → source) only requires `unluac.jar` and does not need `luac`.

### Pre-built binaries (Windows / Linux / macOS)

Download from **[Lua Binaries](https://luabinaries.sourceforge.net)** — pick the package matching your OS and Lua version.

Recommended files for Windows:

| Lua Version | Package |
|-------------|---------|
| 5.1 *(bundled)* | `lua-5.1.5_Win64_bin.zip` |
| 5.2 | `lua-5.2.4_Win64_bin.zip` |
| 5.3 | `lua-5.3.6_Win64_bin.zip` |
| 5.4 | `lua-5.4.7_Win64_bin.zip` |

Extract and place `luac.exe` (and any required `.dll` files) in the same folder as `FW LUA Script.exe`.

> Rename the binary to match the version if needed — e.g. `luac5.3.exe` or `luac53.exe` — the tool searches for both formats.

### Build from source

If no pre-built binary is available for your platform or version, download the source from **[lua.org/download](https://www.lua.org/download.html)** and compile it:

```bash
# Linux / macOS example
tar xzf lua-5.x.x.tar.gz
cd lua-5.x.x
make all
# The luac binary will be in ./src/
```

---

## unluac Version Compatibility

| Lua Version | unluac Support |
|-------------|---------------|
| 5.0 – 5.4 | ✅ Full |
| 5.5 | ⚠️ Partial (experimental) |
| 4.0 | ⚠️ Partial |
| 1.x / 2.x / 3.x | ❌ Limited — use a version-specific decompiler (e.g. luadec) |

> The tool auto-detects the Lua version from the bytecode header, so you rarely need to change the version dropdown.

---

## Folder Structure

If running from source or using the unbundled `.exe`:

```
FW LUA Script.exe
unluac.jar
luac.exe          ← Lua 5.1 (bundled)
lua51.dll         ← include if luac.exe requires it
lua5.1.dll        ← include if luac.exe requires it
icon.ico

# Additional luac binaries (optional, for other Lua versions)
luac5.2.exe  (or luac52.exe)
luac5.3.exe  (or luac53.exe)
luac5.4.exe  (or luac54.exe)
```

---

## Usage

### GUI

Double-click `FW LUA Script.exe`.  
The status bar at the top shows whether each required tool was found.

**Decrypt (bytecode → source):**
1. Select the input `.lua` or `.luac` bytecode file
2. Choose an output path (auto-filled by default)
3. The **Lua Version** field auto-fills after clicking **Detect**, or leave it on **Auto**
4. Click **Decrypt** — use **Preview** to inspect the source before saving

**Encrypt (source → bytecode):**
1. Select the decrypted `.lua` source file
2. Choose the target Lua version from the dropdown
3. Click **Encrypt**

**Batch processing:**
- **Batch Decrypt** — processes all `.lua` and `.luac` files in a folder recursively, preserving subfolder structure
- **Batch Encrypt** — compiles all `.lua` source files in a folder recursively

**Drag-and-drop** *(requires `tkinterdnd2`)*:  
Drop a file onto the input field to set the path. The output path is auto-filled.

**Language:**  
Use the language selector in the title bar to switch between **English** and **Chinese (中文)**.

Output filenames are auto-generated:
- `file.lua` → `file_decrypted.lua`
- `file_decrypted.lua` → `file_encrypted.lua`

---

### CLI

```bash
# Decrypt (auto-detect Lua version)
python fw_lua_script.py decrypt input.lua

# Decrypt with explicit version
python fw_lua_script.py decrypt input.lua --lua-version 5.1
python fw_lua_script.py decrypt input.lua -o output.lua

# Encrypt
python fw_lua_script.py encrypt input.lua
python fw_lua_script.py encrypt input.lua --lua-version 5.3
python fw_lua_script.py encrypt input.lua -o output.lua

# Detect Lua version from a file
python fw_lua_script.py detect input.lua

# Check tool availability
python fw_lua_script.py status

# List all supported Lua versions and luac binaries found
python fw_lua_script.py versions
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
| Tag `v*` (e.g. `v3.0`) | Builds the `.exe` and creates a GitHub Release with it attached |

The workflow file is located at `.github/workflows/build.yml`.

---

## Notes

- **Lua 5.1 is the default** and is supported natively (luac bundled). Other versions require the matching `luac` binary in the program folder.
- The decrypt → encrypt cycle is **functionally faithful**: all logic, loops, functions, and tables are preserved. Variable names in stripped bytecode may be replaced with generic names (e.g. `local0`) — this is normal and does not affect runtime behavior.
- **Comments are not recoverable** — they are not stored in bytecode.
- Batch decrypt accepts both `.lua` and `.luac` extensions. Batch encrypt only processes `.lua` source files.
- If `unluac.jar` fails with an unrecognized option error, the tool automatically falls back to auto-detection mode without passing version flags — ensuring compatibility across different unluac releases.
