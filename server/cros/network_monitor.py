# Copyright 2026 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
import logging
import threading
import time
import urllib.parse

class NetworkMonitor:
    """Generic network monitor to track connection and speed during long downloads."""

    # Target interfaces to monitor for debugging rx_bytes drops
    DEBUG_INTERFACES = ['eth', 'wlan', 'mlan', 'usb0']

    BYTES_TO_MB = 1024 * 1024

    def __init__(self, host, target_url):
        self._host = host
        self._target_url = target_url
        self._stop_monitor = threading.Event()
        self._thread = None
        self.previous_rx_bytes = 0
        self.previous_time = 0

    def _get_devserver_ip(self):
        try:
            url = self._target_url

            # urlparse requires a scheme to correctly identify the hostname.
            # If missing, prepend a dummy 'http://' just for parsing purposes.
            if '://' not in url:
                url = 'http://' + url

            parsed_url = urllib.parse.urlparse(url)
            return parsed_url.hostname
        except Exception as e:
            logging.error("NETWORK_MONITOR: Failed to parse devserver IP: %s", e)
            return None

    def _get_total_rx_bytes(self):
        try:
            res = self._host.run('cat /proc/net/dev', ignore_status=True)
            if res.exit_status != 0 or not res.stdout:
                logging.error("NETWORK_MONITOR: Failed to read /proc/net/dev. Exit status: %s", res.exit_status)
                return 0
            total = 0
            for line in res.stdout.splitlines():
                if any(iface in line for iface in self.DEBUG_INTERFACES):
                    parts = line.split(':')
                    if len(parts) == 2:
                        total += int(parts[1].split()[0])
            return total
        except Exception as e:
            logging.error("NETWORK_MONITOR: Exception while calculating rx_bytes: %s", e)
            return 0

    def _monitor_network(self):
        devserver_ip = self._get_devserver_ip()
        logging.info("NETWORK_MONITOR: Started verbose background polling (IP: %s).", devserver_ip)

        self.previous_rx_bytes = self._get_total_rx_bytes()
        self.previous_time = time.time()

        while not self._stop_monitor.is_set():
            try:
                # Interface Check
                link_res = self._host.run('ip -o link show up', ignore_status=True)
                active_interfaces = []
                if link_res.exit_status == 0 and link_res.stdout:
                    for line in link_res.stdout.splitlines():
                        if 'loopback' in line or 'lo' in line:
                            continue
                        parts = line.split(':')
                        if len(parts) >= 2:
                            active_interfaces.append(parts[1].strip().split('@')[0])

                if not active_interfaces:
                    logging.warning("NETWORK_MONITOR: HARDWARE WARNING - All network interfaces are DOWN!")

                # Ping Test
                if devserver_ip:
                    ping_res = self._host.run('ping -c 1 -W 2 %s' % devserver_ip, ignore_status=True)
                    if ping_res.exit_status != 0:
                        logging.warning("NETWORK_MONITOR: Ping to %s -> FAILED (Packet Drop!)", devserver_ip)
                else:
                    logging.warning("NETWORK_MONITOR: Skipping ping test; devserver IP could not be resolved.")

                # Speed Calculation
                current_rx_bytes = self._get_total_rx_bytes()
                current_time = time.time()

                # Only calculate speed and update baseline if we got a valid reading (solves the 0 bug)
                if current_rx_bytes > 0:
                    # Ensure we have a valid previous reading before doing math
                    if self.previous_rx_bytes > 0:
                        bytes_downloaded = current_rx_bytes - self.previous_rx_bytes

                        # Prevent negative math in case device network counters reset
                        if bytes_downloaded >= 0:
                            time_elapsed = current_time - self.previous_time

                            # Use the new constant here instead of hardcoding 1024 * 1024
                            speed_mbps = (bytes_downloaded / time_elapsed) / self.BYTES_TO_MB

                            logging.info("NETWORK_MONITOR: Current download speed: %.2f MB/s", speed_mbps)

                    # Update the 'previous' variables for the next loop
                    self.previous_rx_bytes = current_rx_bytes
                    self.previous_time = current_time

            except Exception as e:
                logging.error("NETWORK_MONITOR: SSH connection failed! Network likely dropped: %s", e)

            # Sleep check
            for _ in range(10):
                if self._stop_monitor.is_set():
                    break
                time.sleep(1)

    def start(self):
        self._thread = threading.Thread(target=self._monitor_network, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop_monitor.set()
        if self._thread:
            self._thread.join(timeout=30)
