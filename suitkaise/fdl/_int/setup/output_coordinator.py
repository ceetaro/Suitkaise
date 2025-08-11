# output manager that dictates what can be outputted
"""
Exclusive output coordinator for animated displays (effects, progress bars).

Responsibilities:
- Enforce single active display (effect or progress) at a time
- Buffer non-display output while a display is active
- Provide warning queue to emit after release
- Sanitize user-provided text to prevent cursor movement sequences
"""

from __future__ import annotations

import re
import sys
import threading
from typing import List, Optional


class _OutputCoordinator:
    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._active_owner: Optional[str] = None  # 'effect' | 'progress' | None
        self._buffer: List[str] = []
        self._warnings: List[str] = []

        # Regex to strip cursor movement CSI sequences (keep SGR m)
        # Matches ESC [ ... final with ABCDHf (cursor moves) or s/u (save/restore)
        self._cursor_move_re = re.compile(
            r"\x1B\[[0-9;?]*[ABCDHf]"  # CUP H/f, CUU/CUD/CUF/CUB
        )
        self._save_restore_re = re.compile(r"\x1B\[[0-9;?]*[su]")

    def acquire(self, owner: str) -> bool:
        with self._lock:
            if self._active_owner is None:
                self._active_owner = owner
                return True
            return False

    def is_active(self) -> bool:
        with self._lock:
            return self._active_owner is not None

    def release(self, owner: str) -> None:
        with self._lock:
            if self._active_owner == owner:
                self._active_owner = None
                # Flush warnings then buffered output
                for w in self._warnings:
                    sys.stdout.write(w + "\n")
                self._warnings.clear()
                if self._buffer:
                    sys.stdout.write("".join(self._buffer))
                    self._buffer.clear()
                sys.stdout.flush()

    def add_warning(self, text: str) -> None:
        with self._lock:
            self._warnings.append(text)

    def buffer_write(self, text: str) -> None:
        with self._lock:
            self._buffer.append(text)

    def write_now(self, text: str) -> None:
        with self._lock:
            if self._active_owner is None:
                sys.stdout.write(text)
                sys.stdout.flush()
            else:
                self._buffer.append(text)

    def sanitize_user_text(self, text: str) -> str:
        # Remove cursor movement and save/restore; preserve SGR colors (m)
        text = self._cursor_move_re.sub("", text)
        text = self._save_restore_re.sub("", text)
        return text


_output_coordinator = _OutputCoordinator()

# both spinners and progress bars are managed by the output manager, 
# and only one total can be active at a time.

# the output manager then becomes the sole communicator with _Formatter to determine
# if output is currently allowed.