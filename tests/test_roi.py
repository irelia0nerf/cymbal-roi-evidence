import copy
from decimal import getcontext
import io
import json
from pathlib import Path
import subprocess
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout

from demo import main, reject_duplicate_keys
from roi_model import calculate

ROOT = Path(__file__).resolve().parents[1]


class ROITest(unittest.TestCase):
    def setUp(self):
        self.data = {"currency": "BRL", "assumptions": ["Fictício"], "scenarios": [{
            "name": "A", "initial_investment": "1000000.00",
            "annual_benefits": ["700000.00"] * 3,
            "annual_operating_costs": ["200000.00"] * 3}]}

    def result(self):
        return calculate(self.data)["scenarios"][0]

    def test_known_three_year_result(self):
        r = self.result()
        self.assertEqual((r["total_benefits"], r["total_operating_costs"],
                          r["net_result_after_investment"], r["roi_percent"],
                          r["simple_payback_months"]),
                         ("2100000.00", "600000.00", "500000.00", "50.00", "24.00"))

    def test_fractional_payback_and_rounding(self):
        s = self.data["scenarios"][0]
        s.update(initial_investment="100.00", annual_benefits=["300.00"],
                 annual_operating_costs=["0.00"])
        self.assertEqual(self.result()["simple_payback_months"], "4.00")
        s["annual_benefits"] = ["180.00"]
        self.assertEqual(self.result()["simple_payback_months"], "6.67")

    def test_no_payback_and_negative_roi(self):
        self.data["scenarios"][0]["annual_benefits"] = ["100000.00"] * 3
        self.assertEqual(self.result()["roi_percent"], "-130.00")
        self.assertIsNone(self.result()["simple_payback_months"])

    def test_initial_loss_then_recovery(self):
        self.data["scenarios"][0].update(initial_investment="100.00",
            annual_benefits=["0.00", "200.00"], annual_operating_costs=["50.00", "0.00"])
        self.assertEqual(self.result()["simple_payback_months"], "21.00")

    def test_break_even(self):
        self.data["scenarios"][0]["initial_investment"] = "1500000.00"
        self.assertEqual(self.result()["roi_percent"], "0.00")
        self.assertEqual(self.result()["simple_payback_months"], "36.00")

    def test_invalid_money_rejected(self):
        for value in (0, True, None, "-1", "NaN", "Infinity", "1e3", "1.001",
                      "1,00", " 1.00", "1000000000000000", "01.00"):
            with self.subTest(value=value):
                self.data["scenarios"][0]["initial_investment"] = value
                with self.assertRaises(ValueError):
                    calculate(self.data)

    def test_zero_investment_rejected(self):
        self.data["scenarios"][0]["initial_investment"] = "0.00"
        with self.assertRaises(ValueError):
            calculate(self.data)

    def test_horizon_mismatch_rejected(self):
        self.data["scenarios"][0]["annual_benefits"] = ["1.00"]
        with self.assertRaises(ValueError):
            calculate(self.data)

    def test_different_scenario_horizons_rejected(self):
        other = copy.deepcopy(self.data["scenarios"][0])
        other.update(name="B", annual_benefits=["1.00"], annual_operating_costs=["0.00"])
        self.data["scenarios"].append(other)
        with self.assertRaises(ValueError):
            calculate(self.data)

    def test_duplicate_names_rejected(self):
        self.data["scenarios"].append(copy.deepcopy(self.data["scenarios"][0]))
        with self.assertRaises(ValueError):
            calculate(self.data)

    def test_currency_and_unknown_fields_rejected(self):
        self.data["currency"] = "USD"
        with self.assertRaises(ValueError):
            calculate(self.data)
        self.data["currency"] = "BRL"
        self.data["invented"] = True
        with self.assertRaises(ValueError):
            calculate(self.data)

    def test_missing_assumptions_rejected(self):
        self.data["assumptions"] = []
        with self.assertRaises(ValueError):
            calculate(self.data)

    def test_does_not_mutate_input_or_decimal_context(self):
        before = copy.deepcopy(self.data)
        precision = getcontext().prec
        calculate(self.data)
        self.assertEqual(self.data, before)
        self.assertEqual(getcontext().prec, precision)

    def test_cli_missing_file_no_payload(self):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            status = main(["/nonexistent/cymbal.json"])
        self.assertEqual(status, 2)
        self.assertEqual(out.getvalue(), "")
        self.assertIn("Erro:", err.getvalue())

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"currency":"BRL","currency":"USD"}',
                       object_pairs_hook=reject_duplicate_keys)

    def test_example_cli_matches_expected(self):
        run = subprocess.run([sys.executable, str(ROOT / "demo.py"),
                              str(ROOT / "examples/roi_input.json")],
                             capture_output=True, text=True, encoding="utf-8")
        self.assertEqual(run.returncode, 0, run.stderr)
        expected = json.loads((ROOT / "examples/roi_output.expected.json").read_text(
            encoding="utf-8"))
        self.assertEqual(json.loads(run.stdout), expected)


if __name__ == "__main__":
    unittest.main()
