#!/usr/bin/env python
'''
Created on Jun 10, 2014

@author: stephanep
'''
import subprocess
import os
from DIRAC.Core.Utilities.Subprocess import shellCall
import urllib2

def execscript(comm):
    """
    Execute command, and catch if error
    """
    res= shellCall(0, comm)
    if not res['OK']:
        gLogger.error("Failed call", res)
    status  = res['Value'][0]
    
    os.unlink("tmp.sh")
    message = ''
    if status:
        gLogger.error("Issue with call -> ", res['Value'][2])
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
    return execscript(comm)

def getAmazonVMId( ):
    try:
        fd = urllib2.urlopen("http://instance-data.ec2.internal/latest/meta-data/instance-id", timeout=30)
    except urllib2.URLError:
        gLogger.warn("Can not connect to EC2 URL. Trying address 169.254.169.254 directly...")
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
    
    res = getAmazonVMId()
    if not res['OK']:
        gLogger.error("Failed getting VM ID: ", res['Message'])
        vmID = '0000'
    else:
        vmID = res['Value']
    
    # First: collect the version
    from DIRAC import gLogger, exit as dexit
    from DIRAC import rootPath
    from DIRAC.ConfigurationSystem.Client.Helpers.Operations import Operations
    ops = Operations()
    aldirac_version = ops.getValue("Cloud/ALDIRAC/Version")
    if not aldirac_version:
        gLogger.error("Missing ALDIRAC version to install")
        dexit(1)
    gLogger.info("Will install ALDIRAC ", aldirac_version)
    dirac_version = ops.getValue("Cloud/ALDIRAC/%s/DiracVersion" % aldirac_version)
    if not dirac_version:
        gLogger.error("Missing DIRAC version")
        dexit(1)
    gLogger.info("Will install DIRAC ", dirac_version)
    
    os.chdir(os.path.join(rootPath, "DIRAC"))
    # do git fetch
    f_d = fetch()
    if f_d[0]:
        gLogger.error("Failed:", f_d[1])
        dexit(1)
    g_v_d = get_version(dirac_version)
    if g_v_d[0]:
        gLogger.error("Failed updating DIRAC: ", g_v_d[1])
        dexit(1)
    
    os.chdir(os.path.join(rootPath, "ALDIRAC"))
    f_a = fetch()
    if f_a[0]:
        gLogger.error("Failed: ", f_a[1])
        dexit(1)
    g_v_a = get_version(aldirac_version)
    if g_v_a[0]:
        gLogger.error("Failed updating ALDIRAC: ", g_v_a[1])
        dexit(1)
    
    
    
    dexit(0)