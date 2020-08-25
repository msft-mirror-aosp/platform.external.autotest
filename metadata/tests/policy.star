
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

# !!! GENERATED FILE. DO NOT EDIT !!!

load('//metadata/test_common.star', 'test_common')

def define_tests():
    return [
        test_common.define_test(
            'policy/AccessibilityTest',
            suites = [],
        ),
        test_common.define_test(
            'policy/AlternateErrorPages',
            suites = [],
        ),
        test_common.define_test(
            'policy/ArcAudioCaptureAllowed',
            suites = [],
        ),
        test_common.define_test(
            'policy/ArcBackupRestoreServiceEnabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/ArcDisableScreenshots',
            suites = [],
        ),
        test_common.define_test(
            'policy/ArcExternalStorageDisabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/ArcVideoCaptureAllowed',
            suites = [],
        ),
        test_common.define_test(
            'policy/AudioOutputAllowed',
            suites = [],
        ),
        test_common.define_test(
            'policy/AutotestSanity',
            suites = ['bvt-perbuild', 'ent-nightly', 'policy', 'smoke'],
        ),
        test_common.define_test(
            'policy/BookmarkBarEnabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/ChromeOsLockOnIdleSuspend',
            suites = [],
        ),
        test_common.define_test(
            'policy/CookiesAllowedForUrls',
            suites = [],
        ),
        test_common.define_test(
            'policy/CookiesBlockedForUrls',
            suites = [],
        ),
        test_common.define_test(
            'policy/CookiesSessionOnlyForUrls',
            suites = [],
        ),
        test_common.define_test(
            'policy/DefaultGeolocationSetting',
            suites = [],
        ),
        test_common.define_test(
            'policy/DefaultImagesSetting',
            suites = [],
        ),
        test_common.define_test(
            'policy/DefaultJavaScriptSetting',
            suites = [],
        ),
        test_common.define_test(
            'policy/DefaultNotificationsSetting',
            suites = [],
        ),
        test_common.define_test(
            'policy/DefaultSearchProvider',
            suites = [],
        ),
        test_common.define_test(
            'policy/DefaultSearchProviderEnabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/DeveloperToolsAvailability',
            suites = [],
        ),
        test_common.define_test(
            'policy/DeviceAllowBluetooth',
            suites = [],
        ),
        test_common.define_test(
            'policy/DeviceAutoUpdateDisabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/DeviceBootOnAcEnabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/DeviceCharging',
            suites = [],
        ),
        test_common.define_test(
            'policy/DeviceEphemeralUsersEnabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/DeviceScheduledCharging',
            suites = [],
        ),
        test_common.define_test(
            'policy/DeviceWilcoDtcAllowed',
            suites = [],
        ),
        test_common.define_test(
            'policy/DisableScreenshots',
            suites = [],
        ),
        test_common.define_test(
            'policy/DownloadDirectory',
            suites = [],
        ),
        test_common.define_test(
            'policy/DriveDisabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/EditBookmarksEnabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/EnrollmentRetainment',
            suites = [],
        ),
        test_common.define_test(
            'policy/EnterpriseForceInstallCustom',
            suites = [],
        ),
        test_common.define_test(
            'policy/ExtensionAllowedTypes',
            suites = [],
        ),
        test_common.define_test(
            'policy/ExtensionControl',
            suites = [],
        ),
        test_common.define_test(
            'policy/ExtensionPolicy',
            suites = ['ent-nightly', 'policy'],
        ),
        test_common.define_test(
            'policy/ExternalStorageDisabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/ExternalStorageReadOnly',
            suites = [],
        ),
        test_common.define_test(
            'policy/ForceGoogleSafeSearch',
            suites = [],
        ),
        test_common.define_test(
            'policy/ForceYouTubeRestrict',
            suites = [],
        ),
        test_common.define_test(
            'policy/ForceYouTubeSafetyMode',
            suites = [],
        ),
        test_common.define_test(
            'policy/GlobalNetworkSettings',
            suites = [],
        ),
        test_common.define_test(
            'policy/HomepageLocation',
            suites = [],
        ),
        test_common.define_test(
            'policy/ImagesAllowedForUrls',
            suites = [],
        ),
        test_common.define_test(
            'policy/ImagesBlockedForUrls',
            suites = [],
        ),
        test_common.define_test(
            'policy/JavaScriptAllowedForUrls',
            suites = [],
        ),
        test_common.define_test(
            'policy/JavaScriptBlockedForUrls',
            suites = [],
        ),
        test_common.define_test(
            'policy/KeyPermissions',
            suites = [],
        ),
        test_common.define_test(
            'policy/KeyboardDefaultFunctionKeys',
            suites = [],
        ),
        test_common.define_test(
            'policy/KioskModeEnabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/ManagedBookmarks',
            suites = [],
        ),
        test_common.define_test(
            'policy/NewTabPageLocation',
            suites = [],
        ),
        test_common.define_test(
            'policy/NotificationsAllowedForUrls',
            suites = [],
        ),
        test_common.define_test(
            'policy/NotificationsBlockedForUrls',
            suites = [],
        ),
        test_common.define_test(
            'policy/PinnedLauncherApps',
            suites = [],
        ),
        test_common.define_test(
            'policy/PlatformKeys',
            suites = ['ent-nightly', 'policy'],
        ),
        test_common.define_test(
            'policy/PluginsAllowedForUrls',
            suites = [],
        ),
        test_common.define_test(
            'policy/PluginsBlockedForUrls',
            suites = [],
        ),
        test_common.define_test(
            'policy/PolicyRefreshRate',
            suites = [],
        ),
        test_common.define_test(
            'policy/PopupsAllowedForUrls',
            suites = [],
        ),
        test_common.define_test(
            'policy/PopupsBlockedForUrls',
            suites = [],
        ),
        test_common.define_test(
            'policy/PowerManagementIdleSettings',
            suites = [],
        ),
        test_common.define_test(
            'policy/PrintingEnabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/PromptForDownloadLocation',
            suites = [],
        ),
        test_common.define_test(
            'policy/ProxySettings',
            suites = [],
        ),
        test_common.define_test(
            'policy/ReportUploadFrequency',
            suites = [],
        ),
        test_common.define_test(
            'policy/RestoreOnStartupURLs',
            suites = [],
        ),
        test_common.define_test(
            'policy/SafeBrowsingEnabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/SavingBrowserHistoryDisabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/ScreenBrightnessPercent',
            suites = [],
        ),
        test_common.define_test(
            'policy/SearchSuggestEnabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/SecondaryGoogleAccountSigninAllowed',
            suites = [],
        ),
        test_common.define_test(
            'policy/ShowHomeButton',
            suites = [],
        ),
        test_common.define_test(
            'policy/ShowLogoutButtonInTray',
            suites = [],
        ),
        test_common.define_test(
            'policy/SystemTimezone',
            suites = [],
        ),
        test_common.define_test(
            'policy/TouchVirtualKeyboardEnabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/TranslateEnabled',
            suites = [],
        ),
        test_common.define_test(
            'policy/UIUtilsSmokeTest',
            suites = [],
        ),
        test_common.define_test(
            'policy/UserNativePrintersAllowed',
            suites = [],
        ),
        test_common.define_test(
            'policy/VirtualMachinesAllowed',
            suites = [],
        ),
        test_common.define_test(
            'policy/WiFiAutoconnect',
            suites = [],
        ),
        test_common.define_test(
            'policy/WiFiPrecedence',
            suites = [],
        ),
        test_common.define_test(
            'policy/WiFiTypes',
            suites = [],
        ),
        test_common.define_test(
            'policy/WiFiTypesServer',
            suites = [],
        ),
        test_common.define_test(
            'policy/WilcoOnNonWilcoDevice',
            suites = [],
        ),
        test_common.define_test(
            'policy/WilcoUSBPowershare',
            suites = [],
        )
    ]
