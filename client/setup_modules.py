import os
import re
import six
import sys

# This must run on Python versions less than 2.4.
dirname = os.path.dirname(sys.modules[__name__].__file__)
common_dir = os.path.abspath(os.path.join(dirname, 'common_lib'))
sys.path.insert(0, common_dir)
import check_version
sys.path.pop(0)

FILE_ERROR = FileExistsError if six.PY3 else OSError


def _get_pyversion_from_args():
    """Extract, format, & pop the current py_version from args, if provided."""
    py_version = 3
    py_version_re = re.compile(r'--py_version=(\w+)\b')

    version_found = False
    for i, arg in enumerate(sys.argv):
        if not arg.startswith('--py_version'):
            continue
        result = py_version_re.search(arg)
        if result:
            if version_found:
                raise ValueError('--py_version may only be specified once.')
            py_version = result.group(1)
            version_found = True
            if py_version not in ('2', '3'):
                raise ValueError('Python version must be "2" or "3".')

            # Remove the arg so other argparsers don't get grumpy.
            sys.argv.pop(i)

    return py_version


def _desired_version():
    """
    Returns desired python version.

    If the PY_VERSION env var is set, just return that. This is the case
    when autoserv kicks of autotest on the server side via a job.run(), or
    a process created a subprocess.

    Otherwise, parse & pop the sys.argv for the '--py_version' flag. If no
    flag is set, default to python 3.

    """
    # Even if the arg is in the env vars, we will attempt to get it from the
    # args, so that it can be popped prior to other argparsers hitting.
    py_version = _get_pyversion_from_args()

    if os.getenv('PY_VERSION'):
        return int(os.getenv('PY_VERSION'))

    os.environ['PY_VERSION'] = str(py_version)
    return int(py_version)


desired_version = _desired_version()
if desired_version == sys.version_info.major:
    os.environ['AUTOTEST_NO_RESTART'] = 'True'
else:
    # There are cases were this can be set (ie by test_that), but a subprocess
    # is launched in the incorrect version.
    if os.getenv('AUTOTEST_NO_RESTART'):
        del os.environ['AUTOTEST_NO_RESTART']
    check_version.check_python_version(desired_version)

import glob, traceback


def import_module(module, from_where):
    """Equivalent to 'from from_where import module'
    Returns the corresponding module"""
    from_module = __import__(from_where, globals(), locals(), [module])
    return getattr(from_module, module)


def _autotest_logging_handle_error(self, record):
    """Method to monkey patch into logging.Handler to replace handleError."""
    # The same as the default logging.Handler.handleError but also prints
    # out the original record causing the error so there is -some- idea
    # about which call caused the logging error.
    import logging
    if logging.raiseExceptions:
        # Avoid recursion as the below output can end up back in here when
        # something has *seriously* gone wrong in autotest.
        logging.raiseExceptions = 0
        sys.stderr.write('Exception occurred formatting message: '
                         '%r using args %r\n' % (record.msg, record.args))
        traceback.print_stack()
        sys.stderr.write('-' * 50 + '\n')
        traceback.print_exc()
        sys.stderr.write('Future logging formatting exceptions disabled.\n')


def _monkeypatch_logging_handle_error():
    """Setup logging method.  """
    # Hack out logging.py*
    logging_py = os.path.join(os.path.dirname(__file__), 'common_lib',
                              'logging.py*')
    if glob.glob(logging_py):
        os.system('rm -f %s' % logging_py)

    # Monkey patch our own handleError into the logging module's StreamHandler.
    # A nicer way of doing this -might- be to have our own logging module define
    # an autotest Logger instance that added our own Handler subclass with this
    # handleError method in it.  But that would mean modifying tons of code.
    import logging
    assert callable(logging.Handler.handleError)
    logging.Handler.handleError = _autotest_logging_handle_error


def _insert_site_packages(root):
    """Allow locally installed third party packages to be found before any that
    are installed on the system itself when not running as a client.

    This is primarily for the benefit of frontend and tko so that they may use
    libraries other than those available as system packages.
    """
    if six.PY2:
        sys.path.insert(0, os.path.join(root, 'site-packages'))


import importlib

ROOT_MODULE_NAME_ALLOW_LIST = (
        'autotest_lib',
        'autotest_lib.client',
)


def _setup_top_level_symlink(base_path, autotest_lib_name):
    """Create a self pointing symlink in the base_path)."""

    # Create symlink of autotest_lib_name to the current directory
    autotest_lib_path = os.path.join(base_path, autotest_lib_name)
    if os.path.exists(autotest_lib_path):
        return

    # Save state of current working dir
    current_dir = os.getcwd()

    os.chdir(base_path)
    try:
        os.symlink('.', 'autotest_lib')
    except FILE_ERROR as e:
        if os.path.islink('autotest_lib'):
            return
        raise e
    finally:
        # Return state of current working dir
        os.chdir(current_dir)


def _setup_client_symlink(base_path, autotest_lib_name):
    """Setup the client symlink for the DUT.

    Creates a folder named  autotest_lib_name, then creates a symlink called
    "client" pointing back to ../, as well as an __init__ for the folder.
    """

    def _create_client_symlink():
        """Create client symlink to parent dir.
        """
        with open('__init__.py', 'w'):
            pass
        os.symlink('../', 'client')

    # Create autotest_lib directory and symlinks
    autotest_lib_dir = os.path.join(base_path, autotest_lib_name)
    link_path = os.path.join(autotest_lib_dir, 'client')

    # TODO: Use os.makedirs(..., exist_ok=True) after switching to Python 3
    if not os.path.isdir(autotest_lib_dir):
        try:
            os.mkdir(autotest_lib_dir)
        except FILE_ERROR as e:
            if not os.path.isdir(autotest_lib_dir):
                raise e

    if os.path.islink(link_path):
        return

    # Save state of current working dir
    current_dir = os.getcwd()

    os.chdir(autotest_lib_dir)
    try:
        _create_client_symlink()
    # It's possible 2 autotest processes are running at once, and one
    # creates the symlink in the time between checking and creating.
    # Thus if the symlink DNE, and we cannot create it, check for its
    # existence and exit if it exists.
    except FILE_ERROR as e:
        if os.path.islink(link_path):
            return
        raise e
    finally:
        # Return state of current working dir
        os.chdir(current_dir)


def setup(base_path, root_module_name):
    """import autotest_lib modules and toplevel submodules.

    ex:
    - autotest_lib
    - autotest_lib.client
    - autotest_lib.client.bin
    """
    # Input verification first
    if root_module_name not in ROOT_MODULE_NAME_ALLOW_LIST:
        raise Exception('Unexpected root module: ' + root_module_name)

    # Function will only have an effect if running python2
    _insert_site_packages(base_path)

    # Default autotest_lib name
    autotest_lib_name = 'autotest_lib'

    # Ie, server (or just not /client)
    if root_module_name == 'autotest_lib':
        # Creates a symlink to itself
        _setup_top_level_symlink(base_path, autotest_lib_name)

        # Base path is just x/x/x/x/autotest/files
        _setup_autotest_lib(base_path, autotest_lib_name)

        # Setup the autotest_lib.* modules
        _preimport_top_level_packages(
                base_path,
                parent='autotest_lib',
                autotest_lib_name=autotest_lib_name)
    else:  # aka, in /client/
        # Takes you from /client/ to /files
        # this is because on DUT there is no files/client
        if os.path.exists(os.path.join(os.path.dirname(base_path), 'server')):
            autotest_base_path = os.path.dirname(base_path)
        else:
            # TODO(b/228100799): revert crrev.com/c/3869349 once au_e2e is SSP.
            autotest_lib_name = 'autotest_lib_%s' % os.getpid()
            autotest_base_path = base_path

        _setup_client_symlink(base_path, autotest_lib_name)

        # Modules autotest_lib_<PID> -> dir/autotest_lib_<PID>
        _setup_autotest_lib(autotest_base_path, autotest_lib_name)

        # setup autotest_lib, autotest_lib.client.*
        _preimport_top_level_packages(os.path.join(autotest_base_path,
                                                   autotest_lib_name),
                                      parent='autotest_lib',
                                      autotest_lib_name=autotest_lib_name)
        _preimport_top_level_packages(os.path.join(autotest_base_path,
                                                   autotest_lib_name, 'client'),
                                      parent='autotest_lib.client',
                                      autotest_lib_name=autotest_lib_name)

    _monkeypatch_logging_handle_error()


def _setup_autotest_lib(autotest_lib_path, autotest_lib_name):
    """Sets up the toplevel module 'autotest_lib'.

    Imports the module autotest_lib_name and maps the desired 'autotest_lib'
    name to it.
    """
    # Add autotest_lib to our path
    sys.path.insert(0, autotest_lib_path)

    # This is a symlink back to the root directory
    importlib.import_module(autotest_lib_name)

    # Setup toplevel 'autotest_lib' module name
    sys.modules['autotest_lib'] = sys.modules[autotest_lib_name]

    # Restore original state of path
    sys.path.pop(0)


def _preimport_top_level_packages(root, parent, autotest_lib_name):
    """Pre import the autotest_lib module top level packages.

    The existence of an __init__.py file in a directory is used to determine if
    that directory is pre-imported as a sub module of autotest_lib or
    autotest_lib.client.

    The intent is to reduce the number of imports required in the codebase.

    Args:
      root:
        Location we will be looking for directories that contain '__init__.py'
        files
      parent:
        Module name those directories should be imported as sub modules of,
        autotest_lib or autotest_lib.client
      autotest_lib_name:
        Name of the autotest_lib we used when creating the directory structure
    """
    # The old code to setup the packages used to fetch the top-level packages
    # inside autotest_lib. We keep that behaviour in order to avoid having to
    # add import statements for the top-level packages all over the codebase.
    #
    # e.g.,
    #  import common
    #  from autotest_lib.server import utils
    #
    # must continue to work. The _right_ way to do that import would be.
    #
    #  import common
    #  import autotest_lib.server
    #  from autotest_lib.server import utils

    # Find the top-level packages, they are identified by directories that
    # contain __init__ files
    names = []
    for filename in os.listdir(root):
        path = os.path.join(root, filename)
        if not os.path.isdir(path):
            continue  # skip files
        if '.' in filename:
            continue  # if "." is in the name it's not a valid package name
        if not os.access(path, os.R_OK | os.X_OK):
            continue  # need read + exec access to make a dir importable
        if '__init__.py' in os.listdir(path):
            names.append(filename)

    # Do not import autotest_lib or autotest_lib_<PID>, only the packages
    autotest_re = r'^autotest_lib[_0123456789]*'
    for name in names:
        if re.match(autotest_re, name) is None:
            pname = parent + '.' + name
            importlib.import_module(pname)
            sys.modules[name] = sys.modules[pname]
