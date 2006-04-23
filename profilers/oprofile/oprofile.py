import shutil

class oprofile(profiler.profiler):
	version = 1

# http://prdownloads.sourceforge.net/oprofile/oprofile-0.9.1.tar.gz
	def setup(self, tarball = self.bindir + 'oprofile-0.9.1.tar.bz2'):
		self.tarball = unmap_potential_url(tarball, self.tmpdir)
		extract_tarball_to_dir(self.tarball, self.srcdir)
		os.chdir(self.srcdir)

		pwd = os.getcwd()
		system('./configure --with-kernel-support --prefix=' + pwd)
		system('make')
		system('make install')

		self.opreport = self.srcdir + 'pp/opcontrol'
		self.opcontrol = self.srcdir + 'utils/opcontrol'

		arch = get_arch()
		if (arch == 'i386'):
			self.setup_i386()
		else:
			raise UnknownError, 'Architecture %s not supported by oprofile wrapper' % arch


	def start(self):
		vmlinux = '--vmlinux=' + get_vmlinux()
		system(self.opcontrol + ' --shutdown')
		system('rm -rf /var/lib/oprofile/samples/current')
		system(''.join(self.opcontrol, vmlinux, self.args, '--start'))
		system(self.opcontrol + ' --reset')


	def stop(self):
		system(self.opcontrol + ' --dump')


	def report(self):
		reportfile = self.resultsdir + '/results/oprofile.txt'
		modules = ' -p ' + get_modules_dir()
		system(self.opreport + ' -l ' + modules + ' > ' + reportfile
		system(self.opcontrol + ' --shutdown')


	def setup_i386(self):
		self.args = '-e CPU_CLK_UNHALTED:100000'

