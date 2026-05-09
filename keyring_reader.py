"""Keyring credential reader — auto-detects GNOME or KDE wallet and dispatches
to the appropriate backend module.

Supported backends
------------------
  GNOME Keyring  (.keyring binary or collection label)
                 via the secretstorage / org.freedesktop.Secret.Service D-Bus API.
                 Default path: ~/.local/share/keyrings/login.keyring

  KDE Wallet     (.kwl binary)
                 via kwalletd's SecretService D-Bus compatibility layer.
                 Default path: ~/.local/share/kwalletd/kdewallet.kwl
"""

from __future__ import annotations

from pathlib import Path

from _keyring_gnome import is_gnome_keyring, read_gnome_keyring
from _keyring_kde import is_kde_wallet, read_kde_keyring

# Default keyring file locations for each desktop environment.
GNOME_DEFAULT = Path.home() / ".local/share/keyrings/login.keyring"
KDE_DEFAULT   = Path.home() / ".local/share/kwalletd/kdewallet.kwl"


def detect_keyring_type(path: Path) -> str:
    """Return ``'gnome'``, ``'kde'``, or ``'unknown'`` based on magic bytes."""
    if is_gnome_keyring(path):
        return "gnome"
    if is_kde_wallet(path):
        return "kde"
    return "unknown"


def detect_default_keyring() -> tuple[Path | None, str | None]:
    """Probe default locations and return ``(path, kind)`` for the first valid keyring found.

    *kind* is ``'GNOME'``, ``'KDE'``, or ``None`` when nothing is found.
    """
    if GNOME_DEFAULT.is_file() and is_gnome_keyring(GNOME_DEFAULT):
        return GNOME_DEFAULT, "GNOME"
    if KDE_DEFAULT.is_file() and is_kde_wallet(KDE_DEFAULT):
        return KDE_DEFAULT, "KDE"
    return None, None


def _find_keyring_in_dir(directory: Path) -> tuple[Path | None, str]:
    """Scan *directory* for a recognised keyring file.

    Returns ``(path, kind)`` for the first match, or ``(None, '')`` if none
    is found.  GNOME ``.keyring`` files are preferred over KDE ``.kwl`` files
    when both are present.
    """
    for candidate in sorted(directory.iterdir()):
        if not candidate.is_file():
            continue
        if is_gnome_keyring(candidate):
            return candidate, "gnome"
        if is_kde_wallet(candidate):
            return candidate, "kde"
    return None, ""


def read_keyring(keyring_arg: str) -> list[dict]:
    """Detect keyring type and return a normalised list of credential dicts.

    Each dict has keys: label, username, password, server, attributes.

    keyring_arg may be:
    - A file path to a .keyring binary  → GNOME (label extracted from header)
    - A file path to a .kwl binary      → KDE
    - A directory path                  → scanned for the first valid keyring file
    - A plain collection label string   → GNOME (label passed directly)
    - An empty string / None            → GNOME (all unlocked collections)

    Raises RuntimeError with a user-friendly message on any validation or
    connection error so the caller can halt and display the error cleanly.
    """
    if keyring_arg:
        p = Path(keyring_arg)
        if p.is_dir():
            found, ktype = _find_keyring_in_dir(p)
            if found is None:
                raise RuntimeError(
                    f"No recognised keyring file found in directory: {p}"
                )
            print(f"Found {ktype.upper()} keyring in directory: {found}")
            p = found
        if p.is_file():
            ktype = detect_keyring_type(p)
            if ktype == "kde":
                return read_kde_keyring(p)
            # "gnome" or "unknown" → GNOME reader handles both cases
            return read_gnome_keyring(str(p))
    return read_gnome_keyring(keyring_arg or "")
