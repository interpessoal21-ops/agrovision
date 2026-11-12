import unittest
import pandas as pd

from agrovision_zarc import (
    crop_matches_app_crop,
    decode_risk,
    decendio_columns,
    expand_decendios,
    filter_zarc_rows,
)


class ZarcDataTests(unittest.TestCase):
    def setUp(self):
        self.frame = pd.DataFrame([
            {
                "Nome_cultura": "Soja", "UF": "GO", "municipio": "Rio Verde",
                "Cod_Solo": "11", "Cod_Ciclo": "20", "Nome_Outros_Manejos": "Sequeiro",
                "Nome_Clima": "Clima Tropical", "Portaria": "Portaria SPA/MAPA",
                "dec1": "20", "dec2": "30", "dec3": "0", "dec4": "",
            },
            {
                "Nome_cultura": "Milho", "UF": "GO", "municipio": "Rio Verde",
                "Cod_Solo": "11", "Cod_Ciclo": "21", "Nome_Outros_Manejos": "Sequeiro",
                "Nome_Clima": "Clima Tropical", "Portaria": "Portaria SPA/MAPA",
                "dec1": "40", "dec2": "0", "dec3": "", "dec4": "",
            },
        ])

    def test_exact_filters_do_not_mix_crops(self):
        result = filter_zarc_rows(self.frame, {
            "crop": "Soja", "uf": "GO", "municipality": "Rio Verde",
            "soil": "11", "cycle": "20"
        })
        self.assertEqual(len(result), 1)
        self.assertEqual(result.iloc[0]["Nome_cultura"], "Soja")

    def test_decendio_columns_and_risk_values_are_preserved(self):
        columns = decendio_columns(self.frame)
        self.assertEqual(sorted(columns), [1, 2, 3, 4])
        periods = expand_decendios(self.frame.iloc[0], columns)
        self.assertEqual([p["Risco (%)"] for p in periods], [20, 30, 0])
        self.assertEqual(periods[0]["Mês"], "Janeiro")
        self.assertEqual(periods[2]["Período"], "21–fim")

    def test_zero_is_not_recommended_and_not_a_risk_percentage(self):
        self.assertEqual(decode_risk("0")["label"], "Fora da janela recomendada (0)")
        self.assertEqual(decode_risk("40")["risk"], 40)
        self.assertIsNone(decode_risk("") )

    def test_crop_aliases_match_official_portuguese_names(self):
        self.assertTrue(crop_matches_app_crop("Feijão-comum", "Common bean (dry)"))
        self.assertTrue(crop_matches_app_crop("Milho 2ª safra", "Maize (grain)"))
        self.assertFalse(crop_matches_app_crop("Soja", "Maize (grain)"))


if __name__ == "__main__":
    unittest.main()
