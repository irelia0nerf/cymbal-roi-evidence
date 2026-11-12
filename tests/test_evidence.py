import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from evidence import (
    create_receipt,
    receipt_digest,
    signing_key_id,
    verify_chain,
    verify_receipt,
)

ROOT = Path(__file__).resolve().parents[1]
COMMITMENT_KEY_ID = "test-commitment-key-v1"


class EvidenceReceiptTest(unittest.TestCase):
    def setUp(self):
        self.payload = {
            "currency": "BRL",
            "assumptions": ["Premissa confidencial de teste"],
            "scenarios": [{
                "name": "Cliente reservado",
                "initial_investment": "1000000.00",
                "annual_benefits": ["700000.00", "700000.00"],
                "annual_operating_costs": ["200000.00", "200000.00"],
            }],
        }
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        self.public_key = self.private_key.public_key()
        self.commitment_key = b"c" * 32
        self.key_id = signing_key_id(self.public_key)
        self.receipt = create_receipt(
            self.payload,
            self.private_key,
            self.commitment_key,
            COMMITMENT_KEY_ID,
        )

    def verify(self, payload=None, receipt=None, **kwargs):
        return verify_receipt(
            self.payload if payload is None else payload,
            self.receipt if receipt is None else receipt,
            self.public_key,
            self.commitment_key,
            kwargs.get("expected_signing_key_id", self.key_id),
            kwargs.get("expected_commitment_key_id", COMMITMENT_KEY_ID),
        )

    def test_signed_receipt_replays_against_original_input(self):
        result = self.verify()
        self.assertEqual(result.decision_id, self.receipt["decision_id"])
        self.assertEqual(result.receipt_sha256, receipt_digest(self.receipt))
        self.assertEqual(result.formula_version, "simple-roi-v1")

    def test_receipt_contains_commitments_not_payload_values(self):
        encoded = json.dumps(self.receipt, ensure_ascii=False)
        self.assertNotIn("Cliente reservado", encoded)
        self.assertNotIn("Premissa confidencial", encoded)
        self.assertNotIn("1000000.00", encoded)
        self.assertTrue(self.receipt["input_commitment"].startswith("hmac-sha256:"))

    def test_object_key_order_does_not_change_commitment(self):
        reordered = dict(reversed(list(self.payload.items())))
        self.verify(payload=reordered)

    def test_changed_input_fails_commitment_verification(self):
        changed = copy.deepcopy(self.payload)
        changed["scenarios"][0]["annual_benefits"][0] = "710000.00"
        with self.assertRaisesRegex(ValueError, "entrada não corresponde"):
            self.verify(payload=changed)

    def test_wrong_trusted_signing_key_fails(self):
        with self.assertRaisesRegex(ValueError, "impressão digital confiável"):
            self.verify(expected_signing_key_id="sha256:" + "0" * 64)

    def test_wrong_commitment_key_or_id_fails(self):
        with self.assertRaisesRegex(ValueError, "entrada não corresponde"):
            verify_receipt(
                self.payload,
                self.receipt,
                self.public_key,
                b"x" * 32,
                self.key_id,
                COMMITMENT_KEY_ID,
            )
        with self.assertRaisesRegex(ValueError, "identificador da chave"):
            self.verify(expected_commitment_key_id="other-key")

    def test_modified_receipt_signature_fails(self):
        changed = dict(self.receipt)
        changed["output_commitment"] = "hmac-sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "assinatura.*não é válida"):
            self.verify(receipt=changed)

    def test_hash_chain_verifies_order_and_links(self):
        second_payload = copy.deepcopy(self.payload)
        second_payload["scenarios"][0]["name"] = "Cliente seguinte"
        second = create_receipt(
            second_payload,
            self.private_key,
            self.commitment_key,
            COMMITMENT_KEY_ID,
            receipt_digest(self.receipt),
        )
        verified = verify_chain(
            [(self.payload, self.receipt), (second_payload, second)],
            self.public_key,
            self.commitment_key,
            self.key_id,
            COMMITMENT_KEY_ID,
        )
        self.assertEqual(len(verified), 2)
        self.assertEqual(verified[1].previous_receipt_sha256, verified[0].receipt_sha256)

    def test_broken_hash_chain_is_rejected(self):
        second_payload = copy.deepcopy(self.payload)
        bad_link = create_receipt(
            second_payload,
            self.private_key,
            self.commitment_key,
            COMMITMENT_KEY_ID,
            "sha256:" + "0" * 64,
        )
        with self.assertRaisesRegex(ValueError, "elo anterior"):
            verify_chain(
                [(self.payload, self.receipt), (second_payload, bad_link)],
                self.public_key,
                self.commitment_key,
                self.key_id,
                COMMITMENT_KEY_ID,
            )

    def test_non_p256_key_is_rejected(self):
        other_key = ec.generate_private_key(ec.SECP384R1())
        with self.assertRaisesRegex(ValueError, "ECDSA P-256"):
            create_receipt(
                self.payload,
                other_key,
                self.commitment_key,
                COMMITMENT_KEY_ID,
            )

    def test_cli_issue_and_independent_verify(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            input_path = folder / "input.json"
            private_path = folder / "signing-private.pem"
            public_path = folder / "signing-public.pem"
            commitment_path = folder / "commitment.key"
            receipt_path = folder / "receipt.json"
            second_input_path = folder / "input-2.json"
            second_receipt_path = folder / "receipt-2.json"
            environment = os.environ.copy()
            environment["TEST_SIGNING_PASSWORD"] = "demo-passphrase"
            input_path.write_text(json.dumps(self.payload), encoding="utf-8")
            second_payload = copy.deepcopy(self.payload)
            second_payload["scenarios"][0]["name"] = "Cliente seguinte"
            second_input_path.write_text(json.dumps(second_payload), encoding="utf-8")
            private_path.write_bytes(self.private_key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.BestAvailableEncryption(b"demo-passphrase"),
            ))
            public_path.write_bytes(self.public_key.public_bytes(
                serialization.Encoding.PEM,
                serialization.PublicFormat.SubjectPublicKeyInfo,
            ))
            commitment_path.write_bytes(self.commitment_key)

            issued = subprocess.run(
                [sys.executable, str(ROOT / "evidence_cli.py"), "issue",
                 str(input_path), "--signing-key", str(private_path),
                 "--signing-key-password-env", "TEST_SIGNING_PASSWORD",
                 "--commitment-key", str(commitment_path),
                 "--commitment-key-id", COMMITMENT_KEY_ID,
                 "--output", str(receipt_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
            )
            self.assertEqual(issued.returncode, 0, issued.stderr)
            self.assertEqual(issued.stdout, "")
            self.assertNotIn("Cliente reservado", receipt_path.read_text(encoding="utf-8"))

            second_issue = subprocess.run(
                [sys.executable, str(ROOT / "evidence_cli.py"), "issue",
                 str(second_input_path), "--signing-key", str(private_path),
                 "--signing-key-password-env", "TEST_SIGNING_PASSWORD",
                 "--commitment-key", str(commitment_path),
                 "--commitment-key-id", COMMITMENT_KEY_ID,
                 "--previous-receipt", str(receipt_path),
                 "--output", str(second_receipt_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
            )
            self.assertEqual(second_issue.returncode, 0, second_issue.stderr)

            verified = subprocess.run(
                [sys.executable, str(ROOT / "evidence_cli.py"), "verify",
                 str(input_path), str(receipt_path),
                 "--public-key", str(public_path),
                 "--trusted-signing-key-id", self.key_id,
                 "--commitment-key", str(commitment_path),
                 "--commitment-key-id", COMMITMENT_KEY_ID],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(verified.returncode, 0, verified.stderr)
            self.assertEqual(json.loads(verified.stdout)["status"], "VERIFIED")

            chain = subprocess.run(
                [sys.executable, str(ROOT / "evidence_cli.py"), "verify-chain",
                 "--entry", str(input_path), str(receipt_path),
                 "--entry", str(second_input_path), str(second_receipt_path),
                 "--public-key", str(public_path),
                 "--trusted-signing-key-id", self.key_id,
                 "--commitment-key", str(commitment_path),
                 "--commitment-key-id", COMMITMENT_KEY_ID],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(chain.returncode, 0, chain.stderr)
            self.assertEqual(json.loads(chain.stdout)["receipt_count"], 2)

            manifest_path = folder / "merkle-manifest.json"
            merkle_build = subprocess.run(
                [sys.executable, str(ROOT / "evidence_cli.py"), "merkle-build",
                 str(receipt_path), str(second_receipt_path),
                 "--signing-key", str(private_path),
                 "--signing-key-password-env", "TEST_SIGNING_PASSWORD",
                 "--receipt-public-key", str(public_path),
                 "--trusted-receipt-key-id", self.key_id,
                 "--output", str(manifest_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
            )
            self.assertEqual(merkle_build.returncode, 0, merkle_build.stderr)
            merkle_verify = subprocess.run(
                [sys.executable, str(ROOT / "evidence_cli.py"), "merkle-verify",
                 str(manifest_path), str(second_receipt_path),
                 "--public-key", str(public_path),
                 "--trusted-signing-key-id", self.key_id],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(merkle_verify.returncode, 0, merkle_verify.stderr)
            self.assertEqual(
                json.loads(merkle_verify.stdout)["status"],
                "VERIFIED",
            )

            help_output = subprocess.run(
                [sys.executable, str(ROOT / "evidence_cli.py"), "--help"],
                capture_output=True,
                text=True,
                encoding="utf-8",
            )
            self.assertEqual(help_output.returncode, 0)
            self.assertIn("criptográficos", help_output.stdout)

            overwrite = subprocess.run(
                [sys.executable, str(ROOT / "evidence_cli.py"), "issue",
                 str(input_path), "--signing-key", str(private_path),
                 "--signing-key-password-env", "TEST_SIGNING_PASSWORD",
                 "--commitment-key", str(commitment_path),
                 "--commitment-key-id", COMMITMENT_KEY_ID,
                 "--output", str(receipt_path)],
                capture_output=True,
                text=True,
                encoding="utf-8",
                env=environment,
            )
            self.assertEqual(overwrite.returncode, 2)


if __name__ == "__main__":
    unittest.main()
