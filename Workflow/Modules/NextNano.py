'''
Created on Aug 5, 2014

@author: stephanep
'''
import os

from ALDIRAC.Workflow.Modules.ModuleBase import ModuleBase
from DIRAC.Core.Utilities.ReturnValues import S_ERROR, S_OK
from DIRAC.Core.Utilities.Subprocess import shellCall
from DIRAC import gLogger
import shutil
import tarfile

def locateLicense():
    """
    Find where the license file is
    """
    if os.path.exists("license.txt"):
        return S_OK(os.path.join(os.getcwd(), "license.txt"))
    return S_ERROR("Failed to locate license")
    
def tar_output_directory(filename):
    """
    Tar the output directory
    """
    try:
        output = tarfile.open( filename, "w:gz" )
        output.add("output/")
        output.close()
    except Exception as error:
        return S_ERROR(error)
    return S_OK()

class NextNano(ModuleBase):

    def __init__(self):
        '''
        Constructor
        '''
        super(NextNano, self).__init__()
        self.log = gLogger.getSubLogger("Nextnano")
        self.license_path = ""
        self.application_path = ""
        self.applicationName = "nextnano"
        self.taskname = ""
    
    def applicationSpecificInputs(self):
        """
        This is done before the applicationSpecificMoveBefore, so the license file isn't here yet, 
        must be done when calling the application
        """
        res = self.locateBinary()
        if not res['OK']:
            self.log.error("Failed to find the nextnano binary:", res['Message'])
            return S_ERROR("Failed to find the nextnano binary")
        self.application_path = res['Value']
        
        if not self.taskname:
            self.taskname = self.workflow_commons.get("TaskName", self.jobName)
        return S_OK()

    def applicationSpecificMoveBefore(self):
        if os.path.exists(os.path.join(self.basedirectory, "license.txt")):
            shutil.copy(os.path.join(self.basedirectory, "license.txt"), "./license.txt")
        return S_OK()

    def runIt(self):
        self.result = S_OK()
        if not self.applicationLog:
            self.result = S_ERROR( 'No Log file provided' )
        if not self.result['OK']:
            self.log.error("Failed to resolve input parameters:", self.result["Message"])
            return self.result

        if not self.workflowStatus['OK'] or not self.stepStatus['OK']:
            self.log.verbose('Workflow status = %s, step status = %s' % (self.workflowStatus['OK'], self.stepStatus['OK']))
            return S_OK('%s should not proceed as previous step did not end properly' % self.applicationName)

        res = locateLicense()
        if not res['OK']:
            self.log.error("Failed to find the nextnano license")
            return S_ERROR("Failed to find the nextnano license")
        self.license_path = res['Value']

        self.SteeringFile = os.path.basename(self.SteeringFile)
        
        scriptName ='%s_%s_Run_%s.sh' % (self.applicationName, self.applicationVersion, self.STEP_NUMBER)
        with open(scriptName, "w") as script:
            script.write("#!/bin/bash\n")
            script.write("%s -l %s %s \n" % (self.application_path.replace(" ", "\ "), self.license_path, self.SteeringFile))
            script.write("exit $?\n")
        os.chmod(scriptName, 0755)
        
        comm = 'sh -c "./%s"' % (scriptName)
        self.setApplicationStatus('%s %s step %s' % (self.applicationName, self.applicationVersion, self.STEP_NUMBER))
        self.stdError = ''
        result = shellCall(0, comm, callbackFunction = self.redirectLogOutput, bufferLimit = 20971520)
        if not result['OK']:
            self.log.error("Application failed :", result["Message"])   
            return S_ERROR('Problem Executing Application')

        resultTuple = result['Value']
        
        status = resultTuple[0]
        self.log.info( "Status after %s execution is %s" %(os.path.basename(scriptName), str(status)) )
        failed = False
        if status != 0:
            self.log.info( "%s execution completed with non-zero status:" % os.path.basename(scriptName) )
            failed = True
        else:
            self.log.info( "%s execution completed successfully:" % os.path.basename(scriptName) )
        
        res = tar_output_directory(self.OutputFile)
        if not res['OK']:
            self.log.error("Failed to tar the output directory:", res['Message'])
            failed = True
        
        if failed == True:
            self.log.error( "==================================\n StdError:\n" )
            self.log.error( self.stdError )
            return S_ERROR('%s Exited With Status %s' % (os.path.basename(scriptName), status))
        
        #Above can't be removed as it is the last notification for user jobs
        self.setApplicationStatus('%s (%s %s) Successful' %(os.path.basename(scriptName), 
                                                            self.applicationName, self.applicationVersion))
        return S_OK('%s (%s %s) Successful' % (os.path.basename(scriptName), 
                                               self.applicationName, self.applicationVersion))
    
    def locateBinary(self):
        """
        Find out where is the nextnano binary, given that it was installed using standard methods.
        """
        self.log.info("Env:", str(os.environ))
        if "%s_%s_DIR" %(self.applicationName, self.applicationVersion) in os.environ:
            path = os.environ["%s_%s_DIR" %(self.applicationName, self.applicationVersion)]
            fin_path = os.path.join(path, "bin 64bit", "nnp_gcc_Ubuntu_64bit.x")
            if os.path.exists(fin_path):
                return S_OK(fin_path)
            else:
                return S_ERROR("Directory found, but no binary")
        else:
            return S_ERROR("Missing nextnano directory")
    