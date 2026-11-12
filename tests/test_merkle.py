import copy
import unittest

from cryptography.hazmat.primitives.asymmetric import ec

from evidence import create_receipt, signing_key_id
from merkle import (
    build_merkle_proof,
    create_merkle_manifest,
    verify_merkle_manifest,
    verify_merkle_proof,
    verify_receipt_inclusion,
)

COMMITMENT_KEY_ID = "test-commitment-key-v1"


class MerkleManifestTest(unittest.TestCase):
    def setUp(self):
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        self.public_key = self.private_key.public_key()
        self.key_id = signing_key_id(self.public_key)
        self.commitment_key = b"m" * 32
        self.payloads = [
            {
                "currency": "BRL",
                "assumptions": [f"Teste {index}"],
                "scenarios": [{
                    "name": f"Cenário {index}",
                    "initial_investment": "100.00",
                    "annual_benefits": ["200.00"],
                    "annual_operating_costs": ["0.00"],
                }],
            }
            for index in range(3)
        ]
        self.receipts = [
            create_receipt(
                payload,
                self.private_key,
                self.commitment_key,
                COMMITMENT_KEY_ID,
            )
            for payload in self.payloads
        ]
        self.manifest = create_merkle_manifest(self.receipts, self.private_key)

    def test_signed_manifest_and_all_odd_batch_proofs_verify(self):
        manifest_hash = verify_merkle_manifest(
            self.manifest,
            self.public_key,
            self.key_id,
        )
        self.assertTrue(manifest_hash.startswith("sha256:"))
        for index, receipt in enumerate(self.receipts):
            proof = build_merkle_proof(self.manifest, index)
            self.assertTrue(verify_merkle_proof(
                proof,
                self.manifest["merkle_root_sha256"],
            ))
            result = verify_receipt_inclusion(
                receipt,
                self.manifest,
                proof,
                self.public_key,
                self.key_id,
            )
            self.assertEqual(result.leaf_index, index)
            self.assertEqual(result.leaf_count, 3)

    def test_single_and_even_batch_proofs_verify(self):
        for receipts in (self.receipts[:1], self.receipts[:2]):
            manifest = create_merkle_manifest(receipts, self.private_key)
            verify_merkle_manifest(manifest, self.public_key, self.key_id)
            for index in range(len(receipts)):
                proof = build_merkle_proof(manifest, index)
                self.assertTrue(verify_merkle_proof(
                    proof,
                    manifest["merkle_root_sha256"],
                ))

    def test_tampered_proof_is_rejected(self):
        proof = build_merkle_proof(self.manifest, 2)
        changed = copy.deepcopy(proof)
        changed["siblings"][0]["sha256"] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "nó duplicado|prova não pertence"):
            verify_merkle_proof(changed, self.manifest["merkle_root_sha256"])

    def test_tampered_or_untrusted_manifest_is_rejected(self):
        changed = copy.deepcopy(self.manifest)
        changed["receipt_sha256s"][0] = "sha256:" + "0" * 64
        with self.assertRaisesRegex(ValueError, "raiz Merkle"):
            verify_merkle_manifest(changed, self.public_key, self.key_id)
        with self.assertRaisesRegex(ValueError, "impressão digital confiável"):
            verify_merkle_manifest(
                self.manifest,
                self.public_key,
                "sha256:" + "0" * 64,
            )

    def test_receipt_not_in_manifest_is_rejected(self):
        proof = build_merkle_proof(self.manifest, 0)
        with self.assertRaisesRegex(ValueError, "não referencia este recibo"):
            verify_receipt_inclusion(
                self.receipts[1],
                self.manifest,
                proof,
                self.public_key,
                self.key_id,
            )

    def test_duplicate_and_empty_batches_are_rejected(self):
        with self.assertRaisesRegex(ValueError, "pelo menos um recibo"):
            create_merkle_manifest([], self.private_key)
        with self.assertRaisesRegex(ValueError, "recibos duplicados"):
            create_merkle_manifest(
                [self.receipts[0], self.receipts[0]],
                self.private_key,
            )


if __name__ == "__main__":
    unittest.main()
