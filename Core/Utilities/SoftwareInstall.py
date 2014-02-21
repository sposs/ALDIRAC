'''
Created on Feb 21, 2014

@author: stephanep
'''

from DIRAC.ConfigurationSystem.Client.Helpers.Operations  import Operations

from DIRAC import S_OK, S_ERROR, gLogger
import time
import os
import subprocess
from math import log

def WasteCPUCycles(timecut):
    """ Waste, waste, and waste more CPU.
    """
    a = 1e31
    first = time.clock()
    while time.clock()-first < timecut:
        try:
            a = log(a)
        except Exception, x:
            return S_ERROR("Failed to waste %s CPU seconds:%s" % (timecut, str(x)))  
        if a < 0:
            a = -a
        if a == 0:
            a = 4  
    return S_OK("Successfully wasted %s seconds" % timecut)    

def createLock(lockname):
    """ Need to lock the area to prevent 2 jobs to write in the same area
    """
    try:
        lock = file(lockname,"w")
        lock.write("Locking this directory\n")
        lock.close()
    except IOError as error:
        gLogger.error("Failed creating lock")
        return S_ERROR("Not allowed to write here: IOError %s" % (str(error)))
    return S_OK()

def checkLockAge(lockname):
    """ Check if there is a lock, and in that case deal with it, 
    potentially remove it after n minutes
    """
    overwrite = False
    count = 0
    while (1):
        if not os.path.exists(lockname):
            break
        count += 1
        gLogger.warn("Will wait one minute before proceeding")
        res = WasteCPUCycles(60)
        if not res['OK']:
            continue
        last_touch = time.time()
        try:
            stat = os.stat(lockname)
            last_touch = float(stat.st_atime)
        except EnvironmentError, why:
            gLogger.warn("File not available: %s, assume removed" % str(why)) 
            break
        loc_time = time.time()
        tdiff = loc_time-last_touch
        if tdiff > 10*60: ##this is where I say the file is too old to still be valid (10 minutes)
            gLogger.info("File is %s seconds old" % tdiff)
            overwrite = True
            res = clearLock(lockname)
            if res['OK']:
                break
        if count > 10: #We have been waiting for 10 minutes, something is wrong, kill it
            gLogger.error("Seems file stat is wrong, assume buggy, will fail installation")
            #overwrite = True
            res = clearLock(lockname)
            return S_ERROR("Buggy lock, removed: %s" % res['OK'])
        
    return S_OK(overwrite)
  
def clearLock(lockname):
    """ And we need to clear the lock once the operation is done
    """
    try:
        os.unlink(lockname)
    except OSError as error:
        gLogger.error("Failed cleaning lock: OSError", "%s" % (str(error)))
        return S_ERROR("Failed to clear lock: %s" % (str(error)) )
    return S_OK()


class SoftwareInstall(object):
    '''
    Software installation module. Makes sure the software version
    required is installed
    '''
    def __init__(self, argumentsDict):
        '''
        Constructor
        '''
        super(SoftwareInstall, self).__init__()
        self.job = {}
        if argumentsDict.has_key('Job'):
            self.job = argumentsDict['Job']
        self.ce = {}
        if argumentsDict.has_key('CE'):
            self.ce = argumentsDict['CE']
        self.source = {}
        if argumentsDict.has_key('Source'):
            self.source = argumentsDict['Source']
            
        apps = []
        if self.job.has_key('SoftwarePackages'):
            if type( self.job['SoftwarePackages'] ) == type(''):
                apps = [self.job['SoftwarePackages']]
            elif type( self.job['SoftwarePackages'] ) == type([]):
                apps = self.job['SoftwarePackages']

        self.apps = []
        for app in apps:
            gLogger.verbose( 'Requested Package', str(app))
            app = tuple(app.split('.'))
            if len(app) > 2:
                tempapp = app
                app = []
                app.append(tempapp[0])
                app.append(".".join(tempapp[1:]))
            self.apps.append(app)
            
        ops = Operations()
        self.user = ops.getValue("SoftwareInstall/User", None)
        self.path = ops.getValue("SoftwareInstall/Path", None)
        self.host = ops.getValue("SoftwareInstall/Host", None)
        
    def execute(self):
        """ Run the installation procedure
        """
        if not self.apps:
            # There is nothing to do
            return S_OK()
        
        if not self.user or not self.path or not self.host:
            gLogger.error("Missing user or path or host from CS")
            return S_ERROR("Missing user or path or host from CS")
        
        lockname = "soft_install.lock"
        res = checkLockAge(lockname)
        if not res['OK']:
            gLogger.error("Something uncool happened with the lock, will kill installation")
            gLogger.error("Message: %s" % res['Message'])
            return S_ERROR("Failed lock checks")
        if res.has_key('Value'):
            if res['Value']: #this means the lock file was very old, meaning that the installation failed elsewhere
                overwrite = True
                
        res = createLock(lockname)##This will fail if not allowed to write here
        if not res['OK']:
            gLogger.error(res['Message'])
            return res
        
        
        # try to rsync Packages
        #assumming the key is located in $HOME/.ssh/id_dsa
        comm = ["rsync", "-avz", "-e", '"ssh -i %s/.ssh/id_dsa"' % os.environ["HOME"], 
                "%s@%s:%s/Packages" % (self.user, self.host, self.path), "%s/" % os.environ["HOME"]]
        try:
            gLogger.notice("Running", " ".join(comm))
            subprocess.check_call(comm)
        except subprocess.CalledProcessError:
            gLogger.error("Failed to run the rsync, failing")
            clearLock(lockname)
            return S_ERROR("Failed installation")
        #try to rsync app vX, use overwrite flag
        
        #if app==sewlab: install sewlabwrapper with pip, given the local path
        comm = ["pip", "install", "sewlabwrapper", "-f", "file://%s/Packages/sewlabwrapper" % os.environ["HOME"], 
                 "-f", "file://%s/Packages/configuration_manager" % os.environ["HOME"], "--allow-all-external", "-U"]
        try:
            gLogger.notice("installing sewlabwrapper with", " ".join(comm))
            subprocess.check_call(comm)
        except subprocess.CalledProcessError:
            gLogger.error("Couldn't install sewlabwrapper")
            clearLock(lockname)
            return S_ERROR("Failed installation")
        #Everything went fine, we try to clear the lock  
        clearLock(lockname)

        return S_OK()