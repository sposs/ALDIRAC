'''
Created on Mar 5, 2014

@author: stephanep
'''
from DIRAC.Core.DISET.RequestHandler import RequestHandler
from DIRAC import gLogger, S_OK, S_ERROR
import pickle
import types

gSimuDB = False
def initializeSimuDBHandler( serviceInfo ):
    global gSimuDB
    
state_transitions = {"new": ["waiting"], "waiting": ["running"], "running": ["running", "done", "failed"], "done": [], "failed": []}
class SimuDBHandler(RequestHandler):
    """ Simple service that inserts the simulation results into the DB
    """ 
    types_addResult = [types.StringTypes, types.StringTypes]
    def export_addResult(self, simuid, result):
        try:
            res_dict = pickle.loads(result)
        except:
            gLogger.error("Coudn't convert the received data")
            return S_ERROR("Failed converting the data")
        group_id, simu_id = [int(x) for x in simuid.split("_")]
        simug = gSimuDB.get_simulations_groups(id = group_id)
        if not simug:
            gLogger.error("Cannot find group", group_id)
            return S_ERROR("Cannot find simulation group %s" % group_id)
        simug = simug[0]
        simu = simug.get_simulations(id = simu_id)
        if not simu:
            gLogger.error("Cannot find simu in group %s:" % group_id, simu_id)
            return S_ERROR("Simulation %s_%s not found" % (group_id, simu_id))
        simu = simu[0]
        if simu.status in ["done", "failed"]:
            return S_ERROR("Cannot insert result, job is already completed")
        try:
            simu.set_data(res_dict)
        except Exception as error:
            simu.set_status("failed", "Failed to insert result: %s" % str(error))
            return S_ERROR("Failed to insert result")
        return self.export_setStatus("done", simuid)
    
    types_setStatus = [types.StringType, types.StringTypes]
    def export_setStatus(self, simuid, status, message = ""):
        """ Set the task status
        """
        group_id, simu_id = [int(x) for x in simuid.split("_")]
        simug = gSimuDB.get_simulations_groups(id = group_id)
        if not simug:
            gLogger.error("Cannot find group", group_id)
            return S_ERROR("Cannot find simulation group %s" % group_id)
        simug = simug[0]
        simu = simug.get_simulations(id = simu_id)
        if not simu:
            gLogger.error("Cannot find simu in group %s:" % group_id, simu_id)
            return S_ERROR("Simulation %s_%s not found" % (group_id, simu_id))
        simu = simu[0]
        current_status = simu.status
        if not status in state_transitions[current_status]:
            gLogger.error("Invalid transition")
            return {"OK": False, "Message": "Invalid transition from %s to %s" % (current_status, status), "Status": current_status}
        try:
            simu.set_status(status, message)
        except Exception as error:
            return S_ERROR("Failed to set new status %s: %s" % (status, str(error)))
        return S_OK(status)
        