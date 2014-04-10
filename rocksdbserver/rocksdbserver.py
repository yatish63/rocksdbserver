import os
import uuid

import msgpack
import rocksdb
from funcserver import RPCServer, RPCClient, BaseHandler

def ensuretable(fn):
    def wfn(self, table, *args, **kwargs):
        if table not in self.tables:
            raise Exception('Table "%s" does not exist' % table)
        return fn(self, self.tables[table], *args, **kwargs)
    return wfn

class Table(object):
    NAME = 'noname'

    def __init__(self, data_dir, db):
        self.data_dir = os.path.join(data_dir, self.NAME)
        self.rdb = self.open()
        self.db = db

    def __str__(self):
        return '<Table: %s>' % self.NAME

    def __unicode__(self):
        return str(self)

    def open(self, prefix_length=None):
        opts = self.define_options()
        opts.create_if_missing = True
        return rocksdb.DB(self.data_dir, opts)

    def define_options(self):
        opts = rocksdb.Options()
        return opts

    def put(self, key, item, batch=None):
        db = batch or self.rdb

        key = key or item.get('_id', None) or uuid.uuid1().hex
        item['_id'] = key

        value = msgpack.packb(item)
        db.put(key, value)

        return key

    def get(self, key):
        value = self.rdb.get(key)
        if value is None: return None

        item = msgpack.unpackb(value)
        return item

    def delete(self, key, batch=None):
        db = batch or self.rdb

        db.delete(key)

    def delete_many(self, keys):
        batch = rocksdb.WriteBatch()
        for key in keys:
            self.delete(key, batch=batch)
        self.rdb.write(batch)

    def put_many(self, data):
        batch = rocksdb.WriteBatch()
        for key, item in data:
            self.put(key, item, batch=batch)
        self.rdb.write(batch)

    def get_many(self, keys):
        data = self.rdb.multi_get(keys)
        for key, value in data.iteritems():
            data[key] = None if value is None else msgpack.unpackb(value)
        return data

    def iteritems(self, prefix):
        it = self.rdb.iteritems()
        it.seek_to_first()
        it = dict(it)

        return it

    def iterkeys(self):
        it = self.rdb.iterkeys()
        it.seek_to_first()
        return list(it)

    def itervalues(self):
        it = self.rdb.iterkeys()
        it.seek_to_first()
        return list(it)

class RocksDBAPI(object):
    def __init__(self, data_dir):
        self.data_dir = data_dir
        self.tables = self.define_tables()

    def define_tables(self):
        return {}

    def list_tables(self):
        return self.tables.keys()

    @ensuretable
    def put(self, table, key, item):
        return table.put(key, item)

    @ensuretable
    def get(self, table, key):
        return table.get(key)

    @ensuretable
    def put_many(self, table, data):
        return table.put_many(data)

    @ensuretable
    def get_many(self, table, keys):
        return table.get_many(keys)

    @ensuretable
    def delete(self, table, key):
        return table.delete(key)

    @ensuretable
    def delete_many(self, table, keys):
        return table.delete_many(keys)

    @ensuretable
    def iteritems(self, table, prefix=None):
        return table.iteritems(prefix)

    @ensuretable
    def iterkeys(self, table):
        return table.iterkeys()

    @ensuretable
    def itervalues(self, table):
        return table.itervalues()

class RocksDBServer(RPCServer):
    NAME = 'RocksDBServer'
    DESC = 'RocksDB Server'

    def __init__(self, *args, **kwargs):
        super(RocksDBServer, self).__init__(*args, **kwargs)

        # make data dir if not already present
        self.data_dir = os.path.abspath(self.args.data_dir)
        if not os.path.exists(self.data_dir):
            os.makedirs(self.data_dir)

    def prepare_api(self):
        return RocksDBAPI(self.args.data_dir)

    def define_args(self, parser):
        parser.add_argument('data_dir', type=str, metavar='data-dir',
            help='Directory path where data is stored')

class RocksDBClient(RPCClient):
    pass

if __name__ == '__main__':
    RocksDBServer().start()
