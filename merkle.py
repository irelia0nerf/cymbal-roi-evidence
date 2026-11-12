"""Signed Merkle batches for already-issued ROI evidence receipts."""

import base64
import binascii
from dataclasses import dataclass
import hashlib
import json
import re
from typing import Any, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from evidence import canonical_json_bytes, receipt_digest, signing_key_id

MANIFEST_SCHEMA = "foundlab.roi-merkle-manifest.v1"
SIGNATURE_ALGORITHM = "ECDSA-P256-SHA256"
BODY_FIELDS = (
    "schema_version",
    "signature_algorithm",
    "signing_key_id",
    "merkle_root_sha256",
    "leaf_count",
    "receipt_sha256s",
)
MANIFEST_FIELDS = frozenset((*BODY_FIELDS, "signature"))
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
SIGNATURE_PATTERN = re.compile(r"[A-Za-z0-9_-]+\Z")


@dataclass(frozen=True)
class VerifiedInclusion:
    receipt_sha256: str
    merkle_root_sha256: str
    leaf_index: int
    leaf_count: int


def create_merkle_manifest(
    receipts: Sequence[dict[str, Any]],
    private_key: ec.EllipticCurvePrivateKey,
) -> dict[str, Any]:
    """Create a signed Merkle root over unique, already-issued receipts."""
    _require_p256_private_key(private_key)
    if not receipts:
        raise ValueError("o lote Merkle precisa conter pelo menos um recibo")
    receipt_hashes = [receipt_digest(receipt) for receipt in receipts]
    if len(set(receipt_hashes)) != len(receipt_hashes):
        raise ValueError("o lote contém recibos duplicados")

    body = {
        "schema_version": MANIFEST_SCHEMA,
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signing_key_id": signing_key_id(private_key.public_key()),
        "merkle_root_sha256": _merkle_root(receipt_hashes),
        "leaf_count": len(receipt_hashes),
        "receipt_sha256s": receipt_hashes,
    }
    signature = private_key.sign(
        canonical_json_bytes(body),
        ec.ECDSA(hashes.SHA256()),
    )
    manifest = dict(body)
    manifest["signature"] = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return manifest


def manifest_digest(manifest: dict[str, Any]) -> str:
    _validate_manifest_shape(manifest)
    return "sha256:" + hashlib.sha256(canonical_json_bytes(manifest)).hexdigest()


def build_merkle_proof(manifest: dict[str, Any], leaf_index: int) -> dict[str, Any]:
    """Build an inclusion proof from a manifest's ordered receipt hashes."""
    _validate_manifest_shape(manifest)
    _require_manifest_root(manifest)
    if isinstance(leaf_index, bool) or not isinstance(leaf_index, int):
        raise ValueError("leaf_index deve ser inteiro")
    hashes_at_level = [
        _leaf_hash(_digest_bytes(value)) for value in manifest["receipt_sha256s"]
    ]
    if not 0 <= leaf_index < len(hashes_at_level):
        raise ValueError("leaf_index fora do lote")

    original_index = leaf_index
    index = leaf_index
    siblings = []
    while len(hashes_at_level) > 1:
        if len(hashes_at_level) % 2:
            hashes_at_level.append(hashes_at_level[-1])
        sibling_index = index - 1 if index % 2 else index + 1
        siblings.append({
            "side": "left" if index % 2 else "right",
            "sha256": "sha256:" + hashes_at_level[sibling_index].hex(),
        })
        hashes_at_level = [
            _parent_hash(hashes_at_level[position], hashes_at_level[position + 1])
            for position in range(0, len(hashes_at_level), 2)
        ]
        index //= 2

    return {
        "receipt_sha256": manifest["receipt_sha256s"][original_index],
        "leaf_index": original_index,
        "leaf_count": manifest["leaf_count"],
        "siblings": siblings,
    }


def verify_merkle_manifest(
    manifest: dict[str, Any],
    public_key: ec.EllipticCurvePublicKey,
    expected_signing_key_id: str,
) -> str:
    """Verify the manifest signature, trusted key, and committed Merkle root."""
    _validate_manifest_shape(manifest)
    _require_p256_public_key(public_key)
    if signing_key_id(public_key) != expected_signing_key_id:
        raise ValueError("chave pública não corresponde à impressão digital confiável")
    if manifest["signing_key_id"] != expected_signing_key_id:
        raise ValueError("manifesto assinado por uma chave não confiável")
    _require_manifest_root(manifest)

    signature_text = manifest["signature"]
    try:
        signature = base64.b64decode(
            signature_text + "=" * (-len(signature_text) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError) as exc:
        raise ValueError("assinatura do manifesto tem formato inválido") from exc

    body = {field: manifest[field] for field in BODY_FIELDS}
    try:
        public_key.verify(
            signature,
            canonical_json_bytes(body),
            ec.ECDSA(hashes.SHA256()),
        )
    except InvalidSignature as exc:
        raise ValueError("assinatura do manifesto não é válida") from exc
    return manifest_digest(manifest)


def verify_merkle_proof(
    proof: dict[str, Any],
    expected_merkle_root_sha256: str,
) -> bool:
    """Verify a domain-separated Merkle inclusion proof."""
    _validate_proof_shape(proof)
    _require_digest(expected_merkle_root_sha256, "merkle_root_sha256")
    current = _leaf_hash(_digest_bytes(proof["receipt_sha256"]))
    index = proof["leaf_index"]
    width = proof["leaf_count"]

    for sibling in proof["siblings"]:
        side = sibling["side"]
        expected_side = "left" if index % 2 else "right"
        if side != expected_side:
            raise ValueError("ordem dos nós do caminho Merkle inválida")
        sibling_hash = _digest_bytes(sibling["sha256"])
        if width % 2 and index == width - 1 and sibling_hash != current:
            raise ValueError("nó duplicado do nível ímpar não corresponde")
        current = (
            _parent_hash(sibling_hash, current)
            if side == "left"
            else _parent_hash(current, sibling_hash)
        )
        index //= 2
        width = (width + 1) // 2

    if width != 1 or "sha256:" + current.hex() != expected_merkle_root_sha256:
        raise ValueError("prova não pertence à raiz Merkle esperada")
    return True


def verify_receipt_inclusion(
    receipt: dict[str, Any],
    manifest: dict[str, Any],
    proof: dict[str, Any],
    public_key: ec.EllipticCurvePublicKey,
    expected_signing_key_id: str,
) -> VerifiedInclusion:
    """Verify a receipt is included in a trusted, signed Merkle manifest."""
    verify_merkle_manifest(manifest, public_key, expected_signing_key_id)
    _validate_proof_shape(proof)
    digest = receipt_digest(receipt)
    index = proof["leaf_index"]
    if proof["receipt_sha256"] != digest:
        raise ValueError("a prova não referencia este recibo")
    if proof["leaf_count"] != manifest["leaf_count"]:
        raise ValueError("quantidade de folhas da prova não corresponde")
    if not 0 <= index < manifest["leaf_count"]:
        raise ValueError("índice da prova fora do manifesto")
    if manifest["receipt_sha256s"][index] != digest:
        raise ValueError("recibo não está listado no manifesto")
    verify_merkle_proof(proof, manifest["merkle_root_sha256"])
    return VerifiedInclusion(
        receipt_sha256=digest,
        merkle_root_sha256=manifest["merkle_root_sha256"],
        leaf_index=index,
        leaf_count=manifest["leaf_count"],
    )


def _leaf_hash(receipt_hash: bytes) -> bytes:
    return hashlib.sha256(b"\x00" + receipt_hash).digest()


def _parent_hash(left: bytes, right: bytes) -> bytes:
    return hashlib.sha256(b"\x01" + left + right).digest()


def _merkle_root(receipt_hashes: Sequence[str]) -> str:
    nodes = [_leaf_hash(_digest_bytes(value)) for value in receipt_hashes]
    if not nodes:
        raise ValueError("a árvore Merkle precisa de pelo menos uma folha")
    while len(nodes) > 1:
        if len(nodes) % 2:
            nodes.append(nodes[-1])
        nodes = [
            _parent_hash(nodes[position], nodes[position + 1])
            for position in range(0, len(nodes), 2)
        ]
    return "sha256:" + nodes[0].hex()


def _require_manifest_root(manifest: dict[str, Any]) -> None:
    if _merkle_root(manifest["receipt_sha256s"]) != manifest["merkle_root_sha256"]:
        raise ValueError("raiz Merkle não corresponde às folhas")


def _validate_manifest_shape(manifest: Any) -> None:
    if not isinstance(manifest, dict) or set(manifest) != MANIFEST_FIELDS:
        raise ValueError("campos do manifesto Merkle inválidos")
    if manifest["schema_version"] != MANIFEST_SCHEMA:
        raise ValueError("versão de manifesto Merkle não suportada")
    if manifest["signature_algorithm"] != SIGNATURE_ALGORITHM:
        raise ValueError("algoritmo de assinatura do manifesto não suportado")
    _require_digest(manifest["signing_key_id"], "signing_key_id")
    _require_digest(manifest["merkle_root_sha256"], "merkle_root_sha256")
    leaves = manifest["receipt_sha256s"]
    count = manifest["leaf_count"]
    if isinstance(count, bool) or not isinstance(count, int) or count < 1:
        raise ValueError("leaf_count inválido")
    if not isinstance(leaves, list) or len(leaves) != count:
        raise ValueError("quantidade de folhas inválida")
    for value in leaves:
        _require_digest(value, "receipt_sha256")
    if len(set(leaves)) != count:
        raise ValueError("manifesto contém recibos duplicados")
    signature = manifest["signature"]
    if (
        not isinstance(signature, str)
        or len(signature) > 256
        or not SIGNATURE_PATTERN.fullmatch(signature)
    ):
        raise ValueError("assinatura do manifesto tem formato inválido")


def _validate_proof_shape(proof: Any) -> None:
    if not isinstance(proof, dict) or set(proof) != {
        "receipt_sha256",
        "leaf_index",
        "leaf_count",
        "siblings",
    }:
        raise ValueError("campos da prova Merkle inválidos")
    _require_digest(proof["receipt_sha256"], "receipt_sha256")
    index = proof["leaf_index"]
    count = proof["leaf_count"]
    if (
        isinstance(index, bool)
        or not isinstance(index, int)
        or isinstance(count, bool)
        or not isinstance(count, int)
        or count < 1
        or not 0 <= index < count
    ):
        raise ValueError("índice ou quantidade de folhas inválidos")
    siblings = proof["siblings"]
    if not isinstance(siblings, list):
        raise ValueError("siblings deve ser uma lista")
    expected_depth = 0
    width = count
    while width > 1:
        expected_depth += 1
        width = (width + 1) // 2
    if len(siblings) != expected_depth:
        raise ValueError("profundidade da prova Merkle inválida")
    for sibling in siblings:
        if (
            not isinstance(sibling, dict)
            or set(sibling) != {"side", "sha256"}
            or sibling["side"] not in ("left", "right")
        ):
            raise ValueError("nó irmão da prova Merkle inválido")
        _require_digest(sibling["sha256"], "sibling.sha256")


def _digest_bytes(value: str) -> bytes:
    _require_digest(value, "digest")
    return bytes.fromhex(value.removeprefix("sha256:"))


def _require_digest(value: Any, label: str) -> None:
    if not isinstance(value, str) or not DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{label} deve ser sha256 seguido de 64 dígitos hexadecimais")


def _require_p256_private_key(key: Any) -> None:
    if not isinstance(key, ec.EllipticCurvePrivateKey) or key.curve.name != "secp256r1":
        raise ValueError("a chave privada deve usar ECDSA P-256")


def _require_p256_public_key(key: Any) -> None:
    if not isinstance(key, ec.EllipticCurvePublicKey) or key.curve.name != "secp256r1":
        raise ValueError("a chave pública deve usar ECDSA P-256")
