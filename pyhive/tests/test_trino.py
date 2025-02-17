"""Trino integration tests.

These rely on having a Trino+Hadoop cluster set up.
They also require a tables created by make_test_tables.sh.
"""

from __future__ import absolute_import
from __future__ import unicode_literals

from pyhive import trino
from pyhive.tests.dbapi_test_case import with_cursor, with_complex_processing_cursor
from pyhive.tests.test_presto import TestPresto

import datetime

_HOST = 'localhost'
_PORT = '18080'


class TestTrino(TestPresto):
    __test__ = True

    def connect(self, process_complex_columns=False):
        return trino.connect(host=_HOST, port=_PORT, source=self.id(),
                             process_complex_columns=False)

    def test_bad_protocol(self):
        self.assertRaisesRegexp(ValueError, 'Protocol must be',
                                lambda: trino.connect('localhost', protocol='nonsense').cursor())

    def test_escape_args(self):
        escaper = trino.TrinoParamEscaper()

        self.assertEqual(escaper.escape_args((datetime.date(2020, 4, 17),)),
                         ("date '2020-04-17'",))
        self.assertEqual(escaper.escape_args((datetime.datetime(2020, 4, 17, 12, 0, 0, 123456),)),
                         ("timestamp '2020-04-17 12:00:00.123'",))

    @with_cursor
    def test_description(self, cursor):
        cursor.execute('SELECT 1 AS foobar FROM one_row')
        self.assertEqual(cursor.description, [('foobar', 'integer', None, None, None, None, True)])
        self.assertIsNotNone(cursor.last_query_id)

    @with_cursor
    def test_complex(self, cursor):
        cursor.execute('SELECT * FROM one_row_complex')
        # TODO Trino drops the union field

        tinyint_type = 'tinyint'
        smallint_type = 'smallint'
        float_type = 'real'
        self.assertEqual(cursor.description, [
            ('boolean', 'boolean', None, None, None, None, True),
            ('tinyint', tinyint_type, None, None, None, None, True),
            ('smallint', smallint_type, None, None, None, None, True),
            ('int', 'integer', None, None, None, None, True),
            ('bigint', 'bigint', None, None, None, None, True),
            ('float', float_type, None, None, None, None, True),
            ('double', 'double', None, None, None, None, True),
            ('string', 'varchar', None, None, None, None, True),
            ('timestamp', 'timestamp', None, None, None, None, True),
            ('binary', 'varbinary', None, None, None, None, True),
            ('array', 'array(integer)', None, None, None, None, True),
            ('map', 'map(integer,integer)', None, None, None, None, True),
            ('struct', 'row(a integer,b integer)', None, None, None, None, True),
            # ('union', 'varchar', None, None, None, None, True),
            ('decimal', 'decimal(10,1)', None, None, None, None, True),
        ])
        rows = cursor.fetchall()
        expected = [(
            True,
            127,
            32767,
            2147483647,
            9223372036854775807,
            0.5,
            0.25,
            'a string',
            '1970-01-01 00:00:00.000',
            b'123',
            [1, 2],
            {"1": 2, "3": 4},  # Trino converts all keys to strings so that they're valid JSON
            [1, 2],  # struct is returned as a list of elements
            # '{0:1}',
            '0.1',
        )]
        self.assertEqual(rows, expected)
        # catch unicode/str
        self.assertEqual(list(map(type, rows[0])), list(map(type, expected[0])))

    @with_complex_processing_cursor
    def test_complex_processing_cursor(self, cursor):
        cursor.execute('SELECT * FROM one_row_deep_complex')
        fetched_rows = cursor.fetchall()

        expected_rows = [(
            {
                'inner_int1': 2,
                'inner_int2': 3,
                'inner_int_array': [4, 5],
                'inner_row1': {
                    'inner_inner_varbinary': b'binarydata',
                    'inner_inner_string': 'some string'
                }
            },
            {
                'key1': {
                    'double_attribute': 2.2,
                    'integer_attribute': 60,
                    'map_attribute': {
                        602: ['string1', 'string2'],
                        21: ['other string', 'another string']
                    }
                },
                'key2': {
                    'double_attribute': 42.15,
                    'integer_attribute': 6060,
                    'map_attribute': {
                        14: ['11string1', 'somestring'],
                        22: ['other string', 'another string']
                    }
                }
            },
            [
                {
                    'int1': 42,
                    'double1': 24.5,
                    'string1': 'lalala'
                },
                {
                    'int1': 421,
                    'double1': 244.25,
                    'string1': 'bababa'
                }
            ]
        )]

        self.assertEqual(expected_rows, fetched_rows)
