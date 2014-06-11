#!/usr/bin/env python
'''
Utility that updates DIRAC and an extension (hard coded) from git tags defined in the CS. 
Uses the Logger to send error messages to the SystemLogging, given that the CS 
holds the right info. The CS must be like::

  Operations
  {
    Defaults
    {
      Cloud
      {
        Logger
        {
          LogLevel=ERROR
          LogBackends = server, stdout
          BackendsOptions
          {
            FileName = Dirac-log.log
            Interactive = False
            SleepTime = 5
          }
        }
      }
    }
  }

Currently specific to Amazon to get the VM ID. I hope that one day VMDIRAC 
will propose utilities to ask this kind of generic question

@since Jun 10, 2014

@author: Stephane Poss
'''

import subprocess
import os
from DIRAC.Core.Utilities.Subprocess import shellCall
import urllib2
from DIRAC import S_OK, S_ERROR
import time

def execscript(comm):
    """
    Execute command, and catch if error
    """
    res= shellCall(0, comm)
    if not res['OK']:
        return (-1, 'Issue with shellCall')
    status  = res['Value'][0]
    
    os.unlink("tmp.sh")
    message = ''
    if status:
        message = res['Value'][2]
    
    return (status, message)


def fetch():
    """
    Do a git fetch
    """
    with open("tmp.sh", "w") as script:
        script.write("""#!/bin/bash
unset LD_LIBRARY_PATH
git fetch
exit $?
""")
    os.chmod("tmp.sh", 0755)
    comm = "sh -c './tmp.sh'" 
    return execscript(comm)

def get_version(version):
    """
    Checkout a version
    """
    with open("tmp.sh", "w") as script:
        script.write("""#!/bin/bash
unset LD_LIBRARY_PATH
git checkout refs/tags/%s
exit $?
""" % version)
    os.chmod("tmp.sh", 0755)
    comm = "sh -c './tmp.sh'" 
    return execscript(log, comm)

def getAmazonVMId( log ):
    """
    Get the VM ID from Amazon provider 
    """
    try:
        fd = urllib2.urlopen("http://instance-data.ec2.internal/latest/meta-data/instance-id", timeout=30)
    except urllib2.URLError:
        log.warn("Can not connect to EC2 URL. Trying address 169.254.169.254 directly...")
    try:
        fd = urllib2.urlopen("http://169.254.169.254/latest/meta-data/instance-id", timeout=30)
    except urllib2.URLError, e:
        return S_ERROR( "Could not retrieve amazon instance id: %s" % str( e ) )
    iD = fd.read().strip()
    fd.close()
    return S_OK( iD )


if __name__ == '__main__':
    from DIRAC.Core.Base import Script
    Script.parseCommandLine()
    from DIRAC.FrameworkSystem.private.logging.Logger import Logger
    from DIRAC import gConfig
    baselog = Logger()
    baselog.initialize("update_dirac","/Operations/Defaults/Cloud/Logger")
    l = baselog.getSubLogger("UpdateDirac")
    l.initialize("update_dirac","/Operations/Defaults/Cloud/Logger")
    #This is to guarantee the messages will be send before the script exists.
    #HACK as long as ExitCallBack is disabled.
    time_to_sleep = gConfig.getValue("/Operations/Defaults/Cloud/Logger/BackendsOptions/SleepTime", 10)+2
    res = getAmazonVMId(l)
    if not res['OK']:
        l.error("Failed getting VM ID: %s" % res['Message'])
        time.sleep(time_to_sleep)
        vmID = '0000'
    else:
        vmID = res['Value']
    # First: collect the version
    from DIRAC import exit as dexit
    from DIRAC import rootPath
    from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations
    ops = Operations()
    aldirac_version = ops.getValue("Cloud/ALDIRAC/Version")
    if not aldirac_version:
        l.error("Missing ALDIRAC version on %s" % vmID)
        time.sleep(time_to_sleep)
        dexit(1)
    l.info("Will install ALDIRAC ", aldirac_version)
    dirac_version = ops.getValue("Cloud/ALDIRAC/%s/DiracVersion" % aldirac_version)
    if not dirac_version:
        l.error("Missing DIRAC version on %s" % vmID)
        time.sleep(time_to_sleep)
        dexit(1)
    l.info("Will install DIRAC ", dirac_version)
    
    os.chdir(os.path.join(rootPath, "DIRAC"))
    # do git fetch
    f_d = fetch()
    if f_d[0]:
        l.error("Failed fetching DIRAC on %s: %s" % (vmID, f_d[1]))
        time.sleep(time_to_sleep)
        dexit(1)
    g_v_d = get_version(dirac_version)
    if g_v_d[0]:
        l.error("Failed updating DIRAC on %s: %s" % (vmID, g_v_d[1]))
        time.sleep(time_to_sleep)
        dexit(1)
    
    #Handle ALDIRAC
    os.chdir(os.path.join(rootPath, "ALDIRAC"))
    f_a = fetch()
    if f_a[0]:
        l.error("Failed fetch ALDIRAC on %s: %s" % (vmID, f_a[1]) )
        time.sleep(time_to_sleep)
        dexit(1)
        
    g_v_a = get_version(aldirac_version)
    if g_v_a[0]:
        l.error("Failed updating ALDIRAC on %s: %s" % (vmID, g_v_a[1]) )
        time.sleep(time_to_sleep)
        dexit(1)
    l.notice("All good")
    time.sleep(time_to_sleep)
    dexit(0)
