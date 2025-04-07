import sqlite3
import pandas as pd
import os
import logging
from datetime import datetime

class SchemaValidator:
    def __init__(self, db_path="sheet_data.db", log_file="error_log.txt"):
        """Initialize validator with database connection and logging."""
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        
        # Setup logging
        logging.basicConfig(
            filename=log_file,
            level=logging.ERROR,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging
    
    def get_table_schema(self, table_name):
        """
        Get schema information for an existing table.
        
        Args:
            table_name (str): Name of the table
            
        Returns:
            dict: Column name to data type mapping, or None if table doesn't exist
        """
        try:
            self.cursor.execute(f"PRAGMA table_info({table_name})")
            columns = self.cursor.fetchall()
            
            if not columns:
                return None
                
            schema = {}
            for col in columns:
                # col format: (cid, name, type, notnull, dflt_value, pk)
                schema[col[1]] = col[2]
            
            return schema
        except sqlite3.Error as e:
            self.logger.error(f"Error getting schema for table {table_name}: {e}")
            return None
    
    def check_schema_conflict(self, table_name, new_schema):
        """
        Check for conflicts between existing table schema and new schema.
        
        Args:
            table_name (str): Table name to check
            new_schema (dict): New schema to compare
            
        Returns:
            tuple: (conflict_exists, details)
        """
        existing_schema = self.get_table_schema(table_name)
        
        if not existing_schema:
            return False, "Table does not exist"
        
        conflicts = []
        for col, dtype in new_schema.items():
            if col in existing_schema and existing_schema[col] != dtype:
                conflicts.append(f"Column '{col}' type mismatch: existing={existing_schema[col]}, new={dtype}")
        
        # Also check for missing columns in new schema
        for col in existing_schema:
            if col not in new_schema:
                conflicts.append(f"Column '{col}' exists in table but not in new schema")
        
        return len(conflicts) > 0, conflicts
    
    def handle_schema_conflict(self, table_name, df, new_schema, action="prompt"):
        """
        Handle schema conflicts based on specified action.
        
        Args:
            table_name (str): Table name
            df (DataFrame): Data to insert
            new_schema (dict): New schema
            action (str): Action to take - 'overwrite', 'rename', 'skip', or 'prompt'
            
        Returns:
            bool: Success or failure
        """
        conflict_exists, details = self.check_schema_conflict(table_name, new_schema)
        
        if not conflict_exists:
            # No conflict, proceed with insertion
            try:
                df.to_sql(table_name, self.conn, if_exists="replace", index=False)
                print(f"Data successfully inserted into {table_name}")
                return True
            except Exception as e:
                self.logger.error(f"Error inserting data into {table_name}: {e}")
                print(f"Error: {e}")
                return False
        
        # Handle conflict based on action
        if action == "prompt":
            print(f"Schema conflict detected for table {table_name}:")
            for detail in details:
                print(f"- {detail}")
            
            choice = input("Choose action: [o]verwrite, [r]ename, [s]kip: ").lower()
            
            if choice.startswith('o'):
                action = "overwrite"
            elif choice.startswith('r'):
                action = "rename"
            else:
                action = "skip"
        
        if action == "overwrite":
            try:
                self.cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
                self.conn.commit()
                df.to_sql(table_name, self.conn, if_exists="replace", index=False)
                print(f"Table {table_name} was overwritten with new schema")
                return True
            except Exception as e:
                self.logger.error(f"Error overwriting table {table_name}: {e}")
                print(f"Error: {e}")
                return False
                
        elif action == "rename":
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            new_table_name = f"{table_name}_{timestamp}"
            try:
                df.to_sql(new_table_name, self.conn, if_exists="replace", index=False)
                print(f"Data inserted into new table: {new_table_name}")
                return True
            except Exception as e:
                self.logger.error(f"Error creating renamed table {new_table_name}: {e}")
                print(f"Error: {e}")
                return False
                
        elif action == "skip":
            print(f"Skipped inserting data into {table_name} due to schema conflict")
            return False
    
    def validate_csv_load(self, csv_path, table_name, action="prompt"):
        """
        Validate and load CSV into SQLite with conflict handling.
        
        Args:
            csv_path (str): Path to CSV file
            table_name (str): Target table name
            action (str): Conflict resolution action
            
        Returns:
            bool: Success or failure
        """
        if not os.path.exists(csv_path):
            print(f"Error: CSV file not found at {csv_path}")
            self.logger.error(f"CSV file not found: {csv_path}")
            return False
        
        try:
            # Load CSV and infer schema
            df = pd.read_csv(csv_path)
            
            # Infer schema
            schema = {}
            for column in df.columns:
                if pd.api.types.is_numeric_dtype(df[column]):
                    if df[column].dropna().apply(lambda x: x.is_integer() if isinstance(x, float) else True).all():
                        schema[column] = "INTEGER"
                    else:
                        schema[column] = "REAL"
                else:
                    schema[column] = "TEXT"
            
            # Check if table exists
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name=?", (table_name,))
            table_exists = self.cursor.fetchone() is not None
            
            if not table_exists:
                # Create new table
                df.to_sql(table_name, self.conn, if_exists="replace", index=False)
                print(f"Table {table_name} created successfully")
                return True
            else:
                # Handle potential conflicts
                return self.handle_schema_conflict(table_name, df, schema, action)
                
        except Exception as e:
            print(f"Error processing CSV: {e}")
            self.logger.error(f"Error processing CSV {csv_path}: {e}")
            return False
    
    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            print("Database connection closed")

# Example usage
if __name__ == "__main__":
    validator = SchemaValidator()
    
    # Test validation with a sample CSV
    if os.path.exists("sample.csv"):
        # First load
        print("First load of sample.csv:")
        validator.validate_csv_load("sample.csv", "test_table")
        
        # Create a modified CSV with schema conflict
        df = pd.read_csv("sample.csv")
        
        # Modify a column type (e.g., convert a numeric column to text)
        numeric_cols = df.select_dtypes(include=['number']).columns
        if len(numeric_cols) > 0:
            first_numeric = numeric_cols[0]
            df[first_numeric] = df[first_numeric].astype(str) + "_modified"
            df.to_csv("modified_sample.csv", index=False)
            
            # Try loading modified CSV (should detect conflict)
            print("\nTrying to load modified CSV with schema conflict:")
            validator.validate_csv_load("modified_sample.csv", "test_table")
    else:
        print("Sample CSV file not found. Please create one to test.")
    
    validator.close()