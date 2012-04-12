import platform
import sys

import stoneridge

class StoneRidgeUploader(object):
    def __init__(self):
        pass

    def run(self):
        data = {'test_machine':{'name':platform.node(),
                                'os':self._get_os(),
                                'osversion':self._get_os_ver(),
                                'platform':platform.machine()},
                'test_build':{'name':'Firefox',
                              'version':'<fx version:14.0a1>',
                              'revision':'<hg revision:785345035a3b>',
                              'branch':'',
                              'id':'<buildid:20120228122102>'},
                'testrun':{'date':int(time.time()), # time tests occurred
                           'suite':'<suite name:Talos tp5r>',
                           'options':'<dict of test options -> values>',
                           'results':{}, # test name -> list of times
                           'results_aux':{}} # like results, but not random info we may want to keep around
               }
        results = data['testrun']['results']
        for o in self.outfiles:
            with file(o) as f:
                run_data = json.load(f)
            for name, res in run_data.iteritems():
                results[name] = [res['end'] - res['start']]
        sys.stderr.write('Uploading results is not yet implemented\n')

@stoneridge.main
def main():
    uploader = StoneRidgeUploader()
    uploader.run()
