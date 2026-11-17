"""Ejecucion de los scripts de analisis sellados como procesos independientes (misma invocacion que en local)."""
import os, shlex, subprocess, sys


def sh(cmd, cwd=None, tail=600, show=True):
    """Ejecuta 'python script args [> log 2>&1]'. Sustituye 'python' por el interprete actual, redirige la salida al log
    indicado (si lo hay) y detiene el notebook con la cola del log si el proceso falla. Devuelve la cola del log."""
    log = None
    if ' > ' in cmd:
        cmd, rest = cmd.split(' > ', 1)
        log = rest.replace('2>&1', '').strip()
    args = shlex.split(cmd, posix=True)
    if args and args[0] == 'python':
        args[0] = sys.executable
    out = open(log, 'wb') if log else subprocess.PIPE
    try:
        p = subprocess.run(args, stdout=out, stderr=subprocess.STDOUT, cwd=cwd, env=dict(os.environ, PYTHONIOENCODING='utf-8', PYTHONUTF8='1'))
    finally:
        if log: out.close()
    texto = open(log, encoding='utf-8', errors='replace').read() if log else p.stdout.decode('utf-8', 'replace')
    if p.returncode != 0:
        raise RuntimeError(f"El script termino con codigo {p.returncode}: {' '.join(args[1:])}\n--- cola del registro ---\n{texto[-1500:]}")
    if show and not log: print(texto[-tail:])
    return texto[-tail:]
