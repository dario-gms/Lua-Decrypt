# FW LUA Script v2.0

A tool for decrypting and encrypting Lua 5.1 bytecode files from Forsaken World (and other Lua 5.1 games).

---

## Requirements

| Tool | Purpose | Download |
|------|---------|----------|
| **Java JRE 8+** | Required to run unluac | [adoptium.net](https://adoptium.net) |
| **unluac.jar** | Decompiles bytecode → source | [github.com/HansWessels/unluac](https://github.com/HansWessels/unluac/releases) |
| **luac.exe** | Compiles source → bytecode | [luabinaries.sourceforge.net](https://luabinaries.sourceforge.net) — `lua-5.1.5_Win64_bin.zip` |

> **Note:** If using the standalone `.exe` build, all tools are already bundled — no extra files needed.

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

- **Decrypt** — select a `.lua` bytecode file and click **Decrypt**. Use **Preview** to inspect the source before saving.
- **Encrypt** — select a decrypted `.lua` source file and click **Encrypt** to recompile it to bytecode.

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
# 1. Compile unluac.jar (only needed once)
build_unluac.bat

# 2. Build the .exe
build.bat
```

Output: `dist\FW LUA Script.exe`

The build embeds `unluac.jar`, `luac.exe`, `lua51.dll`, and `icon.ico` directly into the `.exe`.

---

## Notes

- Only **Lua 5.1** bytecode is supported.
- The decrypt → encrypt cycle is **functionally faithful**: all logic, loops, functions, and tables are preserved. Variable names in stripped bytecode may be replaced with generic names (e.g. `local0`) — this is normal and does not affect behavior.
- Comments from the original source are not recoverable (they are not stored in bytecode).
