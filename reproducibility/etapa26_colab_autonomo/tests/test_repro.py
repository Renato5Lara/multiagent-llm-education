"""Pruebas de la biblioteca de reproduccion (sin red). Ejecutar:  python -m unittest discover -s tests -v   (desde etapa26_colab_autonomo/)"""
import json
import os
import re
import sys
import tempfile
import unittest
import zipfile

AQUI = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(AQUI, '..', 'src'))
from repro import data_loading, validation  # noqa: E402

MAN = os.path.join(AQUI, '..', 'manifests', 'data_manifest.json')
VAL = os.path.join(AQUI, '..', 'manifests', 'valores_oficiales.json')


def _res(**kw):
    base = dict(estructura_igual=True, n_hojas=10, n_numericas=10, n_con_diferencia=0, max_abs=0.0, max_rel=0.0, peor=None, fuera_tol=[])
    base.update(kw)
    return base


class Clasificacion(unittest.TestCase):
    def test_exacta(self):
        self.assertEqual(validation.clasificar(_res())[0], 'EXACTA')

    def test_dentro_de_tolerancia(self):
        self.assertEqual(validation.clasificar(_res(n_con_diferencia=2, max_abs=1e-11, max_rel=1e-12))[0], 'DENTRO_DE_TOLERANCIA')

    def test_explicada_por_version_solo_si_scipy_difiere(self):
        r = _res(n_con_diferencia=1, max_abs=5e-4, fuera_tol=[('/contrastes/3/p_wilcoxon', 0.0238, 0.0243)])
        self.assertEqual(validation.clasificar(r, scipy_version='1.16.3')[0], 'EXPLICADA_POR_VERSION')
        self.assertEqual(validation.clasificar(r, scipy_version=validation.SCIPY_REFERENCIA)[0], 'NO_EXPLICADA')

    def test_no_explicada(self):
        r = _res(n_con_diferencia=1, max_abs=0.1, fuera_tol=[('/media', 1.0, 1.1)])
        self.assertEqual(validation.clasificar(r, scipy_version='1.16.3')[0], 'NO_EXPLICADA')

    def test_no_reproducible_por_estructura(self):
        self.assertEqual(validation.clasificar(_res(estructura_igual=False))[0], 'NO_REPRODUCIBLE')

    def test_compare_json_detecta_diferencias(self):
        with tempfile.TemporaryDirectory() as d:
            a, b = os.path.join(d, 'a.json'), os.path.join(d, 'b.json')
            json.dump({'x': 1.0, 'y': [1, 2]}, open(a, 'w')); json.dump({'x': 1.0 + 1e-12, 'y': [1, 3]}, open(b, 'w'))
            r = validation.compare_json(a, b)
            self.assertTrue(r['estructura_igual']); self.assertEqual(len(r['fuera_tol']), 1)


class Descarga(unittest.TestCase):
    def test_hash_incorrecto_detiene_con_archivo_url_y_hash(self):
        with tempfile.TemporaryDirectory() as d:
            z = os.path.join(d, 'x.zip')
            with zipfile.ZipFile(z, 'w') as f:
                f.writestr('a.txt', 'hola')
            man = dict(paquetes=[dict(nombre='x', url='http://127.0.0.1:9/x.zip', tamano_bytes=os.path.getsize(z), sha256='0' * 64, descripcion='')])
            cache = d
            os.replace(z, os.path.join(cache, 'x.zip'))
            with self.assertRaises(data_loading.DataIntegrityError) as cm:
                data_loading.fetch_package('x', dest=os.path.join(d, 'out'), cache=cache, manifest=man)
            self.assertIn('http://127.0.0.1:9/x.zip', str(cm.exception))

    def test_paquete_inexistente(self):
        with self.assertRaises(data_loading.DataIntegrityError):
            data_loading.fetch_package('no_existe', manifest=dict(paquetes=[]))

    def test_ruta_insegura_en_zip(self):
        with tempfile.TemporaryDirectory() as d:
            z = os.path.join(d, 'x.zip')
            with zipfile.ZipFile(z, 'w') as f:
                f.writestr('../fuera.txt', 'x')
            sha = data_loading.sha256_file(z)
            man = dict(paquetes=[dict(nombre='x', url='http://127.0.0.1:9/x.zip', tamano_bytes=os.path.getsize(z), sha256=sha, descripcion='')])
            with self.assertRaises(data_loading.DataIntegrityError):
                data_loading.fetch_package('x', dest=os.path.join(d, 'out'), cache=d, manifest=man)


class Manifiestos(unittest.TestCase):
    def test_manifiesto_de_datos(self):
        m = json.load(open(MAN, encoding='utf-8'))
        self.assertEqual(len(m['paquetes']), 12)
        for p in m['paquetes']:
            self.assertRegex(p['sha256'], r'^[0-9a-f]{64}$')
            self.assertIn(p['commit_publicacion'], p['url'])      # URL fijada a un commit, no a una rama
            self.assertIn(p['commit_publicacion'], (m['commit_datos'], m['commit_datos_v3']))
            self.assertTrue(p['url'].startswith('https://raw.githubusercontent.com/'))
            self.assertGreater(p['tamano_bytes'], 0)
        self.assertEqual(len({p['nombre'] for p in m['paquetes']}), 12)

    def test_paquetes_de_oe2b_son_los_de_la_version_3(self):
        m = json.load(open(MAN, encoding='utf-8'))
        for n in ('oe2b_colab_paquete', 'oe2b_http_p1'):
            p = next(x for x in m['paquetes'] if x['nombre'] == n)
            self.assertIn('/paquetes_v3/', p['url'])
            self.assertEqual(p['commit_publicacion'], m['commit_datos_v3'])
            self.assertNotEqual(p['sha256'], p['sustituye_a']['sha256'])
            f = os.path.join(AQUI, '..', 'paquetes_v3', n + '.zip')
            self.assertEqual(data_loading.sha256_file(f), p['sha256'])       # el manifiesto coincide con el archivo del repositorio
        for p in m['paquetes']:
            if p['nombre'] not in ('oe2b_colab_paquete', 'oe2b_http_p1'):
                self.assertIn(m['commit_datos'], p['url'])

    def test_notebooks_apuntan_solo_a_la_etiqueta_v3(self):
        nbdir = os.path.join(AQUI, '..', 'notebooks')
        for f in sorted(os.listdir(nbdir)):
            t = open(os.path.join(nbdir, f), encoding='utf-8').read()
            self.assertIn("REPO_REF = 'repro-etapa26-v3'", t, f)
            self.assertNotIn('etapa26-v2', t, f)
            self.assertNotIn('etapa26-v1', t, f)

    def test_sin_datos_personales_en_manifiestos(self):
        for f in (MAN, VAL):
            t = open(f, encoding='utf-8').read()
            self.assertIsNone(re.search(r'C:\\Users|/Users/|AppData', t))

    def test_valores_oficiales(self):
        v = json.load(open(VAL, encoding='utf-8'))
        ids = [c['id'] for c in v['comprobaciones']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertTrue({c['oe'] for c in v['comprobaciones']} >= {'OE1', 'OE2-A', 'OE2-B', 'OE3', 'OE4', 'OE5'})
        oe5 = next(c for c in v['comprobaciones'] if c['id'] == 'OE5-01')
        self.assertAlmostEqual(oe5['esperado'], 0.8044238095238094, places=15)


class ScriptsSellados(unittest.TestCase):
    def test_copias_legibles_identicas_a_las_de_los_paquetes(self):
        base = os.path.join(AQUI, '..', 'analisis_sellado'); paq = os.path.join(AQUI, '..', '..', 'etapa23_oe1_oe5', 'paquetes')
        if not os.path.isdir(paq):
            self.skipTest('paquetes no disponibles')
        import hashlib
        n = 0
        for z in sorted(os.listdir(paq)):
            with zipfile.ZipFile(os.path.join(paq, z)) as f:
                for i in f.infolist():
                    if i.filename.endswith('.py'):
                        b = f.read(i)
                        self.assertEqual(hashlib.sha256(b).hexdigest(), hashlib.sha256(open(os.path.join(base, os.path.basename(i.filename)), 'rb').read()).hexdigest(), i.filename)
                        n += 1
        self.assertGreaterEqual(n, 12)


if __name__ == '__main__':
    unittest.main()
