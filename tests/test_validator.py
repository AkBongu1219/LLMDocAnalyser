import unittest
import tempfile
import os
import sqlite3
import pandas as pd
from modules.validator import SchemaValidator

class TestSchemaValidator(unittest.TestCase):
    def setUp(self):
        # Use an in-memory SQLite database for testing.
        self.validator = SchemaValidator(db_path=":memory:", log_file="test_error_log.txt")
    
    def tearDown(self):
        self.validator.close()
        # Clean up the test log file if it was created.
        if os.path.exists("test_error_log.txt"):
            os.remove("test_error_log.txt")
    
    def create_temp_csv(self, content):
        """Helper function to create a temporary CSV file with given content."""
        tmp_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False)
        tmp_file.write(content)
        tmp_file.flush()
        tmp_file.close()
        return tmp_file.name

    def test_get_table_schema(self):
        """Test get_table_schema returns the correct schema for an existing table."""
        # Manually create a table.
        self.validator.cursor.execute("CREATE TABLE test_table (a INTEGER, b TEXT);")
        self.validator.conn.commit()
        schema = self.validator.get_table_schema("test_table")
        self.assertIsNotNone(schema)
        # SQLite returns types in the same case as specified.
        self.assertEqual(schema, {"a": "INTEGER", "b": "TEXT"})

    def test_check_schema_conflict_no_conflict(self):
        """Test check_schema_conflict returns no conflict when schemas match."""
        # Create a table.
        self.validator.cursor.execute("CREATE TABLE test_table (a INTEGER, b TEXT);")
        self.validator.conn.commit()
        new_schema = {"a": "INTEGER", "b": "TEXT"}
        conflict_exists, details = self.validator.check_schema_conflict("test_table", new_schema)
        self.assertFalse(conflict_exists)
        self.assertEqual(details, "Table does not exist" if new_schema is None else [])

    def test_check_schema_conflict_with_conflict(self):
        """Test check_schema_conflict detects mismatches and missing columns."""
        # Create a table with two columns.
        self.validator.cursor.execute("CREATE TABLE test_table (a INTEGER, b TEXT);")
        self.validator.conn.commit()
        # New schema changes type of 'a' and drops 'b'
        new_schema = {"a": "REAL"}
        conflict_exists, details = self.validator.check_schema_conflict("test_table", new_schema)
        self.assertTrue(conflict_exists)
        # Expect details about type mismatch and missing column 'b'
        self.assertTrue(any("Column 'a' type mismatch" in d for d in details))
        self.assertTrue(any("Column 'b' exists in table but not in new schema" in d for d in details))
    
    def test_handle_schema_conflict_overwrite(self):
        """Test handle_schema_conflict with 'overwrite' action resolves conflict by replacing table."""
        # Create an initial table with one schema.
        self.validator.cursor.execute("CREATE TABLE test_table (a INTEGER, b TEXT);")
        self.validator.conn.commit()
        # Prepare a DataFrame and a new schema that conflicts (simulate change: column a becomes REAL)
        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        new_schema = {"a": "REAL", "b": "TEXT"}
        # Call handle_schema_conflict with action "overwrite".
        result = self.validator.handle_schema_conflict("test_table", df, new_schema, action="overwrite")
        self.assertTrue(result)
        # Verify that the table has been overwritten by querying its contents.
        data_df = pd.read_sql_query("SELECT * FROM test_table", self.validator.conn)
        pd.testing.assert_frame_equal(data_df.reset_index(drop=True), df.reset_index(drop=True))
    
    def test_handle_schema_conflict_rename(self):
        """Test handle_schema_conflict with 'rename' action creates a new table."""
        # Create an initial table.
        self.validator.cursor.execute("CREATE TABLE test_table (a INTEGER, b TEXT);")
        self.validator.conn.commit()
        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        new_schema = {"a": "REAL", "b": "TEXT"}
        result = self.validator.handle_schema_conflict("test_table", df, new_schema, action="rename")
        self.assertTrue(result)
        # Look for a new table name that starts with "test_table_"
        cursor = self.validator.conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name LIKE 'test_table_%'")
        new_table = cursor.fetchone()
        self.assertIsNotNone(new_table)
        # Verify data was inserted into the new table.
        data_df = pd.read_sql_query(f"SELECT * FROM {new_table[0]}", self.validator.conn)
        pd.testing.assert_frame_equal(data_df.reset_index(drop=True), df.reset_index(drop=True))
    
    def test_handle_schema_conflict_skip(self):
        """Test handle_schema_conflict with 'skip' action skips insertion."""
        # Create an initial table.
        self.validator.cursor.execute("CREATE TABLE test_table (a INTEGER, b TEXT);")
        self.validator.conn.commit()
        df = pd.DataFrame({"a": [1, 2], "b": ["x", "y"]})
        new_schema = {"a": "REAL", "b": "TEXT"}
        result = self.validator.handle_schema_conflict("test_table", df, new_schema, action="skip")
        self.assertFalse(result)
    
    def test_validate_csv_load_file_not_found(self):
        """Test that validate_csv_load returns False when CSV file is missing."""
        result = self.validator.validate_csv_load("nonexistent.csv", "dummy_table")
        self.assertFalse(result)
    
    def test_validate_csv_load_no_conflict(self):
        """Test validate_csv_load creates table when no conflict exists."""
        csv_content = "a,b\n1,foo\n2,bar\n"
        tmp_csv = self.create_temp_csv(csv_content)
        table_name = "new_table"
        result = self.validator.validate_csv_load(tmp_csv, table_name, action="overwrite")
        os.remove(tmp_csv)
        self.assertTrue(result)
        # Verify that the table exists and data is correct.
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.validator.conn)
        expected_df = pd.DataFrame({"a": [1, 2], "b": ["foo", "bar"]})
        pd.testing.assert_frame_equal(df.reset_index(drop=True), expected_df.reset_index(drop=True))
    
    def test_validate_csv_load_with_conflict_overwrite(self):
        """Test validate_csv_load when table exists with conflict and action 'overwrite' is used."""
        # Create an initial CSV and load it.
        csv_content = "a,b\n1,foo\n2,bar\n"
        tmp_csv1 = self.create_temp_csv(csv_content)
        table_name = "conflict_table"
        result1 = self.validator.validate_csv_load(tmp_csv1, table_name, action="overwrite")
        os.remove(tmp_csv1)
