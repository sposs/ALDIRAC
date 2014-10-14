#!/bin/env python
import urllib2
import datetime

__author__ = 'stephanep'


def get_info(parameter):
    """
    Query the amazon service for the instance parameters
    :param parameter: parameter to query
    :return: value of the parameter
    """
    fd = None
    try:
        fd = urllib2.urlopen("http://169.254.169.254/latest/meta-data/%s" % parameter, timeout=30)
    except urllib2.URLError, e:
        l.error("Failed to retrieve %s" % parameter, e)
        return None
    value = fd.read().strip()
    fd.close()
    return value

if __name__ == "__main__":
    from DIRAC.Core.Base import Script
    Script.parseCommandLine()
    from DIRAC.FrameworkSystem.private.logging.Logger import Logger
    from DIRAC.Core.DISET.RPCClient import RPCClient
    from DIRAC import exit as dexit
    l = Logger()
    l.initialize("report_alive", "/Operations/Defaults/Cloud/Logger")
    vmdb = RPCClient("SimuDB/VMDB")
    instance_id = get_info("instance-id")
    p_dict = {'Start': datetime.datetime.utcnow().replace(microsecond=0)}
    res = vmdb.isAlive(instance_id, p_dict)
    if not res['OK']:
        l.error("Failed to report VM as alive", res['Message'])
        dexit(1)
    dexit(0)