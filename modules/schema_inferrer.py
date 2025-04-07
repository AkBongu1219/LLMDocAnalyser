import pandas as pd
import sqlite3
import os
import numpy as np

class SchemaInferrer:
    def __init__(self, db_path="sheet_data.db"):
        """Initialize with database connection."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
    
    def infer_schema_from_csv(self, csv_path):
        """
        Infer schema from CSV file.
        
        Args:
            csv_path (str): Path to CSV file
            
        Returns:
            tuple: (DataFrame, schema_dict)
        """
        try:
            # Load CSV with pandas
            df = pd.read_csv(csv_path)
            
            # Infer schema
            schema = {}
            for column in df.columns:
                # Check if column contains only numeric values
                if pd.api.types.is_numeric_dtype(df[column]):
                    # Check if all values are integers
                    if df[column].dropna().apply(lambda x: x.is_integer() if isinstance(x, float) else True).all():
                        schema[column] = "INTEGER"
                    else:
                        schema[column] = "REAL"
                else:
                    schema[column] = "TEXT"
            
            print(f"Schema inferred from CSV: {schema}")
            return df, schema
        except Exception as e:
            print(f"Error inferring schema: {e}")
            return None, None
    
    def generate_create_table_sql(self, table_name, schema):
        """
        Generate SQL CREATE TABLE statement from schema.
        
        Args:
            table_name (str): Name of the table
            schema (dict): Column name to data type mapping
            
        Returns:
            str: SQL CREATE TABLE statement
        """
        columns = []
        for col_name, data_type in schema.items():
            # Sanitize column name (replace spaces with underscores)
            safe_col_name = col_name.replace(" ", "_")
            columns.append(f'"{safe_col_name}" {data_type}')
        
        create_statement = f"CREATE TABLE IF NOT EXISTS {table_name} (\n  "
        create_statement += ",\n  ".join(columns)
        create_statement += "\n);"
        
        return create_statement
    
    def create_table_from_csv(self, csv_path, table_name):
        """
        Create a table from CSV by inferring its schema.
        
        Args:
            csv_path (str): Path to CSV file
            table_name (str): Name of the table to create
            
        Returns:
            bool: Success or failure
        """
        # Infer schema
        df, schema = self.infer_schema_from_csv(csv_path)
        if df is None or schema is None:
            return False
        
        # Generate and execute CREATE TABLE statement
        create_sql = self.generate_create_table_sql(table_name, schema)
        print(f"Generated SQL:\n{create_sql}")
        
        try:
            self.cursor.execute(create_sql)
            self.conn.commit()
            print(f"Table '{table_name}' created successfully.")
            
            # Insert data
            df.to_sql(table_name, self.conn, if_exists="replace", index=False)
            print(f"Data inserted into table '{table_name}'.")
            return True
        except sqlite3.Error as e:
            print(f"Error creating table: {e}")
            return False
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed.")

# Example usage
if __name__ == "__main__":
    inferrer = SchemaInferrer()
    
    # Test with a sample CSV
    if os.path.exists("sample.csv"):
        inferrer.create_table_from_csv("sample.csv", "auto_table")
        
        # Verify the table was created
        conn = sqlite3.connect("sheet_data.db")
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='auto_table'")
        result = cursor.fetchone()
        if result:
            print("Table verification: Success!")
            
            # Show table schema
            cursor.execute("PRAGMA table_info(auto_table)")
            schema_info = cursor.fetchall()
            print("\nTable schema:")
            for col in schema_info:
                print(f"Column: {col[1]}, Type: {col[2]}")
        else:
            print("Table verification: Failed!")
        conn.close()
    else:
        print("Sample CSV file not found. Please create one to test.")
    
    inferrer.close()