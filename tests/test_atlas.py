import unittest
from agrovision_atlas import BIOMES, AGRICULTURAL_HUBS, validate_atlas_catalog

class AtlasCatalogTests(unittest.TestCase):
    def test_catalog_is_valid(self):
        self.assertTrue(validate_atlas_catalog())

    def test_contains_six_ibge_terrestrial_biomes(self):
        self.assertEqual(
            {item["name_pt"] for item in BIOMES},
            {"Amazônia", "Caatinga", "Cerrado", "Mata Atlântica", "Pampa", "Pantanal"},
        )

    def test_agricultural_hubs_are_reference_examples(self):
        self.assertGreaterEqual(len(AGRICULTURAL_HUBS), 5)
        self.assertIn("Rio Verde · GO", {item["name_pt"] for item in AGRICULTURAL_HUBS})

    def test_all_coordinates_are_in_geographic_range(self):
        for item in BIOMES + AGRICULTURAL_HUBS:
            self.assertTrue(-90 <= item["lat"] <= 90)
            self.assertTrue(-180 <= item["lon"] <= 180)

if __name__ == "__main__":
    unittest.main()
