import base64
import hashlib
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import update_rex as updater


ROOT = Path(__file__).resolve().parents[1]
CASK = (ROOT / "Casks/rex.rb").read_text()
SIGNATURE = base64.b64encode(b"s" * 64).decode()


def feed(version="0.1.0", build="1409", url=None, minimum="15.0", size="512", signature=SIGNATURE):
    url = url or f"{updater.PREFIX}Rex-{version}-{build}.dmg"
    return f'''<rss xmlns:sparkle="http://www.andymatuschak.org/xml-namespaces/sparkle"><channel><item>
<sparkle:shortVersionString>{version}</sparkle:shortVersionString><sparkle:version>{build}</sparkle:version>
<sparkle:minimumSystemVersion>{minimum}</sparkle:minimumSystemVersion>
<enclosure url="{url}" length="{size}" sparkle:edSignature="{signature}" />
</item></channel></rss>'''.encode()


class UpdaterTests(unittest.TestCase):
    def test_feed(self):
        release = updater.parse_feed(feed())
        self.assertEqual(release.key, (0, 1, 0, 1409))

    def test_rejects_invalid_version(self):
        for version in ['0.1.0;touch BAD', '$(id)', '1.0.0-beta', '0.1']:
            with self.subTest(version=version), self.assertRaises(ValueError):
                updater.parse_feed(feed(version=version))

    def test_rejects_bad_urls(self):
        for url in ['http://blob.superlogical.com/public/rex-app/preview/appcast.xml',
                    'https://blob.superlogical.com.evil.test/public/rex-app/preview/appcast.xml',
                    'https://blob.superlogical.com@evil.test/public/rex-app/preview/appcast.xml',
                    updater.FEED + '?token=x', updater.FEED + '#x',
                    'https://blob.superlogical.com/public/rex-app/preview/../evil.dmg']:
            with self.subTest(url=url), self.assertRaises(ValueError):
                updater.validate_url(url)

    def test_rejects_mismatched_release_url(self):
        with self.assertRaises(ValueError):
            updater.parse_feed(feed(build="1409", url=f"{updater.PREFIX}Rex-0.1.0-1408.dmg"))

    def test_rejects_off_host_redirect(self):
        with self.assertRaises(ValueError):
            updater.SafeRedirect().redirect_request(None, None, 302, '', {}, 'https://evil.test/rex.dmg')

    def test_rejects_signature_and_size(self):
        for kwargs in [{"signature": "bad"}, {"signature": ""}, {"size": "0"}, {"size": str(updater.MAX_DMG + 1)}]:
            with self.subTest(kwargs=kwargs), self.assertRaises((ValueError, base64.binascii.Error)):
                updater.parse_feed(feed(**kwargs))

    def test_rejects_xml_entities_and_oversized_feed(self):
        for data in [b'<!DOCTYPE rss [<!ENTITY x "y">]><rss/>', b'x' * (2 * 1024 * 1024 + 1), b'<rss/>']:
            with self.assertRaises(ValueError):
                updater.parse_feed(data)

    def test_selects_newest_numerically(self):
        a = feed(build="9").decode().split('<item>')[1].split('</item>')[0]
        data = feed(build="10").replace(b'</channel>', f'<item>{a}</item></channel>'.encode())
        self.assertEqual(updater.parse_feed(data).build, "10")

    def test_refuses_conflicting_duplicate(self):
        data = feed().replace(b'</channel>', feed(size="513").split(b'<item>')[1].split(b'</item>')[0].join([b'<item>', b'</item></channel>']))
        with self.assertRaises(ValueError):
            updater.parse_feed(data)

    def test_updates_only_version_and_hash_preserving_zap(self):
        version, build = updater.VERSION_LINE.search(CASK).groups()
        release = updater.parse_feed(feed(version=version, build=str(int(build) + 1)))
        digest = "a" * 64
        result = updater.updated_content(CASK, release, digest)
        normalize = lambda text: updater.HASH_LINE.sub('HASH', updater.VERSION_LINE.sub('VERSION', text))
        self.assertEqual(normalize(result), normalize(CASK))
        self.assertEqual(result.split('  zap trash:')[1], CASK.split('  zap trash:')[1])
        self.assertEqual(sum(a != b for a, b in zip(CASK.splitlines(), result.splitlines())), 2)

    def test_refuses_downgrade_and_changed_minimum(self):
        for release in [updater.parse_feed(feed(version="0.0.1", build="1")), updater.parse_feed(feed(build="999999", minimum="16.0"))]:
            with self.assertRaises(ValueError):
                updater.updated_content(CASK, release, "a" * 64)

    def test_same_release_unchanged_or_tampered(self):
        version, build = updater.VERSION_LINE.search(CASK).groups()
        release = updater.parse_feed(feed(version=version, build=build))
        digest = updater.HASH_LINE.search(CASK).group(1)
        self.assertEqual(updater.updated_content(CASK, release, digest), CASK)
        with self.assertRaises(ValueError):
            updater.updated_content(CASK, release, "0" * 64)

    def test_rejects_unexpected_cask(self):
        for content in [CASK.replace('cask "rex"', 'cask "other"'), CASK + '\n  version "1.2.3,4"\n', CASK.replace('macos: :sequoia', 'macos: :sonoma')]:
            with self.assertRaises(ValueError):
                updater.current_version(content)

    def test_download_validates_size_container_and_signature(self):
        release = updater.parse_feed(feed())
        data = b'koly' + b'\0' * 508
        with patch.object(updater, 'open_vendor', return_value=io.BytesIO(data)), patch.object(updater, 'verify_signature') as verify:
            self.assertEqual(updater.download_hash(release), hashlib.sha256(data).hexdigest())
            verify.assert_called_once()
        for data in [b'koly', b'x' * 513, b'x' * 512]:
            with patch.object(updater, 'open_vendor', return_value=io.BytesIO(data)), self.assertRaises(ValueError):
                updater.download_hash(release)
        with patch.object(updater, 'open_vendor', return_value=io.BytesIO(b'koly' + b'\0' * 508)), patch.object(updater, 'verify_signature', side_effect=ValueError('bad signature')), self.assertRaises(ValueError):
            updater.download_hash(release)

    def test_unchanged_skips_download_and_write(self):
        version, build = updater.VERSION_LINE.search(CASK).groups()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'rex.rb'
            path.write_text(CASK)
            with patch.object(updater, 'open_vendor', return_value=io.BytesIO(feed(version=version, build=build))), patch.object(updater, 'download_hash') as download:
                updater.update(path)
                download.assert_not_called()
            self.assertEqual(path.read_text(), CASK)

    def test_bad_signature_rejected_by_openssl(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'data'
            path.write_bytes(b'not a signed release')
            with self.assertRaises(subprocess.CalledProcessError):
                updater.verify_signature(path, b'x' * 64)


if __name__ == '__main__':
    unittest.main()
