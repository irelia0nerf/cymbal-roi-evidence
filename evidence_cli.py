"""Issue and verify signed ROI evidence receipts without serializing source payloads."""

import argparse
import json
import os
from pathlib import Path
import sys

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from demo import reject_duplicate_keys
from evidence import (
    create_receipt,
    receipt_digest,
    signing_key_id,
    verify_chain,
    verify_receipt,
    verify_receipt_signature,
)
from merkle import (
    build_merkle_proof,
    create_merkle_manifest,
    verify_merkle_manifest,
    verify_receipt_inclusion,
)


def _read_json(path):
    return json.loads(
        Path(path).read_text(encoding="utf-8"),
        object_pairs_hook=reject_duplicate_keys,
    )


def _read_private_key(path, password_env):
    password = None
    if password_env:
        value = os.environ.get(password_env)
        if value is None:
            raise ValueError(f"variável de ambiente {password_env} não está definida")
        password = value.encode("utf-8")
    try:
        return serialization.load_pem_private_key(
            Path(path).read_bytes(),
            password=password,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("não foi possível carregar a chave privada PEM") from exc


def _read_public_key(path):
    try:
        return serialization.load_pem_public_key(Path(path).read_bytes())
    except (TypeError, ValueError) as exc:
        raise ValueError("não foi possível carregar a chave pública PEM") from exc


def _read_commitment_key(path):
    key = Path(path).read_bytes()
    if len(key) < 32:
        raise ValueError("arquivo da chave HMAC deve conter pelo menos 32 bytes")
    return key


def _write_json(value):
    text = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False)
    sys.stdout.buffer.write((text + "\n").encode("utf-8"))


def _write_artifact(value, output_path):
    text = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n"
    if output_path is None:
        sys.stdout.buffer.write(text.encode("utf-8"))
        return
    with Path(output_path).open("x", encoding="utf-8", newline="\n") as stream:
        stream.write(text)


def _parser():
    parser = argparse.ArgumentParser(
        description="Recibos criptográficos para o motor local de ROI FoundLab."
    )
    commands = parser.add_subparsers(dest="command", required=True)

    issue = commands.add_parser("issue", help="calcula o ROI e emite recibo assinado")
    issue.add_argument("input", help="JSON de entrada; permanece fora do recibo")
    issue.add_argument("--signing-key", required=True, help="chave privada PEM P-256")
    issue.add_argument("--signing-key-password-env",
                       help="variável de ambiente com a senha do PEM")
    issue.add_argument("--commitment-key", required=True,
                       help="arquivo com chave HMAC secreta de pelo menos 32 bytes")
    issue.add_argument("--commitment-key-id", required=True,
                       help="identificador não secreto da chave HMAC")
    issue.add_argument("--previous-receipt",
                       help="recibo anterior a encadear; forneça apenas uma cabeça validada")
    issue.add_argument("--output",
                       help="salva apenas o recibo em arquivo novo; nunca sobrescreve")

    verify = commands.add_parser("verify", help="verifica assinatura e reproduz o cálculo")
    verify.add_argument("input", help="JSON original usado para o cálculo")
    verify.add_argument("receipt", help="recibo assinado")
    verify.add_argument("--public-key", required=True, help="chave pública PEM P-256")
    verify.add_argument("--trusted-signing-key-id", required=True,
                        help="fingerprint sha256:... obtida por canal confiável")
    verify.add_argument("--commitment-key", required=True,
                        help="mesma chave HMAC usada para emitir o recibo")
    verify.add_argument("--commitment-key-id", required=True,
                        help="identificador esperado da chave HMAC")

    chain = commands.add_parser("verify-chain", help="verifica uma sequência encadeada")
    chain.add_argument("--entry", nargs=2, action="append", required=True,
                       metavar=("INPUT", "RECEIPT"),
                       help="par JSON de entrada e recibo; repita na ordem")
    chain.add_argument("--public-key", required=True, help="chave pública PEM P-256")
    chain.add_argument("--trusted-signing-key-id", required=True,
                       help="fingerprint sha256:... obtida por canal confiável")
    chain.add_argument("--commitment-key", required=True,
                       help="mesma chave HMAC usada para emitir os recibos")
    chain.add_argument("--commitment-key-id", required=True,
                       help="identificador esperado da chave HMAC")

    fingerprint = commands.add_parser(
        "fingerprint",
        help="imprime o fingerprint de uma chave pública P-256",
    )
    fingerprint.add_argument("public_key", help="chave pública PEM P-256")

    merkle_build = commands.add_parser(
        "merkle-build",
        help="assina uma raiz Merkle para um lote de recibos",
    )
    merkle_build.add_argument("receipts", nargs="+", help="recibos assinados")
    merkle_build.add_argument("--signing-key", required=True,
                              help="chave privada PEM P-256")
    merkle_build.add_argument("--signing-key-password-env",
                              help="variável de ambiente com a senha do PEM")
    merkle_build.add_argument("--receipt-public-key", required=True,
                              help="chave pública para validar as assinaturas dos recibos")
    merkle_build.add_argument("--trusted-receipt-key-id", required=True,
                              help="fingerprint confiável das chaves dos recibos")
    merkle_build.add_argument("--output", required=True,
                              help="manifesto de saída; precisa ser um arquivo novo")

    merkle_verify = commands.add_parser(
        "merkle-verify",
        help="verifica a inclusão de um recibo em um lote assinado",
    )
    merkle_verify.add_argument("manifest", help="manifesto Merkle assinado")
    merkle_verify.add_argument("receipt", help="recibo a localizar no lote")
    merkle_verify.add_argument("--public-key", required=True,
                               help="chave pública PEM P-256")
    merkle_verify.add_argument("--trusted-signing-key-id", required=True,
                               help="fingerprint sha256:... obtida por canal confiável")
    return parser


def main(argv=None):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")
    args = _parser().parse_args(argv)
    try:
        if args.command == "issue":
            payload = _read_json(args.input)
            private_key = _read_private_key(
                args.signing_key,
                args.signing_key_password_env,
            )
            commitment_key = _read_commitment_key(args.commitment_key)
            previous_digest = None
            if args.previous_receipt:
                previous_digest = receipt_digest(_read_json(args.previous_receipt))
            receipt = create_receipt(
                payload,
                private_key,
                commitment_key,
                args.commitment_key_id,
                previous_digest,
            )
            _write_artifact(receipt, args.output)
            return 0

        if args.command == "fingerprint":
            public_key = _read_public_key(args.public_key)
            if not isinstance(public_key, ec.EllipticCurvePublicKey):
                raise ValueError("a chave pública deve ser ECDSA P-256")
            _write_json({"signing_key_id": signing_key_id(public_key)})
            return 0

        if args.command == "merkle-build":
            private_key = _read_private_key(
                args.signing_key,
                args.signing_key_password_env,
            )
            receipt_public_key = _read_public_key(args.receipt_public_key)
            receipts = [_read_json(path) for path in args.receipts]
            for receipt in receipts:
                verify_receipt_signature(
                    receipt,
                    receipt_public_key,
                    args.trusted_receipt_key_id,
                )
            manifest = create_merkle_manifest(receipts, private_key)
            _write_artifact(manifest, args.output)
            return 0

        if args.command == "merkle-verify":
            manifest = _read_json(args.manifest)
            receipt = _read_json(args.receipt)
            public_key = _read_public_key(args.public_key)
            try:
                verify_merkle_manifest(
                    manifest,
                    public_key,
                    args.trusted_signing_key_id,
                )
                digest = receipt_digest(receipt)
                leaf_index = manifest["receipt_sha256s"].index(digest)
                proof = build_merkle_proof(manifest, leaf_index)
                inclusion = verify_receipt_inclusion(
                    receipt,
                    manifest,
                    proof,
                    public_key,
                    args.trusted_signing_key_id,
                )
            except ValueError as exc:
                print(f"VERIFICAÇÃO FALHOU: {exc}", file=sys.stderr)
                return 1
            except AttributeError as exc:
                print("VERIFICAÇÃO FALHOU: manifesto ou recibo inválido", file=sys.stderr)
                return 1
            _write_json({
                "status": "VERIFIED",
                "receipt_sha256": inclusion.receipt_sha256,
                "merkle_root_sha256": inclusion.merkle_root_sha256,
                "leaf_index": inclusion.leaf_index,
                "leaf_count": inclusion.leaf_count,
            })
            return 0

        public_key = _read_public_key(args.public_key)
        commitment_key = _read_commitment_key(args.commitment_key)
        if args.command == "verify":
            entries = [(_read_json(args.input), _read_json(args.receipt))]
        else:
            entries = [
                (_read_json(input_path), _read_json(receipt_path))
                for input_path, receipt_path in args.entry
            ]
    except (OSError, UnicodeError, ValueError, RecursionError) as exc:
        print(f"Erro: {exc}", file=sys.stderr)
        return 2

    try:
        if args.command == "verify":
            verified = verify_receipt(
                entries[0][0],
                entries[0][1],
                public_key,
                commitment_key,
                args.trusted_signing_key_id,
                args.commitment_key_id,
            )
            _write_json({
                "status": "VERIFIED",
                "decision_id": verified.decision_id,
                "receipt_sha256": verified.receipt_sha256,
                "formula_version": verified.formula_version,
            })
        else:
            verified = verify_chain(
                entries,
                public_key,
                commitment_key,
                args.trusted_signing_key_id,
                args.commitment_key_id,
            )
            _write_json({
                "status": "VERIFIED",
                "receipt_count": len(verified),
                "decision_ids": [item.decision_id for item in verified],
                "chain_head_sha256": verified[-1].receipt_sha256,
            })
    except ValueError as exc:
        print(f"VERIFICAÇÃO FALHOU: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
