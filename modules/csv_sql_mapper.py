import pandas as pd
import sqlite3
import os

class CSVSQLMapper:
    def __init__(self, db_path="sheet_data.db"):
        """Initialize the mapper with a database path."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        print(f"Connected to database: {db_path}")
        
    def create_table_manually(self, table_name, columns):
        """
        Manually create a table in SQLite.
        
        Args:
            table_name (str): Name of the table to create
            columns (list): List of tuples (column_name, data_type)
        """
        columns_str = ", ".join([f"{name} {dtype}" for name, dtype in columns])
        create_statement = f"CREATE TABLE IF NOT EXISTS {table_name} ({columns_str})"
        
        try:
            self.cursor.execute(create_statement)
            self.conn.commit()
            print(f"Table '{table_name}' created successfully.")
        except sqlite3.Error as e:
            print(f"Error creating table: {e}")
    
    def load_csv_to_dataframe(self, csv_path):
        """
        Load a CSV file into a pandas DataFrame.
        
        Args:
            csv_path (str): Path to the CSV file
            
        Returns:
            DataFrame: The loaded data
        """
        try:
            df = pd.read_csv(csv_path)
            print(f"CSV loaded successfully from {csv_path}")
            print(f"Data preview:\n{df.head()}")
            return df
        except Exception as e:
            print(f"Error loading CSV: {e}")
            return None
    
    def insert_dataframe_to_table(self, df, table_name, if_exists="replace"):
        """
        Insert DataFrame data into SQLite table.
        
        Args:
            df (DataFrame): pandas DataFrame with data
            table_name (str): Target table name
            if_exists (str): How to behave if table exists ('fail', 'replace', 'append')
        """
        try:
            df.to_sql(table_name, self.conn, if_exists=if_exists, index=False)
            print(f"Data inserted into table '{table_name}' successfully.")
        except Exception as e:
            print(f"Error inserting data: {e}")
    
    def execute_query(self, query):
        """
        Execute an SQL query and return results.
        
        Args:
            query (str): SQL query to execute
            
        Returns:
            list: Query results
        """
        try:
            result = pd.read_sql_query(query, self.conn)
            return result
        except Exception as e:
            print(f"Error executing query: {e}")
            return None
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

# Example usage
if __name__ == "__main__":
    mapper = CSVSQLMapper()
    
    # Manually create a table
    mapper.create_table_manually("employees", [
        ("id", "INTEGER PRIMARY KEY"),
        ("name", "TEXT"),
        ("department", "TEXT"),
        ("salary", "REAL")
    ])
    
    # Load a CSV (assuming sample.csv exists)
    if os.path.exists("sample.csv"):
        df = mapper.load_csv_to_dataframe("sample.csv")
        if df is not None:
            mapper.insert_dataframe_to_table(df, "employees")
            
            # Run some basic queries
            print("\nRunning SELECT query:")
            result = mapper.execute_query("SELECT * FROM employees LIMIT 5")
            print(result)
            
            print("\nRunning WHERE query:")
            result = mapper.execute_query("SELECT name, salary FROM employees WHERE salary > 50000")
            print(result)
    else:
        print("Sample CSV file not found. Please create one to test.")
    
    mapper.close()