#!/usr/bin/env python


import MySQLdb

from rezina.backends.base import StorageBackend


class Mysql(StorageBackend):

    def _generate_insert_sql(self, table_name, data):
        ''''''
        keys = [k.strip() for k in data.keys()]
        attrs = ','.join(keys)
        values = ','.join(['%('+v+')s' for v in keys])
        sql = 'INSERT INTO %s (%s) VALUES (%s)' % (table_name, attrs, values)
        return sql

    def _get_attr_type(self, attr):
        if isinstance(attr, int):
            attr_type = 'bigint'
        elif isinstance(attr, float):
            attr_type = 'double'
        else:
            attr_type = 'varchar(500)'
        return attr_type

    def _create_table(self, table_name, data):
        attrs = ', '.join(['%s %s DEFAULT NULL' % (k, self._get_attr_type(v)) for k, v in data.items()])
        sql = '''create table if not exists %s (
                    id bigint NOT NULL AUTO_INCREMENT,
                    %s,
                    create_time timestamp not null default current_timestamp,
                    PRIMARY KEY (`id`)
                    ) ENGINE=InnoDB DEFAULT CHARSET=utf8;
                    ''' % (table_name, attrs)
        return sql

    def open(self):
        self.table_name = self.kwargs['table']
        del self.kwargs['table']
        self.kwargs['port'] = int(self.kwargs['port'])
        self.inited = False
        self.conn = MySQLdb.connect(*self.args, **self.kwargs)
        self.cursor = self.conn.cursor()

    def write(self, data):
        try:
            if not isinstance(data, list):
                data = [data]
            if not self.inited:
                self.insert_sql = self._generate_insert_sql(self.table_name, data[0])
                create_table_sql = self._create_table(self.table_name, data[0])
                self.cursor.execute(create_table_sql)
                self.inited = True
            self.cursor.executemany(self.insert_sql, data)
            self.conn.commit()
        except MySQLdb.Error:
            self.conn.rollback()
            for d in data:
                self.cursor.execute(self.insert_sql, d)

    def close(self):
        self.cursor.close()
        self.conn.commit()
        self.conn.close()
