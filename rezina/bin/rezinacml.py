#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------
#
#
# -----------------------------------------
from __future__ import print_function

import cmd
import os
import subprocess
import argparse
import textwrap
import sys

from rezina.service.database import DBClient as DBC
from rezina.service.manager import ProcessManager as PM
from rezina.bin.master import init_master_service
from rezina.bin.worker import init_worker
from rezina.utils.network import get_ip
from rezina.utils.daemon import daemonize
from rezina.utils.colorterminal import colorful_print, color
from rezina.utils.timeout import timeout
from rezina.utils.model import CMLModel


class RezinaCLI(object):

    def __init__(self):
        self.hint = '''
        command: rezina-cli runmaster
        args:
            -H master_ip
            -P master_port            (default 12345)
            -D run as daemon          (default False)
            -L log directory          (default ~/rezina/log)
            -W workerspace directory  (default ~/rezina/workerspace)
            -HP http-port             (default 31238)
            -R recrate DB             (default False)
        -------------------------------------------------------------
        command: rezina-cli runworker
        args:
            -H master_ip
            -P master_port            (default 12345)
            -WIP worker_ip
            -D run as daeom           (default False)
        -------------------------------------------------------------
        command: rezina-cli runconsole
        args:
            -H master_ip
            -P master_port            (default 12345)
        '''
        parser_parent = argparse.ArgumentParser(add_help=False)

        parser_parent.add_argument('-H', '--host', default=get_ip(),
                                   help='ip of rezina master server')
        parser_parent.add_argument('-P', '--port', default='12345',
                                   help='port of rezina rezina server')

        parser = argparse.ArgumentParser(
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=color(textwrap.dedent(self.hint), 'yellow'))

        subparsers = parser.add_subparsers()

        sp_list = []

        for sub_cmd in ['runmaster', 'runworker', 'runconsole']:
            sp = subparsers.add_parser(sub_cmd, parents=[parser_parent])
            sp.set_defaults(func=getattr(self, 'run_' + sub_cmd))
            sp_list.append(sp)

        sp_list[0].add_argument('-D', '--daemon', action='store_true',
                                help='run as a daemon process')
        sp_list[0].add_argument('-L', '--log_dir', dest='log_dir',
                                default=os.path.join(os.path.expanduser('~'),
                                                     'rezina', 'logs'),
                                help='log directory')

        sp_list[0].add_argument('-W', '--workspace', dest='workspace',
                                default=os.path.join(os.path.expanduser('~'),
                                                     'rezina', 'workspace'),
                                help='workspace for syncing files')

        sp_list[0].add_argument('-R', '--refresh', action='store_true',
                                help='creating a new database file.')

        sp_list[0].add_argument('-HP', '--http_port', dest='http_port',
                                default=31218,
                                help='web server listening port')

        sp_list[1].add_argument('-D', '--daemon', action='store_true',
                                help='run as a daemon process')

        sp_list[1].add_argument('-WIP', '--worker_ip', dest='worker_ip',
                                default=get_ip(),
                                help='the ip of this worker used to communicat\
                                 with master')

        args = parser.parse_args()
        try:
            args.func(args)
        except AttributeError:
            colorful_print(textwrap.dedent(self.hint), 'yellow')

    def run_runmaster(self, args):
        self._check_is_master_running(args.host, args.port)
        try:
            os.makedirs(args.workspace)
        except OSError:
            pass

        if args.daemon:
            hint = '''
            Daemon Mode Enabled
            ===================
            If master does not run as expect, please check the -H and -P
            parameters and make sure they are avilable.
            If you use diffrent -H, -P or -HP parameter from last run,
            add -R to make the changes effective.
            '''
            colorful_print(textwrap.dedent(hint), 'yellow', True)
            daemonize()
        try:
            init_master_service(args.host, int(args.port),
                                log_dir=args.log_dir, daemon=args.daemon,
                                refresh=args.refresh, http_port=args.http_port,
                                workspace=args.workspace)
        except KeyboardInterrupt:
            colorful_print('Quit', 'yellow')

    def run_runworker(self, args):
        devices_addr = self._check_db_connection(args.host, args.port)
        running_workers = self.dbc.get_worker_status()['status'].keys()
        if args.worker_ip in running_workers:
            colorful_print('[Failed] %s is running.' % (args.worker_ip), 'red')
            hint = '''
            Master think %s has already been started,
            if it is killed and you want to restart immediately,
            please waiting for 9 seconds at most and retry.
            ''' % (args.worker_ip)
            colorful_print(textwrap.dedent(hint), "yellow")
            os._exit(-1)
        colorful_print('Worker Connected successfully. [OK]',
                       'green', True)
        if args.daemon:
            daemonize()
        init_worker(devices_addr, args.worker_ip)

    def run_runconsole(self, args):
        self._check_db_connection(args.host, args.port)
        try:
            Console(self.db_server_addr).cmdloop()
        except KeyboardInterrupt:
            colorful_print('Quit', 'yellow')

    def _check_is_master_running(self, host, port):
        colorful_print('Starting... ', 'yellow', end=' ')
        sys.stdout.flush()
        db_server_addr = 'tcp://' + host + ':' + port
        with timeout(1):
            dbc = DBC(db_server_addr)
            devices_addr = dbc.get()
            if devices_addr is not None:
                colorful_print('Master is running [Failed] ', 'red')
                os._exit(-1)
        colorful_print('[Done]', 'green')

    def _check_db_connection(self, host, port):
        self.db_server_addr = 'tcp://' + host + ':' + port
        with timeout(2):
            self.dbc = DBC(self.db_server_addr)
            devices_addr = self.dbc.get()
            if devices_addr is None:
                hint = '''
                [Error] Connection Timeout.
                1. check if master is alive.
                2. make sure the ip and port used to connect master are correct
                '''
                colorful_print(textwrap.dedent(hint), 'red', True)
                os._exit(-1)
        return devices_addr


class Console(cmd.Cmd):
    '''
    Welcome to the Rezina Console.

    Type help to see all avilable commands.
    '''

    def __init__(self, db_server_addr):
        cmd.Cmd.__init__(self)
        self.dbclient = DBC(db_server_addr)
        self.pm = PM(self.dbclient.get())
        self.prompt = 'rezina> '
        self.intro = color(textwrap.dedent(self.__doc__), 'green')
        self.model = CMLModel(self.dbclient, self.pm)

    def do_shell(self, line):
        '''
        Run shell command in rezina console
        -----------------------------------------------------
        shell command
        '''
        try:
            s = subprocess.check_output(line, shell=True)
        except subprocess.CalledProcessError:
            pass
        else:
            print(s)

    def default(self, line):
        colorful_print('[Error]: Unkonwn Command: %s' % (line,))

    def do_list(self, line):
        '''
        List Informations about typology, master and worker
        -----------------------------------------------------------
        list master                          list master info
        list workers                         list all workers
        list typology or list                list all typology
        list typology typo_name              list typo_name
        list settings                        list startup settings
        '''
        parser = argparse.ArgumentParser(prog="list",
                                         description=self.do_list.__doc__)

        parser.add_argument('t', nargs='?', default='typology',
                            choices=['typology', 'workers',
                                     'master', 'settings'])

        cmd_args = line.strip().split()
        try:
            args = parser.parse_args(cmd_args[:1])
        except SystemExit:
            return
        value = ' '.join(cmd_args[1:])
        getattr(self.model, 'cml_list_'+args.t)(value)

    def do_start(self, name):
        '''
        Start typology
        ---------------
        start typo_name
        '''
        self.model.cml_oper_warpper('start', name)

    def do_stop(self, name):
        '''
        Stop typology
        ---------------
        stop typo_name
        '''
        self.model.cml_oper_warpper('stop', name)

    def do_remove(self, name):
        '''
        Remove typology (stop first and remove settings from db)
        ---------------------------------------------------------
        remove typo_name
        '''
        self.model.cml_oper_warpper('remove', name)

    def do_restart(self, name):
        '''
        Restart typology
        ---------------
        restart typo_name
        '''
        self.model.cml_oper_warpper('restart', name)

    def do_kill(self, line):
        '''
        Kill all workers, master or both
        ----------------------------------------------
        kill master            kill rezina master
        kill workers           kill all workers
        kill all               kill workers and master
        '''
        parser = argparse.ArgumentParser(
            prog="kill",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            description=self.do_kill.__doc__)

        parser.add_argument('t', nargs='?', default='workers',
                            choices=['workers', 'master', 'all'],
                            help='kill worker, master or both')
        try:
            args = parser.parse_args(line.split())
        except SystemExit:
            return
        if args.t == 'workers':
            self.model.cml_kill_workers()
        if args.t == 'master':
            self.model.cml_kill_master()
        if args.t == 'all':
            self.model.cml_kill_workers()
            self.model.cml_kill_master()

    def do_launch(self, line):
        '''
        Launch more components to speed up execution.
        note: only Notct or Bocca can be launched.
        ----------------------------------------------------
        launch component number

        example:
            launch typo1::Notch::1 30
            launch typo2::Bocca::0 2
        '''
        args = line.strip().split()
        if len(args) != 2:
            colorful_print("launch take two args", 'red')
            return
        self.model.cml_launch(*args)

    def do_workerkill(self, ip):
        '''
        Kill one worker
        -----------------
        workerkill worker_ip
        '''
        self.model.cml_kill_selected_worker(ip)

    def do_exit(self, line):
        '''
        quit rezina console
        '''
        return True

    def do_EOF(self, line):
        '''
        quit rezina console when Ctrl-D pressed
        '''
        return self.do_exit(line)


if __name__ == '__main__':
    RezinaCLI()
