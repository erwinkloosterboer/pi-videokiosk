"""evdev-based QR/barcode scanner input capture."""

from __future__ import annotations

import logging
import threading
from queue import Queue
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# Key code to character mapping (US QWERTY, evdev KEY_* codes)
# Format: keycode -> (normal_char, shift_char), None means special key
_KEY_TO_CHAR: dict[int, tuple[Optional[str], Optional[str]]] = {
    2: ("1", "!"),
    3: ("2", "@"),
    4: ("3", "#"),
    5: ("4", "$"),
    6: ("5", "%"),
    7: ("6", "^"),
    8: ("7", "&"),
    9: ("8", "*"),
    10: ("9", "("),
    11: ("0", ")"),
    12: ("-", "_"),
    13: ("=", "+"),
    16: ("q", "Q"),
    17: ("w", "W"),
    18: ("e", "E"),
    19: ("r", "R"),
    20: ("t", "T"),
    21: ("y", "Y"),
    22: ("u", "U"),
    23: ("i", "I"),
    24: ("o", "O"),
    25: ("p", "P"),
    26: ("[", "{"),
    27: ("]", "}"),
    30: ("a", "A"),
    31: ("s", "S"),
    32: ("d", "D"),
    33: ("f", "F"),
    34: ("g", "G"),
    35: ("h", "H"),
    36: ("j", "J"),
    37: ("k", "K"),
    38: ("l", "L"),
    39: (";", ":"),
    40: ("'", '"'),
    41: ("`", "~"),
    43: ("\\", "|"),
    44: ("z", "Z"),
    45: ("x", "X"),
    46: ("c", "C"),
    47: ("v", "V"),
    48: ("b", "B"),
    49: ("n", "N"),
    50: ("m", "M"),
    51: (",", "<"),
    52: (".", ">"),
    53: ("/", "?"),
    57: (" ", " "),
}

# Modifier key codes
_KEY_LEFTSHIFT = 42
_KEY_RIGHTSHIFT = 54
_KEY_ENTER = 28
_KEY_KPENTER = 96


def _find_scanner_device(device_path: Optional[str] = None):
    """Find the scanner device. Returns InputDevice or None."""
    import evdev
    from evdev import InputDevice

    if device_path:
        try:
            return InputDevice(device_path)
        except (OSError, PermissionError) as e:
            logger.warning("Could not open configured scanner device %s: %s", device_path, e)
            return None

    for path in evdev.list_devices():
        try:
            dev = InputDevice(path)
            name = dev.name.lower()
            # Prefer devices that look like scanners
            if "scanner" in name or "barcode" in name or "qr" in name:
                return dev
        except (OSError, PermissionError):
            continue

    # Fallback: first device that has key events (keyboard-like)
    for path in evdev.list_devices():
        try:
            dev = InputDevice(path)
            caps = dev.capabilities()
            if evdev.ecodes.EV_KEY in caps:
                return dev
        except (OSError, PermissionError):
            continue

    return None


def _decode_key_event(code: int, value: int, shift_pressed: bool) -> Optional[str]:
    """
    Decode a key event to a character.
    Returns the character, or None for non-printable (e.g. Enter, modifier).
    """
    if code in (_KEY_LEFTSHIFT, _KEY_RIGHTSHIFT):
        return None
    if code in (_KEY_ENTER, _KEY_KPENTER):
        return "\n"  # Use newline as scan complete signal
    if value != 1:  # Only key press, not release
        return None

    mapping = _KEY_TO_CHAR.get(code)
    if not mapping:
        return None
    normal, shifted = mapping
    return shifted if shift_pressed and shifted else (normal or shifted)


def run_scanner_listener(
    callback: Callable[[str], None],
    device_path: Optional[str] = None,
    queue: Optional[Queue] = None,
) -> None:
    """
    Run the scanner listener in the current thread (blocking).

    Accumulates key events until Enter, then passes the full URL string to callback.
    If queue is provided, also puts each scanned string on the queue.
    """
    from evdev import ecodes

    dev = _find_scanner_device(device_path)
    if not dev:
        logger.error("No scanner device found. Connect a USB barcode/QR scanner.")
        return

    try:
        dev.grab()
    except (IOError, OSError) as e:
        logger.error("Could not grab scanner device (may need root): %s", e)
        return

    logger.info("Scanner listener started on device: %s", dev.name)
    buffer: list[str] = []
    shift_pressed = False

    try:
        for event in dev.read_loop():
            if event.type != ecodes.EV_KEY:
                continue

            if event.code in (_KEY_LEFTSHIFT, _KEY_RIGHTSHIFT):
                shift_pressed = event.value == 1
                continue

            char = _decode_key_event(event.code, event.value, shift_pressed)
            if char is None:
                continue

            if char == "\n":
                if buffer:
                    url = "".join(buffer)
                    buffer.clear()
                    callback(url)
                    if queue is not None:
                        queue.put(url)
            else:
                buffer.append(char)
    except (IOError, OSError) as e:
        logger.error("Scanner device error: %s", e)
    finally:
        try:
            dev.ungrab()
        except Exception:
            pass


def start_scanner_listener_thread(
    callback: Callable[[str], None],
    device_path: Optional[str] = None,
    queue: Optional[Queue] = None,
) -> tuple[threading.Thread, Queue]:
    """
    Start the scanner listener in a background thread.

    Returns (thread, queue). The queue receives each scanned URL string.
    """
    if queue is None:
        queue = Queue()
    thread = threading.Thread(
        target=run_scanner_listener,
        args=(callback, device_path, queue),
        daemon=True,
    )
    thread.start()
    return thread, queue
