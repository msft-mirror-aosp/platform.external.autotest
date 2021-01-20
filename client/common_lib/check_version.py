# This file must use Python 1.5 syntax.
import glob
import logging
import os
import sys

PY_GLOBS = {
        3: ['/usr/bin/python3*', '/usr/local/bin/python3*'],
        2: ['/usr/bin/python2*', '/usr/local/bin/python2*']
}


class check_python_version:

    def __init__(self, desired_version=2):
        # In order to ease the migration to Python3, disable the restart logic
        # when AUTOTEST_NO_RESTART is set. This makes it possible to run
        # autotest locally as Python3 before any other environment is switched
        # to Python3.
        if os.getenv("AUTOTEST_NO_RESTART"):
            return
        self.desired_version = desired_version
        if self.desired_version == 3:
            logging.warning("Python3 not not ready yet. Swapping to Python 2.")
            self.desired_version = 2
        # The change to prefer 2.4 really messes up any systems which have both
        # the new and old version of Python, but where the newer is default.
        # This is because packages, libraries, etc are all installed into the
        # new one by default. Some things (like running under mod_python) just
        # plain don't handle python restarting properly. I know that I do some
        # development under ipython and whenever I run (or do anything that
        # runs) 'import common' it restarts my shell. Overall, the change was
        # fairly annoying for me (and I can't get around having 2.4 and 2.5
        # installed with 2.5 being default).
        if sys.version_info.major != self.desired_version:
            try:
                # We can't restart when running under mod_python.
                from mod_python import apache
            except ImportError:
                self.restart()

    def find_desired_python(self):
        """Returns the path of the desired python interpreter."""
        # CrOS only ever has Python 2.7 available, so pick whatever matches.
        pyv_strings = PY_GLOBS[self.desired_version]
        pythons = []
        for glob_str in pyv_strings:
            pythons.extend(glob.glob(glob_str))
        return pythons[0]

    def restart(self):
        python = self.find_desired_python()
        sys.stderr.write('NOTE: %s switching to %s\n' %
                         (os.path.basename(sys.argv[0]), python))
        sys.argv.insert(0, '-u')
        sys.argv.insert(0, python)
        os.execv(sys.argv[0], sys.argv)
