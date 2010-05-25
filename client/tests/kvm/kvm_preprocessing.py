import sys, os, time, commands, re, logging, signal, glob, threading, shutil
from autotest_lib.client.bin import test, utils
from autotest_lib.client.common_lib import error
import kvm_vm, kvm_utils, kvm_subprocess, ppm_utils
try:
    import PIL.Image
except ImportError:
    logging.warning('No python imaging library installed. PPM image '
                    'conversion to JPEG disabled. In order to enable it, '
                    'please install python-imaging or the equivalent for your '
                    'distro.')


_screendump_thread = None
_screendump_thread_termination_event = None


def preprocess_image(test, params):
    """
    Preprocess a single QEMU image according to the instructions in params.

    @param test: Autotest test object.
    @param params: A dict containing image preprocessing parameters.
    @note: Currently this function just creates an image if requested.
    """
    image_filename = kvm_vm.get_image_filename(params, test.bindir)

    create_image = False

    if params.get("force_create_image") == "yes":
        logging.debug("'force_create_image' specified; creating image...")
        create_image = True
    elif (params.get("create_image") == "yes" and not
          os.path.exists(image_filename)):
        logging.debug("Creating image...")
        create_image = True

    if create_image and not kvm_vm.create_image(params, test.bindir):
        raise error.TestError("Could not create image")


def preprocess_vm(test, params, env, name):
    """
    Preprocess a single VM object according to the instructions in params.
    Start the VM if requested and get a screendump.

    @param test: An Autotest test object.
    @param params: A dict containing VM preprocessing parameters.
    @param env: The environment (a dict-like object).
    @param name: The name of the VM object.
    """
    logging.debug("Preprocessing VM '%s'..." % name)
    vm = kvm_utils.env_get_vm(env, name)
    if vm:
        logging.debug("VM object found in environment")
    else:
        logging.debug("VM object does not exist; creating it")
        vm = kvm_vm.VM(name, params, test.bindir, env.get("address_cache"))
        kvm_utils.env_register_vm(env, name, vm)

    start_vm = False
    for_migration = False

    if params.get("start_vm_for_migration") == "yes":
        logging.debug("'start_vm_for_migration' specified; (re)starting VM "
                      "with -incoming option...")
        start_vm = True
        for_migration = True
    elif params.get("restart_vm") == "yes":
        logging.debug("'restart_vm' specified; (re)starting VM...")
        start_vm = True
    elif params.get("start_vm") == "yes":
        if not vm.is_alive():
            logging.debug("VM is not alive; starting it...")
            start_vm = True
        elif vm.make_qemu_command() != vm.make_qemu_command(name, params,
                                                            test.bindir):
            logging.debug("VM's qemu command differs from requested one; "
                          "restarting it...")
            start_vm = True

    if start_vm and not vm.create(name, params, test.bindir, for_migration):
        raise error.TestError("Could not start VM")

    scrdump_filename = os.path.join(test.debugdir, "pre_%s.ppm" % name)
    vm.send_monitor_cmd("screendump %s" % scrdump_filename)


def postprocess_image(test, params):
    """
    Postprocess a single QEMU image according to the instructions in params.
    Currently this function just removes an image if requested.

    @param test: An Autotest test object.
    @param params: A dict containing image postprocessing parameters.
    """
    if params.get("remove_image") == "yes":
        kvm_vm.remove_image(params, test.bindir)


def postprocess_vm(test, params, env, name):
    """
    Postprocess a single VM object according to the instructions in params.
    Kill the VM if requested and get a screendump.

    @param test: An Autotest test object.
    @param params: A dict containing VM postprocessing parameters.
    @param env: The environment (a dict-like object).
    @param name: The name of the VM object.
    """
    logging.debug("Postprocessing VM '%s'..." % name)
    vm = kvm_utils.env_get_vm(env, name)
    if vm:
        logging.debug("VM object found in environment")
    else:
        logging.debug("VM object does not exist in environment")
        return

    scrdump_filename = os.path.join(test.debugdir, "post_%s.ppm" % name)
    vm.send_monitor_cmd("screendump %s" % scrdump_filename)

    if params.get("kill_vm") == "yes":
        kill_vm_timeout = float(params.get("kill_vm_timeout", 0))
        if kill_vm_timeout:
            logging.debug("'kill_vm' specified; waiting for VM to shut down "
                          "before killing it...")
            kvm_utils.wait_for(vm.is_dead, kill_vm_timeout, 0, 1)
        else:
            logging.debug("'kill_vm' specified; killing VM...")
        vm.destroy(gracefully = params.get("kill_vm_gracefully") == "yes")


def process_command(test, params, env, command, command_timeout,
                    command_noncritical):
    """
    Pre- or post- custom commands to be executed before/after a test is run

    @param test: An Autotest test object.
    @param params: A dict containing all VM and image parameters.
    @param env: The environment (a dict-like object).
    @param command: Command to be run.
    @param command_timeout: Timeout for command execution.
    @param command_noncritical: If True test will not fail if command fails.
    """
    # Export environment vars
    for k in params:
        os.putenv("KVM_TEST_%s" % k, str(params[k]))
    # Execute commands
    try:
        utils.system("cd %s; %s" % (test.bindir, command))
    except error.CmdError, e:
        logging.warn("Custom processing command '%s' failed, output is: %s",
                     command, str(e))
        if not command_noncritical:
            raise error.TestError("Custom processing command failed: %s" %
                                  str(e))


def process(test, params, env, image_func, vm_func):
    """
    Pre- or post-process VMs and images according to the instructions in params.
    Call image_func for each image listed in params and vm_func for each VM.

    @param test: An Autotest test object.
    @param params: A dict containing all VM and image parameters.
    @param env: The environment (a dict-like object).
    @param image_func: A function to call for each image.
    @param vm_func: A function to call for each VM.
    """
    # Get list of VMs specified for this test
    vm_names = kvm_utils.get_sub_dict_names(params, "vms")
    for vm_name in vm_names:
        vm_params = kvm_utils.get_sub_dict(params, vm_name)
        # Get list of images specified for this VM
        image_names = kvm_utils.get_sub_dict_names(vm_params, "images")
        for image_name in image_names:
            image_params = kvm_utils.get_sub_dict(vm_params, image_name)
            # Call image_func for each image
            image_func(test, image_params)
        # Call vm_func for each vm
        vm_func(test, vm_params, env, vm_name)


def preprocess(test, params, env):
    """
    Preprocess all VMs and images according to the instructions in params.
    Also, collect some host information, such as the KVM version.

    @param test: An Autotest test object.
    @param params: A dict containing all VM and image parameters.
    @param env: The environment (a dict-like object).
    """
    # Start tcpdump if it isn't already running
    if "address_cache" not in env:
        env["address_cache"] = {}
    if "tcpdump" in env and not env["tcpdump"].is_alive():
        env["tcpdump"].close()
        del env["tcpdump"]
    if "tcpdump" not in env and params.get("run_tcpdump", "yes") == "yes":
        command = "/usr/sbin/tcpdump -npvi any 'dst port 68'"
        logging.debug("Starting tcpdump (%s)...", command)
        env["tcpdump"] = kvm_subprocess.kvm_tail(
            command=command,
            output_func=_update_address_cache,
            output_params=(env["address_cache"],))
        if kvm_utils.wait_for(lambda: not env["tcpdump"].is_alive(),
                              0.1, 0.1, 1.0):
            logging.warn("Could not start tcpdump")
            logging.warn("Status: %s" % env["tcpdump"].get_status())
            logging.warn("Output:" + kvm_utils.format_str_for_message(
                env["tcpdump"].get_output()))

    # Destroy and remove VMs that are no longer needed in the environment
    requested_vms = kvm_utils.get_sub_dict_names(params, "vms")
    for key in env.keys():
        vm = env[key]
        if not kvm_utils.is_vm(vm):
            continue
        if not vm.name in requested_vms:
            logging.debug("VM '%s' found in environment but not required for "
                          "test; removing it..." % vm.name)
            vm.destroy()
            del env[key]

    # Get the KVM kernel module version and write it as a keyval
    logging.debug("Fetching KVM module version...")
    if os.path.exists("/dev/kvm"):
        try:
            kvm_version = open("/sys/module/kvm/version").read().strip()
        except:
            kvm_version = os.uname()[2]
    else:
        kvm_version = "Unknown"
        logging.debug("KVM module not loaded")
    logging.debug("KVM version: %s" % kvm_version)
    test.write_test_keyval({"kvm_version": kvm_version})

    # Get the KVM userspace version and write it as a keyval
    logging.debug("Fetching KVM userspace version...")
    qemu_path = kvm_utils.get_path(test.bindir, params.get("qemu_binary",
                                                           "qemu"))
    version_line = commands.getoutput("%s -help | head -n 1" % qemu_path)
    matches = re.findall("[Vv]ersion .*?,", version_line)
    if matches:
        kvm_userspace_version = " ".join(matches[0].split()[1:]).strip(",")
    else:
        kvm_userspace_version = "Unknown"
        logging.debug("Could not fetch KVM userspace version")
    logging.debug("KVM userspace version: %s" % kvm_userspace_version)
    test.write_test_keyval({"kvm_userspace_version": kvm_userspace_version})

    # Execute any pre_commands
    if params.get("pre_command"):
        process_command(test, params, env, params.get("pre_command"),
                        int(params.get("pre_command_timeout", "600")),
                        params.get("pre_command_noncritical") == "yes")

    # Preprocess all VMs and images
    process(test, params, env, preprocess_image, preprocess_vm)

    # Start the screendump thread
    if params.get("take_regular_screendumps") == "yes":
        logging.debug("Starting screendump thread")
        global _screendump_thread, _screendump_thread_termination_event
        _screendump_thread_termination_event = threading.Event()
        _screendump_thread = threading.Thread(target=_take_screendumps,
                                              args=(test, params, env))
        _screendump_thread.start()


def postprocess(test, params, env):
    """
    Postprocess all VMs and images according to the instructions in params.

    @param test: An Autotest test object.
    @param params: Dict containing all VM and image parameters.
    @param env: The environment (a dict-like object).
    """
    # Postprocess all VMs and images
    process(test, params, env, postprocess_image, postprocess_vm)

    # Terminate the screendump thread
    global _screendump_thread, _screendump_thread_termination_event
    if _screendump_thread:
        logging.debug("Terminating screendump thread...")
        _screendump_thread_termination_event.set()
        _screendump_thread.join(10)

    # Warn about corrupt PPM files
    for f in glob.glob(os.path.join(test.debugdir, "*.ppm")):
        if not ppm_utils.image_verify_ppm_file(f):
            logging.warn("Found corrupt PPM file: %s", f)

    # Should we convert PPM files to PNG format?
    if params.get("convert_ppm_files_to_png") == "yes":
        logging.debug("'convert_ppm_files_to_png' specified; converting PPM "
                      "files to PNG format...")
        try:
            for f in glob.glob(os.path.join(test.debugdir, "*.ppm")):
                if ppm_utils.image_verify_ppm_file(f):
                    new_path = f.replace(".ppm", ".png")
                    image = PIL.Image.open(f)
                    image.save(new_path, format='PNG')
        except NameError:
            pass

    # Should we keep the PPM files?
    if params.get("keep_ppm_files") != "yes":
        logging.debug("'keep_ppm_files' not specified; removing all PPM files "
                      "from debug dir...")
        for f in glob.glob(os.path.join(test.debugdir, '*.ppm')):
            os.unlink(f)

    # Should we keep the screendump dirs?
    if params.get("keep_screendumps") != "yes":
        logging.debug("'keep_screendumps' not specified; removing screendump "
                      "dirs...")
        for d in glob.glob(os.path.join(test.debugdir, "screendumps_*")):
            if os.path.isdir(d) and not os.path.islink(d):
                shutil.rmtree(d, ignore_errors=True)

    # Kill all unresponsive VMs
    if params.get("kill_unresponsive_vms") == "yes":
        logging.debug("'kill_unresponsive_vms' specified; killing all VMs "
                      "that fail to respond to a remote login request...")
        for vm in kvm_utils.env_get_all_vms(env):
            if vm.is_alive():
                session = vm.remote_login()
                if session:
                    session.close()
                else:
                    vm.destroy(gracefully=False)

    # Kill the tailing threads of all VMs
    for vm in kvm_utils.env_get_all_vms(env):
        vm.kill_tail_thread()

    # Terminate tcpdump if no VMs are alive
    living_vms = [vm for vm in kvm_utils.env_get_all_vms(env) if vm.is_alive()]
    if not living_vms and "tcpdump" in env:
        env["tcpdump"].close()
        del env["tcpdump"]

    # Execute any post_commands
    if params.get("post_command"):
        process_command(test, params, env, params.get("post_command"),
                        int(params.get("post_command_timeout", "600")),
                        params.get("post_command_noncritical") == "yes")

    # Abort on error?
    if params.get("abort") == "yes":
        exc_string = str(sys.exc_info()[1])
        logging.info("Aborting job (%s)", exc_string)
        for vm in kvm_utils.env_get_all_vms(env):
            if not vm.is_dead():
                logging.info("VM '%s' is alive.", vm.name)
                logging.info("The monitor unix socket of '%s' is: %s",
                             vm.name, vm.monitor_file_name)
                logging.info("The command line used to start '%s' was:\n%s",
                             vm.name, vm.make_qemu_command())
        raise error.JobError("Abort requested (%s)" % exc_string)


def postprocess_on_error(test, params, env):
    """
    Perform postprocessing operations required only if the test failed.

    @param test: An Autotest test object.
    @param params: A dict containing all VM and image parameters.
    @param env: The environment (a dict-like object).
    """
    params.update(kvm_utils.get_sub_dict(params, "on_error"))


def _update_address_cache(address_cache, line):
    if re.search("Your.IP", line, re.IGNORECASE):
        matches = re.findall(r"\d*\.\d*\.\d*\.\d*", line)
        if matches:
            address_cache["last_seen"] = matches[0]
    if re.search("Client.Ethernet.Address", line, re.IGNORECASE):
        matches = re.findall(r"\w*:\w*:\w*:\w*:\w*:\w*", line)
        if matches and address_cache.get("last_seen"):
            mac_address = matches[0].lower()
            logging.debug("(address cache) Adding cache entry: %s ---> %s",
                          mac_address, address_cache.get("last_seen"))
            address_cache[mac_address] = address_cache.get("last_seen")
            del address_cache["last_seen"]


def _take_screendumps(test, params, env):
    global _screendump_thread_termination_event
    temp_dir = test.debugdir
    if params.get("screendump_temp_dir"):
        temp_dir = kvm_utils.get_path(test.bindir,
                                      params.get("screendump_temp_dir"))
        try:
            os.makedirs(temp_dir)
        except OSError:
            pass
    temp_filename = os.path.join(temp_dir, "scrdump-%s.ppm" %
                                 kvm_utils.generate_random_string(6))
    delay = float(params.get("screendump_delay", 5))
    quality = int(params.get("screendump_quality", 30))
    if params.get("screendump_verbose") == 'yes':
        screendump_verbose = True
    else:
        screendump_verbose = False

    cache = {}

    while True:
        for vm in kvm_utils.env_get_all_vms(env):
            if vm.is_dead():
                continue
            if screendump_verbose:
                vm.send_monitor_cmd("screendump %s" % temp_filename)
            else:
                vm.send_monitor_cmd("screendump %s" % temp_filename,
                                    verbose=False)
            if not os.path.exists(temp_filename):
                logging.warn("VM '%s' failed to produce a screendump", vm.name)
                continue
            if not ppm_utils.image_verify_ppm_file(temp_filename):
                logging.warn("VM '%s' produced an invalid screendump", vm.name)
                os.unlink(temp_filename)
                continue
            screendump_dir = os.path.join(test.debugdir,
                                          "screendumps_%s" % vm.name)
            try:
                os.makedirs(screendump_dir)
            except OSError:
                pass
            screendump_filename = os.path.join(screendump_dir,
                    "%s_%s.jpg" % (vm.name,
                                   time.strftime("%Y-%m-%d_%H-%M-%S")))
            hash = utils.hash_file(temp_filename)
            if hash in cache:
                try:
                    os.link(cache[hash], screendump_filename)
                except OSError:
                    pass
            else:
                try:
                    image = PIL.Image.open(temp_filename)
                    image.save(screendump_filename, format="JPEG", quality=quality)
                    cache[hash] = screendump_filename
                except NameError:
                    pass
            os.unlink(temp_filename)
        if _screendump_thread_termination_event.isSet():
            break
        _screendump_thread_termination_event.wait(delay)
