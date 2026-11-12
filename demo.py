"""CLI local do estudo de ROI FoundLab.

Uso: python demo.py examples/roi_input.json
"""

import json
from pathlib import Path
import sys
from roi_model import calculate


def reject_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("JSON contém chave duplicada")
        result[key] = value
    return result


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1:
        print("Uso: python3 demo.py CAMINHO_JSON", file=sys.stderr)
        return 2
    try:
        payload = json.loads(Path(args[0]).read_text(encoding="utf-8"),
                             object_pairs_hook=reject_duplicate_keys)
        result = calculate(payload)
    except (OSError, UnicodeError, ValueError, RecursionError):
        print("Erro: arquivo ilegível ou entrada fora do contrato. Consulte docs/04-garantias-e-limites.md.",
              file=sys.stderr)
        return 2
    output = json.dumps(result, indent=2, ensure_ascii=False, allow_nan=False)
    sys.stdout.buffer.write((output + "\n").encode("utf-8"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
