import unittest
from agrovision_systems import AGRONOMIC_SYSTEMS, validate_catalog

class AgronomicSystemsTests(unittest.TestCase):
    def test_catalog_schema(self):
        self.assertTrue(validate_catalog())

    def test_catalog_has_brazil_relevant_systems(self):
        names = {item["pt"] for item in AGRONOMIC_SYSTEMS}
        self.assertIn("Plantio direto", names)
        self.assertIn("Integração lavoura-pecuária (ILP)", names)
        self.assertIn("Integração lavoura-pecuária-floresta (ILPF)", names)
        self.assertIn("Integração lavoura-floresta (ILF)", names)
        self.assertIn("Integração pecuária-floresta (IPF)", names)
        self.assertIn("Sistemas agroflorestais (SAF)", names)

    def test_catalog_has_unique_portuguese_names(self):
        names = [item["pt"] for item in AGRONOMIC_SYSTEMS]
        self.assertEqual(len(names), len(set(names)))

if __name__ == "__main__":
    unittest.main()
