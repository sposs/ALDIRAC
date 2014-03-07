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
        simu_id = int(simuid)
        try: 
            status = gSimuDB.get_simulation_status(simu_id)
        except:
            return S_ERROR("Failed getting the status")
        if status in ["done", "failed"]:
            return S_ERROR("Cannot insert result, job is already completed")
        try:
            gSimuDB.set_simulation_result(pickle.dump(res_dict))
        except Exception as error:
            gSimuDB.set_simulation_status(simu_id, "failed", "Failed to insert result: %s" % str(error))
            return S_ERROR("Failed to insert result")
        try:
            gSimuDB.set_simulation_status(simu_id, "done")
        except:
            return S_ERROR("Failed reporting status")
        return S_OK()
    
    types_setStatus = [types.StringType, types.StringTypes]
    def export_setStatus(self, simuid, status, message = ""):
        """ Set the task status
        """
        simu_id = int(simuid)
        current_status = gSimuDB.get_simulation_status(simu_id)
        if not status in state_transitions[current_status]:
            gLogger.error("Invalid transition")
            return {"OK": False, "Message": "Invalid transition from %s to %s" % (current_status, status), "Status": current_status}
        try:
            gSimuDB.set_simulation_status(simu_id, status, message)
        except Exception as error:
            return S_ERROR("Failed to set new status %s: %s" % (status, str(error)))
        return S_OK(status)
        