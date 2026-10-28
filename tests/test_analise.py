"""Testes automáticos com a base entregue pelo professor."""
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analise import ler_dados, filtrar_dados, indicadores, obter_incidentes, top_usuarios, por_departamento
from relatorio import gerar_relatorio_html


class DashboardTestes(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.df = ler_dados(ROOT / "dados" / "trafego_rede.csv")

    def test_registros_e_identificadores(self):
        self.assertEqual(len(self.df), 2000)
        self.assertEqual(self.df["session_id"].nunique(), 2000)
        self.assertEqual(self.df["user_id"].nunique(), 15)
        self.assertEqual(self.df["department"].nunique(), 12)

    def test_classificacao_de_risco(self):
        k = indicadores(self.df)
        self.assertEqual(k["bloqueados"], 175)
        self.assertEqual(k["alto"], 100)
        self.assertEqual(k["alertas"], 88)
        self.assertEqual(k["incidentes"], 175)  # altos já estão entre bloqueados
        self.assertEqual(len(obter_incidentes(self.df)), 175)
        self.assertEqual(len(obter_incidentes(self.df, "Somente risco alto")), 100)

    def test_totais_bytes_e_arredondamento(self):
        k = indicadores(self.df)
        self.assertAlmostEqual(k["volume_mb"], 51350942629 / 1024**2, places=5)
        self.assertAlmostEqual(k["volume_mb"], k["upload_mb"] + k["download_mb"], places=6)

    def test_agregacoes(self):
        self.assertAlmostEqual(top_usuarios(self.df, 15)["volume_mb"].sum(),
                               indicadores(self.df)["volume_mb"], places=6)
        self.assertAlmostEqual(por_departamento(self.df)["volume_mb"].sum(),
                               indicadores(self.df)["volume_mb"], places=6)

    def test_filtro(self):
        filtro = filtrar_dados(self.df, acoes=["BLOCKED"], riscos=["Alto"])
        self.assertEqual(len(filtro), 100)
        self.assertTrue(filtro["action"].eq("BLOCKED").all())

    def test_html_escapado(self):
        r = self.df.iloc[0].to_dict()
        r["dest_domain"] = "<script>alert(1)</script>"
        pagina = gerar_relatorio_html(r)
        self.assertNotIn("<script>", pagina)
        self.assertIn("&lt;script&gt;", pagina)


if __name__ == "__main__":
    unittest.main()
