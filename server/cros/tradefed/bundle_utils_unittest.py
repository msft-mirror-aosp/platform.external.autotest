import unittest

from autotest_lib.server.cros.tradefed import bundle_utils


CTS_URL_CONFIG = {
    'public_base': 'https://dl.google.com/dl/android/cts/',
    'internal_base': 'gs://chromeos-arc-images/cts/bundle/R/',
    'partner_base': 'gs://chromeos-partner-gts/R/',
    'official_url_pattern': 'android-cts-11_r9-linux_x86-%s.zip',
    'preview_url_pattern': 'android-cts-9099362-linux_x86-%s.zip',
    'abi_list': ['arm', 'x86']
}

GTS_URL_CONFIG = {
    'internal_base': 'gs://chromeos-arc-images/cts/bundle/',
    'partner_base': 'gs://chromeos-partner-gts/',
    'official_url_pattern': 'android-gts-9.1-R2-P-8632016.zip',
    'preview_url_pattern': 'android-gts-9.1-R2-P-Preview18-9049557.zip',
}

STS_URL_CONFIG = {
    "internal_base": "gs://chromeos-arc-images/sts/bundle/R/",
    "partner_base": "gs://chromeos-partner-gts/",
    "preview_url_pattern": "android-sts-11_sts-latest-linux-%s.zip",
    "abi_list": ["arm64", "x86_64"]
}

VTS_URL_CONFIG = {
    "internal_base": "gs://chromeos-arc-images/vts/bundle/T/",
    "preview_url_pattern": "android-vts-8890152-linux_%s.zip",
    "abi_list": ["arm", "x86"]
}

class BundelUtilsTest(unittest.TestCase):
    """Unittest for bundle_utils."""

    def test_make_bundle_url_cts_public_arm(self):
        """Test for cts make_bundle_url in the case of (public, arm)."""

        uri = bundle_utils.make_bundle_url(
            url_config=CTS_URL_CONFIG,
            bundle_type=None,
            abi='arm'
        )
        self.assertEquals(
            'https://dl.google.com/dl/android/cts/android-cts-11_r9-linux_x86-arm.zip', uri
        )

    def test_make_bundle_url_cts_public_x86(self):
        """Test for cts make_bundle_url in the case of (public, x86)."""

        uri = bundle_utils.make_bundle_url(
            url_config=CTS_URL_CONFIG,
            bundle_type=None,
            abi='x86'
        )
        self.assertEquals(
            'https://dl.google.com/dl/android/cts/android-cts-11_r9-linux_x86-x86.zip', uri
        )

    def test_make_bundle_url_cts_latest_arm(self):
        """Test for cts make_bundle_url in the case of (latest, arm)."""

        uri = bundle_utils.make_bundle_url(
            url_config=CTS_URL_CONFIG,
            bundle_type='LATEST',
            abi='arm'
        )
        self.assertEquals(
            'gs://chromeos-arc-images/cts/bundle/R/android-cts-11_r9-linux_x86-arm.zip', uri
        )

    def test_make_bundle_url_cts_latest_x86(self):
        """Test for cts make_bundle_url in the case of (latest, x86)."""

        uri = bundle_utils.make_bundle_url(
            url_config=CTS_URL_CONFIG,
            bundle_type='LATEST',
            abi='x86'
        )
        self.assertEquals(
            'gs://chromeos-arc-images/cts/bundle/R/android-cts-11_r9-linux_x86-x86.zip', uri
        )

    def test_make_bundle_url_cts_dev_arm(self):
        """Test for cts make_bundle_url in the case of (dev, arm)."""

        uri = bundle_utils.make_bundle_url(
            url_config=CTS_URL_CONFIG,
            bundle_type='DEV',
            abi='arm'
        )
        self.assertEquals(
            'gs://chromeos-arc-images/cts/bundle/R/android-cts-9099362-linux_x86-arm.zip', uri
        )

    def test_make_bundle_url_cts_dev_x86(self):
        """Test for cts make_bundle_url in the case of (dev, x86)."""

        uri = bundle_utils.make_bundle_url(
            url_config=CTS_URL_CONFIG,
            bundle_type='DEV',
            abi='x86'
        )
        self.assertEquals(
            'gs://chromeos-arc-images/cts/bundle/R/android-cts-9099362-linux_x86-x86.zip', uri
        )

    def test_make_bundle_url_gts_public(self):
        """Test for cts make_bundle_url in the case of (public)."""

        uri = bundle_utils.make_bundle_url(
            url_config=GTS_URL_CONFIG,
            bundle_type=None,
            abi=None
        )
        self.assertEquals(
            'gs://chromeos-partner-gts/android-gts-9.1-R2-P-8632016.zip', uri
        )

    def test_make_bundle_url_gts_latest(self):
        """Test for gts make_bundle_url in the case of (latest)."""

        uri = bundle_utils.make_bundle_url(
            url_config=GTS_URL_CONFIG,
            bundle_type='LATEST',
            abi=None
        )
        self.assertEquals(
            'gs://chromeos-arc-images/cts/bundle/android-gts-9.1-R2-P-8632016.zip', uri
        )

    def test_make_bundle_url_gts_dev(self):
        """Test for gts make_bundle_url in the case of (dev)."""

        uri = bundle_utils.make_bundle_url(
            url_config=GTS_URL_CONFIG,
            bundle_type='DEV',
            abi=None
        )
        self.assertEquals(
            'gs://chromeos-arc-images/cts/bundle/android-gts-9.1-R2-P-Preview18-9049557.zip', uri
        )

    def test_make_bundle_url_sts_dev_arm64(self):
        """Test for sts make_bundle_url in the case of (dev, arm64)."""

        uri = bundle_utils.make_bundle_url(
            url_config=STS_URL_CONFIG,
            bundle_type='DEV',
            abi='arm64'
        )
        self.assertEquals(
            'gs://chromeos-arc-images/sts/bundle/R/android-sts-11_sts-latest-linux-arm64.zip', uri
        )

    def test_make_bundle_url_sts_dev_x86_64(self):
        """Test for sts make_bundle_url in the case of (dev, x86_64)."""

        uri = bundle_utils.make_bundle_url(
            url_config=STS_URL_CONFIG,
            bundle_type='DEV',
            abi='x86_64'
        )
        self.assertEquals(
            'gs://chromeos-arc-images/sts/bundle/R/android-sts-11_sts-latest-linux-x86_64.zip', uri
        )

    def test_make_bundle_url_vts_dev_arm(self):
        """Test for vts make_bundle_url in the case of (dev, arm)."""

        uri = bundle_utils.make_bundle_url(
            url_config=VTS_URL_CONFIG,
            bundle_type='DEV',
            abi='arm'
        )
        self.assertEquals(
            'gs://chromeos-arc-images/vts/bundle/T/android-vts-8890152-linux_arm.zip', uri
        )

    def test_make_bundle_url_vts_dev_x86(self):
        """Test for vts make_bundle_url in the case of (dev, x86)."""

        uri = bundle_utils.make_bundle_url(
            url_config=VTS_URL_CONFIG,
            bundle_type='DEV',
            abi='x86'
        )
        self.assertEquals(
            'gs://chromeos-arc-images/vts/bundle/T/android-vts-8890152-linux_x86.zip', uri
        )
