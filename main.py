"""Compatibilité : délègue l'exécution à la CLI installable."""

from kairos.cli import main


if __name__ == "__main__":
    raise SystemExit(main())
