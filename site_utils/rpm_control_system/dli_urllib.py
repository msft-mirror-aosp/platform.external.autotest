from six.moves import urllib

import common

from autotest_lib.site_utils.rpm_control_system import dli


class Powerswitch(dli.powerswitch):
    """
    This class will utilize urllib instead of pycurl to get the web page info.
    """


    def geturl(self,url='index.htm') :
        self.contents=''
        path = 'http://%s:%s@%s:80/%s' % (self.userid,self.password,
                                          self.hostname,url)
        web_file = urllib.request.urlopen(path)
        if web_file.getcode() != 200:
            return None
        self.contents = web_file.read()
        return self.contents
