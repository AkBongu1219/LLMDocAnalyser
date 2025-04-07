import unittest
import tempfile
import os
import pandas as pd
from modules.csv_sql_mapper import CSVSQLMapper

class TestCSVSQLMapper(unittest.TestCase):
    def setUp(self):
        # Use an in-memory SQLite database for testing.
        self.mapper = CSVSQLMapper(db_path=":memory:")

    def tearDown(self):
        self.mapper.close()

    def test_create_table_manually(self):
        """
        Test that a table is created successfully.
        """
        table_name = "employees"
        columns = [
            ("id", "INTEGER PRIMARY KEY"),
            ("name", "TEXT"),
            ("department", "TEXT"),
            ("salary", "REAL")
        ]
        self.mapper.create_table_manually(table_name, columns)
        # Check the sqlite_master table to ensure the table exists.
        query = f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table_name}'"
        result = self.mapper.execute_query(query)
        self.assertIsNotNone(result)
        self.assertFalse(result.empty)
        # The returned table name should match.
        self.assertEqual(result.iloc[0]['name'], table_name)

    def test_load_csv_to_dataframe(self):
        """
        Test loading a CSV file into a DataFrame.
        """
        # Create a temporary CSV file.
        csv_content = "name,age,city\nAlice,30,New York\nBob,25,Chicago\n"
        with tempfile.NamedTemporaryFile(mode='w+', suffix=".csv", delete=False) as tmp:
            tmp.write(csv_content)
            tmp.flush()
            tmp_path = tmp.name

        # Load the CSV using the mapper.
        df = self.mapper.load_csv_to_dataframe(tmp_path)
        # Expected DataFrame.
        expected_df = pd.DataFrame({
            "name": ["Alice", "Bob"],
            "age": [30, 25],
            "city": ["New York", "Chicago"]
        })
        # Compare the DataFrames.
        pd.testing.assert_frame_equal(df.reset_index(drop=True), expected_df)
        os.remove(tmp_path)

    def test_insert_dataframe_to_table_and_execute_query(self):
        """
        Test inserting a DataFrame into a table and then retrieving it.
        """
        table_name = "test_table"
        df = pd.DataFrame({
            "name": ["Alice", "Bob"],
            "age": [30, 25]
        })
        # Insert the DataFrame into the table.
        self.mapper.insert_dataframe_to_table(df, table_name, if_exists="replace")
        # Retrieve data from the table.
        result = self.mapper.execute_query(f"SELECT * FROM {table_name}")
        self.assertFalse(result.empty)
        # Compare the result DataFrame with the original one.
        pd.testing.assert_frame_equal(
            result.sort_index(axis=1).reset_index(drop=True),
            df.sort_index(axis=1).reset_index(drop=True)
        )

    def test_execute_query_error(self):
        """
        Test that executing an invalid query returns None.
        """
        # Querying a non-existing table should trigger an error and return None.
        result = self.mapper.execute_query("SELECT * FROM non_existing_table")
        self.assertIsNone(result)

if __name__ == "__main__":
    unittest.main()
