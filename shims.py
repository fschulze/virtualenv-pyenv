from __future__ import print_function
try:
    from urllib.parse import urlparse
except ImportError:
    from urlparse import urlparse
try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tarfile
import textwrap


virtualenv_infos = {
    '16.7.9': dict(
        url=(
            "https://files.pythonhosted.org/packages/aa/3b/"
            "213c384c65e17995cccd0f2bb993b7b82c41f62e74c2f8f39c8e60549d86/"
            "virtualenv-16.7.9.tar.gz"),
        sha256=(
            "0d62c70883c0342d59c11d0ddac0d954d0431321a41ab20851facf2b222598f3")
    ),
    '20.0.17': dict(
        url=(
            "https://files.pythonhosted.org/packages/1c/fc/"
            "1bcbb524de8cef189166e7e42c31f411ace373ceacdd77d9a366d13976c6/"
            "virtualenv-20.0.17.tar.gz"),
        use_venv=True,
        sha256=(
            "c8364ec469084046c779c9a11ae6340094e8a0bf1d844330fc55c1cefe67c172")
    )}


NEWEST_VIRTUALENV = '20.0.17'


python_virtualenv = {
    (2, 7): '16.7.9',
    (3, 4): '16.7.9',
    (3, 5): '16.7.9',
    (3, 6): '16.7.9',
    (3, 7): '20.0.17',
    (3, 8): '20.0.17',
    (3, 9): '20.0.17',
    (3, 10): '20.0.17'}


def download_virtualenv(url):
    parts = urlparse(url)
    basename = os.path.basename(parts.path)
    path = os.path.abspath(basename)
    if os.path.exists(path):
        return path
    data = urlopen(url).read()
    with open(path, 'wb') as f:
        f.write(data)
    return path


def verify_virtualenv(path, sha):
    with open(path, 'rb') as f:
        data = f.read()
    return hashlib.sha256(data).hexdigest() == sha


def unpack_virtualenv(path):
    tf = tarfile.open(path)
    names = tf.getnames()
    (basename,) = {x.split('/')[0] for x in names}
    base = os.path.abspath(basename)
    existing = [basename]
    dirs = set([base])
    while dirs:
        current = dirs.pop()
        if not os.path.exists(current):
            continue
        for name in os.listdir(current):
            name = os.path.join(current, name)
            existing.append(basename + name[len(base):])
            if os.path.isdir(name):
                dirs.add(name)
                continue
    if os.path.exists(base):
        extra = sorted(set(existing).difference(names))
        if not extra:
            return base
        shutil.rmtree(base)
    tf.extractall()
    return base


def get_shims():
    output = subprocess.check_output(['pyenv', 'shims'])
    output = output.decode('utf-8')
    shims = list(line.strip() for line in output.splitlines())
    return list(
        (os.path.basename(shim), shim)
        for shim in filter(None, shims))


def get_pythons(shims):
    pythons = []
    for shim in shims:
        match = re.match(
            r"^python(2\.\d)$|^python(3.\d+)$|^(pypy)$|^(pypy3)$",
            shim[0])
        if not match:
            continue
        python_version_script = textwrap.dedent("""\
            import json
            import sys
            print(json.dumps(list(sys.version_info)))""")
        python_version = tuple(json.loads(subprocess.check_output([
            shim[1], '-c', python_version_script]))[:2])
        virtualenv_version = python_virtualenv[python_version]
        virtualenv = "virtualenv-%s" % tuple(filter(None, match.groups()))
        pythons.append((python_version, virtualenv, virtualenv_version, shim[1]))
    return [x[1:] for x in sorted(pythons)]


def make_scripts(bin_path, venvs):
    shims = get_shims()
    template = textwrap.dedent("""\
        #!/bin/sh
        exec {python} {virtualenv_py} $*
    """)
    for virtualenv, virtualenv_version, shim in get_pythons(shims):
        path = os.path.join(bin_path, virtualenv)
        if os.path.exists(path):
            os.unlink(path)
        use_venv = virtualenv_infos[virtualenv_version].get('use_venv', False)
        virtualenv_py = get_virtualenv_py(venvs, shim, virtualenv_version)
        if use_venv:
            print(
                f"Linking {virtualenv} to {virtualenv_py!r} for {shim!r}.")
            os.symlink(virtualenv_py, path)
            continue
        with open(path, 'w') as f:
            print(
                f"Writing {virtualenv} for {shim!r} with "
                f"virtualenv-{virtualenv_version}.")
            f.write(
                template.format(
                    python=shim,
                    virtualenv_py=virtualenv_py))
        os.chmod(path, 0o755)


def make_virtualenv_py(venvs, python, base):
    virtualenv_py = os.path.join(base, 'virtualenv.py')
    if os.path.exists(virtualenv_py):
        return virtualenv_py
    python_basename = os.path.basename(python)
    virtualenv_basename = os.path.basename(base)
    venv = os.path.join(venvs, python_basename, virtualenv_basename)
    virtualenv_py = os.path.join(venv, 'bin', 'virtualenv')
    if os.path.exists(virtualenv_py):
        return virtualenv_py
    if os.path.exists(venv):
        shutil.rmtree(venv)
    os.makedirs(venv)
    subprocess.check_call([python, '-m', 'venv', venv])
    pip = os.path.join(venv, 'bin', 'pip')
    subprocess.check_call([pip, 'install', base])
    return virtualenv_py


def get_virtualenv_py(venvs, python, version):
    virtualenv_info = virtualenv_infos[version]
    path = download_virtualenv(virtualenv_info['url'])
    if not verify_virtualenv(path, virtualenv_info['sha256']):
        print(
            f"The sha256 sum doesn't match for "
            f"virtualenv-{version} at {path!r}.")
        sys.exit(3)
    base = unpack_virtualenv(path)
    return make_virtualenv_py(venvs, python, base)


def run():
    bin_path = os.path.abspath('bin')
    if not os.path.isdir(bin_path):
        print("Creating directory %s" % bin_path)
        os.mkdir(bin_path)
    venvs = os.path.abspath('venvs')
    if not os.path.isdir(venvs):
        print(f"Creating directory {venvs}")
        os.mkdir(venvs)
    make_scripts(bin_path, venvs)


if __name__ == '__main__':
    run()
