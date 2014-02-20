'''
Created on Feb 20, 2014

@author: stephanep
'''
import unittest


class Test(unittest.TestCase):


    def setUp(self):
        pass


    def tearDown(self):
        pass


    def testUtils(self):
        from ALDIRAC.Core.Utilities.Sewlabparams import SewLabParams
        pp = SewLabParams()
        res = pp.set_param("something", 12)
        print res
