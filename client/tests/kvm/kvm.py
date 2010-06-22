import sys, os, time, logging, imp
from autotest_lib.client.bin import test
from autotest_lib.client.common_lib import error
import kvm_utils, kvm_preprocessing


class kvm(test.test):
    """
    Suite of KVM virtualization functional tests.
    Contains tests for testing both KVM kernel code and userspace code.

    @copyright: Red Hat 2008-2009
    @author: Uri Lublin (uril@redhat.com)
    @author: Dror Russo (drusso@redhat.com)
    @author: Michael Goldish (mgoldish@redhat.com)
    @author: David Huff (dhuff@redhat.com)
    @author: Alexey Eromenko (aeromenk@redhat.com)
    @author: Mike Burns (mburns@redhat.com)

    @see: http://www.linux-kvm.org/page/KVM-Autotest/Client_Install
            (Online doc - Getting started with KVM testing)
    """
    version = 1

    def run_once(self, params):
        # Report the parameters we've received and write them as keyvals
        logging.debug("Test parameters:")
        keys = params.keys()
        keys.sort()
        for key in keys:
            logging.debug("    %s = %s", key, params[key])
            self.write_test_keyval({key: params[key]})

        # Set the log file dir for the logging mechanism used by kvm_subprocess
        # (this must be done before unpickling env)
        kvm_utils.set_log_file_dir(self.debugdir)

        # Open the environment file
        logging.info("Unpickling env. You may see some harmless error "
                     "messages.")
        env_filename = os.path.join(self.bindir, params.get("env", "env"))
        env = kvm_utils.load_env(env_filename, {})
        logging.debug("Contents of environment: %s", env)

        test_passed = False

        try:
            try:
                try:
                    # Get the test routine corresponding to the specified
                    # test type
                    t_type = params.get("type")
                    # Verify if we have the correspondent source file for it
                    subtest_dir = os.path.join(self.bindir, "tests")
                    module_path = os.path.join(subtest_dir, "%s.py" % t_type)
                    if not os.path.isfile(module_path):
                        raise error.TestError("No %s.py test file found" %
                                              t_type)
                    # Load the test module
                    f, p, d = imp.find_module(t_type, [subtest_dir])
                    test_module = imp.load_module(t_type, f, p, d)
                    f.close()

                    # Preprocess
                    try:
                        kvm_preprocessing.preprocess(self, params, env)
                    finally:
                        kvm_utils.dump_env(env, env_filename)
                    # Run the test function
                    run_func = getattr(test_module, "run_%s" % t_type)
                    try:
                        run_func(self, params, env)
                    finally:
                        kvm_utils.dump_env(env, env_filename)
                    test_passed = True

                except Exception, e:
                    logging.error("Test failed: %s", e)
                    try:
                        kvm_preprocessing.postprocess_on_error(
                            self, params, env)
                    finally:
                        kvm_utils.dump_env(env, env_filename)
                    raise

            finally:
                # Postprocess
                try:
                    try:
                        kvm_preprocessing.postprocess(self, params, env)
                    except Exception, e:
                        if test_passed:
                            raise
                        logging.error("Exception raised during "
                                      "postprocessing: %s", e)
                finally:
                    kvm_utils.dump_env(env, env_filename)
                    logging.debug("Contents of environment: %s", env)

        except Exception, e:
            if params.get("abort_on_error") != "yes":
                raise
            # Abort on error
            logging.info("Aborting job (%s)", e)
            for vm in kvm_utils.env_get_all_vms(env):
                if vm.is_dead():
                    continue
                logging.info("VM '%s' is alive.", vm.name)
                for m in vm.monitors:
                    logging.info("'%s' has a %s monitor unix socket at: %s",
                                 vm.name, m.protocol, m.filename)
                logging.info("The command line used to start '%s' was:\n%s",
                             vm.name, vm.make_qemu_command())
            raise error.JobError("Abort requested (%s)" % e)
