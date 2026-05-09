import csv
import argparse

from keyring_reader import detect_default_keyring, detect_keyring_type, read_keyring
from pathlib import Path


def main():
    # Auto-detect default keyring for the help text and startup message.
    default_path, default_kind = detect_default_keyring()
    default_hint = (
        f"{default_path} ({default_kind})" if default_path else "not detected"
    )

    parser = argparse.ArgumentParser(
        description=(
            "Export GNOME Keyring (Seahorse) or KDE Wallet (KWallet) credentials\n"
            "to a CSV file ready for import into KeePassXC\n"
            "(Database → Import → CSV file).\n\n"
            "The script connects to the running keyring daemon via D-Bus, so no\n"
            "password or manual decryption is needed — the daemon handles that\n"
            "after your session is unlocked.\n\n"
            f"Auto-detected keyring: {default_hint}"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  # auto-detect and export all unlocked collections\n"
            "  python run.py --output export.csv\n\n"
            "  # export a specific GNOME keyring binary\n"
            "  python run.py --keyring ~/.local/share/keyrings/login.keyring --output export.csv\n\n"
            "  # export a GNOME collection by label\n"
            "  python run.py --keyring Login --output export.csv\n\n"
            "  # export a KDE wallet binary\n"
            "  python run.py --keyring ~/.local/share/kwalletd/kdewallet.kwl --output export.csv\n\n"
            "notes:\n"
            "  - Locked collections are skipped with a warning.\n"
            "  - The output CSV contains plaintext passwords; delete it after importing.\n"
            "  - For GNOME: pass a .keyring file path or a plain collection label.\n"
            "  - For KDE: pass a .kwl file path; kwalletd must be running.\n"
        ),
    )
    parser.add_argument(
        "--keyring",
        metavar="FILE_OR_LABEL",
        default=None,
        help=(
            "GNOME: path to a .keyring binary or a plain collection label "
            "(e.g. 'Login'). "
            "KDE: path to a .kwl wallet binary "
            "(e.g. ~/.local/share/kwalletd/kdewallet.kwl). "
            "When omitted the keyring type is auto-detected from the default "
            "locations and all unlocked entries are exported."
        ),
    )
    parser.add_argument(
        "--output",
        metavar="CSV_FILE",
        default="keyring_export.csv",
        help="Path for the output CSV file. (default: keyring_export.csv)",
    )
    args = parser.parse_args()

    # Report what we are reading.
    if args.keyring:
        p = Path(args.keyring)
        if p.is_dir():
            print(f"Scanning directory for keyring files: {p}")
        elif p.is_file():
            ktype = detect_keyring_type(p)
            kind_label = ktype.upper() if ktype != "unknown" else "unknown"
            print(f"Reading keyring: {p} (detected: {kind_label})")
        else:
            print(f"Using '{args.keyring}' as GNOME collection label")
    else:
        if default_path:
            print(f"Auto-detected {default_kind} keyring: {default_path}")
        else:
            print(
                "Warning: no default keyring found at the standard locations.\n"
                "Pass --keyring to specify a file or collection label explicitly."
            )

    try:
        entries = read_keyring(args.keyring or "")
    except RuntimeError as exc:
        print(f"Error: {exc}")
        return

    rows = []
    for entry in entries:
        rows.append(
            [
                "Imported",
                entry["label"],
                entry["username"],
                entry["password"],
                entry["server"],
                "Imported from keyring",
            ]
        )

    with open(args.output, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["Group", "Title", "Username", "Password", "URL", "Notes"])
        writer.writerows(rows)

    print(f"Exported {len(rows)} entries to '{args.output}'")


if __name__ == "__main__":
    main()