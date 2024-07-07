# Lint as: python2, python3
# Copyright 2017 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
"""
Convenience functions for use by tests or whomever.
"""

# pylint: disable=missing-docstring

from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

import base64
import chardet
import collections
import errno
import glob
import logging
import math
import multiprocessing
import os
import platform
import re
import shutil
import signal
import string
import subprocess
import sys
import tempfile
import time
import uuid
import json

from autotest_lib.client.common_lib import error
from autotest_lib.client.common_lib import magic
from autotest_lib.client.common_lib import utils
from autotest_lib.client.common_lib.cros import cros_config

from autotest_lib.client.common_lib.utils import *
import six
from six.moves import map
from six.moves import range
from six.moves import zip


def grep(pattern, file):
    """
    This is mainly to fix the return code inversion from grep
    Also handles compressed files.

    returns 1 if the pattern is present in the file, 0 if not.
    """
    command = 'grep "%s" > /dev/null' % pattern
    ret = cat_file_to_cmd(file, command, ignore_status=True)
    return not ret


def cat_file_to_cmd(file, command, ignore_status=0, return_output=False):
    """
    equivalent to 'cat file | command' but knows to use
    zcat or bzcat if appropriate
    """
    if not os.path.isfile(file):
        raise NameError('invalid file %s to cat to command %s' %
                        (file, command))

    if return_output:
        run_cmd = utils.system_output
    else:
        run_cmd = utils.system

    if magic.guess_type(file) == 'application/x-bzip2':
        cat = 'bzcat'
    elif magic.guess_type(file) == 'application/x-gzip':
        cat = 'zcat'
    else:
        cat = 'cat'
    return run_cmd('%s %s | %s' % (cat, file, command),
                   ignore_status=ignore_status)


def extract_tarball_to_dir(tarball, dir):
    """
    Extract a tarball to a specified directory name instead of whatever
    the top level of a tarball is - useful for versioned directory names, etc
    """
    if os.path.exists(dir):
        if os.path.isdir(dir):
            shutil.rmtree(dir)
        else:
            os.remove(dir)
    pwd = os.getcwd()
    os.chdir(os.path.dirname(os.path.abspath(dir)))
    newdir = extract_tarball(tarball)
    os.rename(newdir, dir)
    os.chdir(pwd)


def extract_tarball(tarball):
    """Returns the directory extracted by the tarball."""
    extracted = cat_file_to_cmd(tarball,
                                'tar xvf - 2>/dev/null',
                                return_output=True).splitlines()

    dir = None

    for line in extracted:
        if line.startswith('./'):
            line = line[2:]
        if not line or line == '.':
            continue
        topdir = line.split('/')[0]
        if os.path.isdir(topdir):
            if dir:
                assert (dir == topdir), 'tarball must be a a single directory'
            else:
                dir = topdir
    if dir:
        return dir
    else:
        raise NameError('extracting tarball produced no dir')


def force_copy(src, dest):
    """Replace dest with a new copy of src, even if it exists"""
    if os.path.isfile(dest):
        os.remove(dest)
    if os.path.isdir(dest):
        dest = os.path.join(dest, os.path.basename(src))
    shutil.copyfile(src, dest)
    return dest


def file_contains_pattern(file, pattern):
    """Return true if file contains the specified egrep pattern"""
    if not os.path.isfile(file):
        raise NameError('file %s does not exist' % file)
    return not utils.system('egrep -q "' + pattern + '" ' + file,
                            ignore_status=True)


def list_grep(list, pattern):
    """True if any item in list matches the specified pattern."""
    compiled = re.compile(pattern)
    for line in list:
        match = compiled.search(line)
        if (match):
            return 1
    return 0


def get_os_vendor():
    """Try to guess what's the os vendor
    """
    if os.path.isfile('/etc/SuSE-release'):
        return 'SUSE'

    issue = '/etc/issue'

    if not os.path.isfile(issue):
        return 'Unknown'

    if file_contains_pattern(issue, 'Red Hat'):
        return 'Red Hat'
    elif file_contains_pattern(issue, 'Fedora'):
        return 'Fedora Core'
    elif file_contains_pattern(issue, 'SUSE'):
        return 'SUSE'
    elif file_contains_pattern(issue, 'Ubuntu'):
        return 'Ubuntu'
    elif file_contains_pattern(issue, 'Debian'):
        return 'Debian'
    else:
        return 'Unknown'


def get_cc():
    try:
        return os.environ['CC']
    except KeyError:
        return 'gcc'


def get_vmlinux():
    """Return the full path to vmlinux

    Ahem. This is crap. Pray harder. Bad Martin.
    """
    vmlinux = '/boot/vmlinux-%s' % utils.system_output('uname -r')
    if os.path.isfile(vmlinux):
        return vmlinux
    vmlinux = '/lib/modules/%s/build/vmlinux' % utils.system_output('uname -r')
    if os.path.isfile(vmlinux):
        return vmlinux
    return None


def get_systemmap():
    """Return the full path to System.map

    Ahem. This is crap. Pray harder. Bad Martin.
    """
    map = '/boot/System.map-%s' % utils.system_output('uname -r')
    if os.path.isfile(map):
        return map
    map = '/lib/modules/%s/build/System.map' % utils.system_output('uname -r')
    if os.path.isfile(map):
        return map
    return None


def get_modules_dir():
    """Return the modules dir for the running kernel version"""
    kernel_version = utils.system_output('uname -r')
    return '/lib/modules/%s/kernel' % kernel_version


_CPUINFO_RE = re.compile(r'^(?P<key>[^\t]*)\t*: ?(?P<value>.*)$')


def get_cpuinfo():
    """Read /proc/cpuinfo and convert to a list of dicts."""
    cpuinfo = []
    with open('/proc/cpuinfo', 'r') as f:
        cpu = {}
        for line in f:
            line = line.strip()
            if not line:
                cpuinfo.append(cpu)
                cpu = {}
                continue
            match = _CPUINFO_RE.match(line)
            cpu[match.group('key')] = match.group('value')
        if cpu:
            # cpuinfo usually ends in a blank line, so this shouldn't happen.
            cpuinfo.append(cpu)
    return cpuinfo


def get_cpu_arch():
    """Work out which CPU architecture we're running on"""

    # Using 'uname -m' should be a very portable way to do this since the
    # format is pretty standard.
    machine_name = utils.system_output('uname -m').strip()

    # Apparently ARM64 and ARM have both historically returned the string 'arm'
    # here so continue the tradition.  Use startswith() because:
    # - On most of our arm devices we'll actually see the string armv7l.
    # - In theory the machine name could include a suffix for endianness.
    if machine_name.startswith('aarch64') or machine_name.startswith('arm'):
        return 'arm'

    # Historically we _have_ treated x86_64 and i386 separately.
    if machine_name in ('x86_64', 'i386'):
        return machine_name

    raise error.TestError('unsupported machine type %s' % machine_name)


def get_cpu_soc_family():
    try:
        cmd = '/usr/local/graphics/hardware_probe'
        output = utils.run(cmd, ignore_status=True).stdout
        return json.loads(output)['CPU_SOC_Family']
    except json.decoder.JSONDecodeError:
        """Like get_cpu_arch, but for ARM, returns the SoC family name"""
        cmd = '/usr/local/graphics/hardware_probe --cpu-soc-family'
        output = utils.run(cmd, ignore_status=True).stdout
        return output.split(":")[1].strip()


# When adding entries here, also add them at the right spot in the
# INTEL_*_ORDER lists below.
INTEL_UARCH_TABLE = {
        '06_9A': 'Alder Lake',
        '06_BE': 'Alder Lake',
        '06_4C': 'Airmont',
        '06_1C': 'Atom',
        '06_26': 'Atom',
        '06_27': 'Atom',
        '06_35': 'Atom',
        '06_36': 'Atom',
        '06_3D': 'Broadwell',
        '06_47': 'Broadwell',
        '06_4F': 'Broadwell',
        '06_56': 'Broadwell',
        '06_A5': 'Comet Lake',
        '06_A6': 'Comet Lake',
        '06_0D': 'Dothan',
        '06_5C': 'Goldmont',
        '06_7A': 'Goldmont',
        '06_3C': 'Haswell',
        '06_45': 'Haswell',
        '06_46': 'Haswell',
        '06_3F': 'Haswell-E',
        '06_7D': 'Ice Lake',
        '06_7E': 'Ice Lake',
        '06_3A': 'Ivy Bridge',
        '06_3E': 'Ivy Bridge-E',
        '06_8E': 'Kaby Lake',
        '06_9E': 'Kaby Lake',
        '06_0F': 'Merom',
        '06_16': 'Merom',
        '06_AA': 'Meteor Lake',
        '06_17': 'Nehalem',
        '06_1A': 'Nehalem',
        '06_1D': 'Nehalem',
        '06_1E': 'Nehalem',
        '06_1F': 'Nehalem',
        '06_2E': 'Nehalem',
        '0F_03': 'Prescott',
        '0F_04': 'Prescott',
        '0F_06': 'Presler',
        '06_BA': 'Raptor Lake',
        '06_2A': 'Sandy Bridge',
        '06_2D': 'Sandy Bridge',
        '06_37': 'Silvermont',
        '06_4A': 'Silvermont',
        '06_4D': 'Silvermont',
        '06_5A': 'Silvermont',
        '06_5D': 'Silvermont',
        '06_4E': 'Skylake',
        '06_5E': 'Skylake',
        '06_55': 'Skylake',
        '06_8C': 'Tiger Lake',
        '06_8D': 'Tiger Lake',
        '06_86': 'Tremont',
        '06_96': 'Tremont',
        '06_9C': 'Tremont',
        '06_25': 'Westmere',
        '06_2C': 'Westmere',
        '06_2F': 'Westmere',
}

INTEL_ATOM_ORDER = [
        'Silvermont', 'Airmont', 'Goldmont', 'Tremont', 'Gracemont'
]

INTEL_BIGCORE_ORDER = [
        'Prescott', 'Presler', 'Dothan', 'Merom', 'Nehalem', 'Westmere',
        'Sandy Bridge', 'Ivy Bridge', 'Ivy Bridge-E', 'Haswell', 'Haswell-E',
        'Broadwell', 'Skylake', 'Kaby Lake', 'Coffee Lake', 'Whiskey Lake',
        'Cannon Lake', 'Comet Lake', 'Ice Lake', 'Tiger Lake', 'Alder Lake',
        'Raptor Lake', 'Meteor Lake'
]


def get_intel_cpu_uarch(numeric=False):
    """Return the Intel microarchitecture we're running on, or None.

    Returns None if this is not an Intel CPU. Returns the family and model as
    underscore-separated hex (per Intel manual convention) if the uarch is not
    known, or if numeric is True.
    """
    if not get_current_kernel_arch().startswith('x86'):
        return None
    cpuinfo = get_cpuinfo()[0]
    if cpuinfo['vendor_id'] != 'GenuineIntel':
        return None
    family_model = '%02X_%02X' % (int(
            cpuinfo['cpu family']), int(cpuinfo['model']))
    if numeric:
        return family_model
    return INTEL_UARCH_TABLE.get(family_model, family_model)


def is_intel_uarch_older_than(reference):
    """Returns True if the DUT's is older than reference, False otherwise.

    Raises a test error exception if the uarch is unknown to make developers
    add entries to the tables above.
    """

    uarch = get_intel_cpu_uarch()
    if uarch is None:
        raise error.TestError("Doing Intel test for non-Intel hardware.")

    if "_" in uarch:
        raise error.TestError("Intel uarch unknown. Add to tables.")

    if reference not in INTEL_BIGCORE_ORDER and reference not in INTEL_ATOM_ORDER:
        raise error.TestError("Testing for unknown reference Intel uarch.")

    result = False

    if reference in INTEL_BIGCORE_ORDER:
        for v in INTEL_BIGCORE_ORDER:
            if v == reference:
                break
            if v == uarch:
                result = True

    elif reference in INTEL_ATOM_ORDER:
        for v in INTEL_ATOM_ORDER:
            if v == reference:
                break
            if v == uarch:
                result = True

    return result


INTEL_SILVERMONT_BCLK_TABLE = [83333, 100000, 133333, 116667, 80000]


def get_intel_bclk_khz():
    """Return Intel CPU base clock.

    This only worked with SandyBridge (released in 2011) or newer. Older CPU has
    133 MHz bclk. See turbostat code for implementation that also works with
    older CPU. https://git.io/vpyKT
    """
    if get_intel_cpu_uarch() == 'Silvermont':
        MSR_FSB_FREQ = 0xcd
        return INTEL_SILVERMONT_BCLK_TABLE[utils.rdmsr(MSR_FSB_FREQ) & 0xf]
    return 100000


def get_energy_usage():
    """On Intel chips that support it, return the energy usage."""
    if get_intel_cpu_uarch() == None:
        return 0

    with open('/sys/class/powercap/intel-rapl/intel-rapl:0/energy_uj') as fd:
        return fd.readline()


def get_current_kernel_arch():
    """Get the machine architecture, now just a wrap of 'uname -m'."""
    return os.popen('uname -m').read().rstrip()


def count_cpus():
    """number of CPUs in the local machine according to /proc/cpuinfo"""
    try:
        return multiprocessing.cpu_count()
    except Exception:
        logging.exception('can not get cpu count from'
                          ' multiprocessing.cpu_count()')
    cpuinfo = get_cpuinfo()
    # Returns at least one cpu. Check comment #1 in crosbug.com/p/9582.
    return len(cpuinfo) or 1


def count_cpu_cores():
    """Number of cores per CPU according to lscpu.

    Note that there could be more than one type of CPU model on the
    heterogeneous systems, so we should take that into account when parsing
    the lscpu output.
    """
    cmds = ["lscpu", "grep 'Core(s)'", "cut -d ':' -f 2"]
    cmd = " | ".join(cmds)
    cores_per_socket = [int(l) for l in utils.system_output(cmd).splitlines()]
    cmds = ["lscpu", "grep 'Socket(s)'", "cut -d ':' -f 2"]
    cmd = " | ".join(cmds)
    sockets = [int(l) for l in utils.system_output(cmd).splitlines()]
    return sum(c * s for (c, s) in zip(cores_per_socket, sockets))


def count_cpu_threads():
    """number of threads per cpu"""
    cmd = "cat /sys/devices/system/cpu/present"
    ret = utils.run(cmd, ignore_status=True)
    if ret.exit_status != 0:
        return 0
    return int(ret.stdout.split('-')[1]) + 1


def get_cpu_vendor():
    """cpu vendor according to lscpu"""
    cmds = ["lscpu", "grep 'Vendor'", "cut -d ':' -f 2"]
    cmd = " | ".join(cmds)
    return utils.system_output(cmd).strip()


def get_cpu_cache_size():
    """cpu L3 cache size according to
    /sys/devices/system/cpu/cpu0/cache/index3/size"""
    cmd = "cat /sys/devices/system/cpu/cpu0/cache/index3/size"
    ret = utils.run(cmd, ignore_status=True)
    if ret.exit_status != 0:
        return 0
    res = ret.stdout.strip()
    if 'K' in res:
        return int(res.split('K')[0])
    elif 'M' in res:
        return int(res.split('M')[0]) * 1000
    else:
        return 0


def cpu_online_map():
    """
    Check out the available cpu online map
    """
    cpuinfo = get_cpuinfo()
    cpus = []
    for cpu in cpuinfo:
        cpus.append(cpu['processor'])  # grab cpu number
    return cpus


def get_gpu_model():
    """get gpu model from lshw"""
    cmds = ["lshw -businfo", "grep -i display"]
    cmd = " | ".join(cmds)
    ret = utils.run(cmd, ignore_status=True)
    if ret.exit_status != 0:
        return ''
    return ret.stdout.split('display')[1].strip()


def get_memory_type():
    """get memory type e.g. LPDDR3"""
    cmds = ["mosys -s dram memory spd print type", "uniq"]
    cmd = " | ".join(cmds)
    return utils.system_output(cmd).strip()


def get_memory_frequency():
    """get memory type e.g. LPDDR3"""
    cmds = [
            "dmidecode --type memory", "grep $'\tSpeed:'", "uniq",
            "cut -d ':' -f 2"
    ]
    cmd = " | ".join(cmds)
    ret = utils.run(cmd, ignore_status=True)
    if ret.exit_status != 0:
        return 0
    res = ret.stdout.strip().split('MT')[0]
    if res and res.isdigit():
        return int(res)
    return 0


# Returns total memory in kb
def read_from_meminfo(key):
    meminfo = utils.system_output('grep %s /proc/meminfo' % key)
    return int(re.search(r'\d+', meminfo).group(0))


def memtotal():
    return read_from_meminfo('MemTotal')


def freememtotal():
    return read_from_meminfo('MemFree')


def usable_memtotal():
    # Reserved 5% for OS use
    return int(read_from_meminfo('MemFree') * 0.95)


def swaptotal():
    return read_from_meminfo('SwapTotal')


def rounded_memtotal():
    # Get total of all physical mem, in kbytes
    usable_kbytes = memtotal()
    # usable_kbytes is system's usable DRAM in kbytes,
    #   as reported by memtotal() from device /proc/meminfo memtotal
    #   after Linux deducts 1.5% to 5.1% for system table overhead
    # Undo the unknown actual deduction by rounding up
    #   to next small multiple of a big power-of-two
    #   eg  12GB - 5.1% gets rounded back up to 12GB
    mindeduct = 0.015  # 1.5 percent
    maxdeduct = 0.055  # 5.5 percent
    # deduction range 1.5% .. 5.5% supports physical mem sizes
    #    6GB .. 12GB in steps of .5GB
    #   12GB .. 24GB in steps of 1 GB
    #   24GB .. 48GB in steps of 2 GB ...
    # Finer granularity in physical mem sizes would require
    #   tighter spread between min and max possible deductions

    # increase mem size by at least min deduction, without rounding
    min_kbytes = int(usable_kbytes / (1.0 - mindeduct))
    # increase mem size further by 2**n rounding, by 0..roundKb or more
    round_kbytes = int(usable_kbytes / (1.0 - maxdeduct)) - min_kbytes
    # find least binary roundup 2**n that covers worst-cast roundKb
    mod2n = 1 << int(math.ceil(math.log(round_kbytes, 2)))
    # have round_kbytes <= mod2n < round_kbytes*2
    # round min_kbytes up to next multiple of mod2n
    phys_kbytes = min_kbytes + mod2n - 1
    phys_kbytes = phys_kbytes - (phys_kbytes % mod2n)  # clear low bits
    return phys_kbytes


_MEMINFO_RE = re.compile('^(\w+)(\(\w+\))?:\s+(\d+)')


def get_meminfo():
    """Returns a namedtuple of pairs from /proc/meminfo.

    Example /proc/meminfo snippets:
        MemTotal:        2048000 kB
        Active(anon):     409600 kB
    Example usage:
        meminfo = utils.get_meminfo()
        print meminfo.Active_anon
    """
    info = {}
    with _open_file('/proc/meminfo') as f:
        for line in f:
            m = _MEMINFO_RE.match(line)
            if m:
                if m.group(2):
                    name = m.group(1) + '_' + m.group(2)[1:-1]
                else:
                    name = m.group(1)
                info[name] = int(m.group(3))
    return collections.namedtuple('MemInfo', list(info.keys()))(**info)


def sysctl(key, value=None):
    """Generic implementation of sysctl, to read and write.

    @param key: A location under /proc/sys
    @param value: If not None, a value to write into the sysctl.

    @return The single-line sysctl value as a string.
    """
    path = '/proc/sys/%s' % key
    if value is not None:
        utils.write_one_line(path, str(value))
    return utils.read_one_line(path)


def sysctl_kernel(key, value=None):
    """(Very) partial implementation of sysctl, for kernel params"""
    if value is not None:
        # write
        utils.write_one_line('/proc/sys/kernel/%s' % key, str(value))
    else:
        # read
        out = utils.read_one_line('/proc/sys/kernel/%s' % key)
        return int(re.search(r'\d+', out).group(0))


def get_num_allocated_file_handles():
    """
    Returns the number of currently allocated file handles.

    Gets this information by parsing /proc/sys/fs/file-nr.
    See https://www.kernel.org/doc/Documentation/sysctl/fs.txt
    for details on this file.
    """
    with _open_file('/proc/sys/fs/file-nr') as f:
        line = f.readline()
    allocated_handles = int(line.split()[0])
    return allocated_handles


def dump_object(object):
    """Dump an object's attributes and methods

    kind of like dir()
    """
    for item in six.iteritems(object.__dict__):
        print(item)
        try:
            (key, value) = item
            dump_object(value)
        except:
            continue


def environ(env_key):
    """return the requested environment variable, or '' if unset"""
    if (env_key in os.environ):
        return os.environ[env_key]
    else:
        return ''


def prepend_path(newpath, oldpath):
    """prepend newpath to oldpath"""
    if (oldpath):
        return newpath + ':' + oldpath
    else:
        return newpath


def append_path(oldpath, newpath):
    """append newpath to oldpath"""
    if (oldpath):
        return oldpath + ':' + newpath
    else:
        return newpath


_TIME_OUTPUT_RE = re.compile(r'([\d\.]*)user ([\d\.]*)system '
                             r'(\d*):([\d\.]*)elapsed (\d*)%CPU')


def to_seconds(time_string):
    """Converts a string in M+:SS.SS format to S+.SS"""
    elts = time_string.split(':')
    if len(elts) == 1:
        return time_string
    return str(int(elts[0]) * 60 + float(elts[1]))


_TIME_OUTPUT_RE_2 = re.compile(r'(.*?)user (.*?)system (.*?)elapsed')


def running_config():
    """
    Return path of config file of the currently running kernel
    """
    version = utils.system_output('uname -r')
    for config in ('/proc/config.gz', \
                   '/boot/config-%s' % version,
                   '/lib/modules/%s/build/.config' % version):
        if os.path.isfile(config):
            return config
    return None


def check_for_kernel_feature(feature):
    config = running_config()

    if not config:
        raise TypeError("Can't find kernel config file")

    if magic.guess_type(config) == 'application/x-gzip':
        grep = 'zgrep'
    else:
        grep = 'grep'
    grep += ' ^CONFIG_%s= %s' % (feature, config)

    if not utils.system_output(grep, ignore_status=True):
        raise ValueError("Kernel doesn't have a %s feature" % (feature))


def check_glibc_ver(ver):
    try:
        glibc_ver = subprocess.check_output("ldd --version", shell=True)
    except subprocess.CalledProcessError:
        # To mimic previous behavior, if the command errors set the result to
        # an empty str
        glibc_ver = ''
    glibc_ver = glibc_ver.splitlines()[0].decode()
    glibc_ver = re.search(r'(\d+\.\d+(\.\d+)?)', glibc_ver).group()
    if utils.compare_versions(glibc_ver, ver) == -1:
        raise error.TestError("Glibc too old (%s). Glibc >= %s is needed." %
                              (glibc_ver, ver))


def check_kernel_ver(ver):
    kernel_ver = utils.system_output('uname -r')
    kv_tmp = re.split(r'[-]', kernel_ver)[0:3]
    # In compare_versions, if v1 < v2, return value == -1
    if utils.compare_versions(kv_tmp[0], ver) == -1:
        raise error.TestError("Kernel too old (%s). Kernel > %s is needed." %
                              (kernel_ver, ver))


def numa_nodes():
    node_paths = glob.glob('/sys/devices/system/node/node*')
    nodes = [int(re.sub(r'.*node(\d+)', r'\1', x)) for x in node_paths]
    return (sorted(nodes))


# Return the kernel version and build timestamp.
def running_os_release():
    return os.uname()[2:4]


def running_os_ident():
    (version, timestamp) = running_os_release()
    return version + '::' + timestamp


def get_storage_type():
    """Get storage type according to rootdev"""
    cmd = "rootdev -s"
    res = utils.system_output(cmd)
    return res.split('/')[2].strip()


def freespace(path):
    """Return the disk free space, in bytes"""
    s = os.statvfs(path)
    return s.f_bavail * s.f_bsize


_DISK_PARTITION_3_RE = re.compile(r'^(/dev/hd[a-z]+)3', re.M)


def get_disk_size(disk_name):
    """
    Return size of disk in byte. Return 0 in Error Case

    @param disk_name: disk name to find size
    """
    device = os.path.basename(disk_name)
    with open('/proc/partitions') as f:
        lines = f.readlines()
    for line in lines:
        try:
            _, _, blocks, name = re.split(r' +', line.strip())
        except ValueError:
            continue
        if name == device:
            return 1024 * int(blocks)
    return 0


def get_disk_size_gb(disk_name):
    """
    Return size of disk in GB (10^9). Return 0 in Error Case

    @param disk_name: disk name to find size
    """
    return int(get_disk_size(disk_name) / (10.0**9) + 0.5)


def get_disk_model(disk_name):
    """
    Return model name for internal storage device

    @param disk_name: disk name to find model
    """
    cmd1 = 'udevadm info --query=property --name=%s' % disk_name
    cmd2 = 'grep -E "ID_(NAME|MODEL)="'
    cmd3 = 'cut -f 2 -d"="'
    cmd = ' | '.join([cmd1, cmd2, cmd3])
    return utils.system_output(cmd)


_DISK_DEV_RE = re.compile(r'/dev/sd[a-z]|'
                          r'/dev/mmcblk[0-9]+|'
                          r'/dev/nvme[0-9]+n[0-9]+')


def get_disk_from_filename(filename):
    """
    Return the disk device the filename is on.
    If the file is on tmpfs or other special file systems,
    return None.

    @param filename: name of file, full path.
    """

    if not os.path.exists(filename):
        raise error.TestError('file %s missing' % filename)

    if filename[0] != '/':
        raise error.TestError('This code works only with full path')

    m = _DISK_DEV_RE.match(filename)
    while not m:
        if filename[0] != '/':
            return None
        if filename == '/dev/root':
            cmd = 'rootdev -d -s'
        elif filename.startswith('/dev/mapper'):
            cmd = 'dmsetup table "%s"' % os.path.basename(filename)
            dmsetup_output = utils.system_output(cmd).split(' ')
            if dmsetup_output[2] == 'verity':
                maj_min = dmsetup_output[4]
            elif dmsetup_output[2] == 'crypt':
                maj_min = dmsetup_output[6]
            elif dmsetup_output[2] in ['thin', 'thin-pool', 'linear']:
                maj_min = dmsetup_output[3]
            cmd = 'realpath "/dev/block/%s"' % maj_min
        elif filename.startswith('/dev/loop'):
            cmd = 'losetup -O BACK-FILE "%s" | tail -1' % filename
        else:
            cmd = 'rootdev -s -d "%s"' % filename
        filename = utils.system_output(cmd, ignore_status=True)
        if not filename:
            return None
        m = _DISK_DEV_RE.match(filename)
    return m.group(0)


def get_disk_firmware_version(disk_name):
    """
    Return firmware version for internal storage device. (empty string for eMMC)

    @param disk_name: disk name to find model
    """
    cmd1 = 'udevadm info --query=property --name=%s' % disk_name
    cmd2 = 'grep -E "ID_REVISION="'
    cmd3 = 'cut -f 2 -d"="'
    cmd = ' | '.join([cmd1, cmd2, cmd3])
    return utils.system_output(cmd)


def is_disk_nvme(disk_name):
    """
    Return true if disk is a nvme device, return false otherwise

    @param disk_name: disk name to check
    """
    return re.match('/dev/nvme[0-9]+n[0-9]+', disk_name)


def is_disk_scsi(disk_name):
    """
    Return true if disk is a scsi device, return false otherwise

    @param disk_name: disk name check
    """
    return re.match('/dev/sd[a-z]+', disk_name)


def is_disk_harddisk(disk_name):
    """
    Return true if disk is a harddisk, return false otherwise

    @param disk_name: disk name check
    """
    cmd1 = 'udevadm info --query=property --name=%s' % disk_name
    cmd2 = 'grep -E "ID_ATA_ROTATION_RATE_RPM="'
    cmd3 = 'cut -f 2 -d"="'
    cmd = ' | '.join([cmd1, cmd2, cmd3])

    rtt = utils.system_output(cmd)

    # eMMC will not have this field; rtt == ''
    # SSD will have zero rotation rate; rtt == '0'
    # For harddisk rtt > 0
    return rtt and int(rtt) > 0


def concat_partition(disk_name, partition_number):
    """
    Return the name of a partition:
    sda, 3 --> sda3
    mmcblk0, 3 --> mmcblk0p3

    @param disk_name: diskname string
    @param partition_number: integer
    """
    if disk_name.endswith(tuple(str(i) for i in range(0, 10))):
        sep = 'p'
    else:
        sep = ''
    return disk_name + sep + str(partition_number)


def verify_hdparm_feature(disk_name, feature):
    """
    Check for feature support for SCSI disk using hdparm

    @param disk_name: target disk
    @param feature: hdparm output string of the feature
    """
    cmd = 'hdparm -I %s | grep -q "%s"' % (disk_name, feature)
    ret = utils.system(cmd, ignore_status=True)
    if ret == 0:
        return True
    elif ret == 1:
        return False
    else:
        raise error.TestFail('Error running command %s' % cmd)


def get_nvme_id_ns_feature(disk_name, feature):
    """
    Return feature value for NVMe disk using nvme id-ns

    @param disk_name: target disk
    @param feature: output string of the feature
    """
    cmd = "nvme id-ns -n 1 %s | grep %s" % (disk_name, feature)
    feat = utils.system_output(cmd, ignore_status=True)
    if not feat:
        return 'None'
    start = feat.find(':')
    value = feat[start + 2:]
    return value


def get_storage_error_msg(disk_name, reason):
    """
    Get Error message for storage test which include disk model.
    and also include the firmware version for the SCSI disk

    @param disk_name: target disk
    @param reason: Reason of the error.
    """

    msg = reason

    model = get_disk_model(disk_name)
    msg += ' Disk model: %s' % model

    if is_disk_scsi(disk_name):
        fw = get_disk_firmware_version(disk_name)
        msg += ' firmware: %s' % fw

    return msg


_IOSTAT_FIELDS = ('transfers_per_s', 'read_kb_per_s', 'written_kb_per_s',
                  'read_kb', 'written_kb')
_IOSTAT_RE = re.compile('ALL' + len(_IOSTAT_FIELDS) * r'\s+([\d\.]+)')


def get_storage_statistics(device=None):
    """
    Fetches statistics for a storage device.

    Using iostat(1) it retrieves statistics for a device since last boot.  See
    the man page for iostat(1) for details on the different fields.

    @param device: Path to a block device. Defaults to the device where root
            is mounted.

    @returns a dict mapping each field to its statistic.

    @raises ValueError: If the output from iostat(1) can not be parsed.
    """
    if device is None:
        device = get_root_device()
    cmd = 'iostat -d -k -g ALL -H %s' % device
    output = utils.system_output(cmd, ignore_status=True)
    match = _IOSTAT_RE.search(output)
    if not match:
        raise ValueError('Unable to get iostat for %s' % device)
    return dict(list(zip(_IOSTAT_FIELDS, list(map(float, match.groups())))))


def load_module(module_name, params=None):
    # Checks if a module has already been loaded
    if module_is_loaded(module_name):
        return False

    cmd = '/usr/bin/modprobe ' + module_name
    if params:
        cmd += ' ' + params
    utils.system(cmd)
    return True


def unload_module(module_name):
    """
    Removes a module. Handles dependencies. If even then it's not possible
    to remove one of the modules, it will trhow an error.CmdError exception.

    @param module_name: Name of the module we want to remove.
    """
    module_name = module_name.replace('-', '_')
    l_raw = utils.system_output("/usr/bin/lsmod").splitlines()
    lsmod = [x for x in l_raw if x.split()[0] == module_name]
    if len(lsmod) > 0:
        line_parts = lsmod[0].split()
        if len(line_parts) == 4:
            submodules = line_parts[3].split(",")
            for submodule in submodules:
                unload_module(submodule)
        utils.system("/usr/bin/modprobe -r %s" % module_name)
        logging.info("Module %s unloaded", module_name)
    else:
        logging.info("Module %s is already unloaded", module_name)


def module_is_loaded(module_name):
    module_name = module_name.replace('-', '_')
    modules = utils.system_output('/usr/bin/lsmod').splitlines()
    for module in modules:
        if module.startswith(module_name) and module[len(module_name)] == ' ':
            return True
    return False


def ping_default_gateway():
    """Ping the default gateway."""

    network = open('/etc/sysconfig/network')
    m = re.search('GATEWAY=(\S+)', network.read())

    if m:
        gw = m.group(1)
        cmd = 'ping %s -c 5 > /dev/null' % gw
        return utils.system(cmd, ignore_status=True)

    raise error.TestError('Unable to find default gateway')


def drop_caches():
    """Writes back all dirty pages to disk and clears all the caches."""
    utils.system("sync")
    # We ignore failures here as this will fail on 2.6.11 kernels.
    utils.system("echo 3 > /proc/sys/vm/drop_caches", ignore_status=True)


def set_hwclock(time='system',
                utc=True,
                rtc=None,
                noadjfile=False,
                ignore_status=False):
    """Uses the hwclock command to set time of an RTC.

    @param time: Either 'system', meaning use the system time, or a string
                 to be passed to the --date argument of hwclock.
    @param utc: Boolean of whether to use UTC or localtime.
    @param rtc: String to be passed to the --rtc arg of hwclock.
    @param noadjfile: Boolean of whether to use --noadjfile flag with hwclock.
    @param ignore_status: Boolean of whether to ignore exit code of hwclock.
    """
    cmd = '/sbin/hwclock'
    if time == 'system':
        cmd += ' --systohc'
    else:
        cmd += ' --set --date "{}"'.format(time)
    if utc:
        cmd += ' --utc'
    else:
        cmd += ' --localtime'
    if rtc is not None:
        cmd += ' --rtc={}'.format(rtc)
    if noadjfile:
        cmd += ' --noadjfile'
    return utils.system(cmd, ignore_status=ignore_status)


def set_wake_alarm(alarm_time):
    """
    Set the hardware RTC-based wake alarm to 'alarm_time'.
    """
    utils.write_one_line('/sys/class/rtc/rtc0/wakealarm', str(alarm_time))


_AUTOTEST_CLIENT_PATH = os.path.join(os.path.dirname(__file__), '..')
_AMD_PCI_IDS_FILE_PATH = os.path.join(_AUTOTEST_CLIENT_PATH,
                                      'bin/amd_pci_ids.json')
_INTEL_PCI_IDS_FILE_PATH = os.path.join(_AUTOTEST_CLIENT_PATH,
                                        'bin/intel_pci_ids.json')
_UI_USE_FLAGS_FILE_PATH = '/etc/ui_use_flags.txt'

# Command to check if a package is installed. If the package is not installed
# the command shall fail.
_CHECK_PACKAGE_INSTALLED_COMMAND = (
        "dpkg-query -W -f='${Status}\n' %s | head -n1 | awk '{print $3;}' | "
        "grep -q '^installed$'")


class Crossystem(object):
    """A wrapper for the crossystem utility."""
    def __init__(self, client):
        self.cros_system_data = {}
        self._client = client

    def init(self):
        self.cros_system_data = {}
        (_, fname) = tempfile.mkstemp()
        f = open(fname, 'w')
        self._client.run('crossystem', stdout_tee=f)
        f.close()
        text = utils.read_file(fname)
        for line in text.splitlines():
            assignment_string = line.split('#')[0]
            if not assignment_string.count('='):
                continue
            (name, value) = assignment_string.split('=', 1)
            self.cros_system_data[name.strip()] = value.strip()
        os.remove(fname)

    def __getattr__(self, name):
        """
        Retrieve a crosssystem attribute.

        The call crossystemobject.name() will return the crossystem reported
        string.
        """
        return lambda: self.cros_system_data[name]


def get_oldest_pid_by_name(name):
    """
    Return the oldest pid of a process whose name perfectly matches |name|.

    name is an egrep expression, which will be matched against the entire name
    of processes on the system.  For example:

      get_oldest_pid_by_name('chrome')

    on a system running
      8600 ?        00:00:04 chrome
      8601 ?        00:00:00 chrome
      8602 ?        00:00:00 chrome-sandbox

    would return 8600, as that's the oldest process that matches.
    chrome-sandbox would not be matched.

    Arguments:
      name: egrep expression to match.  Will be anchored at the beginning and
            end of the match string.

    Returns:
      pid as an integer, or None if one cannot be found.

    Raises:
      ValueError if pgrep returns something odd.
    """
    str_pid = utils.system_output('pgrep -o ^%s$' % name,
                                  ignore_status=True).rstrip()
    if str_pid:
        return int(str_pid)


def get_oldest_by_name(name):
    """Return pid and command line of oldest process whose name matches |name|.

    @param name: egrep expression to match desired process name.
    @return: A tuple of (pid, command_line) of the oldest process whose name
             matches |name|.

    """
    pid = get_oldest_pid_by_name(name)
    if pid:
        command_line = utils.system_output('ps -p %i -o command=' % pid,
                                           ignore_status=True).rstrip()
        return (pid, command_line)


def get_chrome_remote_debugging_port():
    """Returns remote debugging port for Chrome.

    Parse chrome process's command line argument to get the remote debugging
    port. if it is 0, look at DevToolsActivePort for the ephemeral port.
    """
    _, command = get_oldest_by_name('chrome')
    matches = re.search('--remote-debugging-port=([0-9]+)', command)
    if not matches:
        return 0
    port = int(matches.group(1))
    if port:
        return port
    with open('/home/chronos/DevToolsActivePort') as f:
        return int(f.readline().rstrip())


def get_process_list(name, command_line=None):
    """
    Return the list of pid for matching process |name command_line|.

    on a system running
      31475 ?    0:06 /opt/google/chrome/chrome --allow-webui-compositing -
      31478 ?    0:00 /opt/google/chrome/chrome-sandbox /opt/google/chrome/
      31485 ?    0:00 /opt/google/chrome/chrome --type=zygote --log-level=1
      31532 ?    1:05 /opt/google/chrome/chrome --type=renderer

    get_process_list('chrome')
    would return ['31475', '31485', '31532']

    get_process_list('chrome', '--type=renderer')
    would return ['31532']

    Arguments:
      name: process name to search for. If command_line is provided, name is
            matched against full command line. If command_line is not provided,
            name is only matched against the process name.
      command line: when command line is passed, the full process command line
                    is used for matching.

    Returns:
      list of PIDs of the matching processes.

    """
    # TODO(rohitbm) crbug.com/268861
    flag = '-x' if not command_line else '-f'
    name = '\'%s.*%s\'' % (name, command_line) if command_line else name
    str_pid = utils.system_output('pgrep %s %s' % (flag, name),
                                  ignore_status=True).rstrip()
    return str_pid.split()


def nuke_process_by_name(name, with_prejudice=False):
    """Tell the oldest process specified by name to exit.

    Arguments:
      name: process name specifier, as understood by pgrep.
      with_prejudice: if True, don't allow for graceful exit.

    Raises:
      error.AutoservPidAlreadyDeadError: no existing process matches name.
    """
    try:
        pid = get_oldest_pid_by_name(name)
    except Exception as e:
        logging.error(e)
        return
    if pid is None:
        raise error.AutoservPidAlreadyDeadError('No process matching %s.' %
                                                name)
    if with_prejudice:
        utils.nuke_pid(pid, [signal.SIGKILL])
    else:
        utils.nuke_pid(pid)


def is_virtual_machine():
    if 'QEMU' in platform.processor():
        return True

    try:
        with open('/sys/devices/virtual/dmi/id/sys_vendor') as f:
            if 'QEMU' in f.read():
                return True
    except IOError:
        pass

    return False


def save_vm_state(checkpoint):
    """Saves the current state of the virtual machine.

    This function is a NOOP if the test is not running under a virtual machine
    with the USB serial port redirected.

    Arguments:
      checkpoint - Name used to identify this state

    Returns:
      None
    """
    # The QEMU monitor has been redirected to the guest serial port located at
    # /dev/ttyUSB0. To save the state of the VM, we just send the 'savevm'
    # command to the serial port.
    if is_virtual_machine() and os.path.exists('/dev/ttyUSB0'):
        logging.info('Saving VM state "%s"', checkpoint)
        serial = open('/dev/ttyUSB0', 'w')
        serial.write('savevm %s\r\n' % checkpoint)
        logging.info('Done saving VM state "%s"', checkpoint)


def mounts():
    ret = []
    with open('/proc/mounts') as f:
        lines = f.readlines()
    for line in lines:
        m = re.match(
                r'(?P<src>\S+) (?P<dest>\S+) (?P<type>\S+) (?P<opts>\S+).*',
                line)
        if m:
            ret.append(m.groupdict())
    return ret


def is_mountpoint(path):
    return path in [m['dest'] for m in mounts()]


def require_mountpoint(path):
    """
    Raises an exception if path is not a mountpoint.
    """
    if not is_mountpoint(path):
        raise error.TestFail('Path not mounted: "%s"' % path)


def random_username():
    return str(uuid.uuid4()) + '@example.com'


def get_signin_credentials(filepath):
    """Returns user_id, password tuple from credentials file at filepath.

    File must have one line of the format user_id:password

    @param filepath: path of credentials file.
    @return user_id, password tuple.
    """
    user_id, password = None, None
    if os.path.isfile(filepath):
        with open(filepath) as f:
            user_id, password = f.read().rstrip().split(':')
    return user_id, password


def parse_cmd_output(command, run_method=utils.run):
    """Runs a command on a host object to retrieve host attributes.

    The command should output to stdout in the format of:
    <key> = <value> # <optional_comment>


    @param command: Command to execute on the host.
    @param run_method: Function to use to execute the command. Defaults to
                       utils.run so that the command will be executed locally.
                       Can be replace with a host.run call so that it will
                       execute on a DUT or external machine. Method must accept
                       a command argument, stdout_tee and stderr_tee args and
                       return a result object with a string attribute stdout
                       which will be parsed.

    @returns a dictionary mapping host attributes to their values.
    """
    result = {}
    # Suppresses stdout so that the files are not printed to the logs.
    cmd_result = run_method(command, stdout_tee=None, stderr_tee=None)
    for line in cmd_result.stdout.splitlines():
        # Lines are of the format "<key>     = <value>      # <comment>"
        key_value = re.match(
                r'^\s*(?P<key>[^ ]+)\s*=\s*(?P<value>[^ '
                r']+)(?:\s*#.*)?$', line)
        if key_value:
            result[key_value.group('key')] = key_value.group('value')
    return result


def set_from_keyval_output(out, delimiter=' '):
    """Parse delimiter-separated key-val output into a set of tuples.

    Output is expected to be multiline text output from a command.
    Stuffs the key-vals into tuples in a set to be later compared.

    e.g.  deactivated 0
          disableForceClear 0
          ==>  set(('deactivated', '0'), ('disableForceClear', '0'))

    @param out: multiple lines of space-separated key-val pairs.
    @param delimiter: character that separates key from val. Usually a
                      space but may be '=' or something else.
    @return set of key-val tuples.
    """
    results = set()
    kv_match_re = re.compile('([^ ]+)%s(.*)' % delimiter)
    for linecr in out.splitlines():
        match = kv_match_re.match(linecr.strip())
        if match:
            results.add((match.group(1), match.group(2)))
    return results


def get_cpu_usage():
    """Returns machine's CPU usage.

    This function uses /proc/stat to identify CPU usage.
    Returns:
        A dictionary with values for all columns in /proc/stat
        Sample dictionary:
        {
            'user': 254544,
            'nice': 9,
            'system': 254768,
            'idle': 2859878,
            'iowait': 1,
            'irq': 2,
            'softirq': 3,
            'steal': 4,
            'guest': 5,
            'guest_nice': 6
        }
        If a column is missing or malformed in /proc/stat (typically on older
        systems), the value for that column is set to 0.
    """
    with _open_file('/proc/stat') as proc_stat:
        cpu_usage_str = proc_stat.readline().split()
    columns = ('user', 'nice', 'system', 'idle', 'iowait', 'irq', 'softirq',
               'steal', 'guest', 'guest_nice')
    d = {}
    for index, col in enumerate(columns, 1):
        try:
            d[col] = int(cpu_usage_str[index])
        except:
            d[col] = 0
    return d


def compute_active_cpu_time(cpu_usage_start, cpu_usage_end):
    """Computes the fraction of CPU time spent non-idling.

    This function should be invoked using before/after values from calls to
    get_cpu_usage().

    See https://stackoverflow.com/a/23376195 and
    https://unix.stackexchange.com/a/303224 for some more context how
    to calculate usage given two /proc/stat snapshots.
    """
    idle_cols = ('idle', 'iowait')  # All other cols are calculated as active.
    time_active_start = sum([
            x[1] for x in six.iteritems(cpu_usage_start)
            if x[0] not in idle_cols
    ])
    time_active_end = sum([
            x[1] for x in six.iteritems(cpu_usage_end) if x[0] not in idle_cols
    ])
    total_time_start = sum(cpu_usage_start.values())
    total_time_end = sum(cpu_usage_end.values())
    # Avoid bogus division which has been observed on Tegra.
    if total_time_end <= total_time_start:
        logging.warning('compute_active_cpu_time observed bogus data')
        # We pretend to be busy, this will force a longer wait for idle CPU.
        return 1.0
    return ((float(time_active_end) - time_active_start) /
            (total_time_end - total_time_start))


def is_pgo_mode():
    return 'USE_PGO' in os.environ


def wait_for_idle_cpu(timeout, utilization):
    """Waits for the CPU to become idle (< utilization).

    Args:
        timeout: The longest time in seconds to wait before throwing an error.
        utilization: The CPU usage below which the system should be considered
                idle (between 0 and 1.0 independent of cores/hyperthreads).
    """
    time_passed = 0.0
    fraction_active_time = 1.0
    sleep_time = 1
    logging.info('Starting to wait up to %.1fs for idle CPU...', timeout)
    while fraction_active_time >= utilization:
        cpu_usage_start = get_cpu_usage()
        # Split timeout interval into not too many chunks to limit log spew.
        # Start at 1 second, increase exponentially
        time.sleep(sleep_time)
        time_passed += sleep_time
        sleep_time = min(16.0, 2.0 * sleep_time)
        cpu_usage_end = get_cpu_usage()
        fraction_active_time = compute_active_cpu_time(cpu_usage_start,
                                                       cpu_usage_end)
        logging.info('After waiting %.1fs CPU utilization is %.3f.',
                     time_passed, fraction_active_time)
        if time_passed > timeout:
            if fraction_active_time < utilization:
                break
            logging.warning('CPU did not become idle.')
            log_process_activity()
            # crosbug.com/37389
            if is_pgo_mode():
                logging.info('Still continuing because we are in PGO mode.')
                return True

            return False
    logging.info('Wait for idle CPU took %.1fs (utilization = %.3f).',
                 time_passed, fraction_active_time)
    return True


def log_process_activity():
    """Logs the output of top.

    Useful to debug performance tests and to find runaway processes.
    """
    logging.info('Logging current process activity using top and ps.')
    cmd = 'top -b -n1 -c'
    output = utils.run(cmd)
    logging.info(output)
    output = utils.run('ps axl')
    logging.info(output)


def wait_for_cool_machine():
    """
    A simple heuristic to wait for a machine to cool.
    The code looks a bit 'magic', but we don't know ambient temperature
    nor machine characteristics and still would like to return the caller
    a machine that cooled down as much as reasonably possible.
    """
    temperature = get_current_temperature_max()
    # We got here with a cold machine, return immediately. This should be the
    # most common case.
    if temperature < 45:
        return True
    logging.info('Got a hot machine of %dC. Sleeping 1 minute.', temperature)
    # A modest wait should cool the machine.
    time.sleep(60.0)
    temperature = get_current_temperature_max()
    # Atoms idle below 60 and everyone else should be even lower.
    if temperature < 62:
        return True
    # This should be rare.
    logging.info('Did not cool down (%dC). Sleeping 2 minutes.', temperature)
    time.sleep(120.0)
    temperature = get_current_temperature_max()
    # A temperature over 65'C doesn't give us much headroom to the critical
    # temperatures that start at 85'C (and PerfControl as of today will fail at
    # critical - 10'C).
    if temperature < 65:
        return True
    logging.warning('Did not cool down (%dC), giving up.', temperature)
    log_process_activity()
    return False


def report_temperature(test, keyname):
    """Report current max observed temperature with given keyname.

    @param test: autotest_lib.client.bin.test.test instance
    @param keyname: key to be used when reporting perf value.
    """
    temperature = get_current_temperature_max()
    logging.info('%s = %f degree Celsius', keyname, temperature)
    test.output_perf_value(description=keyname,
                           value=temperature,
                           units='Celsius',
                           higher_is_better=False)


# System paths for machine performance state.
_CPUINFO = '/proc/cpuinfo'
_DIRTY_WRITEBACK_CENTISECS = '/proc/sys/vm/dirty_writeback_centisecs'
_KERNEL_MAX = '/sys/devices/system/cpu/kernel_max'
_MEMINFO = '/proc/meminfo'
_TEMP_SENSOR_RE = 'Reading temperature...([0-9]*)'


def _open_file(path):
    """
    Opens a file and returns the file object.

    This method is intended to be mocked by tests.
    @return The open file object.
    """
    return open(path)


def _get_line_from_file(path, line):
    """
    line can be an integer or
    line can be a string that matches the beginning of the line
    """
    with _open_file(path) as f:
        if isinstance(line, int):
            l = f.readline()
            for _ in range(0, line):
                l = f.readline()
            return l
        else:
            for l in f:
                if l.startswith(line):
                    return l
    return None


def _get_match_from_file(path, line, prefix, postfix):
    """
    Matches line in path and returns string between first prefix and postfix.
    """
    match = _get_line_from_file(path, line)
    # Strip everything from front of line including prefix.
    if prefix:
        match = re.split(prefix, match)[1]
    # Strip everything from back of string including first occurence of postfix.
    if postfix:
        match = re.split(postfix, match)[0]
    return match


def _get_float_from_file(path, line, prefix, postfix):
    match = _get_match_from_file(path, line, prefix, postfix)
    return float(match)


def _get_int_from_file(path, line, prefix, postfix):
    match = _get_match_from_file(path, line, prefix, postfix)
    return int(match)


def _get_hex_from_file(path, line, prefix, postfix):
    match = _get_match_from_file(path, line, prefix, postfix)
    return int(match, 16)


def is_system_thermally_throttled():
    """
    Returns whether the system appears to be thermally throttled.
    """
    for path in glob.glob('/sys/class/thermal/cooling_device*/type'):
        with _open_file(path) as f:
            cdev_type = f.read().strip()

        if not (cdev_type == 'Processor'
                or cdev_type.startswith('thermal-devfreq')
                or cdev_type.startswith('thermal-cpufreq')):
            continue

        cur_state_path = os.path.join(os.path.dirname(path), 'cur_state')
        if _get_int_from_file(cur_state_path, 0, None, None) > 0:
            return True

    return False


# The paths don't change. Avoid running find all the time.
_hwmon_paths = {}


def _get_hwmon_datas(file_pattern):
    """Returns a list of reading from hwmon."""
    # Some systems like daisy_spring only have the virtual hwmon.
    # And other systems like rambi only have coretemp.0. See crbug.com/360249.
    #    /sys/class/hwmon/hwmon*/
    #    /sys/devices/virtual/hwmon/hwmon*/
    #    /sys/devices/platform/coretemp.0/
    if file_pattern not in _hwmon_paths:
        cmd = 'find /sys/class /sys/devices -name "' + file_pattern + '"'
        _hwmon_paths[file_pattern] = \
            utils.run(cmd, verbose=False).stdout.splitlines()
    for _hwmon_path in _hwmon_paths[file_pattern]:
        try:
            yield _get_float_from_file(_hwmon_path, 0, None, None) * 0.001
        except IOError as err:
            # Files under /sys may get truncated and result in ENODATA.
            # Ignore those.
            if err.errno is not errno.ENODATA:
                raise


def _get_hwmon_temperatures():
    """
    Returns the currently observed temperatures from hwmon
    """
    return list(_get_hwmon_datas('temp*_input'))


def _get_thermal_zone_temperatures():
    """
    Returns the maximum currently observered temperature in thermal_zones.
    """
    temperatures = []
    for path in glob.glob('/sys/class/thermal/thermal_zone*/temp'):
        try:
            temperatures.append(
                    _get_float_from_file(path, 0, None, None) * 0.001)
        except IOError:
            # Some devices (e.g. Veyron) may have reserved thermal zones that
            # are not active. Trying to read the temperature value would cause a
            # EINVAL IO error.
            continue
    return temperatures


def get_ec_temperatures():
    """
    Uses ectool to return a list of all sensor temperatures in Celsius.

    Output from ectool is an array of Celsius readings.
    """
    temperatures = []
    try:
        output = utils.run('ectool temps all', verbose=False).stdout
        temperatures = re.findall('\S+\s+([0-9]+) K', output)
        temperatures = [int(temp) - 273 for temp in temperatures]
    except Exception as e:
        logging.warning('Unable to read temperature sensors using ectool %s.',
                        e)
    # Check for real world values.
    if not all(10.0 <= temperature <= 150.0 for temperature in temperatures):
        logging.warning('Unreasonable EC temperatures: %s.', temperatures)
    return temperatures


def get_current_temperature_max():
    """
    Returns the highest reported board temperature (all sensors) in Celsius.
    """
    all_temps = (_get_hwmon_temperatures() + _get_thermal_zone_temperatures() +
                 get_ec_temperatures())
    if all_temps:
        temperature = max(all_temps)
    else:
        temperature = -1
    # Check for real world values.
    assert ((temperature > 10.0)
            and (temperature < 150.0)), ('Unreasonable temperature %.1fC.' %
                                         temperature)
    return temperature


def get_cpu_max_frequency():
    """
    Returns the largest of the max CPU core frequencies. The unit is Hz.
    """
    max_frequency = -1
    paths = utils._get_cpufreq_paths('cpuinfo_max_freq')
    if not paths:
        raise ValueError('Could not find max freq; is cpufreq supported?')
    for path in paths:
        try:
            # Convert from kHz to Hz.
            frequency = 1000 * _get_float_from_file(path, 0, None, None)
        # CPUs may come and go. A missing entry or two aren't critical.
        except IOError:
            continue
        max_frequency = max(frequency, max_frequency)
    # Confidence check.
    assert max_frequency > 1e8, ('Unreasonably low CPU frequency: %.1f' %
                                 max_frequency)
    return max_frequency


def get_board_property(key):
    """
    Get a specific property from /etc/lsb-release.

    @param key: board property to return value for

    @return the value or '' if not present
    """
    with open('/etc/lsb-release') as f:
        pattern = '%s=(.*)' % key
        pat = re.search(pattern, f.read())
        if pat:
            return pat.group(1)
    return ''


def get_board():
    """
    Get the ChromeOS release board name from /etc/lsb-release.
    """
    return get_board_property('BOARD')


def get_board_type():
    """
    Get the ChromeOS board type from /etc/lsb-release.

    @return device type.
    """
    return get_board_property('DEVICETYPE')


def get_chromeos_version():
    """
    Get the ChromeOS build version from /etc/lsb-release.

    @return chromeos release version.
    """
    return get_board_property('CHROMEOS_RELEASE_VERSION')


def get_android_version():
    """
    Get the Android SDK version from /etc/lsb-release.

    @return android sdk version.
    """
    return get_board_property('CHROMEOS_ARC_ANDROID_SDK_VERSION')


def is_arcvm():
    try:
        return int(get_android_version()) >= 30
    except:
        return False


def get_platform():
    """
    Get the ChromeOS platform name.

    For unibuild this should be equal to model name.  For non-unibuild
    it will either be board name or empty string.  In the case of
    empty string return board name to match equivalent logic in
    server/hosts/cros_host.py

    @returns platform name
    """
    platform = cros_config.call_cros_config_get_output('/ name', utils.run)
    if platform == '':
        platform = get_board()
    return platform


def get_sku():
    """
    Get the SKU number.

    @returns SKU number
    """
    return cros_config.call_cros_config_get_output('/identity sku-id',
                                                   utils.run)


def get_ec_version_from_chardev_contents(contents):
    """Given the contents of /dev/cros_ec, interpret the active version.

    @param contents: The contents of a cros_ec chardev.

    @returns The active EC version, or an empty string upon error.
    """
    lines = contents.splitlines()
    if len(lines) != 4:
        return ""
    _, ro_version, rw_version, active_copy = lines
    if active_copy == "read-only":
        return ro_version
    if active_copy == "read-write":
        return rw_version
    return ""


def get_ec_version():
    """Get the ec version as strings.

    @returns a string representing this host's ec version.
    """
    try:
        contents = utils.read_file("/dev/cros_ec")
    except FileNotFoundError:
        return ""
    return get_ec_version_from_chardev_contents(contents)


def get_firmware_version():
    """Get the firmware version as strings.

    @returns a string representing this host's firmware version.
    """
    return utils.run('crossystem fwid').stdout.strip()


def get_hardware_id():
    """Get hardware id as strings.

    @returns a string representing this host's hardware id.
    """
    return utils.run('crossystem hwid').stdout.strip()


def get_hardware_revision():
    """Get the hardware revision as strings.

    @returns a string representing this host's hardware revision.
    """
    result = utils.run("crossystem board_id", ignore_status=True)

    if result.exit_status == 0:
        return 'rev' + result.stdout.strip()
    return ""


def get_kernel_version():
    """Get the kernel version as strings.

    @returns a string representing this host's kernel version.
    """
    return utils.run('uname -r').stdout.strip()


def get_cpu_name():
    """Get the cpu name as strings.

    @returns a string representing this host's cpu name.
    """

    # Try get cpu name from device tree first
    if os.path.exists("/proc/device-tree/compatible"):
        command = "sed -e 's/\\x0/\\n/g' /proc/device-tree/compatible | tail -1"
        return utils.run(command).stdout.strip().replace(',', ' ')

    # Get cpu name from uname -p
    command = "uname -p"
    ret = utils.run(command).stdout.strip()

    # 'uname -p' return variant of unknown or amd64 or x86_64 or i686
    # Try get cpu name from /proc/cpuinfo instead
    if re.match("unknown|amd64|[ix][0-9]?86(_64)?", ret, re.IGNORECASE):
        command = "grep model.name /proc/cpuinfo | cut -f 2 -d: | head -1"
        ret = utils.run(command).stdout.strip()

    # Remove bloat from CPU name, for example
    # 'Intel(R) Core(TM) i5-7Y57 CPU @ 1.20GHz'       -> 'Intel Core i5-7Y57'
    # 'Intel(R) Xeon(R) CPU E5-2690 v4 @ 2.60GHz'     -> 'Intel Xeon E5-2690 v4'
    # 'AMD A10-7850K APU with Radeon(TM) R7 Graphics' -> 'AMD A10-7850K'
    # 'AMD GX-212JC SOC with Radeon(TM) R2E Graphics' -> 'AMD GX-212JC'
    trim_re = " (@|processor|apu|soc|radeon).*|\(.*?\)| cpu"
    return re.sub(trim_re, '', ret, flags=re.IGNORECASE)


def get_screen_resolution():
    """Get the screen(s) resolution as strings.
    In case of more than 1 monitor, return resolution for each monitor separate
    with plus sign.

    @returns a string representing this host's screen(s) resolution.
    """
    command = 'for f in /sys/class/drm/*/*/modes; do head -1 $f; done'
    ret = utils.run(command, ignore_status=True)
    # We might have Chromebox without a screen
    if ret.exit_status != 0:
        return ''
    return ret.stdout.strip().replace('\n', '+')


def has_screen():
    """Return True if the device has a screen. False otherwise."""
    command = 'for f in /sys/class/drm/*/*/modes; do head -1 $f; done'
    ret = utils.run(command, ignore_status=True)
    if ret.exit_status != 0 or ret.stdout.strip() == "":
        return False
    return True


def get_screen_size():
    """Get the screen size in mm.
    If the device does not have a screen we return an empty string."""
    if not has_screen():
        return ''
    cmds = ["modetest -c", "sed -n '/size (mm)/{n;p}'"]
    cmd = " | ".join(cmds)
    res = utils.system_output(cmd).strip()
    res = re.search("[0-9]+x[0-9]+", res).group(0)
    return res


def get_screen_refresh_rate():
    """Get screen refresh rate.
    If the device does not have a screen we return an empty string."""
    if not has_screen():
        return -1
    cmds = ["modetest -c", "grep 'refresh (Hz)'"]
    cmd = " | ".join(cmds)
    res = utils.system_output(cmd).strip()
    res = re.sub('\s+', ' ', res).split(' ')
    pos = res.index('refresh')

    cmds = ["modetest -c", "sed -n '/refresh (Hz)/{n;p}'"]
    cmd = " | ".join(cmds)
    res = utils.system_output(cmd).strip()
    res = re.sub('\s+', ' ', res)
    return round(float(res.split(' ')[pos]))


def get_board_with_frequency_and_memory():
    """
    Returns a board name modified with CPU frequency and memory size to
    differentiate between different board variants. For instance
    link -> link_1.8GHz_4GB.
    """
    board_name = get_board()
    if is_virtual_machine():
        board = '%s_VM' % board_name
    else:
        memory = get_mem_total_gb()
        # Convert frequency to GHz with 1 digit accuracy after the
        # decimal point.
        frequency = int(round(get_cpu_max_frequency() * 1e-8)) * 0.1
        board = '%s_%1.1fGHz_%dGB' % (board_name, frequency, memory)
    return board


def get_mem_total():
    """
    Returns the total memory available in the system in MBytes.
    """
    mem_total = _get_float_from_file(_MEMINFO, 'MemTotal:', 'MemTotal:', ' kB')
    # Confidence check, all Chromebooks have at least 1GB of memory.
    assert mem_total > 256 * 1024, 'Unreasonable amount of memory.'
    return int(mem_total / 1024)


def get_mem_total_gb():
    """
    Returns the total memory available in the system in GBytes.
    """
    return int(round(get_mem_total() / 1024.0))


def get_mem_free():
    """
    Returns the currently free memory in the system in MBytes.
    """
    mem_free = _get_float_from_file(_MEMINFO, 'MemFree:', 'MemFree:', ' kB')
    return int(mem_free / 1024)


def get_mem_free_plus_buffers_and_cached():
    """
    Returns the free memory in MBytes, counting buffers and cached as free.

    This is most often the most interesting number since buffers and cached
    memory can be reclaimed on demand. Note however, that there are cases
    where this as misleading as well, for example used tmpfs space
    count as Cached but can not be reclaimed on demand.
    See https://www.kernel.org/doc/Documentation/filesystems/tmpfs.txt.
    """
    free_mb = get_mem_free()
    cached_mb = (_get_float_from_file(_MEMINFO, 'Cached:', 'Cached:', ' kB') /
                 1024)
    buffers_mb = (
            _get_float_from_file(_MEMINFO, 'Buffers:', 'Buffers:', ' kB') /
            1024)
    return free_mb + buffers_mb + cached_mb


def get_dirty_writeback_centisecs():
    """
    Reads /proc/sys/vm/dirty_writeback_centisecs.
    """
    time = _get_int_from_file(_DIRTY_WRITEBACK_CENTISECS, 0, None, None)
    return time


def set_dirty_writeback_centisecs(time=60000):
    """
    In hundredths of a second, this is how often pdflush wakes up to write data
    to disk. The default wakes up the two (or more) active threads every five
    seconds. The ChromeOS default is 10 minutes.

    We use this to set as low as 1 second to flush error messages in system
    logs earlier to disk.
    """
    # Flush buffers first to make this function synchronous.
    utils.system('sync')
    if time >= 0:
        cmd = 'echo %d > %s' % (time, _DIRTY_WRITEBACK_CENTISECS)
        utils.system(cmd)


def wflinfo_cmd():
    """
    Returns a wflinfo command appropriate to the current graphics platform/api.
    """
    return 'wflinfo -p %s -a %s' % (graphics_platform(), graphics_api())


def has_mali():
    """ @return: True if system has a Mali GPU enabled."""
    return os.path.exists('/dev/mali0')


def get_gpu_family():
    try:
        cmd = '/usr/local/graphics/hardware_probe'
        output = utils.run(cmd, ignore_status=True).stdout
        return json.loads(output)['GPU_Family'][0]['Family']
    except json.decoder.JSONDecodeError:
        """Returns the GPU family name."""
        cmd = '/usr/local/graphics/hardware_probe --gpu-family'
        output = utils.run(cmd, ignore_status=True).stdout
        return output.split(":")[1].strip()


# TODO(ihf): Consider using /etc/lsb-release DEVICETYPE != CHROMEBOOK/CHROMEBASE
# for confidence check, but usage seems a bit inconsistent. See
# src/third_party/chromiumos-overlay/eclass/appid.eclass
_BOARDS_WITHOUT_MONITOR = [
        'anglar', 'mccloud', 'monroe', 'ninja', 'rikku', 'guado', 'jecht',
        'tidus', 'beltino', 'panther', 'stumpy', 'panther', 'tricky', 'zako',
        'veyron_rialto'
]


def has_no_monitor():
    """Returns whether a machine doesn't have a built-in monitor."""
    board_name = get_board()
    if board_name in _BOARDS_WITHOUT_MONITOR:
        return True

    return False


def get_fixed_dst_drive():
    """
    Return device name for internal disk.
    Example: return /dev/sda for falco booted from usb
    """
    cmd = ' '.join([
            '. /usr/sbin/write_gpt.sh;',
            '. /usr/share/misc/chromeos-common.sh;', 'load_base_vars;',
            'get_fixed_dst_drive'
    ])
    return utils.system_output(cmd)


def get_root_device():
    """
    Return root device.
    Will return correct disk device even system boot from /dev/dm-0
    Example: return /dev/sdb for falco booted from usb
    """
    return utils.system_output('rootdev -s -d')


def get_other_device():
    """
    Return the non root devices.
    Will return a list of other block devices, that are not the root device.
    """

    cmd = 'lsblk -dpn -o NAME | grep -v -E "(loop|zram|boot|rpmb)"'
    devs = utils.system_output(cmd).splitlines()

    for dev in devs[:]:
        if not re.match(r'/dev/(sd[a-z]|mmcblk[0-9]+|nvme[0-9]+)p?[0-9]*',
                        dev):
            devs.remove(dev)
        if dev == get_root_device():
            devs.remove(dev)
    return devs


def get_root_partition():
    """
    Return current root partition
    Example: return /dev/sdb3 for falco booted from usb
    """
    return utils.system_output('rootdev -s')


def get_free_root_partition(root_part=None):
    """
    Return currently unused root partion
    Example: return /dev/sdb5 for falco booted from usb

    @param root_part: cuurent root partition
    """
    spare_root_map = {'3': '5', '5': '3'}
    if not root_part:
        root_part = get_root_partition()
    return root_part[:-1] + spare_root_map[root_part[-1]]


def get_kernel_partition(root_part=None):
    """
    Return current kernel partition
    Example: return /dev/sda2 for falco booted from usb

    @param root_part: current root partition
    """
    if not root_part:
        root_part = get_root_partition()
    current_kernel_map = {'3': '2', '5': '4'}
    return root_part[:-1] + current_kernel_map[root_part[-1]]


def get_free_kernel_partition(root_part=None):
    """
    return currently unused kernel partition
    Example: return /dev/sda4 for falco booted from usb

    @param root_part: current root partition
    """
    kernel_part = get_kernel_partition(root_part)
    spare_kernel_map = {'2': '4', '4': '2'}
    return kernel_part[:-1] + spare_kernel_map[kernel_part[-1]]


def is_booted_from_internal_disk():
    """Return True if boot from internal disk. False, otherwise."""
    return get_root_device() == get_fixed_dst_drive()


def get_ui_use_flags():
    """Parses the USE flags as listed in /etc/ui_use_flags.txt.

    @return: A list of flag strings found in the ui use flags file.
    """
    flags = []
    for flag in utils.read_file(_UI_USE_FLAGS_FILE_PATH).splitlines():
        # Removes everything after the '#'.
        flag_before_comment = flag.split('#')[0].strip()
        if len(flag_before_comment) != 0:
            flags.append(flag_before_comment)

    return flags


def graphics_platform():
    """
    Return a string identifying the graphics platform,
    e.g. 'glx' or 'x11_egl' or 'gbm'
    """
    return 'null'


def graphics_api():
    """Return a string identifying the graphics api, e.g. gl or gles2."""
    use_flags = get_ui_use_flags()
    if 'opengles' in use_flags:
        return 'gles2'
    return 'gl'


def is_package_installed(package):
    """Check if a package is installed already.

    @return: True if the package is already installed, otherwise return False.
    """
    try:
        utils.run(_CHECK_PACKAGE_INSTALLED_COMMAND % package)
        return True
    except error.CmdError:
        logging.warning('Package %s is not installed.', package)
        return False


def is_python_package_installed(package):
    """Check if a Python package is installed already.

    @return: True if the package is already installed, otherwise return False.
    """
    try:
        __import__(package)
        return True
    except ImportError:
        logging.warning('Python package %s is not installed.', package)
        return False


def run_sql_cmd(server, user, password, command, database=''):
    """Run the given sql command against the specified database.

    @param server: Hostname or IP address of the MySQL server.
    @param user: User name to log in the MySQL server.
    @param password: Password to log in the MySQL server.
    @param command: SQL command to run.
    @param database: Name of the database to run the command. Default to empty
                     for command that does not require specifying database.

    @return: The stdout of the command line.
    """
    cmd = ('mysql -u%s -p%s --host %s %s -e "%s"' %
           (user, password, server, database, command))
    # Set verbose to False so the command line won't be logged, as it includes
    # database credential.
    return utils.run(cmd, verbose=False).stdout


def strip_non_printable(s):
    """Strip non printable characters from string.

    @param s: Input string

    @return: The input string with only printable characters.
    """
    return ''.join(x for x in s if x in string.printable)


def recursive_func(obj,
                   func,
                   types,
                   sequence_types=(list, tuple, set),
                   dict_types=(dict, ),
                   fix_num_key=False):
    """Apply func to obj recursively.

    This function traverses recursively through any sequence-like and
    dict-like elements in obj.

    @param obj: the object to apply the function func recursively.
    @param func: the function to invoke.
    @param types: the target types in the object to apply func.
    @param sequence_types: the sequence types in python.
    @param dict_types: the dict types in python.
    @param fix_num_key: to indicate if the key of a dict should be
            converted from str type to a number, int or float, type.
            It is a culprit of json that it always treats the key of
            a dict as string.
            Refer to https://docs.python.org/2/library/json.html
            for more information.

    @return: the result object after applying the func recursively.
    """
    def ancestors(obj, types):
        """Any ancestor of the object class is a subclass of the types?

        @param obj: the object to apply the function func.
        @param types: the target types of the object.

        @return: True if any ancestor class of the obj is found in types;
                 False otherwise.
        """
        return any([issubclass(anc, types) for anc in type(obj).__mro__])

    if isinstance(obj, sequence_types) or ancestors(obj, sequence_types):
        result_lst = [
                recursive_func(elm, func, types, fix_num_key=fix_num_key)
                for elm in obj
        ]
        # Convert the result list to the object's original sequence type.
        return type(obj)(result_lst)
    elif isinstance(obj, dict_types) or ancestors(obj, dict_types):
        result_lst = [(recursive_func(key,
                                      func,
                                      types,
                                      fix_num_key=fix_num_key),
                       recursive_func(value,
                                      func,
                                      types,
                                      fix_num_key=fix_num_key))
                      for (key, value) in obj.items()]
        # Convert the result list to the object's original dict type.
        return type(obj)(result_lst)
    # Here are the basic types.
    elif isinstance(obj, types) or ancestors(obj, types):
        if fix_num_key:
            # Check if this is a int or float
            try:
                result_obj = int(obj)
                return result_obj
            except ValueError:
                try:
                    result_obj = float(obj)
                    return result_obj
                except ValueError:
                    pass
        try:
            result_obj = func(obj)
            return result_obj
        except UnicodeEncodeError:
            pass
    else:
        return obj


def is_python2():
    """True if it is interpreted by Python 2."""
    return sys.version_info.major == 2


def base64_recursive_encode(obj):
    """Apply base64 encode recursively into the obj structure.

    Python 2 case:
        Most of the string-like types could be traced to basestring and bytearray
        as follows:
            str: basestring
            bytes: basestring
            dbus.String: basestring
            dbus.Signature: basestring
            dbus.ByteArray: basestring

        Note that all the above types except dbus.String could be traced back to
        str. In order to cover dbus.String, basestring is used as the ancestor
        class for string-like types.

    Python 3 case:
        Perform base64 encode on bytes element only.

    The other type that needs encoding with base64 in a structure includes
        bytearray: bytearray

    The sequence types include (list, tuple, set). The dbus.Array is also
    covered as
        dbus.Array: list

    The base dictionary type is dict. The dbus.Dictionary is also covered as
        dbus.Dictionary: dict

    An example code and output look like
    in Python 2:
        obj = {'a': 10, 'b': 'hello',
               'c': [100, 200, bytearray(b'\xf0\xf1\xf2\xf3\xf4')],
               'd': {784: bytearray(b'@\x14\x01P'),
                     78.0: bytearray(b'\x10\x05\x0b\x10\xb2\x1b\x00')}}
        encode_obj = base64_recursive_encode(obj)
        decode_obj = base64_recursive_decode(encode_obj)

        encode_obj:  {'YQ==': 10,
                      'Yw==': [100, 200, '8PHy8/Q='],
                      'Yg==': 'aGVsbG8='
                      'ZA==': {784: 'QBQBUA==', 78.0: 'EAULELIbAA=='}}
        decode_obj:  {'a': 10,
                      'c': [100, 200, '\xf0\xf1\xf2\xf3\xf4'],
                      'b': 'hello',
                      'd': {784: '@\x14\x01P',
                            78.0: '\x10\x05\x0b\x10\xb2\x1b\x00'}}

    in Python 3:
        obj = {'a': 10, 'b': 'hello',
               'c': [100, 200, bytearray(b'\xf0\xf1\xf2\xf3\xf4')],
               'd': {784: bytearray(b'@\x14\x01P'),
                     78.0: bytearray(b'\x10\x05\x0b\x10\xb2\x1b\x00')}}
        encode_obj = base64_recursive_encode(obj)
        decode_obj = base64_recursive_decode(encode_obj)

        encode_obj:  {'a': 10,
                      'c': [100, 200, '8PHy8/Q='],
                      'b': 'hello',
                      'ZA==': {784: 'QBQBUA==', 78.0: 'EAULELIbAA=='}}
        decode_obj:  {'a': 10,
                      'c': [100, 200, '\xf0\xf1\xf2\xf3\xf4'],
                      'b': 'hello',
                      'd': {784: '@\x14\x01P',
                            78.0: '\x10\x05\x0b\x10\xb2\x1b\x00'}}

    @param obj: the object to apply base64 encoding recursively.

    @return: the base64 encoded object.
    """
    if is_python2():
        encode_types = (six.string_types, bytearray)
    else:
        encode_types = (bytes, bytearray)

    return recursive_func(obj, base64.standard_b64encode, encode_types)


def base64_recursive_decode(obj):
    """Apply base64 decode recursively into the obj structure.

    @param obj: the object to apply base64 decoding recursively.

    @return: the base64 decoded object.
    """
    if is_python2():
        decode_types = (six.string_types, )
    else:
        decode_types = (bytes, bytearray)
    return recursive_func(obj,
                          base64.standard_b64decode,
                          decode_types,
                          fix_num_key=True)


def bytes_to_str_recursive(obj):
    """Converts obj's bytes elements to str.

    It focuses on elements in the input obj whose type is bytes or byearray.
    For the elements, it first guesses the encoding of the input bytes (or
    bytearray) and decode the bytes to str. For unknown encoding, try UTF-8.
    If it still fails, converts the element as "ERROR_DECODE_BYTES_TO_STR".

    @param obj: an object.

    @return: an object that converts the input object's bytes elements to
        strings.
    """
    # Python 2's bytes is equivalent to string. Do nothing.
    if is_python2():
        return obj

    def bytes_to_str(bytes_obj):
        guessed_encoding = chardet.detect(bytes_obj).get('encoding')
        if not guessed_encoding:
            guessed_encoding = 'utf-8'
        try:
            return bytes_obj.decode(guessed_encoding, 'backslashreplace')
        except:
            logging.info("Failed to decode bytes %r to str with encoding %r",
                         bytes_obj, guessed_encoding)
            return 'ERROR_DECODE_BYTES_TO_STR'

    return recursive_func(obj, bytes_to_str, (bytes, bytearray))


def is_cloudbot():
    """Determine if current process is running on cloudbot env."""
    return os.environ.get('CLOUDBOTS_LAB_DOMAIN', '') != ''
