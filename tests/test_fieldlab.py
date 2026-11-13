import unittest
from agrovision_fieldlab import validate_trial_record, relative_difference


class FieldLabTests(unittest.TestCase):
    def setUp(self):
        self.record = {
            "title": "Cobertura do solo e milho safrinha",
            "display_alias": "Campo-07",
            "macroregion": "Centro-Oeste",
            "crop": "Milho",
            "season": "2025/26",
            "hypothesis": "A cobertura pode reduzir a exposição do solo.",
            "strategy": "Sistema com cobertura vegetal",
            "comparator": "Sistema sem cobertura vegetal",
            "metric": "Produtividade",
            "unit": "sacas/ha",
            "baseline_value": 80,
            "alternative_value": 84,
            "notes": "Valores informados pelo participante."
        }

    def test_valid_record_is_normalized(self):
        result = validate_trial_record(self.record)
        self.assertEqual(result["crop"], "Milho")
        self.assertEqual(result["alternative_value"], 84.0)
        self.assertEqual(result["status"], "community observation")

    def test_invalid_region_is_rejected(self):
        item = dict(self.record, macroregion="Atlântico")
        with self.assertRaises(ValueError):
            validate_trial_record(item)

    def test_non_finite_measurement_is_rejected(self):
        item = dict(self.record, baseline_value=float("nan"))
        with self.assertRaises(ValueError):
            validate_trial_record(item)

    def test_relative_difference(self):
        self.assertEqual(relative_difference(80, 84), 5.0)
        self.assertIsNone(relative_difference(0, 10))
        self.assertIsNone(relative_difference(None, 10))


if __name__ == "__main__":
    unittest.main()
