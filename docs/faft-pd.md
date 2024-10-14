# PD FAFT

_Self-link: [go/faft-pd](https://goto.google.com/faft-pd)_

PD FAFT is another set of firmware tests (FAFT), which targets testing USB-C,
PD (Power Delivery) functionalities, and ULP (Ultra Low Power) mode.

[TOC]

## Overview {#overview}

The USB-C and PD stack is complex that involves multiple hardware/firmware:

*   TCPM (USB Type-C Port Manager),
    [integrated in EC, using Chrome EC firmware](https://chromium.googlesource.com/chromiumos/platform/ec/+/main/docs/usb-c.md)
*   TCPC (USB Type-C Port Controller), usually using proprietary firmware, in
    the form of
    *   dedicated chip, like ANX74xx, PS8xxx,
    *   integrated in EC, like IT83xx, or
    *   integrated in PMIC, like MT6370.

The USB-C path also has other functions, like:

*   DisplayPort, which shares the SuperSpeed lanes and the SBU channel;
*   CCD, which shares the SBU channel and has special CC terminations.

Many USB-C bugs are mysterious or flaky, like CCD not being detected, USB
Ethernet connection being lost, or external monitors not showing up, etc. This
kind of issue blocks BIOS/EC FAFT running. Some bugs may be even more serious
that brick the hardware, negotiating a wrong voltage/current.

PD FAFT was proposed to uncover any regression on the PD stack in an automated
way.

PD FAFT requires hardware to emulate the PD port partner, e.g. a PD-capable
power adapter, a USB-C hub, a USB-C debug accessory, a USB-C protocol converter,
a USB-C monitor, etc. PD FAFT uses
[ServoV4](https://chromium.googlesource.com/chromiumos/third_party/hdctools/+/main/docs/servo_v4.md)
as PDTester.

## Test details {#test-details}

The PD FAFT tests are located in the src/platform/tast-tests/src/go.chromium.org/tast-tests/cros/remote/bundles/cros/firmware
directory, usually with the prefix pd_.

firmware.PDConnect, checks:

*   Ability to disconnect, then reconnect establishing a successful PD contract
*   If PD Dual role mode is operational in the DUT

firmware.PDPowerSwap, checks:

*   If the DUT advertises support for dualrole operation
*   If the DUT can receive power swap requests
*   If the DUT can initiate power swap requests

firmware.PDDataSwap, checks:

*   If the DUT advertises support for data role swaps
*   If the DUT can receive data swap requests
*   If the DUT can initiate data swap requests

firmware.PDResetHard, checks:

*   Ability of DUT to initiate hard resets
*   Ability of DUT to receive hard resets
*   If DUT is dualrole capable, hard resets are done with the DUT in each power
    role

firmware.PDResetSoft, checks:

*   Ability of DUT to initiate soft resets
*   Ability of DUT to receive soft reset requests from servo
*   If DUT is dualrole capable, soft resets are done with the DUT in each power
    role

firmware.PDTrySrc, checks:

*   If the DUT advertises support for dualrole and Try.SRC operation
*   A series of disconnects/connects with Try.SRC on
*   A series of disconnects/connects with Try.SRC off
*   Try.SRC on the DUT connects in SRC mode

firmware.PDVbusRequest, checks:

*   Ability to initiate a new PD contract with different VBUS value, according
    to the attached charger capability, like 5V, 9V, 12V, 15V, 20V, etc.
*   Receiving Source Capability messages from PDTester
*   If PD Dual role mode is operational in the DUT

firmware.ECWakefromULP, checks:

*   Ability to wake AP and EC from ULP mode by PB, LID.
*   Ability to wake EC from ULP mode by AC.

The above tests may have multiple subtests, the same test body but different
prerequisite.

.flip subtest, checks

*   If DUT passes the same test on the flipped plug direction, which is
    implemented by electrically flipping the CC signals on PDTester

.dts subtest, checks

*   If DUT passes the same test on a USB-C debug accessory
*   No behavior difference between the normal scenarios and the CCD scenarios
    (it is important as BIOS/EC FAFT uses the CCD setup)

## How to run PD FAFT {#how-to-run-pd-faft}

Hardware setup, check this
[ServoV4 Type-C with servo micro setup](https://chromium.googlesource.com/chromiumos/third_party/autotest/+/refs/heads/main/docs/faft-how-to-run-doc.md#servov4-typec-micro).

Software setup, check this
[Running Tests instructions](https://chromium.googlesource.com/chromiumos/third_party/autotest/+/refs/heads/main/docs/faft-how-to-run-doc.md#faft-running-tests).

## Known issues {#known-issues}

### Multiple USB-C ports {#multiple-usb-c-ports}

Due to the hardware limitation, that PDTester (ServoV4) only supports testing
one DUT-facing USB-C port at a time. If a DUT has two USB-C ports, you have to
run PD FAFT twice -- once for each port under test.
