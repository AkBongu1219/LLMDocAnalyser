import unittest
import tempfile
import os
import pandas as pd
from modules.chat_sheet import ChatSheet

class TestChatSheet(unittest.TestCase):
    def setUp(self):
        # Use an in-memory SQLite database for testing.
        self.chat = ChatSheet(db_path=":memory:")
    
    def tearDown(self):
        self.chat.close()
    
    def test_detect_operation(self):
        """Test that detect_operation correctly identifies SQL operations."""
        self.assertEqual(self.chat.detect_operation("Show me all records"), "select")
        self.assertEqual(self.chat.detect_operation("Insert new record"), "insert")
        self.assertEqual(self.chat.detect_operation("Update the salary of employee"), "update")
        self.assertEqual(self.chat.detect_operation("Delete record from table"), "delete")
        self.assertEqual(self.chat.detect_operation("Custom operation without keyword"), "other")
    
    def test_get_schema_context_no_tables(self):
        """Test that get_schema_context returns a message when no tables exist."""
        schema = self.chat.get_schema_context()
        self.assertEqual(schema, "No tables found in the database.")
    
    def test_get_schema_context_with_table(self):
        """Create a table and verify that get_schema_context returns correct info."""
        self.chat.cursor.execute("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
        self.chat.conn.commit()
        schema = self.chat.get_schema_context()
        self.assertIn("Table: test_table", schema)
        self.assertIn("id (INTEGER)", schema)
        self.assertIn("name (TEXT)", schema)
    
    def test_load_csv(self):
        """Test that a CSV file is loaded into the database and data can be queried."""
        csv_content = "name,age\nAlice,30\nBob,25\n"
        with tempfile.NamedTemporaryFile(mode="w+", suffix=".csv", delete=False) as tmp:
            tmp.write(csv_content)
            tmp.flush()
            tmp_path = tmp.name
        
        table_name = "people"
        self.chat.load_csv(tmp_path, table_name)
        # Verify that data was inserted by reading back from the table.
        df = pd.read_sql_query(f"SELECT * FROM {table_name}", self.chat.conn)
        expected_df = pd.DataFrame({"name": ["Alice", "Bob"], "age": [30, 25]})
        pd.testing.assert_frame_equal(df, expected_df)
        os.remove(tmp_path)
    
    def test_generate_sql_from_natural_language_without_api_key(self):
        """Test that generate_sql_from_natural_language returns an error when no API key is set."""
        self.chat.api_key = None  # Simulate no API key provided.
        response = self.chat.generate_sql_from_natural_language("Select all data")
        expected = "Error: API key not configured. Please set the OPENAI_API_KEY environment variable."
        self.assertEqual(response, expected)

if __name__ == "__main__":
    unittest.main()
