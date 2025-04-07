import unittest
import tempfile
import os
import sqlite3
import pandas as pd
from modules.schema_inferrer import SchemaInferrer

class TestSchemaInferrer(unittest.TestCase):
    def setUp(self):
        # Use an in-memory SQLite database for testing.
        self.inferrer = SchemaInferrer(db_path=":memory:")

    def tearDown(self):
        self.inferrer.close()

    def create_temp_csv(self, content):
        """Helper function to create a temporary CSV file with given content."""
        tmp_file = tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False)
        tmp_file.write(content)
        tmp_file.flush()
        tmp_file.close()
        return tmp_file.name

    def test_infer_schema_from_csv(self):
        """
        Test that the CSV is loaded and the correct schema is inferred.
        Expect:
          - Integer column: 'a'
          - Float column: 'b'
          - Text column: 'c'
        """
        csv_content = "a,b,c\n1,1.1,foo\n2,2.2,bar\n3,3.3,baz\n"
        tmp_csv = self.create_temp_csv(csv_content)
        df, schema = self.inferrer.infer_schema_from_csv(tmp_csv)
        os.remove(tmp_csv)

        # Create expected DataFrame.
        expected_df = pd.DataFrame({
            "a": [1, 2, 3],
            "b": [1.1, 2.2, 3.3],
            "c": ["foo", "bar", "baz"]
        })
        pd.testing.assert_frame_equal(df.reset_index(drop=True), expected_df)
        
        # Expected schema: column 'a' should be INTEGER, 'b' REAL, 'c' TEXT.
        expected_schema = {"a": "INTEGER", "b": "REAL", "c": "TEXT"}
        self.assertEqual(schema, expected_schema)

    def test_generate_create_table_sql(self):
        """
        Test that the generated CREATE TABLE SQL statement is as expected.
        """
        schema = {"a": "INTEGER", "b": "REAL", "c": "TEXT"}
        table_name = "test_table"
        create_sql = self.inferrer.generate_create_table_sql(table_name, schema)
        # Check key substrings to allow for minor formatting differences.
        self.assertIn("CREATE TABLE IF NOT EXISTS test_table", create_sql)
        self.assertIn('"a" INTEGER', create_sql)
        self.assertIn('"b" REAL', create_sql)
        self.assertIn('"c" TEXT', create_sql)
        self.assertTrue(create_sql.strip().endswith(");"))

    def test_create_table_from_csv(self):
        """
        Test creating a table from CSV:
         - The CSV is loaded.
         - The table is created.
         - Data is inserted.
         - Querying returns the expected data.
        """
        csv_content = "a,b,c\n1,1.1,foo\n2,2.2,bar\n3,3.3,baz\n"
        tmp_csv = self.create_temp_csv(csv_content)
        table_name = "auto_table"
        success = self.inferrer.create_table_from_csv(tmp_csv, table_name)
        os.remove(tmp_csv)
        self.assertTrue(success)

        # Verify that the table exists by querying sqlite_master.
        cursor = self.inferrer.conn.cursor()
        cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'")
        result = cursor.fetchone()
        self.assertIsNotNone(result)

        # Verify that data was inserted by selecting from the table.
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.inferrer.conn)
        expected_df = pd.DataFrame({
            "a": [1, 2, 3],
            "b": [1.1, 2.2, 3.3],
            "c": ["foo", "bar", "baz"]
        })
        pd.testing.assert_frame_equal(df.reset_index(drop=True), expected_df)

if __name__ == "__main__":
    unittest.main()
