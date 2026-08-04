"""Commande installée du moteur interne."""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence

from .moteur import MoteurInterne


def construire_parseur() -> argparse.ArgumentParser:
    parseur = argparse.ArgumentParser(prog="kairos-internal")
    parseur.add_argument(
        "action",
        nargs="?",
        default="on",
        choices=("on", "off", "status"),
        help="lance un cycle, inspecte le dernier rapport ou confirme l'arrêt",
    )
    return parseur


def main(argv: Sequence[str] | None = None) -> int:
    args = construire_parseur().parse_args(argv)
    moteur = MoteurInterne()
    try:
        if args.action == "on":
            payload = moteur.run().vers_dict()
        elif args.action == "status":
            payload = moteur.status()
        else:
            payload = moteur.off()
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return 0
    except (RuntimeError, ValueError) as error:
        print(f"INTERNAL_ENGINE_ERROR: {error}")
        return 1
    finally:
        moteur.close()


if __name__ == "__main__":
    raise SystemExit(main())
