from tinydb.storages import Storage, JSONStorage
from tinydb.queries import query, where

__all__ = ('TinyDB', 'where')


class TinyDB(object):
    """
    A plain & simple DB.

    TinyDB stores all types of python objects using a configurable backend.
    It has support for handy querying and tables.

    >>> db = TinyDB('<memory>', backend=MemoryBackend)
    >>> db.insert({'data': 5})  # Insert into '_default' table
    >>> db.search(where('data') == 5)
    [{'data': 5, '_id': 1}]
    >>> # Now let's use a table
    >>> tbl = db.table('our_table')
    >>> for i in range(10):
    ...     tbl.insert({'data': i % 2})
    >>> len(tbl.search(where('data') == 0))
    5
    >>>

    """

    _table_cache = {}

    def __init__(self, *args, **kwargs):
        storage = kwargs.pop('storage', JSONStorage)
        #: :type: Storage
        self._storage = storage(*args, **kwargs)
        self._table = self.table('_default')

    def table(self, name='_default'):
        """
        Get access to a specific table.

        :param name: The name of the table.
        :type name: str
        """
        if name in self._table_cache:
            return self._table_cache[name]

        table = Table(name, self)
        self._table_cache[name] = table
        return table

    def purge_all(self):
        """
        Purge all tables from the database. CANT BE REVERSED!
        """
        self._write({})

    def _read(self, table=None):
        """
        Reading access to the backend.

        :param table: The table, we want to read, or None to read the 'all
        tables' dict.
        :type table: str or None
        :returns: all values
        :rtype: dict, list
        """

        if not table:
            try:
                return self._storage.read()
            except ValueError:
                return {}

        try:
            return self._read()[table]
        except (KeyError, TypeError):
            return []

    def _write(self, values, table=None):
        """
        Writing access to the backend.

        :param table: The table, we want to write, or None to write the 'all
        tables' dict.
        :type table: str or None
        :param values: the new values to write
        :type values: list, dict
        """

        if not table:
            self._storage.write(values)
        else:
            current_data = self._read()
            current_data[table] = values

            self._write(current_data)

    def __len__(self):
        """
        Get the total number of elements in the DB.
        """
        return len(self._table)

    def __contains__(self, item):
        """
        A shorthand for ``query(...) == ... in db.table()``
        """
        return item in self.table()

    def __getattr__(self, name):
        return getattr(self._table, name)


class Table(object):
    """
    Represents a single TinyDB Table.
    """

    def __init__(self, name, db):
        """
        Get access to a table.

        :param name: The name of the table.
        :type name: str
        :param db: The parent database.
        :type db: TinyDB
        """
        self.name = name
        self._db = db
        self._queries_cache = {}

        try:
            self._last_id = self._read().pop()['_id']
        except IndexError:
            self._last_id = 0

    def _read(self):
        """
        Reading access to the DB.

        :returns: all values
        :rtype: list
        """

        return self._db._read(self.name)

    def _write(self, values):
        """
        Writing access to the DB.

        :param values: the new values to write
        :type values: list
        """

        self._clear_query_cache()
        self._db._write(values, self.name)

    def __len__(self):
        """
        Get the total number of elements in the table.
        """
        return len(self.all())

    def __contains__(self, condition):
        """
        Equals to bool(table.search(condition)))
        """
        return bool(self.search(condition))

    def all(self):
        """
        Get all elements stored in the table.

        :returns: a list with all elements.
        :rtype: list
        """

        return self._read()

    def insert(self, element):
        """
        Insert a new element into the table.

        element has to be a dict, not containing the key 'id'.
        """

        self._last_id += 1
        next_id = self._last_id

        element['_id'] = next_id

        data = self._read()
        data.append(element)

        self._write(data)

    def remove(self, cond):
        """
        Remove the element matching the condition.

        :param cond: the condition or ID or a list of IDs
        :type cond: query, int, list
        """

        to_remove = self.search(cond)
        self._write([e for e in self.all() if e not in to_remove])

    def purge(self):
        """
        Purge the table by removing all elements.
        """
        self._write([])

    def search(self, cond):
        """
        Search for all elements matching a 'where' cond or get elements
        by a list of IDs.

        :param cond: the condition to check against
        :type cond: query

        :returns: list of matching elements
        :rtype: list
        """

        if cond in self._queries_cache:
            return self._queries_cache[where]
        else:
            elems = [e for e in self.all() if cond(e)]
            self._queries_cache[where] = elems

            return elems

    def get(self, cond):
        """
        Search for exactly one element matching a 'where' condition.

        :param cond: the condition to check against
        :type cond: query

        :returns: the element or None
        :rtype: dict or None
        """

        for el in self.all():
            if cond(el):
                return el

    def _clear_query_cache(self):
        """

        """
        self._queries_cache = {}