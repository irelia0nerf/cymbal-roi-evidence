"""Signed, privacy-conscious evidence receipts for local ROI decisions."""

import base64
import binascii
from dataclasses import dataclass
import hashlib
import hmac
import json
import re
import uuid
from typing import Any, Sequence

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from roi_model import calculate

RECEIPT_SCHEMA = "foundlab.roi-receipt.v1"
SIGNATURE_ALGORITHM = "ECDSA-P256-SHA256"
COMMITMENT_ALGORITHM = "HMAC-SHA256"
BODY_FIELDS = (
    "schema_version",
    "decision_id",
    "signature_algorithm",
    "signing_key_id",
    "commitment_algorithm",
    "commitment_key_id",
    "formula_version",
    "input_commitment",
    "output_commitment",
    "previous_receipt_sha256",
)
RECEIPT_FIELDS = frozenset((*BODY_FIELDS, "signature"))
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
COMMITMENT_PATTERN = re.compile(r"hmac-sha256:[0-9a-f]{64}\Z")
SIGNATURE_PATTERN = re.compile(r"[A-Za-z0-9_-]+\Z")


@dataclass(frozen=True)
class VerifiedReceipt:
    decision_id: str
    receipt_sha256: str
    formula_version: str
    previous_receipt_sha256: str | None


def canonical_json_bytes(value: Any) -> bytes:
    """Serialize this project's JSON contract deterministically."""
    try:
        text = json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("valor não pode ser serializado como JSON canônico") from exc
    return text.encode("utf-8")


def signing_key_id(public_key: ec.EllipticCurvePublicKey) -> str:
    """Return a SHA-256 fingerprint for a trusted P-256 public key."""
    _require_p256_public_key(public_key)
    encoded = public_key.public_bytes(
        serialization.Encoding.DER,
        serialization.PublicFormat.SubjectPublicKeyInfo,
    )
    return "sha256:" + hashlib.sha256(encoded).hexdigest()


def receipt_digest(receipt: dict[str, Any]) -> str:
    """Hash the complete signed receipt for hash-chain linkage."""
    _validate_receipt_shape(receipt)
    return "sha256:" + hashlib.sha256(canonical_json_bytes(receipt)).hexdigest()


def create_receipt(
    payload: dict[str, Any],
    private_key: ec.EllipticCurvePrivateKey,
    commitment_key: bytes,
    commitment_key_id: str,
    previous_receipt_sha256: str | None = None,
) -> dict[str, Any]:
    """Calculate an ROI and sign keyed commitments without retaining the payload."""
    _require_p256_private_key(private_key)
    _require_commitment_key(commitment_key)
    _require_commitment_key_id(commitment_key_id)
    if previous_receipt_sha256 is not None:
        _require_digest(previous_receipt_sha256, "previous_receipt_sha256")

    result = calculate(payload)
    body = {
        "schema_version": RECEIPT_SCHEMA,
        "decision_id": str(uuid.uuid4()),
        "signature_algorithm": SIGNATURE_ALGORITHM,
        "signing_key_id": signing_key_id(private_key.public_key()),
        "commitment_algorithm": COMMITMENT_ALGORITHM,
        "commitment_key_id": commitment_key_id,
        "formula_version": result["formula_version"],
        "input_commitment": _commitment(commitment_key, payload),
        "output_commitment": _commitment(commitment_key, result),
        "previous_receipt_sha256": previous_receipt_sha256,
    }
    signature = private_key.sign(
        canonical_json_bytes(body),
        ec.ECDSA(hashes.SHA256()),
    )
    receipt = dict(body)
    receipt["signature"] = base64.urlsafe_b64encode(signature).decode("ascii").rstrip("=")
    return receipt


def verify_receipt(
    payload: dict[str, Any],
    receipt: dict[str, Any],
    public_key: ec.EllipticCurvePublicKey,
    commitment_key: bytes,
    expected_signing_key_id: str,
    expected_commitment_key_id: str,
) -> VerifiedReceipt:
    """Verify signer identity, keyed commitments, and deterministic replay."""
    _validate_receipt_shape(receipt)
    _require_commitment_key(commitment_key)
    _require_commitment_key_id(expected_commitment_key_id)
    if receipt["commitment_key_id"] != expected_commitment_key_id:
        raise ValueError("identificador da chave de compromisso não corresponde")
    verify_receipt_signature(receipt, public_key, expected_signing_key_id)

    result = calculate(payload)
    if receipt["formula_version"] != result["formula_version"]:
        raise ValueError("versão da fórmula do recibo não corresponde")
    if not hmac.compare_digest(
        receipt["input_commitment"],
        _commitment(commitment_key, payload),
    ):
        raise ValueError("entrada não corresponde ao compromisso do recibo")
    if not hmac.compare_digest(
        receipt["output_commitment"],
        _commitment(commitment_key, result),
    ):
        raise ValueError("resultado recalculado não corresponde ao recibo")

    return VerifiedReceipt(
        decision_id=receipt["decision_id"],
        receipt_sha256=receipt_digest(receipt),
        formula_version=receipt["formula_version"],
        previous_receipt_sha256=receipt["previous_receipt_sha256"],
    )


def verify_receipt_signature(
    receipt: dict[str, Any],
    public_key: ec.EllipticCurvePublicKey,
    expected_signing_key_id: str,
) -> str:
    """Verify a receipt envelope without asserting its payload commitments."""
    _validate_receipt_shape(receipt)
    _require_p256_public_key(public_key)
    actual_signing_key_id = signing_key_id(public_key)
    if actual_signing_key_id != expected_signing_key_id:
        raise ValueError("chave pública não corresponde à impressão digital confiável")
    if receipt["signing_key_id"] != expected_signing_key_id:
        raise ValueError("recibo assinado por uma chave não confiável")

    signature_text = receipt["signature"]
    try:
        signature = base64.b64decode(
            signature_text + "=" * (-len(signature_text) % 4),
            altchars=b"-_",
            validate=True,
        )
    except (binascii.Error, ValueError) as exc:
        raise ValueError("assinatura do recibo tem formato inválido") from exc

    body = {field: receipt[field] for field in BODY_FIELDS}
    try:
        public_key.verify(
            signature,
            canonical_json_bytes(body),
            ec.ECDSA(hashes.SHA256()),
        )
    except InvalidSignature as exc:
        raise ValueError("assinatura do recibo não é válida") from exc
    return receipt_digest(receipt)


def verify_chain(
    entries: Sequence[tuple[dict[str, Any], dict[str, Any]]],
    public_key: ec.EllipticCurvePublicKey,
    commitment_key: bytes,
    expected_signing_key_id: str,
    expected_commitment_key_id: str,
) -> tuple[VerifiedReceipt, ...]:
    """Verify receipt signatures, input replays, and previous-hash links in order."""
    if not entries:
        raise ValueError("a cadeia precisa conter pelo menos um recibo")

    verified = []
    expected_previous = None
    for payload, receipt in entries:
        _validate_receipt_shape(receipt)
        if receipt["previous_receipt_sha256"] != expected_previous:
            raise ValueError("a cadeia contém um elo anterior inválido")
        result = verify_receipt(
            payload,
            receipt,
            public_key,
            commitment_key,
            expected_signing_key_id,
            expected_commitment_key_id,
        )
        verified.append(result)
        expected_previous = result.receipt_sha256
    return tuple(verified)


def _commitment(key: bytes, value: Any) -> str:
    return "hmac-sha256:" + hmac.new(
        key,
        canonical_json_bytes(value),
        hashlib.sha256,
    ).hexdigest()


def _require_commitment_key(key: bytes) -> None:
    if not isinstance(key, bytes) or len(key) < 32:
        raise ValueError("chave HMAC deve conter pelo menos 32 bytes")


def _require_commitment_key_id(key_id: str) -> None:
    if (
        not isinstance(key_id, str)
        or not key_id.strip()
        or len(key_id) > 256
        or any(ord(char) < 32 for char in key_id)
    ):
        raise ValueError("commitment_key_id deve ser um identificador legível")


def _require_digest(value: str, label: str) -> None:
    if not isinstance(value, str) or not DIGEST_PATTERN.fullmatch(value):
        raise ValueError(f"{label} deve ser um digest SHA-256 hexadecimal")


def _require_p256_private_key(key: Any) -> None:
    if not isinstance(key, ec.EllipticCurvePrivateKey) or key.curve.name != "secp256r1":
        raise ValueError("a chave privada deve usar ECDSA P-256")


def _require_p256_public_key(key: Any) -> None:
    if not isinstance(key, ec.EllipticCurvePublicKey) or key.curve.name != "secp256r1":
        raise ValueError("a chave pública deve usar ECDSA P-256")


def _validate_receipt_shape(receipt: Any) -> None:
    if not isinstance(receipt, dict) or set(receipt) != RECEIPT_FIELDS:
        raise ValueError("campos do recibo inválidos")
    if receipt["schema_version"] != RECEIPT_SCHEMA:
        raise ValueError("versão de recibo não suportada")
    if receipt["signature_algorithm"] != SIGNATURE_ALGORITHM:
        raise ValueError("algoritmo de assinatura não suportado")
    if receipt["commitment_algorithm"] != COMMITMENT_ALGORITHM:
        raise ValueError("algoritmo de compromisso não suportado")
    for field in ("signing_key_id", "formula_version", "signature"):
        if not isinstance(receipt[field], str) or not receipt[field]:
            raise ValueError(f"{field} inválido")
    _require_digest(receipt["signing_key_id"], "signing_key_id")
    _require_commitment_key_id(receipt["commitment_key_id"])
    for field in ("input_commitment", "output_commitment"):
        value = receipt[field]
        if not isinstance(value, str) or not COMMITMENT_PATTERN.fullmatch(value):
            raise ValueError(f"{field} inválido")
    decision_id = receipt["decision_id"]
    try:
        if not isinstance(decision_id, str) or str(uuid.UUID(decision_id)) != decision_id:
            raise ValueError("decision_id deve ser um UUID canônico")
    except (ValueError, AttributeError) as exc:
        raise ValueError("decision_id deve ser um UUID canônico") from exc
    previous = receipt["previous_receipt_sha256"]
    if previous is not None:
        _require_digest(previous, "previous_receipt_sha256")
    signature = receipt["signature"]
    if len(signature) > 256 or not SIGNATURE_PATTERN.fullmatch(signature):
        raise ValueError("assinatura do recibo tem formato inválido")
