import hashlib
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import actualizar_indicadores as modulo


class IndicadoresTests(unittest.TestCase):
    def setUp(self):
        self.temporal = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporal.cleanup)
        self.raiz = Path(self.temporal.name)
        (self.raiz / 'assets').mkdir()
        (self.raiz / 'README.md').write_text(
            '<h1>Perfil sin cambios</h1>\n<img src="./assets/seguidores.svg"><img src="./assets/estrellas.svg">\n',
            encoding='utf-8',
        )

    def contenidos(self):
        return {p.name: p.read_bytes() for p in self.raiz.rglob('*') if p.is_file()}

    def test_actualiza_valores_pagina_repos_y_versiona_sin_duplicar(self):
        with patch.object(modulo, 'consultar', side_effect=[{'followers': 109}, [{'stargazers_count': 1}] * 100, [{'stargazers_count': 34}]]) as api:
            modulo.actualizar(self.raiz)
        self.assertEqual(api.call_count, 3)
        self.assertIn('page=2', api.call_args.args[0])
        readme = (self.raiz / 'README.md').read_text(encoding='utf-8')
        for nombre, valor in [('seguidores', 109), ('estrellas', 134)]:
            svg = self.raiz / 'assets' / (nombre + '.svg')
            self.assertIn(f'>{valor}</text>', svg.read_text(encoding='utf-8'))
            version = hashlib.sha256(svg.read_bytes()).hexdigest()[:12]
            self.assertIn(f'./assets/{nombre}.svg?v={version}', readme)
        antes = self.contenidos()
        with patch.object(modulo, 'consultar', side_effect=[{'followers': 109}, [{'stargazers_count': 134}]]):
            modulo.actualizar(self.raiz)
        self.assertEqual(self.contenidos(), antes)

    def test_error_api_no_sobrescribe_ultimo_resultado(self):
        antes = self.contenidos()
        with patch.object(modulo, 'consultar', side_effect=[{'followers': 110}, RuntimeError('API no disponible')]):
            with self.assertRaises(RuntimeError):
                modulo.actualizar(self.raiz)
        self.assertEqual(self.contenidos(), antes)

    def test_nueva_cantidad_cambia_url_y_preserva_resto_readme(self):
        with patch.object(modulo, 'consultar', side_effect=[{'followers': 109}, []]):
            modulo.actualizar(self.raiz)
        antes = (self.raiz / 'README.md').read_text(encoding='utf-8')
        with patch.object(modulo, 'consultar', side_effect=[{'followers': 110}, []]):
            modulo.actualizar(self.raiz)
        despues = (self.raiz / 'README.md').read_text(encoding='utf-8')
        self.assertNotEqual(antes, despues)
        self.assertEqual(despues.count('?v='), 2)
        self.assertTrue(despues.startswith('<h1>Perfil sin cambios</h1>'))

    def test_referencia_ausente_falla_sin_escribir_archivos(self):
        (self.raiz / 'README.md').write_text('Otro formato', encoding='utf-8')
        antes = self.contenidos()
        with patch.object(modulo, 'consultar', side_effect=[{'followers': 109}, []]):
            with self.assertRaises(ValueError):
                modulo.actualizar(self.raiz)
        self.assertEqual(self.contenidos(), antes)


if __name__ == '__main__':
    unittest.main()
