import json
import os
from pathlib import Path
import ssl
import sys
import urllib.error
import urllib.request

try:
    import certifi
except ImportError:
    certifi = None

from packaging.specifiers import SpecifierSet
from packaging.version import Version

TARGET = "3.11"


def ssl_context():
    ca_file = os.environ.get("SSL_CERT_FILE")
    if ca_file:
        return ssl.create_default_context(cafile=ca_file)
    if certifi is not None:
        return ssl.create_default_context(cafile=certifi.where())
    return ssl.create_default_context()


def fetch_release(name, version):
    url = f"https://pypi.org/pypi/{name}/{version}/json"
    try:
        with urllib.request.urlopen(url, timeout=15, context=ssl_context()) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return None
        raise


def min_python(spec):
    bounds = [Version(s.version) for s in spec if s.operator in (">=", ">", "==", "~=")]
    return max(bounds) if bounds else None


def parse_line(line):
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    name, version = line.split("==", 1)
    return name.strip(), version.strip()


def main(path):
    with open(path) as f:
        deps = [d for d in map(parse_line, f) if d]

    not_found = 0
    incompatible = 0
    highest = None

    for name, version in deps:
        data = fetch_release(name, version)
        if data is None:
            not_found += 1
            continue

        rp = (data["info"].get("requires_python") or "").strip()
        if not rp:
            continue

        spec = SpecifierSet(rp)
        if not spec.contains(TARGET):
            incompatible += 1

        low = min_python(spec)
        if low is not None and (highest is None or low > highest[0]):
            highest = (low, f"{name}=={version}", f">={low}")

    print(f"Dependencies checked: {len(deps)}")
    print(f"Not found on PyPI: {not_found}")
    print(f"Incompatible with Python {TARGET}: {incompatible}")
    if highest:
        print(f"Highest requirement: {highest[1]} ({highest[2]})")
    else:
        print("Highest requirement: none")


if __name__ == "__main__":
    requirements_path = (
        sys.argv[1] if len(sys.argv) > 1 else Path(__file__).with_name("requirements.txt")
    )
    main(requirements_path)