import json
import os
import shutil
import tempfile
import unittest

from autotest_lib.server.cros.tradefed import bundle_utils


CTS_URL_CONFIG = {
        "public_base": "https://dl.google.com/dl/android/cts/",
        "internal_base": "gs://chromeos-arc-images/cts/bundle/R/",
        "partner_base": "gs://chromeos-partner-gts/R/",
        "official_url_pattern": "android-cts-%s-linux_x86-%s.zip",
        "preview_url_pattern": "android-cts-%s-linux_x86-%s.zip",
        "official_version_name": "11_r9",
        "preview_version_name": "9199760",
        "abi_list": {
                "arm": "test_suites_arm64",
                "x86": "test_suites_x86_64"
        }
}

GTS_URL_CONFIG = {
        "internal_base": "gs://chromeos-arc-images/cts/bundle/",
        "partner_base": "gs://chromeos-partner-gts/",
        "official_url_pattern": "android-gts-%s.zip",
        "preview_url_pattern": "android-gts-%s.zip",
        "official_version_name": "9.1-R2-P-8632016",
        "preview_version_name": "9.1-R2-P-Preview18-9049557"
}

STS_URL_CONFIG = {
        "internal_base": "gs://chromeos-arc-images/sts/bundle/R/",
        "partner_base": "gs://chromeos-partner-gts/",
        "preview_url_pattern": "android-sts-%s-linux-%s.zip",
        "preview_version_name": "11_sts-latest",
        "abi_list": ["arm64", "x86_64"]
}

VTS_URL_CONFIG = {
        "internal_base": "gs://chromeos-arc-images/vts/bundle/T/",
        "preview_url_pattern": "android-vts-%s-linux_%s.zip",
        "preview_version_name": "8890152",
        "abi_list": {
                "arm": "test_suites_arm64",
                "x86": "test_suites_x86_64"
        }
}

class BundelUtilsTest(unittest.TestCase):
    """Unittest for bundle_utils."""

    @classmethod
    def setUpClass(self):
        self.test_dir = tempfile.mkdtemp()
        self.cts_config_path = os.path.join(self.test_dir, 'cts_config')

    def setUp(self):
        with open(self.cts_config_path, mode="w") as f:
            json.dump(CTS_URL_CONFIG, f, indent=4)

    @classmethod
    def tearDownClass(self):
        shutil.rmtree(self.test_dir)

    def test_load_config(self):
        """Test for load_config."""

        url_config = bundle_utils.load_config(self.cts_config_path)
        self.assertEquals(CTS_URL_CONFIG, url_config)

    def test_get_official_version_cts(self):
        """Test for cts get_official_version."""

        official_version = bundle_utils.get_official_version(
                url_config=CTS_URL_CONFIG, )
        self.assertEquals('11_r9', official_version)

    def test_get_official_version_error(self):
        """Test for bundle error of get_official_version.

        get_official_version raises a NoVersionNameException,
        when url_config does not contain official_version_name.
        """

        with self.assertRaises(bundle_utils.NoVersionNameException):
            bundle_utils.get_official_version(url_config={})

    def test_get_preview_version_cts(self):
        """Test for cts get_preview_version."""

        preview_version = bundle_utils.get_preview_version(
                url_config=CTS_URL_CONFIG)
        self.assertEquals('9199760', preview_version)

    def test_get_preview_version_error(self):
        """Test for bundle error of get_preview_version.

        get_preview_version raises a NoVersionNameException,
        when url_config does not contain preview_version_name.
        """

        with self.assertRaises(bundle_utils.NoVersionNameException):
            bundle_utils.get_preview_version(url_config={})

    def test_get_abi_info_cts(self):
        """Test for cts get_abi_info."""

        abi_list = bundle_utils.get_abi_info(url_config=CTS_URL_CONFIG)
        self.assertEquals(
                {
                        "arm": "test_suites_arm64",
                        "x86": "test_suites_x86_64"
                }, abi_list)

    def test_get_abi_info_error(self):
        """Test for bundle error of get_abi_info.

        get_abi_info raises an AbiNotFoundException,
        when url_config does not contain abi_list.
        """

        with self.assertRaises(bundle_utils.AbiNotFoundException):
            bundle_utils.get_abi_info(url_config={})

    def test_modify_version_name_in_config_preview(self):
        """Test for cts preview modify_version_name_in_config."""

        expected_version = '0'
        bundle_utils.modify_version_name_in_config(
                latest_version_name=expected_version,
                config_path=self.cts_config_path,
                target_key='preview_version_name')
        with open(self.cts_config_path) as json_object:
            actual_version = json.load(json_object)['preview_version_name']
        self.assertEquals(expected_version, actual_version)

    def test_modify_version_name_in_config_official(self):
        """Test for cts official modify_version_name_in_config."""

        expected_version = '0'
        bundle_utils.modify_version_name_in_config(
                latest_version_name=expected_version,
                config_path=self.cts_config_path,
                target_key='official_version_name')
        with open(self.cts_config_path) as json_object:
            actual_version = json.load(json_object)['official_version_name']
        self.assertEquals(expected_version, actual_version)

    def test_modify_version_name_in_config_error(self):
        """Test for bundle error of modify_version_name_in_config.

        modify_version_name_in_config modifies version name. It raises an InvalidVersionNameKeyException
        when an inappropriate version name is specified.
        """

        modified_json_path = os.path.join(self.test_dir, 'error_test.json')
        with open(modified_json_path, mode='w') as f:
            json.dump(CTS_URL_CONFIG, f, indent=4)
        with self.assertRaises(bundle_utils.InvalidVersionNameKeyException):
            bundle_utils.modify_version_name_in_config(
                    latest_version_name='test',
                    config_path=modified_json_path,
                    target_key='abi_list')

    def test_make_urls_for_all_abis_cts_public(self):
        """Test for cts make_urls_for_all_abis in the case of public."""

        urls = bundle_utils.make_urls_for_all_abis(url_config=CTS_URL_CONFIG,
                                                   bundle_type=None)
        self.assertEquals(
                set([
                        'https://dl.google.com/dl/android/cts/android-cts-11_r9-linux_x86-arm.zip',
                        'https://dl.google.com/dl/android/cts/android-cts-11_r9-linux_x86-x86.zip'
                ]), set(urls))

    def test_make_urls_for_all_abis_cts_latest(self):
        """Test for cts make_urls_for_all_abis in the case of latest."""

        urls = bundle_utils.make_urls_for_all_abis(url_config=CTS_URL_CONFIG,
                                                   bundle_type='LATEST')
        self.assertEquals(
                set([
                        'gs://chromeos-arc-images/cts/bundle/R/android-cts-11_r9-linux_x86-arm.zip',
                        'gs://chromeos-arc-images/cts/bundle/R/android-cts-11_r9-linux_x86-x86.zip'
                ]), set(urls))

    def test_make_urls_for_all_abis_cts_dev(self):
        """Test for cts make_urls_for_all_abis in the case of dev."""

        urls = bundle_utils.make_urls_for_all_abis(url_config=CTS_URL_CONFIG,
                                                   bundle_type='DEV')
        self.assertEquals(
                set([
                        'gs://chromeos-arc-images/cts/bundle/R/android-cts-9199760-linux_x86-arm.zip',
                        'gs://chromeos-arc-images/cts/bundle/R/android-cts-9199760-linux_x86-x86.zip'
                ]), set(urls))

    def test_make_urls_for_all_abis_gts_public(self):
        """Test for gts make_urls_for_all_abis in the case of public."""

        urls = bundle_utils.make_urls_for_all_abis(url_config=GTS_URL_CONFIG,
                                                   bundle_type=None)
        self.assertEquals(
                set([
                        'gs://chromeos-partner-gts/android-gts-9.1-R2-P-8632016.zip'
                ]), set(urls))

    def test_make_urls_for_all_abis_gts_latest(self):
        """Test for gts make_urls_for_all_abis in the case of latest."""

        urls = bundle_utils.make_urls_for_all_abis(url_config=GTS_URL_CONFIG,
                                                   bundle_type='LATEST')
        self.assertEquals(
                set([
                        'gs://chromeos-arc-images/cts/bundle/android-gts-9.1-R2-P-8632016.zip'
                ]), set(urls))

    def test_make_urls_for_all_abis_gts_dev(self):
        """Test for gts make_urls_for_all_abis in the case of dev."""

        urls = bundle_utils.make_urls_for_all_abis(url_config=GTS_URL_CONFIG,
                                                   bundle_type='DEV')
        self.assertEquals(
                set([
                        'gs://chromeos-arc-images/cts/bundle/android-gts-9.1-R2-P-Preview18-9049557.zip'
                ]), set(urls))

    def test_make_urls_for_all_abis_sts_public(self):
        """Test for sts make_urls_for_all_abis in the case of public.

        STS does not have public and official url, so it raises an BundleNotFoundException.
        """

        with self.assertRaises(bundle_utils.BundleNotFoundException):
            bundle_utils.make_urls_for_all_abis(url_config=STS_URL_CONFIG,
                                                bundle_type=None)

    def test_make_urls_for_all_abis_sts_latest(self):
        """Test for sts make_urls_for_all_abis in the case of latest.

        STS does not have official url, so it raises an BundleNotFoundException.
        """

        with self.assertRaises(bundle_utils.BundleNotFoundException):
            bundle_utils.make_urls_for_all_abis(url_config=STS_URL_CONFIG,
                                                bundle_type='LATEST')

    def test_make_urls_for_all_abis_sts_dev(self):
        """Test for sts make_urls_for_all_abis in the case of dev."""

        urls = bundle_utils.make_urls_for_all_abis(url_config=STS_URL_CONFIG,
                                                   bundle_type='DEV')
        self.assertEquals(
                set([
                        'gs://chromeos-arc-images/sts/bundle/R/android-sts-11_sts-latest-linux-arm64.zip',
                        'gs://chromeos-arc-images/sts/bundle/R/android-sts-11_sts-latest-linux-x86_64.zip'
                ]), set(urls))

    def test_make_urls_for_all_abis_vts_public(self):
        """Test for vts make_urls_for_all_abis in the case of public.

        VTS does not have public and official url, so it raises an BundleNotFoundException.
        """

        with self.assertRaises(bundle_utils.BundleNotFoundException):
            bundle_utils.make_urls_for_all_abis(url_config=VTS_URL_CONFIG,
                                                bundle_type=None)

    def test_make_urls_for_all_abis_vts_latest(self):
        """Test for vts make_urls_for_all_abis in the case of latest.

        VTS does not have official url, so it raises an BundleNotFoundException.
        """

        with self.assertRaises(bundle_utils.BundleNotFoundException):
            bundle_utils.make_urls_for_all_abis(url_config=VTS_URL_CONFIG,
                                                bundle_type='LATEST')

    def test_make_urls_for_all_abis_vts_dev(self):
        """Test for vts make_urls_for_all_abis in the case of dev."""

        urls = bundle_utils.make_urls_for_all_abis(url_config=VTS_URL_CONFIG,
                                                   bundle_type='DEV')
        self.assertEquals(
                set([
                        'gs://chromeos-arc-images/vts/bundle/T/android-vts-8890152-linux_arm.zip',
                        'gs://chromeos-arc-images/vts/bundle/T/android-vts-8890152-linux_x86.zip'
                ]), set(urls))

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
                'gs://chromeos-arc-images/cts/bundle/R/android-cts-9199760-linux_x86-arm.zip',
                uri)

    def test_make_bundle_url_cts_dev_x86(self):
        """Test for cts make_bundle_url in the case of (dev, x86)."""

        uri = bundle_utils.make_bundle_url(
            url_config=CTS_URL_CONFIG,
            bundle_type='DEV',
            abi='x86'
        )
        self.assertEquals(
                'gs://chromeos-arc-images/cts/bundle/R/android-cts-9199760-linux_x86-x86.zip',
                uri)

    def test_make_bundle_url_gts_public(self):
        """Test for gts make_bundle_url in the case of (public)."""

        uri = bundle_utils.make_bundle_url(
            url_config=GTS_URL_CONFIG,
            bundle_type=None,
            abi=None
        )
        self.assertEquals(
            'gs://chromeos-partner-gts/android-gts-9.1-R2-P-8632016.zip', uri
        )

    # b/256079546: In GTS, _ABI_LIST is not in url_config, but abi may be specified.
    def test_make_bundle_url_gts_public_arm(self):
        """Test for gts make_bundle_url in the case of (public, arm)."""
        self.assertNotIn(bundle_utils._ABI_LIST, GTS_URL_CONFIG)

        uri = bundle_utils.make_bundle_url(
            url_config=GTS_URL_CONFIG,
            bundle_type=None,
            abi='arm'
        )
        self.assertEquals(
            'gs://chromeos-partner-gts/android-gts-9.1-R2-P-8632016.zip', uri
        )

    # b/256079546: In GTS, _ABI_LIST is not in url_config, but abi may be specified.
    def test_make_bundle_url_gts_public_x86(self):
        """Test for gts make_bundle_url in the case of (public, x86)."""
        self.assertNotIn(bundle_utils._ABI_LIST, GTS_URL_CONFIG)

        uri = bundle_utils.make_bundle_url(
            url_config=GTS_URL_CONFIG,
            bundle_type=None,
            abi='x86'
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

    # b/256079546: In GTS, _ABI_LIST is not in url_config, but abi may be specified.
    def test_make_bundle_url_gts_latest_arm(self):
        """Test for gts make_bundle_url in the case of (latest, arm)."""
        self.assertNotIn(bundle_utils._ABI_LIST, GTS_URL_CONFIG)

        uri = bundle_utils.make_bundle_url(
            url_config=GTS_URL_CONFIG,
            bundle_type='LATEST',
            abi='arm'
        )
        self.assertEquals(
            'gs://chromeos-arc-images/cts/bundle/android-gts-9.1-R2-P-8632016.zip', uri
        )

    # b/256079546: In GTS, _ABI_LIST is not in url_config, but abi may be specified.
    def test_make_bundle_url_gts_latest_x86(self):
        """Test for gts make_bundle_url in the case of (latest, x86)."""
        self.assertNotIn(bundle_utils._ABI_LIST, GTS_URL_CONFIG)

        uri = bundle_utils.make_bundle_url(
            url_config=GTS_URL_CONFIG,
            bundle_type='LATEST',
            abi='x86'
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

    # b/256079546: In GTS, _ABI_LIST is not in url_config, but abi may be specified.
    def test_make_bundle_url_gts_dev_arm(self):
        """Test for gts make_bundle_url in the case of (dev, arm)."""
        self.assertNotIn(bundle_utils._ABI_LIST, GTS_URL_CONFIG)

        uri = bundle_utils.make_bundle_url(
            url_config=GTS_URL_CONFIG,
            bundle_type='DEV',
            abi='arm'
        )
        self.assertEquals(
            'gs://chromeos-arc-images/cts/bundle/android-gts-9.1-R2-P-Preview18-9049557.zip', uri
        )

    # b/256079546: In GTS, _ABI_LIST is not in url_config, but abi may be specified.
    def test_make_bundle_url_gts_dev_x86(self):
        """Test for gts make_bundle_url in the case of (dev, x86)."""
        self.assertNotIn(bundle_utils._ABI_LIST, GTS_URL_CONFIG)

        uri = bundle_utils.make_bundle_url(
            url_config=GTS_URL_CONFIG,
            bundle_type='DEV',
            abi='x86'
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

    def test_make_bundle_url_abi_error(self):
        """Test for abi error of make_bundle_url"""

        with self.assertRaises(bundle_utils.AbiNotFoundException):
            bundle_utils.make_bundle_url(url_config=CTS_URL_CONFIG,
                                         bundle_type=None,
                                         abi='test')

    def test_make_bundle_url_bundle_error(self):
        """Test for bundle error of make_bundle_url"""

        with self.assertRaises(bundle_utils.BundleNotFoundException):
            bundle_utils.make_bundle_url(url_config=CTS_URL_CONFIG,
                                         bundle_type='TEST',
                                         abi='arm')

    def test_get_bundle_password(self):
        self.assertEqual(
                bundle_utils.get_bundle_password(
                        {'bundle_password': 'mysecurepassword'}),
                'mysecurepassword')

    # Verify that if a password is not specified, it returns an empty string.
    def test_get_bundle_password_not_specified(self):
        self.assertEqual(
                bundle_utils.get_bundle_password(
                        {'non_password_entry': 'somethingsomething123'}), '')

    def test_make_preview_urls_cts(self):
        """Test for cts make_preview_urls"""

        preview_urls = bundle_utils.make_preview_urls(
                url_config=CTS_URL_CONFIG, abi='arm')
        self.assertEquals([
                'gs://chromeos-arc-images/cts/bundle/R/android-cts-9199760-linux_x86-arm.zip',
                'gs://chromeos-partner-gts/R/android-cts-9199760-linux_x86-arm.zip'
        ], preview_urls)

    def test_make_preview_urls_vts(self):
        """Test for vts make_preview_urls"""

        preview_urls = bundle_utils.make_preview_urls(
                url_config=VTS_URL_CONFIG, abi='arm')
        self.assertEquals([
                'gs://chromeos-arc-images/vts/bundle/T/android-vts-8890152-linux_arm.zip'
        ], preview_urls)
