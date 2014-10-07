import types
from ALDIRAC.SimuDBSystem.DB.VMDB import VMDB
from DIRAC.Core.DISET.RequestHandler import RequestHandler
from DIRAC import S_OK

__author__ = 'stephanep'
__RCSID__ = "$Id"

gVMDB = None


def initializeVMDBHandler(serviceInfo):
    global gVMDB
    gVMDB = VMDB()
    return S_OK()


class VMDBHandler(RequestHandler):
    types_isAlive = [types.StringTypes, types.DictType]
    def export_isAlive(self, instance_id, instance_parameters):
        res = gVMDB.is_alive(instance_id, instance_parameters)
        return res

    types_isStopped = [types.StringTypes]
    def export_isStopped(self, instance_id):
        res = gVMDB.is_stopped(instance_id)
        return res

    types_status = [types.StringTypes]
    def export_status(self, instance_id):
        return gVMDB.status(instance_id)

    types_runningInstance = []
    def export_runningInstance(self):
        return gVMDB.running_instance()

    types_instanceProperties = [types.StringTypes]
    def export_instanceProperties(self, instance_id):
        return gVMDB.instance_properties(instance_id)