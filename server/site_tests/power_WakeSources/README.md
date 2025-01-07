# Wake sources testing

[TOC]

## Introduction

On Chrome device, several wake sources are expected to wake the system from
sleep. Not all wake sources will turn the display back on after resume (if
[Dark Resume] is enabled). Only wakes that are triggered by input devices will
cause a full Resume (turn the display on).

This test thus makes sure that wakes from input devices cause a Full Resume.
This test also makes sure that RTC triggers a Dark Resume.

## Steps to run the test

The steps below describe how to run the test with a Servo V4. The steps should
be similar for other Servos too.

1.  Make sure that servo has the latest firmware.
    *   `$ sudo servo_updater`
1.  This test depends on the Servo's USB HID emulator capability. See
    https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/HEAD/docs/servo_v4p1_cf.md#programming-the-atmel-atmega32u4
    if your servo's atmel keyboard emulator isn't flashed (uncommon).
1.  Make sure that the USBC charger is plugged into Servo before running the
    test.
1.  Run the test.
    *   `$ test_that ${DUT_ipaddr} power_WakeSources`
1.  Once run, the test publishes a keyval with test results similar to the list
    below.

```python
BASE_ATTACH=SKIPPED
BASE_DETACH=SKIPPED
INTERNAL_KB=PASS
LID_OPEN=PASS
PWR_BTN=PASS
RTC=PASS
TABLET_MODE_OFF=PASS
TABLET_MODE_ON=PASS
USB_KB=FAIL
```

5.  If any of the wake source did not result in expected behavior, the results
    file will indicate it as `FAIL`. For example `USB_KB` in the above result
    did not trigger a full wake.
6.  If any of the valid wake sources for a given platform is `SKIPPED`, please
    [test it manually](#Testing-wake-source-manually).
7.  If you see a valid wake source for a given platform missing from the list,
    please [test it manually](#Testing-wake-source-manually). For example
    internal trackpad is missing from the above list.

## Testing wake source manually

The steps below describe how to test wake sources manually.

1.  Make sure [dark resume is disabled].
2.  Suspend the device using the following command.
    *   `$ powerd_dbus_suspend --print_wakeup_type`
3.  Once the device suspends, trigger the wake using the specific wake source.
4.  For full wake sources except display, you should see output similar to
    `[0916/110326.423855:INFO:powerd_dbus_suspend.cc(57)] Wakeup type : input`.
    *   For display, you may see output similar to `[dark_resume.cc(63)] Transitioning from dark resume to full resume`
        in /var/log/power_manager/powerd.LATEST.
5.  For dark wake sources, you should see output similar to `[0916/110326.423855
    :INFO:powerd_dbus_suspend.cc(57)] Wakeup type : other`.


\[Dark Resume\]: https://chromium.googlesource.com/chromiumos/platform2/+/main/power_manager/docs/dark_resume.md <br>
\[dark resume is disabled\]: https://chromium.googlesource.com/chromiumos/platform2/+/main/power_manager/docs/dark_resume.md#Disabling-Dark-Resume <br>
\[keyboard.hex\]: https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/refs/heads/main/servo/firmware/usbkm/KeyboardSerial/Keyboard.hex <br>
\[chromeos-platform-power\]:  cros-power-notifications@google.com <br>
