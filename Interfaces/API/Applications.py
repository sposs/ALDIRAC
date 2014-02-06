'''
Created on Feb 6, 2014

@author: stephanep
'''
from ALDIRAC.Interfaces.API.Application import Application
from DIRAC.Core.Workflow.Parameter                    import Parameter

from DIRAC import S_OK, S_ERROR
import types, os

class SewLab(Application):
    '''
    classdocs
    '''
    def __init__(self):
        '''
        Constructor
        '''
        self.Parameter = 0
        super(SewLab, self).__init__()
        self._modulename = "SewLab"
        self.appname = self._modulename
        self._moduledescription = 'The sewlab wrapper'
        
    def setParameter(self, param):
        """ Set a parameter
        """
        self._checkArgs( {'param' : types.IntType })

        self.Parameter = param
        return S_OK()
    
    def _applicationModule(self):
        m1 = self._createModuleDefinition()
        m1.addParameter(Parameter("parameter",      "", "int", "", "", False, False, "Application parameter"))
        return m1
    
    def _applicationModuleValues(self, moduleinstance):
        moduleinstance.setValue("parameter",    self.Parameter)
    
    def _userjobmodules(self, stepdefinition):
        res1 = self._setApplicationModuleAndParameters(stepdefinition)
        res2 = self._setUserJobFinalization(stepdefinition)
        if not res1["OK"] or not res2["OK"] :
            return S_ERROR('userjobmodules failed')
        return S_OK()
    
    def _addParametersToStep(self, stepdefinition):
        res = self._addBaseParameters(stepdefinition)
        if not res["OK"]:
            return S_ERROR("Failed to set base parameters")
        return S_OK()
    
    def _setStepParametersValues(self, instance):
        """ Nothing to do here
        """
        #self._setBaseStepParametersValues(instance)
        #for depn, depv in self.dependencies.items():
        #    self._job._addSoftware(depn, depv)
        return S_OK()
    
    def _checkConsistency(self):
        """ Checks that script and dependencies are set.
        """
        if not self.Parameter:
            return S_ERROR("parameter not defined")
        
        return S_OK()  
      
      
        