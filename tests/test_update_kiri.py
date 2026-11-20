import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import update_kiri as updater

# Keep the starting version and hashes fixed as the published cask advances.
CASK = (
    'cask "kiri" do\n'
    '  arch arm: "arm64", intel: "x86_64"\n'
    '  version "0.2.1"\n'
    '  on_arm do\n'
    f'    sha256 "{"c" * 64}"\n'
    '  end\n'
    '  on_intel do\n'
    f'    sha256 "{"d" * 64}"\n'
    '  end\n'
    '  url "https://github.com/libracoder/kiri/releases/download/v#{version}/Kiri-#{version}-#{arch}.dmg"\n'
    '  depends_on macos: :sonoma\n'
    'end\n'
)


def release(version="0.2.2", digest_arm="a" * 64, digest_intel="b" * 64):
    return {
        "tag_name": "v" + version, "draft": False, "prerelease": False,
        "assets": [
            {
                "name": f"Kiri-{version}-{arch}.dmg",
                "browser_download_url": f"{updater.PREFIX}v{version}/Kiri-{version}-{arch}.dmg",
                "digest": "sha256:" + digest,
                "state": "uploaded",
                "size": 123456,
            }
            for arch, digest in (("arm64", digest_arm), ("x86_64", digest_intel))
        ],
    }


class KiriUpdaterTests(unittest.TestCase):
    def test_release_and_update(self):
        parsed = updater.parse_release(release())
        result = updater.updated_content(CASK, parsed)
        self.assertIn('  version "0.2.2"', result)
        self.assertIn('    sha256 "' + "a" * 64 + '"', result)
        self.assertIn('    sha256 "' + "b" * 64 + '"', result)
        self.assertEqual(updater.current(result), ("0.2.2", {"arm64": "a" * 64, "x86_64": "b" * 64}))

    def test_same_version(self):
        version, hashes = updater.current(CASK)
        self.assertEqual(updater.updated_content(CASK, (version, hashes)), CASK)
        with self.assertRaises(ValueError):
            updater.updated_content(CASK, (version, {"arm64": "0" * 64, "x86_64": hashes["x86_64"]}))

    def test_rejects_downgrade(self):
        with self.assertRaises(ValueError):
            updater.updated_content(CASK, updater.parse_release(release(version="0.1.0")))

    def test_rejects_bad_release_metadata(self):
        for bad in [
            {"tag_name": "v0.2.3;id", "assets": []},
            {**release(), "prerelease": True},
            {**release(), "assets": release()["assets"][:1]},
            {**release(), "assets": release()["assets"] * 2},
            {**release(), "assets": [{**release()["assets"][0], "digest": "sha256:bad"}, release()["assets"][1]]},
            {**release(), "assets": [{**release()["assets"][0], "browser_download_url": "https://evil.test/x.dmg"}, release()["assets"][1]]},
        ]:
            with self.subTest(bad=bad), self.assertRaises(ValueError):
                updater.parse_release(bad)

    def test_rejects_cask_change(self):
        for bad in [CASK.replace('cask "kiri"', 'cask "other"'),
                    CASK.replace('macos: :sonoma', 'macos: :ventura'),
                    CASK.replace('  on_arm do', '  on_foo do')]:
            with self.assertRaises(ValueError):
                updater.current(bad)


if __name__ == "__main__":
    unittest.main()
