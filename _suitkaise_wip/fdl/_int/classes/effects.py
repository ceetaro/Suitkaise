# TODO rename spinners to effects across file.

"""
Effects (animated terminal output) engine with exclusive display.

Key rules implemented:
- Single active display (effect or progress bar); others are ignored and warnings queued
- Effects own the first line; either inline with message or centered alone
- Frames and completed frame have fixed visual width; effect width and terminal width treated as fixed for lifetime
- Messages may span multiple lines; user cursor-control sequences are stripped
- Justified output is padded to terminal width globally (via text justifier)
"""

from __future__ import annotations

import re
import sys
import threading
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from ..setup.output_coordinator import _output_coordinator
from ..setup.text_wrapping import _get_visual_width
from ..setup.terminal import _get_terminal
from ..setup.unicode import _get_unicode_support
from ..core.formatter import _Formatter, _OutputType


@dataclass
class _EffectStyle:
    name: str
    frames: List[str]
    completed: str
    interval: float


class _EffectRegistry:
    def __init__(self) -> None:
        self._styles: Dict[str, _EffectStyle] = {}
        self._ascii_fallback = _EffectStyle(
            name="ascii",
            frames=[" - ", " \\ ", " | ", " / "],
            completed=" | ",
            interval=0.15,
        )

    def register(self, name: str, frames: List[str], completed: str, interval: float, overwrite: bool = False) -> None:
        key = (name or "").strip().lower()
        if not key:
            raise ValueError("Effect name cannot be empty")
        if key in self._styles and not overwrite:
            raise ValueError(f"Effect '{name}' already exists; pass overwrite=True to replace it")

        if not frames:
            raise ValueError("Effect frames cannot be empty")

        # Validate equal visual width
        target_width = _get_visual_width(frames[0])
        for f in frames:
            if _get_visual_width(f) != target_width:
                raise ValueError("All frames must have the same visual width")
        if _get_visual_width(completed) != target_width:
            raise ValueError("Completed frame must have the same visual width as frames")

        # Validate encoding support
        if not self._is_supported(frames + [completed]):
            _output_coordinator.add_warning(
                f"Effect '{name}' contains unsupported characters; using ASCII fallback instead."
            )
            self._styles[key] = self._ascii_fallback
            return

        self._styles[key] = _EffectStyle(key, frames, completed, max(0.05, min(1.0, float(interval))))

    def get(self, name: str) -> _EffectStyle:
        key = (name or "").strip().lower()
        style = self._styles.get(key)
        if style is None:
            # Provide unicode-friendly default or ascii fallback
            support = _get_unicode_support()
            if getattr(support, 'supports_unicode_spinners', False):
                # basic dots style
                try:
                    self.register(
                        "dots",
                        [' ⠋ ', ' ⠙ ', ' ⠹ ', ' ⠸ ', ' ⠼ ', ' ⠴ ', ' ⠦ ', ' ⠧ ', ' ⠇ ', ' ⠏ '],
                        ' ⠿ ',
                        0.12,
                        overwrite=False,
                    )
                except Exception:
                    pass
                return self._styles.get("dots", self._ascii_fallback)
            return self._ascii_fallback
        return style

    def _is_supported(self, texts: List[str]) -> bool:
        term = _get_terminal()
        encoding = getattr(term, 'encoding', 'ascii') or 'ascii'
        for t in texts:
            try:
                t.encode(encoding)
            except Exception:
                return False
        return True


_effects_registry = _EffectRegistry()


class _ActiveEffect:
    def __init__(self, style: _EffectStyle, message_fdl: Optional[str], values: Optional[Tuple] = None) -> None:
        self.style = style
        self.values = values if isinstance(values, tuple) or values is None else (values,)
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None

        # Mode and layout state
        self._terminal = _get_terminal()
        self._effect_width = _get_visual_width(style.frames[0])
        self._terminal_width = self._terminal.width
        self._centered = (self._terminal_width - self._effect_width) < 20

        # First-line snapshot parts: [before, effect, after]
        if self._centered:
            left = max(0, (self._terminal_width - self._effect_width) // 2)
            right = max(0, self._terminal_width - self._effect_width - left)
            self._first_line_parts = [" " * left, style.frames[0], " " * right]
        else:
            # Inline: build initial line from message (if any)
            message_lines = self._format_message(style.frames[0], message_fdl, self.values, inline=True)
            first_line = message_lines[0] if message_lines else ""
            # The first line already includes frame + message; split to parts
            prefix = style.frames[0]
            self._first_line_parts = ["", prefix, first_line[len(prefix):]]
        # Store full rendered lines (including first line) for redraw on updates
        self._rendered_lines: List[str] = self._render_current_block()

    def _format_message(self, next_frame: str, fdl_string: Optional[str], values: Optional[Tuple], inline: bool) -> List[str]:
        # Remove justify commands to force left
        clean_fdl = self._strip_justify(fdl_string or "")
        combined = f"{next_frame}{clean_fdl}" if inline else f"{next_frame}{clean_fdl}"
        fmt = _Formatter(combined, values or tuple(), None, {_OutputType.TERMINAL})
        fmt.process()
        out = fmt.terminal_output
        # Sanitize any cursor movement from user content
        out = _output_coordinator.sanitize_user_text(out)
        lines = out.split("\n")
        # Ensure at least one line
        return lines if lines else [""]

    def _strip_justify(self, fdl: str) -> str:
        if not fdl:
            return fdl
        # Remove commands like </justify left>, </justify right>, </justify center>, </end justify>
        return re.sub(r"</\s*justify[^>]*>|</\s*end\s+justify\s*>", "", fdl, flags=re.IGNORECASE)

    def _render_current_block(self) -> List[str]:
        # Build first line from parts
        first_line = "".join(self._first_line_parts)
        # For centered with no message, first line only
        if self._centered:
            return [first_line]
        # For inline, we already cached the after-effect remainder in parts; but need to append wrapped remainder lines.
        # We will keep only the first line here; subsequent lines will be rendered from last formatted message on updates.
        return [first_line]

    def _rewrite_first_line(self, new_frame: str) -> None:
        # Replace effect segment and redraw first line only
        self._first_line_parts[1] = new_frame
        first_line = "".join(self._first_line_parts)
        sys.stdout.write("\r")
        sys.stdout.write(first_line)
        sys.stdout.flush()

    def _redraw_all_lines(self, lines: List[str]) -> None:
        # Move cursor up to the first line of the previous block
        if len(self._rendered_lines) > 1:
            sys.stdout.write(f"\x1b[{len(self._rendered_lines)-1}F")
        max_lines = max(len(lines), len(self._rendered_lines))
        for idx in range(max_lines):
            sys.stdout.write("\r")
            sys.stdout.write(" " * self._terminal_width)
            sys.stdout.write("\r")
            if idx < len(lines):
                sys.stdout.write(lines[idx])
            if idx < max_lines - 1:
                sys.stdout.write("\n")
        sys.stdout.flush()
        self._rendered_lines = lines

    def start(self) -> None:
        # Acquire exclusive ownership
        if not _output_coordinator.acquire("effect"):
            _output_coordinator.add_warning("Effect ignored: another display is active.")
            return
        # Initial draw
        if self._centered:
            sys.stdout.write(self._rendered_lines[0])
        else:
            sys.stdout.write(self._rendered_lines[0])
        sys.stdout.flush()
        # Start animation thread
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        index = 0
        while not self._stop_event.is_set():
            frame = self.style.frames[index]
            self._rewrite_first_line(frame)
            index = (index + 1) % len(self.style.frames)
            time.sleep(self.style.interval)

    def update_message(self, new_message_fdl: str, values: Optional[Tuple] = None) -> None:
        # Scenario 2 (inline) or 4 (centered)
        next_frame = self.style.frames[0]  # for normalization run
        lines = self._format_message(next_frame, new_message_fdl, values or self.values, inline=True)
        if self._centered:
            # Keep first-line parts as-is; redraw entire block with updated message lines
            # First line remains centered effect; following lines are message
            new_lines = ["".join(self._first_line_parts)] + lines[1:]
            self._redraw_all_lines(new_lines)
        else:
            # Inline: recompute first-line parts from the first formatted line
            first_line = lines[0] if lines else ""
            # Remove the literal frame once to get message remainder
            after = first_line.replace(self.style.frames[0], "", 1)
            self._first_line_parts = ["", self.style.frames[0], after]
            new_lines = ["".join(self._first_line_parts)] + lines[1:]
            self._redraw_all_lines(new_lines)

    def stop(self, final_message_fdl: Optional[str] = None, values: Optional[Tuple] = None) -> None:
        self._stop_event.set()
        if self._thread is not None:
            self._thread.join(timeout=0.2)
            self._thread = None
        # Render completed frame and optional final message, replacing current message
        completed = self.style.completed
        if final_message_fdl:
            lines = self._format_message(completed, final_message_fdl, values or self.values, inline=not self._centered)
            if self._centered:
                new_lines = ["".join(self._first_line_parts)] + lines[1:]
            else:
                first_line = lines[0] if lines else ""
                after = first_line.replace(completed, "", 1)
                self._first_line_parts = ["", completed, after]
                new_lines = ["".join(self._first_line_parts)] + lines[1:]
            self._redraw_all_lines(new_lines)
        else:
            self._rewrite_first_line(completed)
        # Release ownership and flush buffered outputs and warnings
        _output_coordinator.release("effect")


# Module-level helpers (internal)

def _effects_register(name: str, frames: List[str], completed: str, interval: float, overwrite: bool = False) -> None:
    _effects_registry.register(name, frames, completed, interval, overwrite)


def _effects_start(name: str, message_fdl: Optional[str] = None, values: Optional[Tuple] = None) -> Optional[_ActiveEffect]:
    style = _effects_registry.get(name)
    # Validate width vs terminal
    term = _get_terminal()
    if _get_visual_width(style.frames[0]) > term.width:
        _output_coordinator.add_warning(f"Effect '{name}' exceeds terminal width; using ASCII fallback.")
        style = _effects_registry.get("ascii")
        if _get_visual_width(style.frames[0]) > term.width:
            _output_coordinator.add_warning("ASCII fallback also exceeds terminal width; effect not started.")
            return None
    eff = _ActiveEffect(style, message_fdl, values)
    eff.start()
    return eff


def _effects_update_message(effect: _ActiveEffect, message_fdl: str, values: Optional[Tuple] = None) -> None:
    effect.update_message(message_fdl, values)


def _effects_stop(effect: _ActiveEffect, final_message_fdl: Optional[str] = None, values: Optional[Tuple] = None) -> None:
    effect.stop(final_message_fdl, values)


