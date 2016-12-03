#!/usr/bin/evn python


''' this module implements some feathers for
supporting web and command line.
'''

from __future__ import print_function

import time
import os
from collections import defaultdict

from rezina.service.database import DBClient
from rezina.service.manager import ProcessManager
from rezina.utils.colorterminal import colorful_print


class Model(object):

    def __init__(self, dbc, pm):
        self.dbc = dbc
        self.pm = pm

    def get_master_status(self):
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
        time_str = time.strftime('%Y-%m-%d %H:%M:%S',
                                 time.localtime(master_status['timestamp']))
        master = []

        for k in master_status['master_processes']:
            pid, name = k.split('#')
            if name in master_status['alive']:
                status = 'running'
            else:
                status = 'stoped'
            master.append({'name': name, 'pid': pid, 'status': status,
                           'addr': master_addr[name]})
        return {'master': master, 'time': time_str}

    def _get_running_typos(self):
        data = self.dbc.get_worker_status()['status']
        running_typos = []
        for v in data.values():
            for p in v['processes']:
                typo_name = p.split('::')[0].split('#')[-1]
                if typo_name not in running_typos:
                    running_typos.append(typo_name)
        return running_typos

    def _get_all_comps(self):
        return self.dbc.list_typos_without_broker().keys()

    def get_typology_status(self):
        running_typos = self._get_running_typos()
        typos = []
        for k, v in self.dbc.list_typos().items():
            if k in running_typos:
                status = 'running'
            else:
                status = 'stoped'
            start_time = v['start_time'] or 'default'
            interval = v['interval'] or 'default'
            typos.append({'name': k, 'start_time': start_time,
                          'interval': interval, 'status': status})
        return typos

    def get_typology_detail(self, name):

        typos = self.dbc.list_typos()
        if name not in typos:
            return {'message': '%s not exists' % (name)}
        else:
            data = typos[name]
        data = [{'name': k, 'udf': v} for k, v in data.items() if k not in ('start_time', 'interval')]

        workers = []
        for k, v in self.dbc.get_worker_status()['status'].items():
            for p in v['processes']:
                if name in p:
                    workers.append(k)
                    break

        return {'comps': data, 'workers': workers}

    def kill_worker(self):
        if not self.dbc.get_worker_status()['status'].keys():
            return {"message": "Faied, No workers", 'err_mes': True}
        self.pm.kill_workers()
        return {"message": "kill worker done.", 'err_mes': False}

    def kill_selected_worker(self, ip):
        if ip not in self.dbc.get_worker_status()['status'].keys():
            return {"message": "Faied, %s is not running" % (ip), 'err_mes': True}
        self.pm.kill_selected_worker(ip)
        return {"message": "kill %s done" % (ip), 'err_mes': False}

    def is_exist(self, name):
        if name in self._get_all_comps():
            return True
        return False

    def oper_warpper(self, action, name):
        if not self.is_exist(name):
            return {'message': '%s not exists' % (name), 'err_mes': True}
        if '::' in name:
            return {'message': 'use typology name, usage: %s %s' % (action, name.split('::')[0]),
                    'err_mes': True}
        running_typos = self._get_running_typos()
        if action == 'start' and name in running_typos:
            return {'message': '%s is running' % (name), 'err_mes': True}

        if action == 'stop' and name not in running_typos:
            return {'message': '%s is not running' % (name), 'err_mes': True}

        getattr(self.pm, action)(name)
        return {'message': '%s %s successfully' % (name, action), 'err_mes': False}

    def launch(self, name, value):
        if not self.is_exist(name):
            return {'message': '%s not exists' % (name), 'err_mes': True}

        if '::' not in name:
            return {'message': '%s must be component. format: typo::Comp::#' % (name), 'err_mes': True}

        if name.split('::')[1] not in ('Notch', 'Bocca'):
            return {'message': 'Type must be Notch or Bocca, not %s.' % (name.split('::')[1]), 'err_mes': True}

        try:
            if int(value) > 0:
                value = int(value)
                self.pm.launch_more(name, value)
                return {'message': 'launch %s %s done.' % (value, name), 'err_mes': False}
        except:
            pass
        return {'message': '%s invalid, must be a positive number.' % (value), 'err_mes': True}


class CMLModel(Model):

    def print_message(self, message):
        if message['err_mes']:
            mes_color = 'red'
        else:
            mes_color = 'green'
        colorful_print(message['message'], mes_color)

    def cml_kill_workers(self):
        self.print_message(self.kill_worker())

    def cml_kill_selected_worker(self, ip):
        self.print_message(self.kill_selected_worker(ip))

    def cml_kill_master(self):
        self.pm.kill_master()
        colorful_print("kill master done. [OK]", 'green', True)
        mess = "console quit, because at this time, console could not talk to the master and execute any command."
        colorful_print(mess, 'yellow')
        os._exit(0)

    def cml_oper_warpper(self, action, name):
        self.print_message(self.oper_warpper(action, name))

    def cml_launch(self, name, value):
        self.print_message(self.launch(name, value))

    def cml_list_typology(self, name):
        if name:
            data = self.get_typology_detail(name)
            if 'message' in data:
                colorful_print(data['message'], 'red')
                return
            print()
            print(name)
            print('=' * len(name))
            for comp in data['comps']:
                print('.' * len(comp['name']))
                print(comp['name'])
                print('.' * len(comp['name']))
                for k, v in comp['udf'].items():
                    print('{:<17}: {}'.format(k, v))
            print()
            return
        data = self.get_typology_status()
        if not data:
            print("No typology.")
            return
        head = "Typology"
        print(head)
        print("=" * len(head))
        print('{:<30}{:<20}{:<10}{}'.format('name', 'start time', 'interval', 'status'))
        for d in data:
            print('{name:<30}{start_time:<20}{interval:<10}{status}'.format(**d))
        print()

    def cml_list_workers(self, ip):
        if ip:
            colorful_print('unknow arg %s, usage: list workers' % (ip), 'red')
            return
        data = self.dbc.get_worker_status()
        head = 'Worker Status:'
        print(head)
        print('=' * len(head))
        print()
        if data['new_workers']:
            sub_head = 'new workers:'
            print(sub_head)
            print('-' * len(sub_head))
            colorful_print(os.linesep.join(data['new_workers']), 'green')
            print()
        if data['offline_workers']:
            sub_head = 'offline workers:'
            print(sub_head)
            print('-' * len(sub_head))
            colorful_print(os.linesep.join(data['offline_workers']), 'red')
            print()
        if not data['status']:
            print('No worker is running.')
            print()
            return
        for k, v in data['status'].items():
            time_str = time.strftime('%Y-%m-%d %H:%M:%S',
                                     time.localtime(v['timestamp']))
            sub_head = '{:<16}time:{:<25}workerload:{}'.format(k, time_str, v['workload'])
            print('.' * len(sub_head))
            print(sub_head)
            print('.' * len(sub_head))
            if v['processes']:
                proc_head = 'current running processes:'
                print(proc_head)
                print('.' * len(proc_head))
                print(os.linesep.join(v['processes']))
            else:
                print('No typology is running on %s' % (k,))
                print()
            if v['new_process']:
                print()
                proc_head = 'new processes:'
                print(proc_head)
                print('.' * len(proc_head))
                print(os.linesep.join(v['new_process']))
            if v['offline_process']:
                print()
                proc_head = 'offline processes:'
                print(proc_head)
                print('.' * len(proc_head))
                print(os.linesep.join(v['offline_process']))
        print()

    def cml_list_master(self, err_arg):
        if err_arg:
            colorful_print('unknow arg %s' % (err_arg), 'red')
            return
        data = self.get_master_status()
        head = 'Master Processes [%s]:' % (data['time'])
        print(head)
        print("=" * len(head))
        for d in data['master']:
            print('{pid:<10}{name:<20}{status:<10}{addr}'.format(**d))
        print()

    def cml_list_settings(self, err_arg):
        if err_arg:
            colorful_print('unknow arg %s' % (err_arg), 'red')
            return
        data = self.dbc.get_startup_setting()
        head = 'Startup Settings'
        print(head)
        print('=' * len(head))
        for k, v in data.items():
            print('{:<20}{}'.format(k, v))
        print()
