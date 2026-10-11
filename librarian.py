"""Portable convenience wrapper; prefer ``python -m librarian``."""
from librarian.__main__ import main

if __name__ == '__main__':
    raise SystemExit(main())
