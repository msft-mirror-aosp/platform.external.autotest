import test, os_dep
from autotest_utils import *


def convert_size(size):
	if size.endswith('G') or size.endswith('g'):
		return int(size[:-1]) * 2**30
	return int(size) * 2**20


class bonnie(test.test):
	version = 1

	# http://www.coker.com.au/bonnie++/bonnie++-1.03a.tgz
	def setup(self, tarball = 'bonnie++-1.03a.tgz'):
		tarball = unmap_url(self.bindir, tarball, self.tmpdir)
		extract_tarball_to_dir(tarball, self.srcdir)
		os.chdir(self.srcdir)

		os_dep.command('g++')
		system('./configure')
		system('make')

	def execute(self, testdir = None, iterations = 1, extra_args = '', user = 'root'):
		if not testdir:
			testdir = self.tmpdir

		args = '-d ' + testdir + ' -u ' + user + ' ' + extra_args

		profilers = self.job.profilers
		if not profilers.only():
			for i in range(iterations):
				system(self.srcdir + '/bonnie++ ' + args)

		# Do a profiling run if necessary
		if profilers.present():
			profilers.start(self)
			system(self.srcdir + '/bonnie++ ' + args)
			profilers.stop(self)
			profilers.report(self)

		self.__format_results(open(self.debugdir + '/stdout').read())

	def __format_results(self, results):
		strip_plus = lambda s: re.sub(r"^\++$", "0", s)
		out = open(self.resultsdir + '/keyval', 'w')
		for line in results.split('\n'):
			if len([c for c in line if c == ',']) != 26:
				continue
			fields = tuple(line.split(','))
			fields = [strip_plus(f) for f in fields]
		fields = tuple([convert_size(fields[1])] + fields[2:])
		print >> out, """size=%s
seqout_perchr_ksec=%s
seqout_perchr_pctcp=%s
seqout_perblk_ksec=%s
seqout_perblk_pctcp=%s
seqout_rewrite_ksec=%s
seqout_rewrite_pctcp=%s
seqin_perchr_ksec=%s
seqin_perchr_pctcp=%s
seqin_perblk_ksec=%s
seqin_perblk_pctcp=%s
rand_ksec=%s
rand_pctcp=%s
files=%s
seqcreate_create_ksec=%s
seqcreate_create_pctcp=%s
seqcreate_read_ksec=%s
seqcreate_read_pctcp=%s
seqcreate_delete_ksec=%s
seqcreate_delete_pctcp=%s
randreate_create_ksec=%s
randcreate_create_pctcp=%s
randcreate_read_ksec=%s
randcreate_read_pctcp=%s
randcreate_delete_ksec=%s
randcreate_delete_pctcp=%s
""" % fields
		out.close()
