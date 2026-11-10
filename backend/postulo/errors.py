"""User-facing errors that are not AI errors (rendering, files...).

`message` is French, understandable and secret-free; `detail` holds the
technical part, shown behind a "details" button. Background jobs show `message`.
"""

from __future__ import annotations


class UserError(Exception):
    def __init__(self, message: str, detail: str = "") -> None:
        super().__init__(message)
        self.message = message
        self.detail = detail
