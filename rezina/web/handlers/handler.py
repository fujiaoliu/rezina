#!/usr/bin/env python


try:
    import urlparse
except ImportError:
    import urllib.parse as urlparse
import json
from collections import defaultdict


from rezina.service.database import DBClient
from rezina.service.manager import ProcessManager
from rezina.utils.udfutil import UDFUtil


class BaseHandler(object):
    def __init__(self, query, subgroup, devices_addr):
        self._query = query
        self.path = subgroup
        self.dbc = DBClient(devices_addr['db_server'])
        self.pm = ProcessManager(devices_addr)

    def input(self, **kwargs):
        data = dict([(k, v[0])
                     for k, v in urlparse.parse_qs(self._query).items()])
        data.update(kwargs)
        return data


class MasterStatusHandler(BaseHandler):

    def GET(self):
        master_addr = defaultdict(list)
        service_addr_map = {'fwd_bckd': 'CommandForworder',
                            'fwd_frtd': 'CommandForworder',
                            'monitor_server': 'MoniterService',
                            'log_server': 'LogService',
                            'db_server': 'DBService',
                            'web_server': 'WebServer'}
        for k, v in self.dbc.get().items():
            master_addr[service_addr_map[k]].append(v)
        master_status = self.dbc.get_master_status()
        master_processes = []
        for k in master_status['master_processes']:
            master_processes.append({'name': k,
                                     'addr': master_addr[k.split('#')[-1]]})
        master_status['master_processes'] = master_processes
        return json.dumps(master_status)


class StartUpSettingHandler(BaseHandler):

    def GET(self):
        return json.dumps(self.dbc.get_startup_setting())


class WorkerStatusHandler(BaseHandler):

    def GET(self):
        data = self.dbc.get_worker_status()
        data['status'] = [{'ip': k, 'workload': v['workload']}
                          for k, v in data['status'].items()]
        [data['status'].append({'ip': k, 'workload': 0})
         for k in data['offline_workers']]
        return json.dumps(data)


class TypologyStatusHandler(BaseHandler):

    def GET(self):
        data = self.dbc.get_worker_status()['status']
        runing_typos = []
        for v in data.values():
            for p in v['processes']:
                typo_name = p.split('::')[0].split('#')[-1]
                if typo_name not in runing_typos:
                    runing_typos.append(typo_name)
        all_typos = [{'name': k,
                      'start_time': v['start_time'],
                      'interval': v['interval']}
                     for k, v in self.dbc.list_typos().items()]
        return json.dumps({'typos': all_typos, 'runing_typos': runing_typos})


class WorkerDetailHandler(BaseHandler):

    def GET(self):
        return json.dumps(self.dbc.get_worker_status()['status'][self.path])


class TypologyDetailHandler(BaseHandler):

    def GET(self):
        data = self.dbc.list_typos()[self.path]
        data = [{'name': k, 'udf': v}
                for k, v in data.items()
                if k not in ('start_time', 'interval')]

        workers = []
        for k, v in self.dbc.get_worker_status()['status'].items():
            for p in v['processes']:
                if self.path in p:
                    workers.append(k)
                    break
        return json.dumps({'setting': data, 'workers': workers})


class KillMasterHandler(BaseHandler):

    def GET(self):
        self.pm.kill_master()


class KillWorkerHandler(BaseHandler):

    def GET(self):
        if not self.dbc.get_worker_status()['status'].keys():
            return json.dumps({"message": "Faied, No workers"})
        self.pm.kill_workers()
        return json.dumps({"message": "Completed"})


class KillOneWorkerHandler(BaseHandler):

    def GET(self):
        self.pm.kill_selected_worker(self.path)
        return json.dumps({"message": "Completed"})


class TypologyActionHandler(BaseHandler):

    def GET(self):

        args = self.input()

        if 'action' not in args:
            return json.dumps({"message": "Faied, args is invalid"})
        action = args['action']
        if action not in ['start', 'stop', 'restart', 'remove', 'launch_more']:
            return json.dumps({"message": "%s is invalid." % (action)})

        if action == 'launch_more':
            try:
                value = int(args['value'])
            except:
                return json.dumps({"message": 'args is invalid'})
            else:
                self.pm.launch_more(self.path, value)
        else:
            if self.path not in self.dbc.list_typos().keys():
                return json.dumps({"message": 'typology %s not exists'
                                   % (self.path)})
            getattr(self.pm, args['action'])(self.path)
        return json.dumps({"message": 'Completed.'})
