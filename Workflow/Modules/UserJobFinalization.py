########################################################################
# $HeadURL:  $
########################################################################
""" 
Module to upload specified job output files according to the parameters
defined in the user workflow.

@author: S. Poss
@since: Sep 01, 2010
"""

__RCSID__ = "$Id: UserJobFinalization.py 71836 2013-11-20 13:47:14Z sposs $"

from DIRAC.DataManagementSystem.Client.DataManager      import DataManager
from DIRAC.DataManagementSystem.Client.FailoverTransfer    import FailoverTransfer

from DIRAC.Core.Security.ProxyInfo                         import getVOfromProxyGroup,\
    getProxyInfo
from DIRAC.Core.Utilities.File import getGlobbedFiles


from ALDIRAC.Workflow.Modules.ModuleBase                 import ModuleBase
from ALDIRAC.Core.Utilities.OutputData                   import constructUserLFNs


from DIRAC                                                 import S_OK, S_ERROR, gLogger, gConfig

import os, random, time


class UserJobFinalization(ModuleBase):
    """ User Job finalization: takes care of uploading the output data to the specified storage elements
    If it does not work, it will upload to a Failover SE, then register the request to replicate and remove.  
    """
    #############################################################################
    def __init__(self):
        """Module initialization.
        """
        super(UserJobFinalization, self).__init__()
        self.version = __RCSID__
        self.log = gLogger.getSubLogger( "UserJobFinalization" )
        self.enable = True
        self.failoverTest = False  # flag to put file to failover SE by default
        self.defaultOutputSE = gConfig.getValue( '/Resources/StorageElementGroups/Tier1-USER', [])    
        self.failoverSEs = gConfig.getValue('/Resources/StorageElementGroups/Tier1-Failover', [])
        #List all parameters here
        self.userFileCatalog = self.ops.getValue('/UserJobs/Catalogs', ['FileCatalog'] )
        self.request = None
        self.lastStep = False
        #Always allow any files specified by users    
        self.outputDataFileMask = ''
        self.userOutputData = '' 
        self.userOutputSE = ''
        self.userOutputPath = ''
        self.jobReport = None
      
    #############################################################################
    def applicationSpecificInputs(self):
        """ By convention the module parameters are resolved here.
        """
        
        #Earlier modules may have populated the report objects
        if self.workflow_commons.has_key('JobReport'):
            self.jobReport = self.workflow_commons['JobReport']
        
        if self.step_commons.has_key('TestFailover'):
            self.enable = self.step_commons['TestFailover']
            if not type(self.failoverTest) == type(True):
                self.log.warn('Test failover flag set to non-boolean value %s, setting to False' % self.failoverTest)
                self.failoverTest = False
        
        if os.environ.has_key('JOBID'):
            self.jobID = os.environ['JOBID']
            self.log.verbose('Found WMS JobID = %s' % self.jobID)
        else:
            self.log.info('No WMS JobID found, disabling module via control flag')
            self.enable = False
        
        #Use LHCb utility for local running via dirac-jobexec
        if self.workflow_commons.has_key('UserOutputData'):
            self.userOutputData = self.workflow_commons['UserOutputData']
            if not type(self.userOutputData) == type([]):
                self.userOutputData = [i.strip() for i in self.userOutputData.split(';')]
        
        if self.workflow_commons.has_key('UserOutputSE'):
            specifiedSE = self.workflow_commons['UserOutputSE']
            if not type(specifiedSE) == type([]):
                self.userOutputSE = [i.strip() for i in specifiedSE.split(';')]
        else:
            self.log.verbose('No UserOutputSE specified, using default value: %s' % (', '.join(self.defaultOutputSE)))
            self.userOutputSE = self.defaultOutputSE
        
        if self.workflow_commons.has_key('UserOutputPath'):
            self.userOutputPath = self.workflow_commons['UserOutputPath']
        
        return S_OK('Parameters resolved')
    
    #############################################################################
    def execute(self):
        """ Main execution function.
        """
        #Have to work out if the module is part of the last step i.e. 
        #user jobs can have any number of steps and we only want 
        #to run the finalization once.
        currentStep = int(self.step_commons['STEP_NUMBER'])
        totalSteps = int(self.workflow_commons['TotalSteps'])
        if currentStep == totalSteps:
            self.lastStep = True
        else:
            self.log.verbose('Current step = %s, total steps of workflow = %s, UserJobFinalization will enable itself only \
            at the last workflow step.' % (currentStep, totalSteps))            
            
        if not self.lastStep:
            return S_OK()    
        
        result = self.resolveInputVariables()
        if not result['OK']:
            self.log.error("Failed to resolve input parameters:", result['Message'])
            return result
        
        self.log.info('Initializing %s' % self.version)
        if not self.workflowStatus['OK'] or not self.stepStatus['OK']:
            self.log.verbose('Workflow status = %s, step status = %s' % (self.workflowStatus['OK'], 
                                                                       self.stepStatus['OK']))
            return S_OK('No output data upload attempted')
        
        self.request.RequestName = 'job_%d_request.xml' % int(self.jobID)
        self.request.JobID = self.jobID
        self.request.SourceComponent = "Job_%d" % int(self.jobID)
        
        if not self.userOutputData:
            self.log.info('No user output data is specified for this job, nothing to do')
            return S_OK('No output data to upload')
            
        #Determine the final list of possible output files for the
        #workflow and all the parameters needed to upload them.
        outputList = []
        possible_files= []
        for i in self.userOutputData:
            files = getGlobbedFiles(i)
            for possible_file in files:
                if possible_file in possible_files:
                    #Don't have twice the same file
                    continue
                outputList.append({'outputDataType' : i.split('.')[-1].upper(),#this would be used to sort the files in different dirs
                                   'outputDataSE' : self.userOutputSE,
                                   'outputFile' : os.path.basename(possible_file)})
                possible_files.append(os.path.basename(possible_file))
                
        self.log.info('Constructing user output LFN(s) for %s' % (', '.join(self.userOutputData)))
        if not self.jobID:
            self.jobID = 12345
        owner = ''
        if 'Owner' in self.workflow_commons:
            owner = self.workflow_commons['Owner']
        else:
            res = getCurrentOwner()
            if not res['OK']:
                self.log.error('Could not find proxy')
                return S_ERROR('Could not obtain owner from proxy')
            owner = res['Value']
        vo = ''
        if self.workflow_commons.has_key('VO'):
            vo = self.workflow_commons['VO']
        else:
            res = getVOfromProxyGroup()
            if not res['OK']:
                self.log.error('Failed finding the VO')
                return S_ERROR('Could not obtain VO from proxy')
            vo = res['Value']
        result = constructUserLFNs(int(self.jobID), vo, owner, 
                                   possible_files, self.userOutputPath)
        if not result['OK']:
            self.log.error('Could not create user LFNs', result['Message'])
            return result
        userOutputLFNs = result['Value']
        
        self.log.verbose('Calling getCandidateFiles( %s, %s)' % (outputList, userOutputLFNs))
        result = self.getCandidateFiles(outputList, userOutputLFNs)
        if not result['OK']:
            if not self.ignoreapperrors:
                self.log.error(result['Message'])
                self.setApplicationStatus(result['Message'])
                return S_OK()
        
        fileDict = result['Value']
        result = self.getFileMetadata(fileDict)
        if not result['OK']:
            if not self.ignoreapperrors:
                self.log.error(result['Message'])
                self.setApplicationStatus(result['Message'])
                return S_OK()
        
        if not result['Value']:
            if not self.ignoreapperrors:
                self.log.info('No output data files were determined to be uploaded for this workflow')
                self.setApplicationStatus('No Output Data Files To Upload')
                return S_OK()
        
        fileMetadata = result['Value']
                 
        orderedSEs = self.userOutputSE
        
        
        self.log.info('Ordered list of output SEs is: %s' % (', '.join(orderedSEs)))    
        final = {}
        for fileName, metadata in fileMetadata.items():
            final[fileName] = metadata
            final[fileName]['resolvedSE'] = orderedSEs
        
        #At this point can exit and see exactly what the module will upload
        if not self.enable:
            self.log.info('Module is disabled by control flag, would have attempted \
to upload the following files %s' % ', '.join(final.keys()))
            for fileName, metadata in final.items():
                self.log.info('--------%s--------' % fileName)
                for n, v in metadata.items():
                    self.log.info('%s = %s' %(n, v))
            
            return S_OK('Module is disabled by control flag')
        
        #Instantiate the failover transfer client with the global request object
        failoverTransfer = FailoverTransfer(self.request)
        
        #One by one upload the files with failover if necessary
        replication = {}
        failover = {}
        uploaded = []
        if not self.failoverTest:
            for fileName, metadata in final.items():
                self.log.info("Attempting to store file %s to the following SE(s):\n%s" % (fileName, 
                                                                                           ', '.join(metadata['resolvedSE'])))
                replicateSE = ''
                result = failoverTransfer.transferAndRegisterFile(fileName, metadata['localpath'], metadata['lfn'],
                                                                  metadata['resolvedSE'], fileMetaDict = metadata, 
                                                                  fileCatalog = self.userFileCatalog)
                if not result['OK']:
                    self.log.error('Could not transfer and register %s with metadata:\n %s' % (fileName, metadata))
                    failover[fileName] = metadata
                else:
                    #Only attempt replication after successful upload
                    lfn = metadata['lfn']
                    uploaded.append(lfn)          
                    seList = metadata['resolvedSE']
                    
                    if result['Value'].has_key('uploadedSE'):
                        uploadedSE = result['Value']['uploadedSE']            
                        for se in seList:
                            if not se == uploadedSE:
                                replicateSE = se
                                break
                  
                if replicateSE and lfn:
                    self.log.info('Will attempt to replicate %s to %s' % (lfn, replicateSE))    
                    replication[lfn] = replicateSE            
        else:
            failover = final
        
        cleanUp = False
        for fileName, metadata in failover.items():
            random.shuffle(self.failoverSEs)
            targetSE = metadata['resolvedSE'][0]
            metadata['resolvedSE'] = self.failoverSEs
            result = failoverTransfer.transferAndRegisterFileFailover(fileName,
                                                                      metadata['localpath'],
                                                                      metadata['lfn'],
                                                                      targetSE,
                                                                      self.failoverSEs,
                                                                      fileMetaDict = metadata,
                                                                      fileCatalog = self.userFileCatalog)
            if not result['OK']:
                self.log.error('Could not transfer and register %s with metadata:\n %s' % (fileName, metadata))
                cleanUp = True
                continue #for users can continue even if one completely fails
            else:
                lfn = metadata['lfn']
                uploaded.append(lfn)
        
        #For files correctly uploaded must report LFNs to job parameters
        if uploaded:
            report = ', '.join( uploaded )
            self.jobReport.setJobParameter( 'UploadedOutputData', report )
        
        self.request = failoverTransfer.request
        
        #If some or all of the files failed to be saved to failover
        if cleanUp:
            self.workflow_commons['Request'] = self.request
            #Leave any uploaded files just in case it is useful for the user
            #do not try to replicate any files.
            return S_ERROR('Failed To Upload Output Data')
        
        #If there is now at least one replica for uploaded files can trigger replication
        rm = DataManager(catalogs=self.userFileCatalog)
        self.log.info('Sleeping for 10 seconds before attempting replication of recently uploaded files')
        time.sleep(10)
        for lfn, repSE in replication.items():
            result = rm.replicateAndRegister(lfn, repSE)
            if not result['OK']:
                self.log.info('Replication failed with below error but file already exists in Grid storage with \
                at least one replica:\n%s' % (result))
        
        self.workflow_commons['Request'] = self.request
        self.generateFailoverFile()    
        
        self.setApplicationStatus('Job Finished Successfully')
        return S_OK('Output data uploaded')

#############################################################################
def getCurrentOwner():
    """Simple function to return current DIRAC username.
    """
    result = getProxyInfo()
    if not result['OK']:
        return S_ERROR('Could not obtain proxy information')
    
    if not result['Value'].has_key('username'):
        return S_ERROR('Could not get username from proxy')
    
    username = result['Value']['username']
    return S_OK(username)

#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#EOF#
