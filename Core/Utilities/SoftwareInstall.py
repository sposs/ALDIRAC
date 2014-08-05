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
import tempfile
from ALDIRAC.Core.Utilities.SoftwareDependencies import resolveDeps
import pkg_resources
from pkg_resources import DistributionNotFound
from DIRAC.Core.Utilities.Os import which
import DIRAC
import shutil
import glob

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

def exists(software):
    """ Check if a given software was already installed with pip
    """
    found = False
    try:
        cur_vers = pkg_resources.get_distribution(software["name"]).version
        gLogger.info("Found %s version %s installed" % (software["name"], cur_vers))
        if cur_vers == software["version"]:
            found = True
        else:
            gLogger.warn("Version mismatch: %s installed, %s required" % (cur_vers, software["name"]))
    except DistributionNotFound:
        #Nothing to do: software isn't found
        pass
    
    if found:
        gLogger.info("Correct version already installed")
        return True
    return False

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
        self.port = ops.getValue("SoftwareInstall/Port", "22")
        
    def execute(self):
        """ Run the installation procedure
        """
        if not self.apps:
            # There is nothing to do
            return S_OK()
        
        if not self.user or not self.path or not self.host:
            gLogger.error("Missing user or path or host from CS")
            return S_ERROR("Missing user or path or host from CS")
        
        lockname = os.path.join(os.environ["HOME"],"soft_install.lock")
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
        dtemp = tempfile.mkdtemp()
        
        #cleanup in case needed
        previous_dirs = glob.glob("/tmp/pip_build*")
        for pdir in previous_dirs:
            if os.path.isdir(pdir):
                try:
                    shutil.rmtree(pdir)
                except OSError:
                    gLogger.error("Failed to delete the directory %s, hope it will succeed anyway" % pdir)
                
        deps_list = []
        #try to rsync app vX, use overwrite flag
        gLogger.verbose("Apps to install:", str(self.apps))
        for app in self.apps:
            name = app[0]
            version = app[1]
            res = resolveDeps(name, version)
            if not res['OK']:
                gLogger.error("Failed getting the dependencies:", res['Message'])
                deps = []
            else:
                deps = res['Value']
            deps_list.extend(deps)
            
            if not os.path.exists("%s/%s/%s" % (os.environ["HOME"], name, version)):
                os.makedirs("%s/%s/%s" % (os.environ["HOME"], name, version))
                os.environ["%s_%s_DIR" % (name, version)] = "%s/%s/%s" % (os.environ["HOME"], name, version)
                gLogger.info("Added %s_%s_DIR to the os.environ:" % (name, version), os.environ["%s_%s_DIR" % (name, version)])
            else:
                #The application already exists here, no need to rsync
                os.environ["%s_%s_DIR" % (name, version)] = "%s/%s/%s" % (os.environ["HOME"], name, version)
                gLogger.info("%s %s already exists locally, will check dependencies" % (name, version))
                gLogger.info("Added %s_%s_DIR to the os.environ:" % (name, version), os.environ["%s_%s_DIR" % (name, version)])
                continue
            fpath = os.path.join(dtemp, "script_%s.sh" % name)
            with open(fpath, "w") as script:
                script.write("#!/bin/bash\n")
                script.write("unset LD_LIBRARY_PATH\n")
                comm = 'rsync -avz -e "ssh -i %(home)s/.ssh/id_dsa -p %(port)s" %(user)s@%(host)s:%(path)s/Packages/%(name)s/%(version)s %(home)s/%(name)s/\n'\
                        % {"home" : os.environ["HOME"], "user": self.user, "host": self.host, "port": self.port, "path": self.path, "name": name, 
                           "version": version}
                gLogger.info("Installing %s %s with" % (name, version), comm)
                script.write(comm)
                script.write("exit $?\n")
            os.chmod(fpath, 0755)
            comm = ["sh", "-c", fpath]
            try:
                subprocess.check_call(comm)
            except subprocess.CalledProcessError:
                gLogger.error("Failed to install", "%s %s" % (name, version))
                clearLock(lockname)
                return S_ERROR("Failed installation")
        
            

        #Now install the dependencies        
        packages = []
        to_install = []
        for dep in deps_list:
            #dependencies are installed in the pythonpath, they should be visible here if they are here
            if exists(dep):
                continue
            to_install.append(dep)
            fpath = os.path.join(dtemp, "rsync%s.sh" % dep['name'])
            with open(fpath, "w") as script:
                script.write("#!/bin/bash\n")
                script.write("unset LD_LIBRARY_PATH\n")
                script.write("mkdir $HOME/Packages\n")
                comm = 'rsync -avz -e "ssh -i %(home)s/.ssh/id_dsa -p %(port)s" %(user)s@%(host)s:%(path)s/Packages/%(package)s %(home)s/Packages/\n' \
                       % {"home": os.environ["HOME"], "port": self.port, "host": self.host, "user": self.user, "path": self.path, "package": dep['name']}
                gLogger.info("Rsync %s with" % dep["name"], comm)
                script.write(comm)
                script.write("exit $?\n")
            os.chmod(fpath, 0755)
            # try to rsync Packages
            #assumming the key is located in $HOME/.ssh/id_dsa
            comm = ["sh", '-c', fpath]  
            try:
                subprocess.check_call(comm)
            except subprocess.CalledProcessError:
                gLogger.error("Failed to run the rsync, failing")
                clearLock(lockname)
                return S_ERROR("Failed installation")
            
            packages.append("-f")
            packages.append("file://%s/Packages/%s" % (os.environ["HOME"], dep["name"]))
        gLogger.info("which pip:", which("pip"))
        gLogger.info("which python:", which("python"))
        
        if len(to_install):
            # reinstall pip
            fname = os.path.join(dtemp, "run.sh")
            with open(fname, "w") as script:
                script.write("#!/bin/bash\n")
                script.write("source %s/bashrc\n" % DIRAC.rootPath)
                script.write("python %s/ALDIRAC/Core/Utilities/get-pip.py\n" % DIRAC.rootPath)
                script.write("pip --version > /tmp/pip.log\n")
                script.write("exit $?\n")
            os.chmod(fname, 0755)
            try:
                subprocess.check_call(["sh", "-c", fname])
            except subprocess.CalledProcessError:
                gLogger.error("Couldn't install pip")
                clearLock(lockname)
                return S_ERROR("Failed installation")
        #now that the local cache is up to date, install the packages.
        for dep in to_install:
            #No need to check again existence
            comm = ["pip", "install", "%s==%s" % (dep['name'], dep["version"])]
            comm.extend(packages)
            comm.extend(["--allow-all-external"])
            fname = os.path.join(dtemp, "run.sh")
            with open(fname, "w") as script:
                script.write("#!/bin/bash\n")
                script.write("source %s/bashrc\n" % DIRAC.rootPath)
                script.write("env > /tmp/localenv.log\n")
                gLogger.notice("Installing %s with" % dep["name"], " ".join(comm))
                script.write(" ".join(comm) + "\n")
                script.write("exit $?\n")
            os.chmod(fname, 0755)
            try:
                subprocess.check_call(["sh", "-c", fname])
            except subprocess.CalledProcessError:
                gLogger.error("Couldn't install %s" % dep["name"])
                clearLock(lockname)
                return S_ERROR("Failed installation")
        #Everything went fine, we try to clear the lock  
        clearLock(lockname)

        return S_OK()
    
