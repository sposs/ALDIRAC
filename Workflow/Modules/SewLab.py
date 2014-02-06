'''
Created on Feb 6, 2014

@author: stephanep
'''
from ALDIRAC.Workflow.Modules.ModuleBase import ModuleBase
from DIRAC import S_OK, S_ERROR, gLogger

class SewLab(ModuleBase):
    def __init__(self):
        super(SewLab, self).__init__()
        ModuleBase.__init__(self)
        self.log = gLogger.getSubLogger("SewLab")
        self.InputFile = []
        self.SteeringFile = ''
        
    def applicationSpecificInputs(self):
        """ Resolve the application specific inputs
        """
        if not self.param:
            return S_ERROR("Missing SewLab parameter")
        return S_OK()
    
    def runIt(self):
        """ Now do something
        """
        
        self.result = S_OK()
        if not self.applicationLog:
            self.result = S_ERROR( 'No Log file provided' )
        if not self.result['OK']:
            self.log.error("Failed to resolve input parameters:", self.result["Message"])
            return self.result
        
        if not self.workflowStatus['OK'] or not self.stepStatus['OK']:
            self.log.verbose('Workflow status = %s, step status = %s' % (self.workflowStatus['OK'], self.stepStatus['OK']))
            return S_OK('%s should not proceed as previous step did not end properly' % self.applicationName)
        
        
        self.log.info("The Sewlab parameter is %s" % self.parameter)
        
        
        return S_OK()