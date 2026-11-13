import unittest
from datetime import date, timedelta
from agrovision_fieldlab import (
    validate_trial_record, validate_trial_update, relative_difference
)


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
        self.update = {
            "trial_id": "00000000-0000-0000-0000-000000000001",
            "display_alias": "Campo-07",
            "season": "2026/27",
            "observation_date": date.today().isoformat(),
            "stage": "Colheita",
            "arm": "Estratégia",
            "observed_value": 88,
            "unit": "sacas/ha",
            "method": "Pesagem de parcelas com protocolo informado.",
            "notes": "Registro posterior da hipótese."
        }

    def test_valid_record_is_normalized(self):
        result = validate_trial_record(self.record)
        self.assertEqual(result["crop"], "Milho")
        self.assertEqual(result["alternative_value"], 84.0)
        self.assertEqual(result["status"], "community observation")

    def test_invalid_region_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_trial_record(dict(self.record, macroregion="Atlântico"))

    def test_non_finite_measurement_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_trial_record(dict(self.record, baseline_value=float("nan")))

    def test_followup_is_validated(self):
        result = validate_trial_update(self.update)
        self.assertEqual(result["observed_value"], 88.0)
        self.assertEqual(result["season"], "2026/27")

    def test_future_followup_date_is_rejected(self):
        future = (date.today() + timedelta(days=1)).isoformat()
        with self.assertRaises(ValueError):
            validate_trial_update(dict(self.update, observation_date=future))

    def test_non_finite_followup_is_rejected(self):
        with self.assertRaises(ValueError):
            validate_trial_update(dict(self.update, observed_value=float("inf")))

    def test_relative_difference(self):
        self.assertEqual(relative_difference(80, 84), 5.0)
        self.assertIsNone(relative_difference(0, 10))
        self.assertIsNone(relative_difference(None, 10))


if __name__ == "__main__":
    unittest.main()
