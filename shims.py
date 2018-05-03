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
import os
import re
import shutil
import subprocess
import sys
import tarfile
import textwrap


VIRTUALENV_URL = "https://files.pythonhosted.org/packages/b1/72/2d70c5a1de409ceb3a27ff2ec007ecdd5cc52239e7c74990e32af57affe9/virtualenv-15.2.0.tar.gz"
VIRTUALENV_SHA256 = "1d7e241b431e7afce47e77f8843a276f652699d1fa4f93b9d8ce0076fd7b0b54"


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
        if sorted(existing) == sorted(names):
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
        virtualenv = "virtualenv-%s" % tuple(filter(None, match.groups()))
        pythons.append((virtualenv, shim[1]))
    return sorted(pythons)


def make_scripts(bin_path, virtualenv_py):
    shims = get_shims()
    template = textwrap.dedent("""\
        #!/bin/sh
        exec {python} {virtualenv_py} $*
    """)
    for virtualenv, shim in get_pythons(shims):
        path = os.path.join(bin_path, virtualenv)
        if os.path.exists(path):
            os.unlink(path)
        with open(path, 'w') as f:
            f.write(
                template.format(
                    python=shim,
                    virtualenv_py=virtualenv_py))
        os.chmod(path, 0o755)


def run():
    path = download_virtualenv(VIRTUALENV_URL)
    if not verify_virtualenv(path, VIRTUALENV_SHA256):
        print("The sha256 sum doesn't match for %s" % path)
        sys.exit(3)
    base = unpack_virtualenv(path)
    virtualenv_py = os.path.join(base, 'virtualenv.py')
    if not os.path.exists(virtualenv_py):
        print("The virtualenv.py script doesn't exist in %s" % base)
        sys.exit(4)
    bin_path = os.path.abspath('bin')
    if not os.path.isdir(bin_path):
        print("Creating directory %s" % bin_path)
        os.mkdir(bin_path)
    make_scripts(bin_path, virtualenv_py)


if __name__ == '__main__':
    run()
