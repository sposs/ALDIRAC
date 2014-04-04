'''
Created on Mar 5, 2014

@author: stephanep
'''
from DIRAC.Core.DISET.RequestHandler import RequestHandler, getServiceOption
from DIRAC import gLogger, S_OK, S_ERROR
import pickle
import types
from simudb.db.simu_interface import SimuInterface
from simudb.helpers.script_base import create_connection
import tempfile
import os

gSimuDB = None
BASE_PATH = ""

__RCSID__ = "$Id"

def initializeSimuDBHandler( serviceInfo ):
    global gSimuDB
    global BASE_PATH
    testmode = getServiceOption( serviceInfo, "TestMode", False)
    gSimuDB = SimuInterface(create_connection(testmode = testmode))
    BASE_PATH = tempfile.mkdtemp()
    return S_OK()

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
            status = gSimuDB.get_run_status(simu_id)#session is opened
        except:
            gSimuDB.close_session()
            return S_ERROR("Failed getting the status")
        if status in ["done", "failed"]:
            gSimuDB.close_session()
            return S_ERROR("Cannot insert result, job is already completed")
        try:
            gSimuDB.set_run_result(pickle.dump(res_dict))
        except Exception as error:
            gSimuDB.set_run_status(simu_id, "failed", 
                                          "Failed to insert result: %s" % str(error))
            gSimuDB.close_session()
            return S_ERROR("Failed to insert result")
        try:
            gSimuDB.set_run_status(simu_id, "done")
        except:
            gSimuDB.close_session()
            return S_ERROR("Failed reporting status")
        gSimuDB.close_session()
        return S_OK()

    def transfer_fromClient( self, fileID, token, fileSize, fileHelper ):
        """ Method to receive file from clients.
        fileID is the local file name in the SE.
        fileSize can be Xbytes or -1 if unknown.
        token is used for access rights confirmation.
        """
        simu_id = int(fileID.replace(".pkl",""))
        try: 
            status = gSimuDB.get_run_status(simu_id)#session is opened
        except Exception as error:
            gLogger.error("Failed getting the status", str(error))
            gSimuDB.close_session()
            return S_ERROR("Failed getting the status")
        if status in ["done", "failed"]:
            gSimuDB.close_session()
            return S_ERROR("Cannot insert result, job is already completed")
        gSimuDB.close_session()
        file_path = os.path.join(BASE_PATH, fileID)
        fileHelper.disableCheckSum()
        try:
            fd = open( file_path, "wb" )
        except Exception, error:
            gLogger.error("Failed to open file", str(error))
            return S_ERROR( "Cannot open to write destination file %s: %s" % ( file_path, str( error ) ) )
        result = fileHelper.networkToDataSink( fd )
        if not result[ 'OK' ]:
            gLogger.error("Failed reading the data", result["Message"])
            return result
        fd.close()
        
        try:
            gSimuDB.set_run_result(simu_id, open(file_path, "rb").read())
            os.unlink(file_path)
        except Exception as error:
            gSimuDB.set_run_status(simu_id, "failed", 
                                          "Failed to insert result: %s" % str(error))
            gLogger.error("Failed to insert result", str(error))
            gSimuDB.close_session()
            return S_ERROR("Failed to insert result")
        try:
            gSimuDB.set_run_status(simu_id, "done")
        except Exception as error:
            gLogger.error("Failed setting final status", str(error))
            gSimuDB.close_session()
            return S_ERROR("Failed reporting status")
        
        gSimuDB.close_session()
        return S_OK()

    def transfer_toClient( self, fileID, token, fileHelper ):
        """ Do nothing, needed for TransferClient interface
        """
        return S_OK()
    
    def transfer_bulkFromClient( self, fileID, token, ignoredSize, fileHelper ):
        """ Receive files packed into a tar archive by the fileHelper logic.
        token is used for access rights confirmation.
        """
        return S_OK()
    
    def transfer_bulkToClient( self, fileId, token, fileHelper ):
        """ Do nothing, needed for TransferClient interface
        """
        return S_OK()
    
    types_setStatus = [types.StringType, types.StringTypes]
    def export_setStatus(self, simuid, status, message = ""):
        """ Set the task status
        """
        simu_id = int(simuid)
        try:
            gSimuDB.set_run_status(simu_id, status, message)
        except Exception as error:
            gSimuDB.close_session()
            return S_ERROR("Failed to set new status %s: %s" % (status, str(error)))
        gSimuDB.close_session()
        return S_OK(status)
        