#!/usr/bin/env python3
"""Encrypt a lecture-note PDF so it can be published but not read without a password.

GitHub Pages serves this site as static files out of a public repo, so there is no
way to stop someone downloading a PDF. Encrypting the file itself is the next best
thing: the bytes are public, the contents are not.

    python3 scripts/lock-note.py Physics627Lec.pdf

Reads the plaintext original from private/notes/ and writes the encrypted copy to
files/notes/, which is what Quarto copies into docs/ and publishes. private/ is
gitignored, so the readable version never enters the repo or its history.

The password is taken from $NOTE_PASSWORD if set, otherwise prompted for. It is
never echoed and never written anywhere.

Re-run the same command any time to change the password.
"""

import argparse
import getpass
import os
import sys
from pathlib import Path

import pikepdf

REPO = Path(__file__).resolve().parent.parent
PLAINTEXT_DIR = REPO / "private" / "notes"
PUBLISHED_DIR = REPO / "files" / "notes"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("name", help="PDF filename")
    args = parser.parse_args()

    source = PLAINTEXT_DIR / Path(args.name).name
    target = PUBLISHED_DIR / Path(args.name).name

    if not source.exists():
        sys.exit(f"No plaintext original at {source.relative_to(REPO)}")

    password = os.environ.get("NOTE_PASSWORD")
    if not password:
        try:
            password = getpass.getpass("Password: ")
        except EOFError:
            sys.exit("No password given (no terminal to prompt on); nothing written.")
    if not password:
        sys.exit("Empty password; nothing written.")

    # If the original opens without a password it is readable, which is what we want
    # to encrypt. If it does not, private/ is not holding a usable original.
    try:
        pdf = pikepdf.open(source)
    except pikepdf.PasswordError:
        sys.exit(
            f"{source.name} is already password-protected. "
            f"Keep the unlocked original in {PLAINTEXT_DIR.relative_to(REPO)}/."
        )

    with pdf:
        pdf.save(
            target,
            encryption=pikepdf.Encryption(user=password, owner=password, R=6),
        )

    # Confirm the published copy actually refuses to open without the password.
    try:
        pikepdf.open(target)
    except pikepdf.PasswordError:
        pass
    else:
        sys.exit(f"{target.name} opened without a password; encryption did not apply.")

    with pikepdf.open(target, password=password) as pdf:
        pages = len(pdf.pages)

    size_mb = target.stat().st_size / 1_000_000
    print(f"Locked {target.relative_to(REPO)} ({pages} pages, {size_mb:.1f} MB)")
    print(f"Card entry: fileSize: '{size_mb:.1f} MB'")
    print("Next: quarto render notes.qmd   (docs/ still has the previous copy)")


if __name__ == "__main__":
    main()
