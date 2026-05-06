# keyring-to-keepassxc

Export GNOME Keyring (Seahorse) credentials to a CSV file ready for import into [KeePassXC](https://keepassxc.org/).

The script reads secrets directly from the running GNOME keyring daemon via D-Bus (using `secretstorage`), so **no password or manual decryption is required**. It optionally accepts a `.keyring` binary file to identify and filter the target collection.

## Requirements

- Python 3.7+
- [`secretstorage`](https://pypi.org/project/SecretStorage/) — D-Bus bridge to the GNOME keyring daemon
- A running GNOME keyring daemon (standard on GNOME, Cinnamon, and most Ubuntu/Fedora desktops)

```
pip install secretstorage
```

## Usage

```
python run.py [--keyring <file-or-label>] [--output <output.csv>]
```

| Argument | Default | Description |
|---|---|---|
| `--keyring` | *(all collections)* | Path to a `.keyring` binary file **or** a plain collection label (e.g. `Login`). When a file is given, the keyring name is read from the binary header; if the file is not a valid GNOME keyring, the value is used as-is as a label. |
| `--output` | `keyring_export.csv` | Path for the output CSV file. |

### Examples

Export a specific keyring identified by its binary file:
```
python run.py --keyring login.keyring --output export.csv
```

Export a collection by label:
```
python run.py --keyring Login --output export.csv
```

Export all unlocked collections:
```
python run.py --output export.csv
```

## Output format

The CSV uses KeePassXC's standard import columns:

| Group | Title | Username | Password | URL | Notes |
|---|---|---|---|---|---|
| Imported | entry label | account / username | secret | service / host | Imported from GNOME Keyring |

To import into KeePassXC: **Database → Import → CSV file**, then map the columns when prompted (they match KeePassXC's defaults).

## How it works

1. **Identify** — if a `.keyring` file is provided, the binary header is parsed to verify the GNOME magic bytes and extract the collection name, format version, and crypto/hash types (AES + MD5 is the only supported combination).
2. **Connect** — connects to the GNOME keyring daemon over D-Bus.
3. **Filter** — selects the matching collection (or all unlocked collections if no filter is given).
4. **Export** — reads each item's label, secret, and attributes (`account`, `username`, `service`, `host`, etc.) and writes them to CSV.

Locked collections are skipped with a warning.

## Notes

- The script does **not** decrypt the `.keyring` file itself — it talks to the daemon, which handles decryption after the session is unlocked.
- Secrets are stripped of trailing null bytes (`\x00`) that GNOME keyring appends to some entries.
- The exported CSV contains **plaintext passwords** — handle it accordingly and delete it after importing.
