# #######################################################################
# $HeadURL$
# #######################################################################
""" NotificationDB class is a front-end to the Notifications database
"""
import datetime

__author__ = 'stephanep'

__RCSID__ = "$Id$"

from DIRAC import S_OK, S_ERROR
from DIRAC.Core.Base.DB import DB


class VMDB(DB):
    def __init__(self, maxQueueSize=10):
        DB.__init__(self, 'VMDB', 'SimuDB/VMDB', maxQueueSize)
        result = self.__initialize_db()
        if not result['OK']:
            self.log.fatal("Cannot initialize DB!", result['Message'])

    def __initialize_db(self):
        retval = self._query("show tables")
        if not retval['OK']:
            return retval

        tablesInDB = [t[0] for t in retval['Value']]
        tablesToCreate = {}
        if "Instances" not in tablesInDB:
            tablesToCreate['Instances'] = {'Fields': {'Id': 'INTEGER UNSIGNED AUTO_INCREMENT NOT NULL',
                                                      'InstanceID': 'VARCHAR(32) NOT NULL',
                                                      'Status': "VARCHAR(8) NOT NULL",
                                                      "StartedAt": "DATETIME",
                                                      "StoppedAt": "DATETIME",
                                                      "Type": "VARCHAR(32) NOT NULL",
                                                      "AMI": "VARCHAR(32) NOT NULL"
            },
                                           'PrimaryKey': 'Id',
                                           'Indexes': {'Status': ['Status'],
                                                       'InstanceID': ['InstanceID']}
            }
        if tablesToCreate:
            result = self._createTables(tablesToCreate)
            if result['OK'] and result['Value']:
                self.log.info("VMDB: created tables %s" % result['Value'])
                return result
        return S_OK()

    def register_instance(self, instance_id, instance_type, instance_image):
        connection = self._getConnection()
        res = self.insertFields("Instances", ['InstanceID', 'Status', "Type", "AMI"],
                                [instance_id, "Standby", instance_type, instance_image],
                                conn=connection)
        return res

    def is_alive(self, instance_id, instance_dict):
        connection = self._getConnection()
        res = self.getFields("Instances", ["Status"], {"InstanceID": instance_id}, conn=connection)
        if not res['OK']:
            return res
        self.log.debug("Status", res['Value'])
        if not len(res['Value']):
            return S_ERROR("VM %s does not exist" % instance_id)
        res = self.updateFields("Instances",
                                ['Status', "StartedAt"],
                                ["Running", instance_dict['Start']],
                                {'InstanceID': instance_id},
                                conn=connection)
        return res

    def is_stopped(self, instance_id):
        conn = self._getConnection()
        res = self.getFields("Instances", ["Status"], {"InstanceID": instance_id}, conn=conn)
        if not res['OK']:
            return res
        if not len(res['Value']):
            return S_ERROR("VM %s does not exist" % instance_id)
        res = self.updateFields("Instances", ['Status', "StoppedAt"],
                                ["Stopped", datetime.datetime.utcnow().replace(microsecond=0)],
                                {'InstanceID': instance_id}, conn=conn)
        return res

    def status(self, instance_id):
        conn = self._getConnection()
        res = self.getFields("Instances", ['Status'], {'InstanceID': instance_id}, conn=conn)
        if not res['OK']:
            return res
        if not len(res['Value']):
            return S_ERROR("No Instance found")
        status = res['Value'][0][0]
        return S_OK(status)

    def running_instance(self):
        conn = self._getConnection()
        res = self.getFields("Instances", ["InstanceID"], {"Status": ["Running", "Standby"]}, conn=conn)
        if not res['OK']:
            return res
        for row in res['Value']:
            if len(row):
                return S_OK(row[0])
        return S_OK("")

    def instance_properties(self, instance_id):
        conn = self._getConnection()
        res = self.getFields("Instances", ["Status", "StartedAt", "StoppedAt", "Type", "AMI"],
                             {"InstanceID": instance_id}, conn=conn)
        if not res['OK']:
            return res
        if not len(res['Value']):
            return S_ERROR("No Instance found")
        if len(res['Value']) > 1:
            return S_ERROR("Too many instances called %s" % instance_id)
        row = res['Value'][0]
        return S_OK({'Status': row[0], "Started": row[1], "Stopped": row[2], "Type": row[3], "AMI": row[4]})
