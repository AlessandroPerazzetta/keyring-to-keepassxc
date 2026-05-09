# keyring-to-keepassxc

Export **GNOME Keyring** (Seahorse) or **KDE Wallet** (KWallet) credentials to a CSV file ready for import into [KeePassXC](https://keepassxc.org/).

The script auto-detects the keyring in use, connects to the running daemon via D-Bus (using `secretstorage`), and exports all unlocked entries — **no password or manual decryption is required**.

## Requirements

- Python 3.10+
- [`secretstorage`](https://pypi.org/project/SecretStorage/) — D-Bus bridge to the keyring daemon
- A running keyring daemon:
  - **GNOME**: `gnome-keyring-daemon` (standard on GNOME, Cinnamon, most Ubuntu/Fedora desktops)
  - **KDE**: `kwalletd5` / `kwalletd6` with its SecretService compatibility layer enabled

```
pip install -r requirements.txt
```

## Usage

```
python run.py [--keyring <file-or-label>] [--output <output.csv>]
```

| Argument | Default | Description |
|---|---|---|
| `--keyring` | *(auto-detect)* | **GNOME**: path to a `.keyring` binary file or a plain collection label (e.g. `Login`). **KDE**: path to a `.kwl` wallet binary. When omitted, the default location for each desktop is probed automatically. |
| `--output` | `keyring_export.csv` | Path for the output CSV file. |

### Examples

Auto-detect the current keyring and export everything:
```
python run.py --output export.csv
```

Export a specific GNOME keyring binary:
```
python run.py --keyring ~/.local/share/keyrings/login.keyring --output export.csv
```

Export a GNOME collection by label:
```
python run.py --keyring Login --output export.csv
```

Export a KDE wallet binary:
```
python run.py --keyring ~/.local/share/kwalletd/kdewallet.kwl --output export.csv
```

## Output format

The CSV uses KeePassXC's standard import columns:

| Group | Title | Username | Password | URL | Notes |
|---|---|---|---|---|---|
| Imported | entry label | account / username | secret | service / host | Imported from keyring |

To import into KeePassXC: **Database → Import → CSV file**, then map the columns when prompted (they match KeePassXC's defaults).

## How it works

The codebase is split into three layers:

### `keyring_reader.py` — auto-detection dispatcher

- `detect_keyring_type(path)` — reads the first bytes of a file and returns `'gnome'`, `'kde'`, or `'unknown'`.
- `detect_default_keyring()` — probes the standard paths (`~/.local/share/keyrings/login.keyring` for GNOME, `~/.local/share/kwalletd/kdewallet.kwl` for KDE) and returns the first valid one found.
- `read_keyring(arg)` — routes to the correct backend based on file magic, then returns a normalised `list[dict]` with keys `label`, `username`, `password`, `server`, `attributes`.

### `_keyring_gnome.py` — GNOME backend

1. If a `.keyring` file is given, its binary header is parsed (GNOME magic bytes + embedded collection name).
2. Connects to the GNOME keyring daemon over D-Bus.
3. Filters collections by label (or reads all unlocked ones).
4. Returns normalised credential dicts.

### `_keyring_kde.py` — KDE backend

1. Validates the `.kwl` file magic bytes.
2. Optionally loads a companion `{stem}_attributes.json` index to supplement item attributes not always exposed by kwalletd's SecretService layer.
3. Connects to kwalletd over D-Bus (SecretService compatibility mode).
4. Matches the collection by wallet name (`.kwl` stem) and returns normalised credential dicts.

Locked collections are skipped with a warning in both backends.

## Notes

- The script does **not** decrypt keyring files directly — it talks to the daemon, which handles decryption after the session is unlocked.
- Secrets are stripped of trailing null bytes (`\x00`) that some keyring implementations append.
- The exported CSV contains **plaintext passwords** — handle it accordingly and delete it after importing.
- KDE: `kwalletd` must have the *SecretService* interface enabled (`System Settings → KWallet → Enable the KDE Wallet subsystem → Also expose via SecretService`).
