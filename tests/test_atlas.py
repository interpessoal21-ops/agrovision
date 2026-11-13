import unittest
from agrovision_atlas import BIOMES, AGRICULTURAL_HUBS, validate_atlas_catalog, DATA_LAYERS

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

    def test_official_layer_catalog_has_provenance_and_status(self):
        self.assertEqual(DATA_LAYERS["ana_bho_part1"]["status"], "live_wms")
        self.assertEqual(DATA_LAYERS["ibge_biomes"]["status"], "linked_not_ingested")
        for layer in DATA_LAYERS.values():
            self.assertTrue(layer["source"])
            self.assertTrue(layer["vintage_or_scale"])
            self.assertTrue(layer["limitations"])

if __name__ == "__main__":
    unittest.main()
