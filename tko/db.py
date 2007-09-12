import sqlite, re, os

class db:
	def __init__(self):
		if not os.path.exists('tko_db'):
			os.system('sqlite tko_db < create_db')
		self.con = sqlite.connect('tko_db')
		self.cur = self.con.cursor()


	def select(self, fields, table, where_dict):
		"""\
			select fields from table where {dictionary}
		"""
		keys = [field + '=%s' for field in where_dict.keys()]
		values = [where_dict[field] for field in where_dict.keys()]

		where = 'and'.join(keys)
		cmd = 'select %s from %s where %s' % (fields, table, where)
		print cmd
		print values
		self.cur.execute(cmd, values)
		return self.cur.fetchall()


	def insert(self, table, data):
		"""\
			'insert into table (keys) values (%s ... %s)', values

			data:
				dictionary of fields and data
		"""
		fields = data.keys()
		refs = ['%s' for field in fields]
		values = [data[field] for field in fields]
		cmd = 'insert into %s (%s) values (%s)' % \
				(table, ','.join(fields), ','.join(refs))
		print cmd
		print values
		self.cur.execute(cmd, values)
		self.con.commit()


	def insert_job(self, tag, job):
		self.insert('jobs', {'tag':tag, 'machine':'UNKNOWN'})
		job.index = self.find_job(tag)
		for test in job.tests:
			self.insert_test(job, test)


	def insert_test(self, job, test):
		kver = self.insert_kernel_version(test.kernel)
		data = {'job_idx':job.index, 'test':test.testname,
			'subdir':test.dir, 
			'status':test.status, 'reason':test.reason}
		self.insert('tests', data)


	def lookup_kernel(self, kernel):
		rows = self.select('kernel_idx', 'kernels', 
				{'kernel_hash':kernel.kernel_hash})
		if rows:
			return rows[0][0]
		else:
			return None


	def insert_kernel_version(self, kernel):
		kver = self.lookup_kernel(kernel)
		if kver:
			return kver
		self.insert('kernels', {'base':kernel.base,
					  'kernel_hash':kernel.kernel_hash,
					  'printable':kernel.base})
		# WARNING - incorrectly shoving base into printable here.
		kver = self.lookup_kernel(kernel)
		for patch in kernel.patches:
			self.insert_patch(kver, patch)
		return kver


	def insert_patch(self, kver, patch):
		print patch.reference
		name = os.path.basename(patch.reference)[:80]
		self.insert('patches', {'kernel_idx': kver, 
					'name':name,
					'url':patch.reference, 
					'hash':patch.hash})


	def find_job(self, tag):
		rows = self.select('job_idx', 'jobs', {'tag': tag})
		if rows:
			return rows[0][0]
		else:
			return None
