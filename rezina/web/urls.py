#!usr/bin/env python


from .handlers.handler import *


urls = {
    '/master': MasterStatusHandler,
    '/worker': WorkerStatusHandler,
    '/typology': TypologyStatusHandler,
    '/typology/(.*)': TypologyDetailHandler,
    '/worker/(.*)': WorkerDetailHandler,
    '/killworker': KillWorkerHandler,
    '/killworker/(.*)': KillOneWorkerHandler,
    '/killmaster': KillMasterHandler,
    '/typoaction/(.*)': TypologyActionHandler,
    '/settings': StartUpSettingHandler
}
