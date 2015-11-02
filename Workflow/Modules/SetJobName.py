'''
Created on Aug 21, 2014

@author: stephanep
'''
from ALDIRAC.Workflow.Modules.ModuleBase import ModuleBase
from DIRAC import S_ERROR, S_OK, gLogger


class SetJobName(ModuleBase):

    def __init__(self):
        '''
        Constructor
        '''
        super(SetJobName, self).__init__()
        self.jobname = ""
        self.log = gLogger.getSubLogger("SetJobName")
        
    def applicationSpecificInputs(self):
        if not self.jobname:
            return S_ERROR("new job name undefined")
        return S_OK()
    
    def execute(self):
        """
        Set the job name given the input value.
        """
        self.resolveInputVariables()
        self.log.info("Setting new job name to", self.jobname)
        self.workflow_commons['TaskName'] = self.jobname
        self.workflowStatus = S_OK()
        return S_OK()
