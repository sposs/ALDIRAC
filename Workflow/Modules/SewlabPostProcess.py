'''
Created on Feb 21, 2014

@author: stephanep
'''
from ALDIRAC.Workflow.Modules.ModuleBase import ModuleBase
from DIRAC                               import S_OK, S_ERROR, gLogger
from DIRAC.Core.Utilities.Subprocess     import shellCall
import os
from ALDIRAC.SimuDBSystem.Client.SimuDBClient import SimuDBClient
from DIRAC.Core.Utilities.Os import which


class SewlabPostProcess(ModuleBase):
    '''
    Convert the sewlab output to python pickle
    '''
    def __init__(self):
        super(SewlabPostProcess, self).__init__()
        self.log = gLogger.getSubLogger("SewlabPostProcess")
        self.simudb = SimuDBClient()
        self.debug = False
        self.taskname = ""
        
    def applicationSpecificInputs(self):
        """ Check if the output file is defined
        """
        if not self.OutputFile:
            self.OutputFile = "output_%s.pkl" % self.jobID
        if not self.InputFile:
            return S_ERROR("Missing input file")
        
        if not self.taskname:
            self.taskname = self.workflow_commons.get("TaskName", self.jobName)
    
        if self.debug:
            self.log.info("Using debug mode: no communication with SimuDB")
        return S_OK()

    def runIt(self):
        """ Run the thing
        """
        self.result = S_OK()
        if not self.applicationLog:
            self.result = S_ERROR( 'No Log file provided' )
        if not self.result['OK']:
            self.log.error("Failed to resolve input parameters:", self.result["Message"])
            return self.result

        if not self.workflowStatus['OK'] or not self.stepStatus['OK']:
            self.log.verbose('Workflow status = %s, step status = %s' % (self.workflowStatus['OK'],
                                                                         self.stepStatus['OK']))
            return S_OK('%s should not proceed as previous step did not end properly' % self.applicationName)
        
        bin_name = self.ops.getValue("SewLab/ConverterName", "sewlabwrapper_convert")
        sewlabconv_path = self.ops.getValue("SharedArea", "")
        if not sewlabconv_path:
            self.log.error("Path to the converter not defined")
            return S_ERROR("Failed to find converter")
        fin_path = os.path.join(sewlabconv_path, bin_name)
        if not os.path.exists(fin_path):
            fin_path = which(bin_name)
            if not fin_path:
                self.log.error("Coudn't find the converter")
                return S_ERROR("Failed to find converter")
        
        self.log.info("Found converter at", fin_path)
            
        scriptName = '%s_Run_%s.sh' % (self.applicationName, self.STEP_NUMBER)
        with open(scriptName, "w") as script:
            script.write("#!/bin/bash\n")
            script.write("declare -x LD_LIBRARY_PATH=/lib/x86_64-linux-gnu/:$LD_LIBRARY_PATH\n")
            comm = "%s --input %s --output %s\n" % (fin_path, self.InputFile[0], self.OutputFile)
            gLogger.info("Running ", comm)
            script.write(comm)
            script.write("exit $?\n")
        os.chmod(scriptName, 0755)
        
        comm = 'sh -c "./%s"' % (scriptName)
        self.setApplicationStatus('%s step %s' % (self.applicationName, self.STEP_NUMBER))
        self.stdError = ''
        result = shellCall(0, comm, callbackFunction = self.redirectLogOutput, bufferLimit = 20971520)
        if not result['OK']:
            self.log.error("Application failed :", result["Message"])
            if not self.debug:
                res = self.simudb.setStatus(self.taskname, "failed", "Error while executing converter" )
                if not res["OK"]:
                    self.log.error("Failed updating task status:", res["Message"])
            else:
                self.log.info("Would have reported task as failed")
            return S_ERROR('Problem Executing Application')
        
        if not os.path.exists(self.OutputFile):
            if self.debug:
                res = self.simudb.setStatus(self.taskname, "failed", "Missing converter output")
                if not res["OK"]:
                    self.log.error("Failed updating task status:", res["Message"])
            else:
                self.log.info("Would have reported task as failed")
            return S_ERROR("Output file not produced")
        else:
            self.log.info("Successfully produced expected output:", self.OutputFile)
        return S_OK()

#################################################################    