"""Update Kiri cask from verified GitHub release asset metadata."""
import argparse
import json
from pathlib import Path
import re
import urllib.request

API = "https://api.github.com/repos/libracoder/kiri/releases/latest"
PREFIX = "https://github.com/libracoder/kiri/releases/download/"
VERSION_LINE = re.compile(r'^  version "([0-9]+(?:\.[0-9]+){2})"$', re.M)
ARM_LINE = re.compile(r'(?<=  on_arm do\n)    sha256 "([0-9a-f]{64})"', re.M)
INTEL_LINE = re.compile(r'(?<=  on_intel do\n)    sha256 "([0-9a-f]{64})"', re.M)
VERSION = re.compile(r'[0-9]+(?:\.[0-9]+){2}')
DIGEST = re.compile(r'sha256:([0-9a-f]{64})')


def current(content):
    versions = VERSION_LINE.findall(content)
    arms = ARM_LINE.findall(content)
    intels = INTEL_LINE.findall(content)
    if len(versions) != 1 or len(arms) != 1 or len(intels) != 1:
        raise ValueError("Unexpected cask version or checksum layout")
    required = [
        'cask "kiri" do', '  arch arm: "arm64", intel: "x86_64"',
        '  url "' + PREFIX + 'v#{version}/Kiri-#{version}-#{arch}.dmg"',
        '  depends_on macos: :sonoma',
    ]
    if any(line not in content for line in required):
        raise ValueError("Unexpected Kiri cask identity, URL or macOS requirement")
    return versions[0], {"arm64": arms[0], "x86_64": intels[0]}


def parse_release(data):
    if data.get("draft") or data.get("prerelease"):
        raise ValueError("Latest release is draft or prerelease")
    tag = data.get("tag_name", "")
    if not re.fullmatch(r"v[0-9]+(?:\.[0-9]+){2}", tag):
        raise ValueError("Unexpected release tag")
    version = tag[1:]
    assets = {}
    for arch in ("arm64", "x86_64"):
        name = f"Kiri-{version}-{arch}.dmg"
        matches = [a for a in data.get("assets", []) if a.get("name") == name]
        if len(matches) != 1:
            raise ValueError(f"Expected exactly one {name} asset")
        asset = matches[0]
        if (asset.get("state") != "uploaded" or not 1024 <= asset.get("size", 0) <= 512 * 1024 * 1024
                or asset.get("browser_download_url") != f"{PREFIX}{tag}/{name}"):
            raise ValueError(f"Invalid release asset metadata: {name}")
        match = DIGEST.fullmatch(asset.get("digest", ""))
        if not match:
            raise ValueError(f"Missing SHA-256 digest for {name}")
        assets[arch] = match.group(1)
    return version, assets


def updated_content(content, release):
    old_version, old_hashes = current(content)
    version, hashes = release
    old_key = tuple(map(int, old_version.split(".")))
    new_key = tuple(map(int, version.split(".")))
    if new_key < old_key:
        raise ValueError("Refusing to downgrade Kiri")
    if new_key == old_key:
        if hashes != old_hashes:
            raise ValueError("Existing release digests changed; manual review required")
        return content
    content = VERSION_LINE.sub(lambda _: f'  version "{version}"', content)
    content = ARM_LINE.sub(lambda _: f'    sha256 "{hashes["arm64"]}"', content)
    content = INTEL_LINE.sub(lambda _: f'    sha256 "{hashes["x86_64"]}"', content)
    return content


def update(path, verify_current=False):
    content = path.read_text()
    current(content)
    request = urllib.request.Request(API, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "homebrew-tap-kiri-updater",
        "X-GitHub-Api-Version": "2022-11-28",
    })
    with urllib.request.urlopen(request, timeout=30) as response:
        raw = response.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024:
        raise ValueError("Release metadata too large")
    release = parse_release(json.loads(raw))
    if verify_current and release[0] != current(content)[0]:
        print(f"Kiri {release[0]} available; cask remains at {current(content)[0]} (verification only).")
        return
    new_content = updated_content(content, release)
    if content != new_content:
        path.write_text(new_content)
        print(f"Updated Kiri to {release[0]}.")
    else:
        print("Kiri is up to date; release digests verified.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--verify-current", action="store_true")
    args = parser.parse_args()
    update(Path(__file__).resolve().parents[1] / "Casks/kiri.rb", args.verify_current)
