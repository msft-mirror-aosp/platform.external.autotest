#!/usr/bin/env python2
# Copyright 2020 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import logging

import common

class AuditError(Exception):
  """Generic error raised during audit."""


class _BaseVerifier(object):
    """Base verify provide and keep base information and methods.

    Verifiers run audit against target host specified by 'get_host()'
    method in subclasses. CrosHost for audit actions against DUT, ServoHost
    for actions against servo and its dependencies.

    Main logic located in '_verify()' method.
    """

    def __init__(self, dut_host):
        self._dut_host = dut_host

    def verify(self):
        """Main method to start the verifier"""
        raise NotImplementedError("'verify' method not implemented")

    def _verify(self):
        """Main method to run the logic of the verifier.

        Access to the host provided by `self.get_host()`.
        """
        raise NotImplementedError("'verify' method not implemented")

    def get_host(self):
        """Provide access to target host"""
        raise NotImplementedError("'get_host' method not implemented")

    def _set_host_info_state(self, prefix, state):
        """Update state value to the label in the host_info

        @param host: dut host presentation to provide access to host_info
        @param prefix: label prefix. (ex. label_prefix:value)
        @param state: new state value for the label
        """
        if self._dut_host and prefix:
            host_info = self._dut_host.host_info_store.get()
            old_state = host_info.get_label_value(prefix)
            host_info.set_version_label(prefix, state)
            logging.info('Set %s as `%s` (previous: `%s`)',
                            prefix, state, old_state)
            self._dut_host.host_info_store.commit(host_info)


class _BaseDUTVerifier(_BaseVerifier):
    """Base verify check availability of DUT before run actual verifier.

    Verifier run audit actions against CrosHost.
    """

    def get_host(self):
        """Return CrosHost"""
        return self._dut_host

    def verify(self):
        """Vallidate the host reachable by SSH and run verifier"""
        if not self._dut_host:
            raise AuditError('host is not present')
        if not self._dut_host.is_up(timeout=20):
            # for failed DUTs will add logic to try to load them from USB
            # need more analysis to confirm it
            raise AuditError('host is not ssh-able')
        self._verify()


class _BaseServoVerifier(_BaseVerifier):
    """Base verify check availability of Servo before run actual verifier

    Verifier run audit actions against ServoHost.
    """

    def get_host(self):
        """Return ServoHost"""
        return self._dut_host._servo_host

    def verify(self):
        """Vallidate the host and servo initialized and run verifier"""
        if not self._dut_host or not self._dut_host._servo_host:
            raise AuditError('host is not present')
        if not self._dut_host.servo:
            raise AuditError('servo is not initialized')
        self._verify()
