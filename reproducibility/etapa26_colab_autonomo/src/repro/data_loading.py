"""Descarga automatica de los paquetes de datos desde GitHub (commit fijado) y verificacion de SHA-256.

Nunca continua con datos incompletos: si falta un archivo, no se puede descargar o su hash no coincide, lanza
DataIntegrityError indicando que archivo, que URL y que hash se esperaba."""
import hashlib, json, os, time, urllib.error, urllib.request, zipfile

MANIFEST_RELATIVO = os.path.join(os.path.dirname(__file__), '..', '..', 'manifests', 'data_manifest.json')


class DataIntegrityError(RuntimeError):
    pass


def sha256_file(path, bloque=1 << 20):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for b in iter(lambda: f.read(bloque), b''):
            h.update(b)
    return h.hexdigest()


def load_manifest(path=None):
    with open(path or MANIFEST_RELATIVO, encoding='utf-8') as f:
        return json.load(f)


def _descargar(url, destino, intentos=3, timeout=180):
    ultimo = None
    for i in range(intentos):
        try:
            req = urllib.request.Request(url, headers={'User-Agent': 'repro-oe1-oe5'})
            with urllib.request.urlopen(req, timeout=timeout) as r, open(destino + '.part', 'wb') as f:
                while True:
                    b = r.read(1 << 20)
                    if not b: break
                    f.write(b)
            os.replace(destino + '.part', destino)
            return
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            ultimo = e; time.sleep(2 * (i + 1))
    raise DataIntegrityError(f"No se pudo descargar {url} tras {intentos} intentos: {ultimo!r}")


def fetch_package(name, dest='.', cache='paquetes_descargados', manifest=None, extract=True):
    """Descarga (si hace falta), verifica tamano y SHA-256 contra el manifiesto y extrae en dest."""
    m = manifest or load_manifest()
    ent = next((p for p in m['paquetes'] if p['nombre'] == name), None)
    if ent is None:
        raise DataIntegrityError(f"El paquete {name!r} no figura en el manifiesto; disponibles: {[p['nombre'] for p in m['paquetes']]}")
    os.makedirs(cache, exist_ok=True)
    local = os.path.join(cache, name + '.zip')
    if not (os.path.exists(local) and sha256_file(local) == ent['sha256']):
        print(f"Descargando {name} ({ent['tamano_bytes']/1e6:.1f} MB) desde {ent['url']}")
        _descargar(ent['url'], local)
    got = sha256_file(local)
    if os.path.getsize(local) != ent['tamano_bytes'] or got != ent['sha256']:
        raise DataIntegrityError(
            f"Archivo con integridad incorrecta: {name}.zip\n  URL: {ent['url']}\n  tamano esperado {ent['tamano_bytes']} / obtenido {os.path.getsize(local)}\n"
            f"  SHA-256 esperado {ent['sha256']}\n  SHA-256 obtenido {got}")
    print(f"OK {name}.zip  {ent['tamano_bytes']} B  sha256 {got[:16]}...  ({ent.get('descripcion','')})")
    if extract:
        base = os.path.realpath(dest)
        with zipfile.ZipFile(local) as z:
            for i in z.infolist():
                objetivo = os.path.realpath(os.path.join(base, i.filename))
                if not (objetivo == base or objetivo.startswith(base + os.sep)):
                    raise DataIntegrityError(f"Ruta insegura en {name}: {i.filename}")
            z.extractall(base)
    return ent


def fetch_packages(names, dest='.', **kw):
    m = kw.pop('manifest', None) or load_manifest()
    return [fetch_package(n, dest=dest, manifest=m, **kw) for n in names]


def verify_sums_file(sums_path, base, anon=None, solo_presentes=True):
    """Verifica un archivo 'sha256  nombre' contra los archivos de base. 'anon' mapea nombre -> sha256 de la copia anonimizada."""
    ok, mal, falta = [], [], []
    for l in open(sums_path, encoding='utf-8'):
        l = l.strip()
        if not l: continue
        h, n = l.split(None, 1); n = n.strip().lstrip('*')
        p = os.path.join(base, n)
        if not os.path.exists(p):
            falta.append(n); continue
        esperado = (anon or {}).get(n, h)
        (ok if sha256_file(p) == esperado else mal).append(n)
    if mal or (falta and not solo_presentes):
        raise DataIntegrityError(f"{sums_path}: hash distinto en {mal[:5]}; ausentes {falta[:5]}")
    return dict(verificados=len(ok), distintos=mal, ausentes=len(falta))
