#!/usr/bin/env python
# -*- coding: utf-8 -*-

# -----------------------------------------
#
#
# -----------------------------------------


import inspect
import importlib
import pkgutil
import os
import imp
import sys
from collections import defaultdict


class UDFUtil(object):

    def __init__(self):
        udf_worker_root_path = os.path.join(os.path.expanduser('~'), '.rezina')
        if udf_worker_root_path not in sys.path:
            sys.path.insert(0, udf_worker_root_path)

    def import_udf(self, mod_name, cls_name, obj_name):
        module = importlib.import_module(mod_name)
        try:
            module = reload(module)
        except NameError:
            module = importlib.reload(module)
        if cls_name:
            cls_obj = getattr(module, cls_name)
            return getattr(cls_obj(), obj_name)
        return getattr(module, obj_name)

    def get_obj_imp_tup(self, obj):
        module = inspect.getmodule(obj)
        mod_name = module.__name__
        if inspect.isclass(obj):
            return (mod_name, obj.__name__, '')
        elif inspect.ismethod(obj):
            try:
                cls_name = obj.im_class.__name__
            except AttributeError:
                cls_name = obj.__self__.__class__.__name__
        else:
            cls_name = ''
        return (mod_name, cls_name, obj.__name__)

    def get_bocca_instance(self, logger, mod_name, cls_name, args, kwargs):
        module = importlib.import_module(mod_name)
        try:
            module = reload(module)
        except NameError:
            module = importlib.reload(module)
        cls_obj = getattr(module, cls_name)
        return cls_obj(logger, *args, **kwargs)

    def get_udfs_tree(self, module):
        udf_tree = {}
        module = importlib.import_module(module)

        functions = inspect.getmembers(module, inspect.isfunction)
        udf_tree['functions'] = [t[0] for t in functions
                                 if not t[0].startswith('_')]

        udf_tree['classes'] = {}
        classes = inspect.getmembers(module, inspect.isclass)
        for class_name, class_obj in classes:
            udf_tree['classes'][class_name] = [m for m in dir(class_obj)
                                               if inspect.ismethod(
                                               getattr(class_obj(), m)) and
                                               not m.startswith('_')]
        return udf_tree

    def list_all_modules(self, package):
        prefix = package + '.'
        package = importlib.import_module(package)

        modules = []
        for importer, mod_name, ispkg in pkgutil.walk_packages(
                package.__path__, prefix):
            if ispkg is False:
                modules.append(mod_name)
        return modules

    def list_udfs_by_pkg(self, package):
        udfs = {}
        for module in self.list_all_modules(package):
            # only list available udfs
            try:
                udfs[module] = self.get_udfs_tree(module)
            except:
                continue
        return udfs

    def list_udfs_by_path(self, path):
        exclude_dirs = ['.git', '.svn', '.hg']
        failed_modules = []
        if path not in sys.path:
            sys.path.insert(0, path)
        udfs = defaultdict(dict)
        for root, dirs, files in os.walk(path):
            dirs[:] = [d for d in dirs if d not in exclude_dirs]
            try:
                root = root.split(path, 1)[-1]
            except IndexError:
                root = ''
            root = root.replace(os.sep, '.')
            for f in files:
                f, ext = os.path.splitext(f)
                if ext != '.py':
                    continue
                if root:
                    module = root + '.' + f
                else:
                    module = f
                try:
                    udfs[root][f] = self.get_udfs_tree(module)
                except ImportError:
                    failed_modules.append(module)
        return {'udf_tree': udfs, 'failed_mod': failed_modules}
