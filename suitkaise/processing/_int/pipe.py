"""
Pipe wrapper for fast, direct, and rigid parent/child communication.

Design goals:
- Keep pipes fast (uses multiprocessing.Pipe under the hood)
- Provide explicit lock semantics (anchor endpoint stays in parent)
- Use cerial for send/recv payloads
- No post-init reattachment
- ensure OH is minimal
"""

from __future__ import annotations

from dataclasses import dataclass
import multiprocessing
import pickle
from typing import Any, Optional, Tuple

from suitkaise import cerial


class PipeEndpointError(RuntimeError):
    """Raised when a pipe endpoint is misused or unpaired."""


@dataclass
class _PipeEndpoint:
    _conn: Optional[Any]
    _locked: bool = False
    _role: str = "point"  # "anchor" or "point"

    def lock(self) -> None:
        """Prevent this endpoint from being transferred."""
        self._locked = True

    def unlock(self) -> None:
        """Allow this endpoint to be transferred."""
        self._locked = False

    @property
    def locked(self) -> bool:
        return self._locked

    def _ensure_conn(self) -> Any:
        if self._conn is None:
            raise PipeEndpointError(
                "Pipe endpoint has no peer. It must be handed off at process start."
            )
        return self._conn

    def send(self, obj: Any) -> None:
        """Serialize with cerial and send through the pipe."""
        conn = self._ensure_conn()
        conn.send_bytes(cerial.serialize(obj))

    def recv(self) -> Any:
        """Receive from the pipe and deserialize with cerial."""
        conn = self._ensure_conn()
        data = conn.recv_bytes()
        return cerial.deserialize(data)

    def close(self) -> None:
        """Close the underlying connection if present."""
        if self._conn is not None:
            try:
                self._conn.close()
            except OSError:
                pass
            finally:
                self._conn = None

    def __reduce__(self):
        """
        Allow endpoint to be transferred at process start.
        Locked endpoints are not transferable.
        """
        if self._locked:
            raise PipeEndpointError(
                "Locked pipe endpoint cannot be transferred. "
                "Keep it in the parent process."
            )
        return (self.__class__._rebuild, (self._conn, self._locked, self._role))

    def __serialize__(self) -> dict:
        """
        Custom cerial serialization.

        We store a pickled handle so multiprocessing can rebuild it
        when deserialized in a child process.
        """
        if self._locked:
            raise PipeEndpointError(
                "Locked pipe endpoint cannot be serialized. "
                "Keep it in the parent process."
            )
        if self._conn is None:
            raise PipeEndpointError(
                "Pipe endpoint has no peer. It must be handed off at process start."
            )
        payload = pickle.dumps(self._conn)
        return {
            "conn_pickle": payload,
            "locked": self._locked,
            "role": self._role,
        }

    @classmethod
    def __deserialize__(cls, state: dict) -> "_PipeEndpoint":
        conn = pickle.loads(state["conn_pickle"])
        return cls(conn, state.get("locked", False), state.get("role", "point"))

    @classmethod
    def _rebuild(
        cls,
        conn: Optional[Any],
        locked: bool,
        role: str,
    ) -> "_PipeEndpoint":
        return cls(conn, locked, role)


class Pipe:
    """
    Pipe wrapper with anchor/point semantics.
    """

    class Anchor(_PipeEndpoint):
        def __init__(
            self,
            conn: Optional[Any],
            locked: bool = True,
            role: str = "anchor",
        ):
            super().__init__(conn, True, role)

        def unlock(self) -> None:
            """Anchor endpoints are always locked."""
            raise PipeEndpointError("Anchor endpoints are always locked.")

    class Point(_PipeEndpoint):
        pass

    @staticmethod
    def pair(one_way: bool = False) -> Tuple["Pipe.Anchor", "Pipe.Point"]:
        """
        Create a pipe pair.

        Args:
            one_way: If True, creates a one-way pipe (duplex=False).

        Returns:
            (anchor, point) where anchor is locked by default.
        """
        conn1, conn2 = multiprocessing.Pipe(duplex=not one_way)
        anchor = Pipe.Anchor(conn1)
        point = Pipe.Point(conn2, False, "point")
        return anchor, point
