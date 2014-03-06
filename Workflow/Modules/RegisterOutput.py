'''
Created on Mar 6, 2014

@author: stephanep
'''
from ALDIRAC.Workflow.Modules.ModuleBase import ModuleBase
from DIRAC.Core.Utilities.ReturnValues import S_OK, S_ERROR
from ALDIRAC.SimuDBSystem.Client.SimuDBClient import SimuDBClient
from DIRAC import gLogger
import pickle
class RegisterOutput(ModuleBase):
    def __init__(self):
        super(RegisterOutput, self).__init__()
        self.log = gLogger.getSubLogger("RegisterOutput")
        
    def applicationSpecificInputs(self):
        """ Resolve the applciation specific inputs
        """
        if not self.jobName:
            return S_ERROR("Cannot find proper job name")
        return S_OK()
    
    def execute(self):
        """ Execute the stuff
        """
        if not self.workflowStatus['OK'] or not self.stepStatus['OK']:
            self.log.verbose('Workflow status = %s, step status = %s' % (self.workflowStatus['OK'], self.stepStatus['OK']))
            return S_OK('%s should not proceed as previous step did not end properly' % self.applicationName)
        
        result = self.resolveInputVariables()
        if not result['OK']:
            self.log.error("Failed to resolve input parameters:", result['Message'])
            return result
        try:
            res_dict = pickle.load(open(self.InputFile,"rb"))
        except Exception as error:
            self.log.error("Failed to load from pickle:", str(error))
            return S_ERROR("Failed loading from pickle")
        
        
        
        simu_db = SimuDBClient()
        res = simu_db.addResult(self.jobName, res_dict.dumps())
        if not res["OK"]:
            res = simu_db.setStatus("failed")
            if not res['OK']:#try again
                res = simu_db.setStatus("failed")
                if not res["OK"]:
                    self.log.error("Failed to set to failed")
                    return S_ERROR("Failed setting final status")
        return S_OK()