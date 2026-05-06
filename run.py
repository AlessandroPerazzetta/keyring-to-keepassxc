import csv
import argparse
import struct
import secretstorage

GNOME_KEYRING_MAGIC = b"GnomeKeyring\n\r\x00\n"

CRYPTO_TYPES = {0: "AES"}
HASH_TYPES = {0: "MD5"}


def identify_keyring(path):
    """Read a .keyring binary file and return its metadata, or None if not recognised."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError as exc:
        return None, f"Cannot read file: {exc}"

    if data[:16] != GNOME_KEYRING_MAGIC:
        return None, "Not a GNOME keyring file (magic mismatch)"

    if len(data) < 29:  # magic(16) + 4 flag bytes + name_len(4) + at least 1 char
        return None, "File too short to be a valid GNOME keyring"

    major = data[16]
    minor = data[17]
    crypto_type = data[18]
    hash_type = data[19]

    name_len = struct.unpack_from(">I", data, 20)[0]
    if 24 + name_len > len(data):
        return None, "Corrupt keyring: name length exceeds file size"

    name = data[24 : 24 + name_len].decode("utf-8", errors="replace")

    info = {
        "name": name,
        "version": f"{major}.{minor}",
        "crypto": CRYPTO_TYPES.get(crypto_type, f"unknown({crypto_type})"),
        "hash": HASH_TYPES.get(hash_type, f"unknown({hash_type})"),
    }
    return info, None


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Export GNOME Keyring (Seahorse) credentials to a CSV file ready for\n"
            "import into KeePassXC (Database → Import → CSV file).\n\n"
            "The script connects to the running GNOME keyring daemon via D-Bus, so\n"
            "no password or manual decryption is needed — the daemon handles that\n"
            "after your session is unlocked."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  # export a specific keyring by its binary file\n"
            "  python run.py --keyring login.keyring --output export.csv\n\n"
            "  # export a collection by label (case-insensitive)\n"
            "  python run.py --keyring Login --output export.csv\n\n"
            "  # export all unlocked collections\n"
            "  python run.py --output export.csv\n\n"
            "notes:\n"
            "  - Locked collections are skipped with a warning.\n"
            "  - The output CSV contains plaintext passwords; delete it after importing.\n"
            "  - To see available collection labels, run without --keyring (a warning\n"
            "    lists them if none match) or open 'Passwords and Keys' (seahorse).\n"
        ),
    )
    parser.add_argument(
        "--keyring",
        metavar="FILE_OR_LABEL",
        default=None,
        help=(
            "Path to a GNOME .keyring binary file (e.g. login.keyring) OR a plain\n"
            "collection label (e.g. 'Login'). When a file is given, its binary header\n"
            "is parsed to verify it is a valid GNOME keyring and the collection name\n"
            "is extracted from it. If no value is given, all unlocked collections are\n"
            "exported."
        ),
    )
    parser.add_argument(
        "--output",
        metavar="CSV_FILE",
        default="keyring_export.csv",
        help="Path for the output CSV file. (default: keyring_export.csv)",
    )
    args = parser.parse_args()

    label_filter = None
    if args.keyring:
        info, error = identify_keyring(args.keyring)
        if error:
            # Not a file path – treat the argument as a plain collection label
            label_filter = args.keyring
            print(f"Using '{label_filter}' as collection label ({error})")
        else:
            label_filter = info["name"]
            print(
                f"Identified GNOME keyring: '{info['name']}' "
                f"(version {info['version']}, crypto={info['crypto']}, hash={info['hash']})"
            )

    conn = secretstorage.dbus_init()
    all_collections = list(secretstorage.get_all_collections(conn))

    if label_filter:
        collections = [
            c for c in all_collections
            if c.get_label().lower() == label_filter.lower()
        ]
        if not collections:
            labels = [c.get_label() for c in all_collections]
            print(f"No collection matching '{label_filter}'. Available: {labels}")
            return
    else:
        collections = all_collections

    entries = []
    for collection in collections:
        if collection.is_locked():
            print(f"Skipping locked collection: '{collection.get_label()}'")
            continue

        for item in collection.get_all_items():
            label = item.get_label() or ""
            raw_secret = item.get_secret()
            secret = raw_secret.decode("utf-8", errors="replace").rstrip("\x00") if raw_secret else ""
            attrs = item.get_attributes()

            username = (
                attrs.get("account")
                or attrs.get("username")
                or attrs.get("user")
                or ""
            )
            service = (
                attrs.get("service")
                or attrs.get("server")
                or attrs.get("host")
                or ""
            )

            entries.append(
                ["Imported", label, username, secret, service, "Imported from GNOME Keyring"]
            )

    with open(args.output, "w", newline="") as f:
        writer = csv.writer(f, quoting=csv.QUOTE_ALL)
        writer.writerow(["Group", "Title", "Username", "Password", "URL", "Notes"])
        writer.writerows(entries)

    print(f"Exported {len(entries)} entries to '{args.output}'")


if __name__ == "__main__":
    main()