# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from oslo.config import cfg

from senlin.db import api as db_api


class Action(object):
    '''
    An action can be performed on a cluster or a node of a cluster.
    '''
    RETURNS = (
        OK, FAILED, RETRY,
    ) = (
        'OK', 'FAILED', 'RETRY',
    )

    # Action status definitions:
    #  INIT:      Not ready to be executed because fields are being modified,
    #             or dependency with other actions are being analyzed.
    #  READY:     Initialized and ready to be executed by a worker.
    #  RUNNING:   Being executed by a worker thread.
    #  SUCCEEDED: Completed with success.
    #  FAILED:    Completed with failure.
    #  CANCELLED: Action cancelled because worker thread was cancelled.
    STATUSES = (
        INIT, WAITING, READY, RUNNING,
        SUCCEEDED, FAILED, CANCELED
    ) = (
        'INIT', 'WAITING', 'READY', 'RUNNING',
        'SUCCEEDED', 'FAILED', 'CANCELLED',
    )

    def __init__(self, context):
        self.id = None
        # context will be persisted into database so that any worker thread
        # can pick the action up and execute it on behalf of the initiator
        self.context = context

        self.description = ''

        # Target is the ID of a cluster, a node, a profile
        self.target = ''

        # An action 
        self.action = ''

        # Why this action is fired, it can be a UUID of another action
        self.cause = ''

        # Owner can be an UUID format ID for the worker that is currently
        # working on the action.  It also serves as a lock.
        self.owner = ''

        # An action may need to be executed repeatitively, interval is the
        # time in seconds between two consequtive execution.
        # A value of -1 indicates that this action is only to be executed once
        self.interval = -1

        # Start time can be an absolute time or a time relative to another
        # action. E.g.
        #   - '2014-12-18 08:41:39.908569'
        #   - 'AFTER: 57292917-af90-4c45-9457-34777d939d4d'
        #   - 'WHEN: 0265f93b-b1d7-421f-b5ad-cb83de2f559d' 
        self.start_time = ''
        self.end_time = '' 

        # Timeout is a placeholder in case some actions may linger too long
        self.timeout = cfg.CONF.default_action_timeout

        # Return code, useful when action is not automatically deleted
        # after execution
        self.status = ''
        self.status_reason = ''

        # All parameters are passed in using keyward arguments which is
        # a list stored as JSON in DB
        self.inputs = {}
        self.outputs = {}

        # Dependency with other actions
        self.depends_on = []
        self.depended_by = []


    def execute(self, **kwargs):
        return NotImplemented

    def cancel(self):
        return NotImplemented

    def store(self):
        #db_api.action_update(self.id) 
        return


class ClusterAction(Action):
    '''
    An action performed on a cluster.
    '''
    ACTIONS = (
        CREATE, DELETE, ADD_NODE, DEL_NODE, UPDATE,
        ATTACH_POLICY, DETACH_POLICY,
    ) = (
        'CREATE', 'DELETE', 'ADD_NODE', 'DEL_NODE', 'UPDATE',
        'ATTACH_POLICY', 'DETACH_POLICY',
    )

    def __init__(self, context, cluster):
        super(ClusterAction, self).__init__(context)
        self.target = cluster

    def execute(self, action, **kwargs):
        if action not in self.ACTIONS:
            return self.FAILED 

        if action == self.CREATE:
            # TODO:
            # We should query the lock of cluster here and wrap
            # cluster.do_create, and then let threadgroupmanager
            # to start a thread for this progress.
            cluster.do_create(kwargs)
        else:
            return self.FAILED

        return self.OK 

    def cancel(self):
        return self.FAILED 


class NodeAction(Action):
    '''
    An action performed on a cluster member.
    '''
    ACTIONS = (
        CREATE, DELETE, UPDATE, JOIN, LEAVE,
    ) = (
        'CREATE', 'DELETE', 'UPDATE', 'JOIN', 'LEAVE',
    )

    def __init__(self, context, node):
        super(NodeAction, self).__init__(context)

        # get cluster of this node 
        # get policies associated with the cluster

    def execute(self, action, **kwargs):
        if action not in self.ACTIONS:
            return self.FAILED 
        return self.OK 

    def cancel(self):
        return self.OK 


class PolicyAction(Action):
    '''
    An action performed on a cluster policy.

    Note that these can be treated as cluster operations instead of operations
    on a policy itself.
    '''

    ACTIONS = (
        ENABLE, DISABLE, UPDATE,
    ) = (
        'ENABLE', 'DISABLE', 'UPDATE',
    )

    def __init__(self, context, cluster_id, policy_id):
        super(PolicyAction, self).__init__(context)
        # get policy associaton using the cluster id and policy id

    def execute(self, action, **kwargs):
        if action not in self.ACTIONS:
            return self.FAILED 

        self.store(start_time=datetime.datetime.utcnow(),
                   status=self.RUNNING)

        cluster_id = kwargs.get('cluster_id')
        policy_id = kwargs.get('policy_id')

        # an ENABLE/DISABLE action only changes the database table
        if action == self.ENABLE:
            db_api.cluster_enable_policy(cluster_id, policy_id)
        elif action == self.DISABLE:
            db_api.cluster_disable_policy(cluster_id, policy_id)
        else: # action == self.UPDATE:
            # There is not direct way to update a policy because the policy
            # might be shared with another cluster, instead, we clone a new
            # policy and replace the cluster-policy entry.
            pass

            # TODO(Qiming): Add DB API complete this.
       
        self.store(end_time=datetime.datetime.utcnow(),
                   status=self.SUCCEEDED)
        return self.OK 

    def cancel(self):
        self.store(end_time=datetime.datetime.utcnow(),
                   status=self.CANCELLED)
        return self.OK 
