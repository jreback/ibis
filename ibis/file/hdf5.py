import pandas as pd
import ibis.expr.operations as ops
from ibis.file.client import FileClient
from ibis.pandas.core import pre_execute, execute  # noqa
from ibis.pandas.client import pandas_dtypes_to_ibis_schema


def connect(path):
    """Create a HDF5Client for use with Ibis

    Parameters
    ----------
    path: str or pathlib.Path

    Returns
    -------
    HDF5Client
    """
    return HDFClient(path)


class HDFTable(ops.DatabaseTable):
    pass


class HDFClient(FileClient):
    extension = 'h5'

    def insert(self, path, key, t, format='table',
               data_columns=True, **kwargs):

        path = self.root / path
        data = execute(t)
        data.to_hdf(str(path), key, format=format,
                    data_columns=data_columns, **kwargs)

    def table(self, name, path):
        if name not in self.list_tables(path):
            raise AttributeError(name)

        # get the schema
        with pd.HDFStore(str(path), mode='r') as store:
            df = store.select(name, start=0, stop=0)
            schema = pandas_dtypes_to_ibis_schema(df, {})

        t = HDFTable(name, schema, self).to_expr()
        self.dictionary[name] = path
        return t

    def list_tables(self, path=None):
        # tables are individual tables within a file

        if path is None:
            path = self.root

        if path.is_file() and str(path).endswith(self.extension):

            with pd.HDFStore(str(path), mode='r') as store:
                # strip leading /
                return [k[1:] for k in store.keys()]

        return []

    def list_databases(self, path=None):
        # databases are dir & a .h5 file
        if path is None:
            path = self.root

        tables = []
        if path.is_dir():
            for d in path.iterdir():
                if d.is_dir():
                    tables.append(d.name)
                elif d.is_file():
                    if str(d).endswith(self.extension):
                        tables.append(d.stem)
        elif path.is_file():
            # by definition we are at the db level at this point
            pass

        return tables


@pre_execute.register(HDFTable, HDFClient)
def hdf_pre_execute_table(op, client, scope=None, **kwargs):
    key = op.name
    path = client.dictionary[key]
    df = pd.read_hdf(str(path), key, mode='r')
    return {op: df}
