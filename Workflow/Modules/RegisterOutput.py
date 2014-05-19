'''
Created on Mar 6, 2014

@author: stephanep
'''
from ALDIRAC.Workflow.Modules.ModuleBase import ModuleBase
from DIRAC.Core.Utilities.ReturnValues import S_OK, S_ERROR
from ALDIRAC.SimuDBSystem.Client.SimuDBClient import SimuDBClient
from DIRAC import gLogger
#import pickle
import os
class RegisterOutput(ModuleBase):
    def __init__(self):
        super(RegisterOutput, self).__init__()
        self.log = gLogger.getSubLogger("RegisterOutput")
        self.simudb = SimuDBClient()
        self.debug = False
        
    def applicationSpecificInputs(self):
        """ Resolve the application specific inputs
        """
        if not self.jobName:
            return S_ERROR("Cannot find proper job name")
        if not self.InputFile:
            return S_ERROR("Missing file to send back")
        if self.debug:
            self.log.info("Using test mode: basically, do nothing here.")
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
#         try:
#             res_dict = pickle.load(open(self.InputFile,"rb"))
#         except Exception as error:
#             self.log.error("Failed to load from pickle:", str(error))
#             res = self.simudb.setStatus(self.jobName, "failed", "Can't load from pickled file")
#             if not res['OK']:
#                 self.log.error("Failed to set status to failed:", res["Message"])
#             return S_ERROR("Failed loading from pickle")
        os.rename(self.InputFile[0], self.jobName+".pkl")
        if self.debug:
            self.log.info("Would have attempted to send the results back")
            return S_OK()
        res = self.simudb.sendResult(self.jobName+".pkl")
        if not res["OK"]:
            self.log.error("Failed to send the results:", res["Message"])
            res = self.simudb.setStatus(self.jobName, "failed", "Cannot send results: %s" % res["Message"])
            if not res['OK']:
                self.log.error("Failed to set status to failed:", res["Message"])
                res = self.simudb.setStatus(self.jobName, "failed", "%s" % res["Message"])
                if not res["OK"]:#try again
                    self.log.error("Failed to set status to failed:", res["Message"])
                    return S_ERROR("Failed setting final failed status")
                
        return S_OK()
