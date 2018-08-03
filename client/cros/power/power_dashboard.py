# Copyright (c) 2017 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.

import collections
import json
import numpy
import os
import re
import time
import urllib
import urllib2

from autotest_lib.client.bin import utils
from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import lsbrelease_utils
from autotest_lib.client.common_lib.cros import retry
from autotest_lib.client.cros.power import power_status
from autotest_lib.client.cros.power import power_utils

_HTML_CHART_STR = '''
<!DOCTYPE html>
<html>
<head>
<script type="text/javascript" src="https://www.gstatic.com/charts/loader.js">
</script>
<script type="text/javascript">
    google.charts.load('current', {{'packages':['corechart']}});
    google.charts.setOnLoadCallback(drawChart);
    function drawChart() {{
        var data = google.visualization.arrayToDataTable([
{data}
        ]);
        var unit = '{unit}';
        var options = {{
            width: 1600,
            height: 1200,
            lineWidth: 1,
            legend: {{ position: 'top', maxLines: 3 }},
            vAxis: {{ viewWindow: {{min: 0}}, title: '{type} ({unit})' }},
            hAxis: {{ viewWindow: {{min: 0}}, title: 'time (second)' }},
        }};
        var element = document.getElementById('{type}');
        var chart;
        if (unit == 'percent') {{
            options['isStacked'] = true;
            chart = new google.visualization.SteppedAreaChart(element);
        }} else {{
            chart = new google.visualization.LineChart(element);
        }}
        chart.draw(data, options);
    }}
</script>
</head>
<body>
<div id="{type}"></div>
</body>
</html>
'''


class BaseDashboard(object):
    """Base class that implements method for prepare and upload data to power
    dashboard.
    """

    def __init__(self, logger, testname, resultsdir=None, uploadurl=None):
        """Create BaseDashboard objects.

        Args:
            logger: object that store the log. This will get convert to
                    dictionary by self._convert()
            testname: name of current test
            resultsdir: directory to save the power json
            uploadurl: url to upload power data
        """
        self._logger = logger
        self._testname = testname
        self._resultsdir = resultsdir
        self._uploadurl = uploadurl

    def _create_powerlog_dict(self, raw_measurement):
        """Create powerlog dictionary from raw measurement data
        Data format in go/power-dashboard-data.

        Args:
            raw_measurement: dictionary contains raw measurement data

        Returns:
            A dictionary of powerlog
        """
        powerlog_dict = {
            'format_version': 4,
            'timestamp': time.time(),
            'test': self._testname,
            'dut': self._create_dut_info_dict(raw_measurement['data'].keys()),
            'power': raw_measurement,
        }
        return powerlog_dict

    def _create_dut_info_dict(self, power_rails):
        """Create a dictionary that contain information of the DUT.

        MUST be implemented in subclass.

        Args:
            power_rails: list of measured power rails

        Returns:
            DUT info dictionary
        """
        raise NotImplementedError

    def _save_json(self, powerlog_dict, resultsdir, filename='power_log.json'):
        """Convert powerlog dict to human readable formatted JSON and
        append to <resultsdir>/<filename>.

        Args:
            powerlog_dict: dictionary of power data
            resultsdir: directory to save formatted JSON object
            filename: filename to append to
        """
        if not os.path.exists(resultsdir):
            raise error.TestError('resultsdir %s does not exist.' % resultsdir)
        filename = os.path.join(resultsdir, filename)
        with file(filename, 'a') as f:
            json.dump(powerlog_dict, f, indent=4, separators=(',', ': '))

    def _save_html(self, powerlog_dict, resultsdir, filename='power_log.html'):
        """Convert powerlog dict to chart in HTML page and append to
        <resultsdir>/<filename>.

        Note that this results in multiple HTML objects in one file but Chrome
        can render all of it in one page.

        Args:
            powerlog_dict: dictionary of power data
            resultsdir: directory to save HTML page
            filename: filename to append to
        """
        # Create dict from type to sorted list of rail names.
        rail_type = collections.defaultdict(list)
        for r, t in powerlog_dict['power']['type'].iteritems():
            rail_type[t].append(r)
        for t in rail_type:
            rail_type[t] = sorted(rail_type[t])

        html_str = ''
        row_indent = ' ' * 12
        for t in rail_type:
            data_str_list = []

            # Generate rail name data string.
            header = ['time'] + rail_type[t]
            header_str = row_indent + "['" + "', '".join(header) + "']"
            data_str_list.append(header_str)

            # Generate measurements data string.
            for i in range(powerlog_dict['power']['sample_count']):
                row = [str(i * powerlog_dict['power']['sample_duration'])]
                for r in rail_type[t]:
                    row.append(str(powerlog_dict['power']['data'][r][i]))
                row_str = row_indent + '[' + ', '.join(row) + ']'
                data_str_list.append(row_str)

            data_str = ',\n'.join(data_str_list)
            unit = powerlog_dict['power']['unit'][rail_type[t][0]]
            html_str += _HTML_CHART_STR.format(data=data_str, unit=unit, type=t)

        if not os.path.exists(resultsdir):
            raise error.TestError('resultsdir %s does not exist.' % resultsdir)
        filename = os.path.join(resultsdir, filename)
        with file(filename, 'a') as f:
            f.write(html_str)

    def _upload(self, powerlog_dict, uploadurl):
        """Convert powerlog dict to minimal size JSON and upload to dashboard.

        Args:
            powerlog_dict: dictionary of power data
            uploadurl: url to upload the power data
        """
        data_obj = {'data': json.dumps(powerlog_dict)}
        encoded = urllib.urlencode(data_obj)
        req = urllib2.Request(uploadurl, encoded)

        @retry.retry(urllib2.URLError, blacklist=[urllib2.HTTPError])
        def _do_upload():
            urllib2.urlopen(req)

        _do_upload()

    def _convert(self):
        """Convert data from self._logger object to raw power measurement
        dictionary.

        MUST be implemented in subclass.

        Return:
            raw measurement dictionary
        """
        raise NotImplementedError

    def upload(self):
        """Upload powerlog to dashboard and save data to results directory.
        """
        raw_measurement = self._convert()
        powerlog_dict = self._create_powerlog_dict(raw_measurement)
        if self._resultsdir is not None:
            self._save_json(powerlog_dict, self._resultsdir)
            self._save_html(powerlog_dict, self._resultsdir)
        if self._uploadurl is not None:
            self._upload(powerlog_dict, self._uploadurl)


class ClientTestDashboard(BaseDashboard):
    """Dashboard class for autotests that run on client side.
    """

    def _create_dut_info_dict(self, power_rails):
        """Create a dictionary that contain information of the DUT.

        Args:
            power_rails: list of measured power rails

        Returns:
            DUT info dictionary
        """
        board = utils.get_board()
        platform = utils.get_platform()

        if not platform.startswith(board):
            board += '_' + platform

        dut_info_dict = {
            'board': board,
            'version': {
                'hw': utils.get_hardware_revision(),
                'milestone': lsbrelease_utils.get_chromeos_release_milestone(),
                'os': lsbrelease_utils.get_chromeos_release_version(),
                'channel': lsbrelease_utils.get_chromeos_channel(),
                'firmware': utils.get_firmware_version(),
                'ec': utils.get_ec_version(),
                'kernel': utils.get_kernel_version(),
            },
            'sku': {
                'cpu': utils.get_cpu_name(),
                'memory_size': utils.get_mem_total_gb(),
                'storage_size': utils.get_disk_size_gb(utils.get_root_device()),
                'display_resolution': utils.get_screen_resolution(),
            },
            'ina': {
                'version': 0,
                'ina': power_rails,
            },
            'note': '',
        }

        if power_utils.has_battery():
            # Round the battery size to nearest tenth because it is fluctuated
            # for platform without battery nominal voltage data.
            dut_info_dict['sku']['battery_size'] = round(
                    power_status.get_status().battery[0].energy_full_design, 1)
            dut_info_dict['sku']['battery_shutdown_percent'] = \
                    power_utils.get_low_battery_shutdown_percent()
        return dut_info_dict


class MeasurementLoggerDashboard(ClientTestDashboard):
    """Dashboard class for power_status.MeasurementLogger.
    """

    def __init__(self, logger, testname, resultsdir=None, uploadurl=None):
        super(MeasurementLoggerDashboard, self).__init__(logger, testname,
                                                         resultsdir, uploadurl)
        self._unit = None
        self._type = None
        self._padded_domains = None

    def _create_padded_domains(self):
        """Pad the domains name for dashboard to make the domain name better
        sorted in alphabetical order"""
        pass

    def _convert(self):
        """Convert data from power_status.MeasurementLogger object to raw
        power measurement dictionary.

        Return:
            raw measurement dictionary
        """
        power_dict = collections.defaultdict(dict, {
            'sample_count': len(self._logger.readings) - 1,
            'sample_duration': 0,
            'average': dict(),
            'data': dict(),
        })
        if power_dict['sample_count'] > 1:
            total_duration = self._logger.times[-1] - self._logger.times[0]
            power_dict['sample_duration'] = \
                    1.0 * total_duration / power_dict['sample_count']

        self._create_padded_domains()
        for i, domain_readings in enumerate(zip(*self._logger.readings)):
            if self._padded_domains:
                domain = self._padded_domains[i]
            else:
                domain = self._logger.domains[i]
            # Remove first item because that is the log before the test begin.
            power_dict['data'][domain] = domain_readings[1:]
            power_dict['average'][domain] = \
                    numpy.average(power_dict['data'][domain])
            if self._unit:
                power_dict['unit'][domain] = self._unit
            if self._type:
                power_dict['type'][domain] = self._type
        return power_dict


class PowerLoggerDashboard(MeasurementLoggerDashboard):
    """Dashboard class for power_status.PowerLogger.
    """

    def __init__(self, logger, testname, resultsdir=None, uploadurl=None):
        if uploadurl is None:
            uploadurl = 'http://chrome-power.appspot.com/rapl'
        super(PowerLoggerDashboard, self).__init__(logger, testname, resultsdir,
                                                   uploadurl)
        self._unit = 'watt'
        self._type = 'power'


class SimplePowerLoggerDashboard(ClientTestDashboard):
    """Dashboard class for simple system power measurement taken and publishing
    it to the dashboard.
    """
    def __init__(self, duration_secs, power_watts, testname, resultsdir=None,
                 uploadurl=None):

        if uploadurl is None:
            uploadurl = 'http://chrome-power.appspot.com/rapl'
        super(SimplePowerLoggerDashboard, self).__init__(
            None, testname, resultsdir, uploadurl)

        self._unit = 'watt'
        self._type = 'power'
        self._duration_secs = duration_secs
        self._power_watts = power_watts

    def _convert(self):
        """Convert vbat to raw power measurement dictionary.

        Return:
            raw measurement dictionary
        """
        power_dict = {
            'sample_count': 1,
            'sample_duration': self._duration_secs,
            'average': {'vbat': self._power_watts},
            'data': {'vbat': [self._power_watts]},
            'unit': {'vbat': self._unit},
            'type': {'vbat': self._type},
        }
        return power_dict


class CPUStatsLoggerDashboard(MeasurementLoggerDashboard):
    """Dashboard class for power_status.CPUStatsLogger.
    """

    def __init__(self, logger, testname, resultsdir=None, uploadurl=None):
        if uploadurl is None:
            uploadurl = 'http://chrome-power.appspot.com/rapl'
        super(CPUStatsLoggerDashboard, self).__init__(logger, testname,
                                                      resultsdir, uploadurl)

    @staticmethod
    def _split_domain(domain):
        """Return domain_type and domain_name for given domain.

        Example: Split ................... to ........... and .......
                       cpuidle_C1E-SKL        cpuidle         C1E-SKL
                       cpuidle_0_3_C0         cpuidle_0_3     C0
                       cpupkg_C0_C1           cpupkg          C0_C1
                       cpufreq_0_3_1512000    cpufreq_0_3     1512000

        Args:
            domain: cpu stat domain name to split

        Return:
            tuple of domain_type and domain_name
        """
        # Regex explanation
        # .*?           matches type non-greedily                 (cpuidle)
        # (?:_\d+_\d+)? matches cpu part, ?: makes it not a group (_0_3)
        # .*            matches name greedily                     (C0_C1)
        return re.match(r'(.*?(?:_\d+_\d+)?)_(.*)', domain).groups()

    def _convert(self):
        power_dict = super(CPUStatsLoggerDashboard, self)._convert()
        for rail in power_dict['data']:
            if rail.startswith('wavg_cpu'):
                power_dict['type'][rail] = 'cpufreq_wavg'
                power_dict['unit'][rail] = 'kilohertz'
            elif rail.startswith('wavg_gpu'):
                power_dict['type'][rail] = 'gpufreq_wavg'
                power_dict['unit'][rail] = 'megahertz'
            else:
                power_dict['type'][rail] = self._split_domain(rail)[0]
                power_dict['unit'][rail] = 'percent'
        return power_dict

    def _create_padded_domains(self):
        """Padded number in the domain name with dot to make it sorted
        alphabetically.

        Example:
        cpuidle_C1-SKL, cpuidle_C1E-SKL, cpuidle_C2-SKL, cpuidle_C10-SKL
        will be changed to
        cpuidle_C.1-SKL, cpuidle_C.1E-SKL, cpuidle_C.2-SKL, cpuidle_C10-SKL
        which make it in alphabetically order.
        """
        longest = collections.defaultdict(int)
        searcher = re.compile(r'\d+')
        number_strs = []
        splitted_domains = \
                [self._split_domain(domain) for domain in self._logger.domains]
        for domain_type, domain_name in splitted_domains:
            result = searcher.search(domain_name)
            if not result:
                number_strs.append('')
                continue
            number_str = result.group(0)
            number_strs.append(number_str)
            longest[domain_type] = max(longest[domain_type], len(number_str))

        self._padded_domains = []
        for i in range(len(self._logger.domains)):
            if not number_strs[i]:
                self._padded_domains.append(self._logger.domains[i])
                continue

            domain_type, domain_name = splitted_domains[i]
            formatter_component = '{:.>%ds}' % longest[domain_type]

            # Change "cpuidle_C1E-SKL" to "cpuidle_C{:.>2s}E-SKL"
            formatter_str = domain_type + '_' + \
                    searcher.sub(formatter_component, domain_name, count=1)

            # Run "cpuidle_C{:_>2s}E-SKL".format("1") to get "cpuidle_C.1E-SKL"
            self._padded_domains.append(formatter_str.format(number_strs[i]))
