# Lint as: python2, python3
# Copyright 2022 The ChromiumOS Authors
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.
#
# Expects to be run in an environment with sudo and no interactive password
# prompt, such as within the Chromium OS development chroot.
"""Host class for GSC devboard connected host."""

import contextlib
import logging
import os
import time

try:
    import docker
except ImportError:
    logging.info("Docker API is not installed in this environment")

from autotest_lib.server.hosts import remote

# Create this file in the chroot home directory
# containing the image to use in place of the default.
SERVICE_IMAGE_OVERRIDE = "gsc_dev_board_override"

# Create this file in the chroot home directory
# containing the image token file to enable image pull.
# gcloud auth print-access-token > /chroot/home/${USER}/gsc_dev_board_token
SERVICE_IMAGE_TOKEN_FILE = "gsc_dev_board_token"

SERVICE_IMAGE_DEFAULT = "gcr.io/satlab-images/gsc_dev_board:release"

SERVICE_START_TIMEOUT = 5

SATLAB_DOCKER_HOST = 'tcp://192.168.231.1:2375'
LOCAL_DOCKER_HOST = 'tcp://127.0.0.1:2375'
DEFAULT_DOCKER_HOST = 'unix:///var/run/docker.sock'

DEFAULT_SERVICE_PORT = 39999

ULTRADEBUG = '18d1:0304'
TI50 = '18d1:504a'


class GSCDevboardHost(remote.RemoteHost):
    """
    A host that is physically connected to a GSC devboard.

    It could either be a SDK workstation (chroot) or a SatLab box.
    """

    def _initialize(self,
                    hostname,
                    service_debugger_serial=None,
                    service_ip=None,
                    service_port=DEFAULT_SERVICE_PORT,
                    service_gsc_serial=None,
                    *args,
                    **dargs):
        """Construct a GSCDevboardHost object.

        @hostname: Name of the devboard host, will be used in future to look up
                   the debugger serial, not currently used.
        @service_debugger_serial: debugger connected to devboard, defaults to
                                  the first one found on the container.
        @service_ip: devboard service ip, default is to start a new container.
        @service_port: devboard service port, defaults to 39999.
        """

        super(GSCDevboardHost, self)._initialize(hostname, *args, **dargs)

        # Use docker host from environment or by probing a list of candidates.
        self._client = None

        self._docker_container = None
        self._service_ip = service_ip
        self._service_port = service_port
        logging.info("Using service port %s", self._service_port)

        if service_ip is not None:
            return

        try:
            self._client = docker.from_env()
            logging.info("Created docker host from env")
        except NameError:
            raise NameError('Please install docker using '
                            '"autotest/files/utils/install_docker_chroot.sh"')
        except docker.errors.DockerException:
            docker_host = None
            candidate_hosts = [
                    SATLAB_DOCKER_HOST, DEFAULT_DOCKER_HOST, LOCAL_DOCKER_HOST
            ]
            for h in candidate_hosts:
                try:
                    c = docker.DockerClient(base_url=h, timeout=2)
                    c.close()
                    docker_host = h
                    break
                except docker.errors.DockerException:
                    pass
            if docker_host is not None:
                self._client = docker.DockerClient(base_url=docker_host,
                                                   timeout=300)
            else:
                raise ValueError('Invalid DOCKER_HOST, ensure dockerd is'
                                 ' running.')
            logging.info("Using docker host at %s", docker_host)

        self._satlab = False
        # GSCDevboardHost should only be created on Satlab or localhost, so
        # assume Satlab if a drone container is running.
        if len(self._client.containers.list(filters={'name': 'drone'})) > 0:
            logging.info("In Satlab")
            self._satlab = True

        image_override = os.path.join(os.path.expanduser('~'),
                                      SERVICE_IMAGE_OVERRIDE)
        logging.info('Checking docker image override at %s', image_override)
        if os.path.exists(image_override):
            logging.info('Using docker image override')
            with open(image_override) as f:
                self._docker_image = f.readline().strip()
        else:
            self._docker_image = SERVICE_IMAGE_DEFAULT

        #TODO(b/257333832): Migrate to CFT to manage image on Satlab.
        token_file = os.path.join(os.path.expanduser('~'),
                                  SERVICE_IMAGE_TOKEN_FILE)
        if not self._satlab and os.path.isfile(token_file):
            try:
                with open(token_file) as f:
                    token = f.readline().strip()

                    logging.info('Pulling image %s', self._docker_image)
                    self._client.login('oauth2accesstoken', token,
                                       registry='https://gcr.io')
                    self._client.images.pull(self._docker_image)
            except docker.errors.NotFound:
                logging.info('Image not found in registry: %s, assuming local.',
                             self._docker_image)
                pass
            except docker.errors.APIError as e:
                logging.info('Failed to pull %s: %s, local image may be '
                             'outdated.', self._docker_image, e)

        self._docker_network = 'default_satlab' if self._satlab else 'host'

        self._service_debugger_serial = self._get_valid_serial(ULTRADEBUG,
            service_debugger_serial)
        self._service_gsc_serial = self._get_valid_serial(TI50,
            service_gsc_serial)

        if (self._service_debugger_serial == "" and
            self._service_gsc_serial == ""):
            raise ValueError('No valid debugger nor gsc found')

        logging.info("Using debugger %s", self._service_debugger_serial)
        logging.info("Using gsc %s", self._service_gsc_serial)

        self._docker_container_name = "gsc_dev_board_{}".format(
                self._service_debugger_serial)


    def _get_valid_serial(self, vidpid, serial):
        """
        Gets a valid serial of vidpid that satisfies the provided serial.

        serial is empty string -> device unused(empty string is returned).
        serial is None -> find unique device(else empty string is returned).
        serial is given -> must find device(else an error is raised).
        """
        if serial == "":
            return ""

        logging.info("Attempt to find serial given %s", serial)

        serials = self._list_usb_serials(vidpid)

        logging.info("Available %s serials: [%s]", vidpid, ', '.join(serials))

        if serial is None:
            return serials[0] if len(serials) == 1 else ""
        if serial in serials:
            return serial
        else:
            raise ValueError('No debuggers found matching %s' % serial)


    def _list_usb_serials(self, vidpid):
        """List all attached devices of vidpid."""

        cmd = ['lsusb', '-v', '-d', vidpid]
        try:
            output = self._client.containers.run(self._docker_image,
                                        cmd,
                                        remove=True,
                                        privileged=True,
                                        volumes=["/dev:/dev"])

            output = output.decode("utf-8").split('\n')
        except docker.errors.ContainerError:
            return []

        serials = [
                l.strip().split(' ')[-1] for l in output
                if l.strip()[:7] == 'iSerial'
        ]

        if not serials:
            logging.info('Could not find any serials for %s in: %s', vidpid,
                         output)

        return serials


    @contextlib.contextmanager
    def service_context(self):
        """Service context manager that provides the service endpoint."""
        self.start_service()
        try:
            yield "{}:{}".format(self.service_ip, self.service_port)
        finally:
            self.stop_service()

    def start_service(self):
        """Starts service if needed."""

        if self._docker_container is not None:
            return

        if self._service_ip:
            # Assume container was manually started if service_ip was set
            logging.info("Skip start_service due to set service_ip")
            return

        environment = {
                'DEVBOARDSVC_PORT': self._service_port,
                'DEBUGGER_SERIAL': self._service_debugger_serial,
                'GSC_SERIAL': self._service_gsc_serial
        }
        start_cmd = ['/opt/gscdevboard/start_devboardsvc.sh']

        # Stop any leftover containers
        try:
            c = self._client.containers.get(self._docker_container_name)
            c.remove(force=True)
        except docker.errors.APIError:
            pass

        self._docker_container = self._client.containers.run(self._docker_image,
                                    remove=True,
                                    privileged=True,
                                    name=self._docker_container_name,
                                    hostname=self._docker_container_name,
                                    network=self._docker_network,
                                    cap_add=["NET_ADMIN"],
                                    detach=True,
                                    volumes=["/dev:/dev"],
                                    environment=environment,
                                    command=start_cmd)

        deadline = time.time() + SERVICE_START_TIMEOUT
        while time.time() <= deadline:
            try:
                log = ''
                self._docker_container.reload()
                _, log = self._docker_container.exec_run(
                        ['bash', '-c', 'cat /var/log/devboardsvc_*.log'],
                        stream=True
                    )
                log = '\n'.join(l.decode("utf-8") for l in log)
                if 'Server started' in log:
                    logging.info('Using service ip %s', self.service_ip)
                    return
                if 'Server failed to start' in log:
                    break
            except docker.errors.APIError:
                break

        logging.debug('Last logs from service: %s', log)
        self.stop_service()
        raise RuntimeError('Server failed to start, check if port is already used.')


    def stop_service(self):
        """Stops service by killing the container."""
        if self._docker_container is None:
            return

        try:
            self._docker_container.kill()
        except docker.errors.NotFound:
            logging.debug('Service container already stopped.')

        self._docker_container = None

    @property
    def service_port(self):
        """Return service port (local to the container host)."""
        return self._service_port

    @property
    def service_ip(self):
        """Return service ip (local to the container host)."""
        if self._service_ip is not None:
            return self._service_ip

        if self._docker_network == 'host':
            return '127.0.0.1'
        else:
            if self._docker_container is None:
                return ''
            else:
                settings = self._docker_container.attrs['NetworkSettings']
                return settings['Networks'][self._docker_network]['IPAddress']
