"""Drives the Memory Bridge of Obsidian API: sends Lua to the running game and prints the answer.

The game must run with Obsidian API and the Memory Bridge option on. Python 3.8+, standard library only.

  python bridge.py "api.game.state_name()"      an expression: the value is printed
  python bridge.py "print(1) return 2, 3"       a chunk: what it prints and returns
  python bridge.py -f probe.lua [args ...]      a file; the args reach it as ...
  python bridge.py status                       whether the bridge answers, the game state, what runs
  python bridge.py stream [--follow] [--clear]  lines from emit() and from failing hooks and frame functions
  python bridge.py undo                         takes back every hook, frame function and set() write

Exit codes: 0 ok, 1 the code failed, 2 refused (public lobby), 3 no answer (game, bridge or compiler).
"""
import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

MAGIC = b"OBSBRIDGE 1\n"
DIR = Path(os.environ.get("APPDATA", ".")) / "Arrowhead" / "Helldivers" / "ObsidianLauncher" / "bridge"

# Compiles one file to LuaJIT 2.0 bytecode with debug info (line numbers in errors), under the chunk
# name the caller gives. string.dump in LuaJIT 2.0 keeps the debug info.
COMPILE = r"""
local src, out, name = arg[1], arg[2], arg[3]
local f = assert(io.open(src, "rb")); local s = f:read("*a"); f:close()
local fn, err = loadstring(s, "=" .. name)
if not fn then io.stderr:write(err, "\n"); os.exit(1) end
f = assert(io.open(out, "wb")); f:write(string.dump(fn)); f:close()
"""


def registry_dirs():
    """Install folders of Obsidian Launcher from the Windows uninstall entries."""
    out = []
    try:
        import winreg
    except ImportError:
        return out
    roots = [(winreg.HKEY_CURRENT_USER, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
             (winreg.HKEY_LOCAL_MACHINE, r"Software\Microsoft\Windows\CurrentVersion\Uninstall"),
             (winreg.HKEY_LOCAL_MACHINE, r"Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall")]
    for root, path in roots:
        try:
            key = winreg.OpenKey(root, path)
        except OSError:
            continue
        for i in range(10000):
            try:
                sub = winreg.OpenKey(key, winreg.EnumKey(key, i))
            except OSError:
                break
            try:
                name = str(winreg.QueryValueEx(sub, "DisplayName")[0])
            except OSError:
                continue
            if not name.startswith("Obsidian Launcher"):
                continue
            for value in ("InstallLocation", "DisplayIcon", "UninstallString"):
                try:
                    v = str(winreg.QueryValueEx(sub, value)[0]).strip().strip('"')
                except OSError:
                    continue
                p = Path(v.split('",')[0].split(",")[0].strip('"'))
                out.append(p if p.is_dir() else p.parent)
    return out


def find_luajit(given):
    """The LuaJIT 2.0 that ships beside Obsidian (the game loads only 2.0 bytecode)."""
    exe = "luajit.exe" if os.name == "nt" else "luajit"
    candidates = []
    if given:
        candidates.append(Path(given))
    if os.environ.get("OBSIDIAN_LUAJIT"):
        candidates.append(Path(os.environ["OBSIDIAN_LUAJIT"]))
    for d in registry_dirs():
        candidates.append(d / "luajit" / exe)
    for base in (os.environ.get("LOCALAPPDATA"), os.environ.get("ProgramFiles"), os.environ.get("ProgramFiles(x86)")):
        if base:
            candidates.append(Path(base) / "Obsidian Launcher" / "luajit" / exe)
    here = Path.cwd()
    for parent in [here] + list(here.parents):
        candidates.append(parent / "ProjectObsidian" / "ObsidianLauncher" / "target" / "luajit" / exe)
        candidates.append(parent / "ObsidianLauncher" / "target" / "luajit" / exe)
    for c in candidates:
        if c.is_file():
            return c
    on_path = shutil.which("luajit")
    if on_path:
        v = subprocess.run([on_path, "-v"], capture_output=True, text=True).stdout
        if v.startswith("LuaJIT 2.0"):
            return Path(on_path)
    return None


def wrap(source):
    """The chunk the bridge runs makes the function it calls: `return function(...) <code> end`, on the
    same lines, so line numbers in errors stay those of the code."""
    if source.startswith("\ufeff"):
        source = source[1:]
    return "return function(...) " + source + "\nend"


def compile_lua(luajit, source, name, strip=False):
    with tempfile.TemporaryDirectory() as tmp:
        src, out = Path(tmp) / "in.lua", Path(tmp) / "out.ljbc"
        src.write_bytes(wrap(source).encode("utf-8"))
        if strip:
            cmd = [str(luajit), "-b", "-s", str(src), str(out)]
        else:
            script = Path(tmp) / "compile.lua"
            script.write_text(COMPILE, encoding="utf-8")
            cmd = [str(luajit), str(script), str(src), str(out), name]
        env = dict(os.environ)
        env.setdefault("LUA_PATH", str(luajit.parent / "lua" / "?.lua") + ";;")
        r = subprocess.run(cmd, capture_output=True, text=True, cwd=str(luajit.parent), env=env)
        if r.returncode != 0:
            return None, (r.stderr or r.stdout).strip()
        return out.read_bytes(), None


def game_running():
    if os.name != "nt":
        return None
    r = subprocess.run(["tasklist", "/FI", "IMAGENAME eq helldivers.exe", "/NH"], capture_output=True, text=True)
    return "helldivers.exe" in r.stdout.lower()


def status_text():
    p = DIR / "status"
    if not p.exists():
        return None, None
    age = time.time() - p.stat().st_mtime
    return p.read_text(encoding="utf-8", errors="replace"), age


NAMES = ""


def opcode_names(luajit):
    """bcnames of the compiler (jit/vmdef.lua beside it): the game interprets the bytecode with them."""
    p = luajit.parent / "lua" / "jit" / "vmdef.lua"
    if p.exists():
        import re
        m = re.search(r'bcnames = "([^"]*)"', p.read_text(encoding="utf-8", errors="replace"))
        if m:
            return m.group(1)
    return ""


def send(code, args, timeout):
    """Writes one request and waits for the answer. Answers (kind, body) or (None, why)."""
    DIR.mkdir(parents=True, exist_ok=True)
    rid = "r%d%03d" % (int(time.time() * 1000) % 10 ** 10, os.getpid() % 1000)
    req = DIR / "request"
    waited = 0.0
    while req.exists() and waited < timeout:
        time.sleep(0.05)
        waited += 0.05
    if req.exists():
        return None, "an earlier request is still waiting: the game isn't reading the bridge folder"
    header = MAGIC + rid.encode() + b"\n" + "\t".join(args).encode("utf-8") + b"\n" + NAMES.encode() + b"\n"
    tmp = DIR / ("request." + rid)
    tmp.write_bytes(header + code)
    os.replace(tmp, req)
    answer = DIR / ("answer_" + rid)
    deadline = time.time() + timeout
    while time.time() < deadline:
        if answer.exists():
            try:
                text = answer.read_text(encoding="utf-8", errors="replace")
                answer.unlink()
            except PermissionError:
                time.sleep(0.02)
                continue
            first, _, body = text.partition("\n")
            return first.split(" ")[0], (first, body)
        time.sleep(0.02)
    # No answer: say why, and take the request back so it doesn't run later by surprise.
    taken = not req.exists()
    if not taken:
        try:
            req.unlink()
        except OSError:
            pass
    running = DIR / "running"
    alive = game_running()
    if running.exists() and running.read_text().strip() == rid and alive is False:
        return None, "the game closed while running this request (an engine assert ends the game; see the game log)"
    if alive is False:
        return None, "the game isn't running"
    if taken:
        return None, "the game took the request and is still running it after %ss (a loop that never ends?)" % timeout
    st, age = status_text()
    if st is None:
        return None, "no answer and no status file: is the Memory Bridge option of Obsidian API on, and the game restarted since?"
    return None, "no answer; the status file is %.0fs old (a loading screen holds frames)" % age


def run(code_bytes, args, timeout, luajit, source, name):
    kind, got = send(code_bytes, args, timeout)
    if kind is None:
        print("no answer:", got, file=sys.stderr)
        return 3
    first, body = got
    sys.stdout.write(body)
    if kind == "ok":
        return 0
    print(first, file=sys.stderr)
    return 2 if kind == "refused" else 1


def main():
    ap = argparse.ArgumentParser(description="Memory Bridge driver", formatter_class=argparse.RawDescriptionHelpFormatter, epilog=__doc__)
    ap.add_argument("code", nargs="?", help="Lua: an expression or a chunk; or status, stream, undo")
    ap.add_argument("args", nargs="*", help="arguments for -f, reaching the file as ...")
    ap.add_argument("-f", "--file", help="a Lua file to run")
    ap.add_argument("-t", "--timeout", type=float, default=10.0)
    ap.add_argument("--luajit", help="the LuaJIT 2.0 compiler (default: the one beside Obsidian)")
    ap.add_argument("--follow", action="store_true", help="stream: keep printing new lines")
    ap.add_argument("--clear", action="store_true", help="stream: empty it after printing")
    a = ap.parse_args()

    if a.file is None and a.code == "status":
        st, age = status_text()
        alive = game_running()
        print("game running:", {True: "yes", False: "no", None: "unknown"}[alive])
        if st is None:
            print("no status file in", DIR)
            return 3
        print("status written %.1fs ago" % age)
        sys.stdout.write(st)
        return 0 if age < 10 else 3
    if a.file is None and a.code == "stream":
        p = DIR / "stream.txt"
        pos = 0
        while True:
            if p.exists():
                data = p.read_bytes()
                if len(data) < pos:
                    pos = 0
                sys.stdout.write(data[pos:].decode("utf-8", "replace"))
                sys.stdout.flush()
                pos = len(data)
            if not a.follow:
                break
            time.sleep(0.2)
        if a.clear and p.exists():
            p.unlink()
        return 0
    if a.file is None and a.code == "undo":
        a.code = "return undo()"

    luajit = find_luajit(a.luajit)
    if luajit is None:
        print("no LuaJIT 2.0 found: pass --luajit or set OBSIDIAN_LUAJIT to luajit.exe in the luajit folder beside Obsidian", file=sys.stderr)
        return 3
    global NAMES
    NAMES = opcode_names(luajit)
    if a.file:
        source = Path(a.file).read_text(encoding="utf-8")
        name = Path(a.file).name
        args = ([a.code] if a.code else []) + a.args
    else:
        if not a.code:
            ap.print_help()
            return 3
        source, name, args = a.code, "bridge", a.args
        # An expression first, so "api.game.state_name()" prints the value; else the text as a chunk.
        code, _ = compile_lua(luajit, "return " + source, name)
        if code is not None:
            return run(code, args, a.timeout, luajit, "return " + source, name)
    code, err = compile_lua(luajit, source, name)
    if code is None:
        print(err, file=sys.stderr)
        return 1
    return run(code, args, a.timeout, luajit, source, name)


if __name__ == "__main__":
    sys.exit(main())
