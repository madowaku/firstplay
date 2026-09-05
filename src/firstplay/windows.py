from __future__ import annotations

import ctypes
import os
import subprocess
import time
from ctypes import wintypes
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

import mss
from PIL import Image

from .models import Action


@dataclass(slots=True, frozen=True)
class WindowRect:
    left: int
    top: int
    width: int
    height: int
    title: str = ""


class WindowsGameSession:
    def __init__(self, executable: Path, launch_wait: float = 2.0) -> None:
        if os.name != "nt":
            raise RuntimeError("FirstPlay v0.1 currently supports Windows only")
        self.executable = executable.resolve()
        self.launch_wait = launch_wait
        self.process: subprocess.Popen[bytes] | None = None
        self.hwnd: int | None = None
        self.rect: WindowRect | None = None

    def start(self) -> WindowRect:
        if not self.executable.exists():
            raise FileNotFoundError(self.executable)
        self.process = subprocess.Popen([str(self.executable)], cwd=str(self.executable.parent))
        time.sleep(max(0.0, self.launch_wait))

        deadline = time.monotonic() + 8.0
        while time.monotonic() < deadline:
            hwnd = _find_window_for_pid(self.process.pid)
            if hwnd:
                self.hwnd = hwnd
                _focus_window(hwnd)
                time.sleep(0.25)
                self.rect = _get_window_rect(hwnd)
                return self.rect
            time.sleep(0.25)

        raise RuntimeError(
            "Could not resolve a visible top-level window for the launched process. "
            "FirstPlay refuses to fall back to whole-desktop capture."
        )

    def refresh_rect(self) -> WindowRect:
        if not self.hwnd:
            raise RuntimeError("Game session has not started")
        self.rect = _get_window_rect(self.hwnd)
        return self.rect

    def capture_png(self) -> bytes:
        rect = self.refresh_rect()
        with mss.mss() as capture:
            shot = capture.grab(
                {"left": rect.left, "top": rect.top, "width": rect.width, "height": rect.height}
            )
            image = Image.frombytes("RGB", shot.size, shot.rgb)
            buffer = BytesIO()
            image.save(buffer, format="PNG", optimize=True)
            return buffer.getvalue()

    def execute(self, action: Action) -> None:
        import pyautogui

        pyautogui.FAILSAFE = True
        if self.hwnd:
            _focus_window(self.hwnd)
        rect = self.refresh_rect()

        if action.type == "click":
            assert action.x is not None and action.y is not None
            x = max(0, min(rect.width - 1, action.x))
            y = max(0, min(rect.height - 1, action.y))
            pyautogui.click(rect.left + x, rect.top + y)
        elif action.type == "key":
            assert action.key
            pyautogui.press(action.key)
        elif action.type == "type_text":
            pyautogui.write(action.text or "", interval=0.03)
        elif action.type == "wait":
            time.sleep(max(0.0, min(action.seconds or 1.0, 10.0)))
        elif action.type == "stop":
            return
        else:  # pragma: no cover - Action validation prevents this
            raise ValueError(f"Unsupported action: {action.type}")

    def terminate(self) -> None:
        if self.process and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=3)
            except subprocess.TimeoutExpired:
                self.process.kill()

    @property
    def is_running(self) -> bool:
        return bool(self.process and self.process.poll() is None)


def _find_window_for_pid(pid: int) -> int | None:
    user32 = ctypes.windll.user32
    matches: list[int] = []

    enum_proc_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)

    def callback(hwnd: int, _lparam: int) -> bool:
        if not user32.IsWindowVisible(hwnd):
            return True
        if user32.GetWindowTextLengthW(hwnd) <= 0:
            return True
        window_pid = ctypes.c_ulong()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(window_pid))
        if window_pid.value == pid:
            matches.append(int(hwnd))
        return True

    user32.EnumWindows(enum_proc_type(callback), 0)
    return matches[0] if matches else None


def _focus_window(hwnd: int) -> None:
    user32 = ctypes.windll.user32
    user32.ShowWindow(hwnd, 5)
    user32.SetForegroundWindow(hwnd)


def _get_window_rect(hwnd: int) -> WindowRect:
    user32 = ctypes.windll.user32
    rect = wintypes.RECT()
    if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
        raise RuntimeError("GetWindowRect failed")

    width = int(rect.right - rect.left)
    height = int(rect.bottom - rect.top)
    if width <= 1 or height <= 1:
        raise RuntimeError(f"Game window has invalid size: {width}x{height}")

    title_length = user32.GetWindowTextLengthW(hwnd)
    buffer = ctypes.create_unicode_buffer(title_length + 1)
    user32.GetWindowTextW(hwnd, buffer, title_length + 1)
    return WindowRect(
        left=int(rect.left),
        top=int(rect.top),
        width=width,
        height=height,
        title=buffer.value,
    )
