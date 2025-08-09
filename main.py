"""Twitch code watcher + optional EA Desktop auto entry.

Environment variables:
  TWITCH_OAUTH (required) oauth: token for IRC
  TWITCH_NICK  (required) username
  TWITCH_CHANNEL (required) channel without '#'
  CODE_REGEX (optional) override pattern
  DISABLE_BEEP (optional) =1 to disable beep
  AUTO_REDEEM (optional) =1 enable EA Desktop automation (use cautiously; ensure ToS compliance)
  EA_PID (optional) PID of EADesktop.exe (e.g. 10912). Required if AUTO_REDEEM=1
  REDEEM_SEND_ENTER (optional) =1 send Enter after typing code
    DISABLE_CLIPBOARD (optional) =1 to skip copying detected codes

Notes: Automation relies on Win32 APIs; best-effort only. Window structure may change.
"""

import os, sys, socket, re, time, threading, datetime, platform
from typing import Set, Optional

HOST = 'irc.chat.twitch.tv'
PORT = 6667

NICK = os.getenv('TWITCH_NICK', '').strip()
TOKEN = os.getenv('TWITCH_OAUTH', '').strip()
CHANNEL_RAW = os.getenv('TWITCH_CHANNEL', '').strip()
CHANNEL = f"#{CHANNEL_RAW}" if CHANNEL_RAW and not CHANNEL_RAW.startswith('#') else CHANNEL_RAW

CODE_PATTERN = os.getenv('CODE_REGEX', r"\b[A-Z0-9]{4}(?:-[A-Z0-9]{4}){3}\b")
AUTO_REDEEM = os.getenv('AUTO_REDEEM') == '1'
EA_PID_ENV = os.getenv('EA_PID')  # If absent we will attempt auto-detect by process name
SEND_ENTER = os.getenv('REDEEM_SEND_ENTER') == '1'
DISABLE_CLIPBOARD = os.getenv('DISABLE_CLIPBOARD') == '1'

if not (NICK and TOKEN and CHANNEL):
    print('Missing required env vars TWITCH_NICK, TWITCH_OAUTH, TWITCH_CHANNEL.')
    sys.exit(1)
if not TOKEN.startswith('oauth:'):
    print('TWITCH_OAUTH must start with oauth:')
    sys.exit(1)
if AUTO_REDEEM and not EA_PID_ENV:
    # We'll attempt auto-detect later; keep AUTO_REDEEM True for now.
    print('AUTO_REDEEM=1 and EA_PID not provided; will try auto-detect for EADesktop.exe')

try:
    EA_PID = int(EA_PID_ENV) if EA_PID_ENV else None
except ValueError:
    EA_PID = None
    print('EA_PID env invalid (not an int); will attempt auto-detect if enabled.')

code_regex = re.compile(CODE_PATTERN)
seen_codes: Set[str] = set()
lock = threading.Lock()

def timestamp() -> str:
    return datetime.datetime.utcnow().isoformat(timespec='milliseconds') + 'Z'

def beep():
    if platform.system() == 'Windows' and os.getenv('DISABLE_BEEP') != '1':
        try:
            import winsound
            winsound.MessageBeep()
        except Exception:
            pass

def copy_to_clipboard(text: str):
    if DISABLE_CLIPBOARD:
        return False
    # Try tkinter (stdlib)
    try:
        import tkinter as tk  # type: ignore
        r = tk.Tk()
        r.withdraw()
        r.clipboard_clear()
        r.clipboard_append(text)
        r.update()  # now it stays on clipboard after window closes
        r.destroy()
        return True
    except Exception:
        pass
    # Windows: Win32 API
    if platform.system() == 'Windows':
        try:
            import ctypes
            CF_UNICODETEXT = 13
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            if user32.OpenClipboard(None):
                try:
                    user32.EmptyClipboard()
                    # Allocate global memory for the text
                    data = text + '\0'
                    size = (len(data)) * 2
                    GMEM_MOVEABLE = 0x0002
                    hGlobal = kernel32.GlobalAlloc(GMEM_MOVEABLE, size)
                    locked = kernel32.GlobalLock(hGlobal)
                    ctypes.memmove(locked, ctypes.create_unicode_buffer(data), size)
                    kernel32.GlobalUnlock(hGlobal)
                    user32.SetClipboardData(CF_UNICODETEXT, hGlobal)
                    return True
                finally:
                    user32.CloseClipboard()
        except Exception:
            pass
    # macOS pbcopy
    if platform.system() == 'Darwin':
        import subprocess
        try:
            p = subprocess.Popen(['pbcopy'], stdin=subprocess.PIPE)
            p.communicate(text.encode('utf-8'))
            return p.returncode == 0
        except Exception:
            pass
    # Linux xclip / xsel
    if platform.system() == 'Linux':
        import subprocess
        for cmd in (['xclip','-selection','clipboard'], ['xsel','--clipboard','--input']):
            try:
                p = subprocess.Popen(cmd, stdin=subprocess.PIPE)
                p.communicate(text.encode('utf-8'))
                if p.returncode == 0:
                    return True
            except Exception:
                continue
    return False

def auto_detect_pid() -> Optional[int]:
    """Attempt to locate EADesktop.exe PID if not supplied."""
    try:
        import psutil  # type: ignore
    except ImportError:
        return None
    candidates = []
    for p in psutil.process_iter(['pid', 'name']):
        try:
            if p.info.get('name') and p.info['name'].lower() == 'eadesktop.exe':
                candidates.append(p.info['pid'])
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            continue
    return candidates[0] if candidates else None

def focus_and_type(code: str):
    """Attempt to focus EA Desktop window (by PID) and type code. Best-effort.

    If EA_PID global is None we try auto-detect (once per call path).
    """
    global EA_PID
    if EA_PID is None:
        EA_PID = auto_detect_pid()
        if EA_PID:
            print(f'[auto] Auto-detected EA Desktop PID: {EA_PID}')
        else:
            print('[auto] Could not auto-detect EA Desktop PID.')
            return
    if platform.system() != 'Windows':
        print('[auto] Non-Windows OS; skipping auto redeem.')
        return
    try:
        import win32gui, win32con, win32process
    except ImportError:
        print('[auto] pywin32 not installed; skipping.')
        return
    target_hwnd = None
    def enum_handler(hwnd, _):
        nonlocal target_hwnd
        if not win32gui.IsWindowVisible(hwnd):
            return
        _, pid = win32process.GetWindowThreadProcessId(hwnd)
        if pid == EA_PID:
            # Heuristic: pick first visible top-level window
            target_hwnd = hwnd
            # stop enumeration by raising
            raise StopIteration
    try:
        win32gui.EnumWindows(enum_handler, None)
    except StopIteration:
        pass
    if not target_hwnd:
        print(f'[auto] No window found for PID {EA_PID}.')
        return
    try:
        win32gui.ShowWindow(target_hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(target_hwnd)
    except Exception as e:
        print(f'[auto] Could not focus window: {e}')
        return
    time.sleep(0.25)
    # Send keystrokes
    try:
        from pywinauto.keyboard import send_keys
    except ImportError:
        print('[auto] pywinauto not installed; cannot send keys.')
        return
    # Attempt simple: select all, paste code via direct typing.
    send_keys('^a{BACKSPACE}')
    send_keys(code)
    if SEND_ENTER:
        send_keys('{ENTER}')
    print(f'[{timestamp()}] AUTO ENTERED (best-effort): {code}')

def handle_code(code: str):
    first = False
    with lock:
        if code not in seen_codes:
            seen_codes.add(code)
            first = True
    if first:
        copied = copy_to_clipboard(code)
        status_extra = ' | copied to clipboard' if copied else ''
        print(f'[{timestamp()}] CODE DETECTED: {code} (new){status_extra}')
        beep()
        if AUTO_REDEEM:
            focus_and_type(code)
    else:
        print(f'[{timestamp()}] CODE REPEAT: {code}')

def process_message(msg: str):
    for m in code_regex.finditer(msg.upper()):
        handle_code(m.group(0))

def send(sock: socket.socket, msg: str):
    sock.send((msg + '\r\n').encode('utf-8'))

def main():
    print(f'[{timestamp()}] Connecting to Twitch IRC as {NICK} ...')
    if os.getenv('NO_CONNECT') == '1':
        test_msg = os.getenv('TEST_MESSAGE', 'TEST-CODE-1234-ABCD')
        print(f'[{timestamp()}] NO_CONNECT=1 self-test with message: {test_msg}')
        process_message(test_msg)
        print(f'[{timestamp()}] Self-test complete. Exiting.')
        return
    with socket.socket() as s:
        s.connect((HOST, PORT))
        send(s, f'PASS {TOKEN}')
        send(s, f'NICK {NICK}')
        send(s, f'JOIN {CHANNEL}')
        print(f'[{timestamp()}] Joined {CHANNEL}')
        buf = ''
        while True:
            try:
                data = s.recv(4096).decode('utf-8', errors='ignore')
            except ConnectionResetError:
                print(f'[{timestamp()}] Connection reset.')
                break
            if not data:
                print(f'[{timestamp()}] Disconnected.')
                break
            buf += data
            while '\r\n' in buf:
                line, buf = buf.split('\r\n', 1)
                if not line:
                    continue
                if line.startswith('PING'):
                    send(s, 'PONG :tmi.twitch.tv')
                else:
                    # Raw IRC line: parse message part after last ':'
                    parts = line.split(' :', 1)
                    if len(parts) == 2:
                        process_message(parts[1])

if __name__ == '__main__':
    main()
