"""Update only Rex's version and checksum after validating a signed vendor DMG."""
import argparse
import base64
from dataclasses import dataclass
import hashlib
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET

FEED = "https://blob.superlogical.com/public/rex-app/snapshot/appcast.xml"
PREFIX = "https://blob.superlogical.com/public/rex-app/snapshot/"
SPARKLE = "{http://www.andymatuschak.org/xml-namespaces/sparkle}"
PUBLIC_KEY = "jG2oqfrStpD6pfzWIBAHHbER3yTLaZWToni8eZiBzxE="
MAX_DMG = 512 * 1024 * 1024
VERSION = re.compile(r"[0-9]+(?:\.[0-9]+){2}")
BUILD = re.compile(r"[0-9]+")
VERSION_LINE = re.compile(r'^  version "([0-9]+\.[0-9]+\.[0-9]+),([0-9]+)"$', re.M)
HASH_LINE = re.compile(r'^  sha256 "([0-9a-f]{64})"$', re.M)


@dataclass(frozen=True)
class Release:
    version: str
    build: str
    url: str
    size: int
    signature: bytes
    minimum_macos: str

    @property
    def key(self):
        return tuple(map(int, self.version.split("."))) + (int(self.build),)


def validate_url(url):
    parsed = urllib.parse.urlsplit(url)
    if (parsed.scheme != "https" or parsed.netloc != "blob.superlogical.com"
            or parsed.query or parsed.fragment
            or not re.fullmatch(r"/public/rex-app/snapshot/(?:appcast\.xml|Rex-[0-9]+\.[0-9]+\.[0-9]+-[0-9]+\.dmg)", parsed.path)):
        raise ValueError("Unexpected vendor URL")
    return url


class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        validate_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def open_vendor(url):
    validate_url(url)
    response = urllib.request.build_opener(SafeRedirect()).open(
        urllib.request.Request(url, headers={"User-Agent": "homebrew-tap-rex-updater"}), timeout=60)
    # Do not allow a different release, even on the same official host.
    if response.geturl() != url:
        response.close()
        raise ValueError("Vendor redirect changed the requested release")
    return response


def parse_feed(data):
    if len(data) > 2 * 1024 * 1024 or b"<!DOCTYPE" in data.upper() or b"<!ENTITY" in data.upper():
        raise ValueError("Unsafe or oversized feed")
    root = ET.fromstring(data)
    releases = []
    for item in root.findall("./channel/item"):
        version = item.findtext(SPARKLE + "shortVersionString", "")
        build = item.findtext(SPARKLE + "version", "")
        minimum = item.findtext(SPARKLE + "minimumSystemVersion", "")
        if not VERSION.fullmatch(version) or not BUILD.fullmatch(build):
            raise ValueError("Unexpected version format")
        enclosure = item.find("enclosure")
        if enclosure is None:
            raise ValueError("Missing release download")
        url = validate_url(enclosure.attrib.get("url", ""))
        if url != f"{PREFIX}Rex-{version}-{build}.dmg":
            raise ValueError("Download URL does not match release version")
        size = int(enclosure.attrib.get("length", "0"))
        if not 512 <= size <= MAX_DMG:
            raise ValueError("Unexpected DMG size")
        signature = base64.b64decode(enclosure.attrib.get(SPARKLE + "edSignature", ""), validate=True)
        if len(signature) != 64:
            raise ValueError("Missing or invalid Ed25519 signature")
        release = Release(version, build, url, size, signature, minimum)
        if any(r.key == release.key and r != release for r in releases):
            raise ValueError("Conflicting duplicate release")
        releases.append(release)
    if not releases:
        raise ValueError("No releases found")
    return max(releases, key=lambda r: r.key)


def current_version(content):
    matches = list(VERSION_LINE.finditer(content))
    if len(matches) != 1 or len(HASH_LINE.findall(content)) != 1:
        raise ValueError("Unexpected cask version/checksum layout")
    if 'cask "rex" do\n' not in content or 'depends_on macos: :sequoia' not in content:
        raise ValueError("Unexpected cask identity or minimum macOS")
    expected = '  url "' + PREFIX + 'Rex-#{version.csv.first}-#{version.csv.second}.dmg"'
    if expected not in content:
        raise ValueError("Unexpected cask download template")
    version, build = matches[0].groups()
    return tuple(map(int, version.split("."))) + (int(build),)


def verify_signature(path, signature):
    with tempfile.TemporaryDirectory() as directory:
        key = Path(directory) / "public.der"
        sig = Path(directory) / "signature"
        key.write_bytes(bytes.fromhex("302a300506032b6570032100") + base64.b64decode(PUBLIC_KEY, validate=True))
        sig.write_bytes(signature)
        subprocess.run(["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(key),
                        "-keyform", "DER", "-rawin", "-in", str(path), "-sigfile", str(sig)],
                       check=True, capture_output=True, timeout=60)


def download_hash(release):
    with tempfile.TemporaryDirectory() as directory:
        path = Path(directory) / "Rex.dmg"
        received = 0
        digest = hashlib.sha256()
        with open_vendor(release.url) as response, path.open("wb") as output:
            while chunk := response.read(1024 * 1024):
                received += len(chunk)
                if received > release.size:
                    raise ValueError("DMG exceeds declared size")
                output.write(chunk)
                digest.update(chunk)
        if received != release.size:
            raise ValueError("DMG size does not match feed")
        with path.open("rb") as source:
            source.seek(-512, 2)
            if source.read(4) != b"koly":
                raise ValueError("Download is not a UDIF disk image")
        verify_signature(path, release.signature)
        return digest.hexdigest()


def updated_content(content, release, digest):
    old = current_version(content)
    if release.key < old:
        raise ValueError("Refusing to downgrade Rex")
    if release.minimum_macos != "15.0":
        raise ValueError("Minimum macOS changed; review the cask manually")
    if not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("Invalid SHA-256")
    if release.key == old:
        if HASH_LINE.search(content).group(1) != digest:
            raise ValueError("Published release checksum changed; manual review required")
        return content
    content = VERSION_LINE.sub(lambda _: f'  version "{release.version},{release.build}"', content)
    return HASH_LINE.sub(lambda _: f'  sha256 "{digest}"', content)


def update(path, verify_current=False):
    content = path.read_text()
    old = current_version(content)
    with open_vendor(FEED) as response:
        release = parse_feed(response.read(2 * 1024 * 1024 + 1))
    if release.key < old:
        raise ValueError("Refusing to downgrade Rex")
    if release.minimum_macos != "15.0":
        raise ValueError("Minimum macOS changed; review the cask manually")
    if release.key == old and not verify_current:
        print("Rex is already up to date; no DMG download or commit needed.")
        return
    updated = updated_content(content, release, download_hash(release))
    if updated == content:
        print("Rex is up to date; current DMG signature and checksum verified.")
        return
    path.write_text(updated)
    print(f"Updated Rex to {release.version},{release.build} after signature verification.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-current", action="store_true")
    args = parser.parse_args()
    update(Path(__file__).resolve().parents[1] / "Casks/rex.rb", args.verify_current)
