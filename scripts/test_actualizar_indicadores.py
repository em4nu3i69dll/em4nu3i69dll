from datetime import date, datetime, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import xml.etree.ElementTree as ET

import actualizar_indicadores as modulo


class IndicadoresTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        (self.raiz / "assets").mkdir()
        self.readme = self.raiz / "README.md"
        self.readme.write_text("Perfil\n" + "\n".join("./assets/" + nombre + ".svg" for nombre in ["seguidores", "estrellas", "github", "lenguajes", "racha"]), encoding="utf-8")
        self.ahora = datetime(2026, 11, 4, 15, tzinfo=timezone.utc)
        self.dias = {date(2026, 11, 3): 3, date(2026, 11, 4): 4}

    def api(self, ruta, datos=None):
        if ruta.startswith("users/") and "/repos?" not in ruta:
            return {"followers": 152, "public_repos": 3, "created_at": "2025-12-10T23:05:10Z"}
        if "/repos?" in ruta:
            return [
                {"name": "propio", "fork": False, "stargazers_count": 5},
                {"name": "fork", "fork": True, "stargazers_count": 2},
            ]
        if ruta.endswith("/languages"):
            self.assertNotIn("/fork/", ruta)
            return {"Python": 300, "JavaScript": 100}
        self.fail(ruta)

    def generar(self):
        with patch.object(modulo, "consultar", side_effect=self.api), patch.object(modulo, "contribuciones", return_value=(self.dias, 12, 1, 2)):
            modulo.actualizar(self.raiz, self.ahora)

    def contenidos(self):
        return {str(p.relative_to(self.raiz)): p.read_bytes() for p in self.raiz.rglob("*") if p.is_file()}

    def test_genera_cinco_imagenes_validas_y_versiona_sin_duplicar(self):
        self.generar()
        for archivo in (self.raiz / "assets").glob("*.svg"):
            ET.fromstring(archivo.read_text(encoding="utf-8"))
        self.assertEqual(len(list((self.raiz / "assets").glob("*.svg"))), 5)
        self.assertIn("75.0%", (self.raiz / "assets/lenguajes.svg").read_text())
        self.assertIn(">152</text>", (self.raiz / "assets/seguidores.svg").read_text())
        self.assertEqual(self.readme.read_text().count("?v="), 5)
        antes = self.contenidos()
        self.generar()
        self.assertEqual(self.contenidos(), antes)

    def test_fallo_de_api_conserva_todas_las_imagenes(self):
        self.generar()
        antes = self.contenidos()
        with patch.object(modulo, "consultar", side_effect=RuntimeError("API no disponible")):
            with self.assertRaises(RuntimeError):
                modulo.actualizar(self.raiz, self.ahora)
        self.assertEqual(self.contenidos(), antes)

    def test_referencia_ausente_no_deja_actualizacion_parcial(self):
        self.generar()
        self.readme.write_text("Otro formato", encoding="utf-8")
        antes = self.contenidos()
        with self.assertRaises(ValueError):
            self.generar()
        self.assertEqual(self.contenidos(), antes)

    def test_racha_permite_ayer_y_se_interrumpe_por_un_dia_sin_actividad(self):
        self.assertEqual(modulo.rachas(self.dias, date(2026, 11, 4)), (2, 2))
        self.assertEqual(modulo.rachas(self.dias, date(2026, 11, 5)), (2, 2))
        self.assertEqual(modulo.rachas(self.dias, date(2026, 11, 6)), (0, 2))
        self.assertEqual(modulo.rachas({date(2026, 11, 1): 1, date(2026, 11, 3): 1}, date(2026, 11, 4)), (1, 1))

    def test_calendario_no_duplica_semanas_entre_anios(self):
        def calendario(ruta, datos):
            self.assertEqual(ruta, "graphql")
            return {"data": {"user": {"contributionsCollection": {
                "totalCommitContributions": 7, "totalPullRequestContributions": 1, "totalIssueContributions": 2,
                "contributionCalendar": {"weeks": [{"contributionDays": [
                    {"date": "2025-12-31", "contributionCount": 3},
                    {"date": "2026-01-01", "contributionCount": 4},
                ]}]},
            }}}}
        with patch.object(modulo, "consultar", side_effect=calendario):
            dias, commits, _, _ = modulo.contribuciones({"created_at": "2025-12-10T23:05:10Z"}, self.ahora)
        self.assertEqual(sum(dias.values()), 7)
        self.assertEqual(commits, 7)


if __name__ == "__main__":
    unittest.main()

