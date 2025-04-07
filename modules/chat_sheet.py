import sqlite3
import pandas as pd
import os
import json
import requests
import re
from datetime import datetime

class ChatSheet:
    def __init__(self, db_path="sheet_data.db", api_key=None):
        """
        Initialize ChatSheet with database connection and API key.
        
        Args:
            db_path (str): Path to SQLite database.
            api_key (str): API key for LLM service.
        """
        self.db_path = db_path
        self.conn = sqlite3.connect(db_path)
        self.cursor = self.conn.cursor()
        self.api_key = api_key or os.environ.get("OPENAI_API_KEY")
        
        if not self.api_key:
            print("Warning: No API key provided. LLM features will be disabled.")
        
        self.running = True

    def get_schema_context(self):
        """
        Get database schema information for context to the LLM.
        
        Returns:
            str: Formatted schema information.
        """
        self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [row[0] for row in self.cursor.fetchall()]
        
        if not tables:
            return "No tables found in the database."
        
        schema_info = []
        for table in tables:
            self.cursor.execute(f"PRAGMA table_info({table})")
            columns = self.cursor.fetchall()
            
            try:
                sample_data = pd.read_sql_query(f"SELECT * FROM {table} LIMIT 3", self.conn)
                sample_data_str = sample_data.to_string(index=False)
            except Exception as e:
                sample_data_str = "No data available"
            
            table_info = f"Table: {table}\nColumns:\n"
            for col in columns:
                table_info += f"  - {col[1]} ({col[2]})"
                if col[5]:
                    table_info += " (Primary Key)"
                table_info += "\n"
            table_info += "\nSample data:\n" + sample_data_str + "\n\n"
            schema_info.append(table_info)
        
        return "\n".join(schema_info)

    def detect_operation(self, user_query):
        """
        Analyze the user’s natural language query to determine the type of SQL operation.
        
        Returns:
            str: Operation type - one of 'select', 'insert', 'update', 'delete', 'drop', 'other'.
        """
        query_lower = user_query.lower()
        if any(keyword in query_lower for keyword in ["delete", "remove", "drop"]):
            return "delete"
        elif any(keyword in query_lower for keyword in ["update", "modify", "change"]):
            return "update"
        elif any(keyword in query_lower for keyword in ["insert", "add", "create"]):
            return "insert"
        elif any(keyword in query_lower for keyword in ["join", "select", "find", "list", "show", "retrieve", "get"]):
            return "select"
        else:
            return "other"

    def generate_sql_from_natural_language(self, user_query):
        """
        Generate SQL from a natural language query using an LLM, constructing a dynamic prompt 
        based on the detected operation.
        """
        if not self.api_key:
            return "Error: API key not configured. Please set the OPENAI_API_KEY environment variable."

        schema_context = self.get_schema_context()
        op_type = self.detect_operation(user_query)

        # Generic examples to guide the LLM
        examples = {
            "select": """
Example 1: Generic Data Retrieval
SQL: SELECT * FROM items WHERE type = 'example';
TEMPLATE: There are {row_count} items of type 'example'. For instance, the item with id {id} is named {name}.

Example 2: Count Operation
SQL: SELECT COUNT(*) AS total_items FROM items;
TEMPLATE: There are {total_items} items in the table.
""",
            "insert": """
Example: Data Insertion
SQL: INSERT INTO items (name, value) VALUES ('Sample Item', 100);
TEMPLATE: The item 'Sample Item' with value 100 has been added.
""",
            "update": """
Example: Data Update
SQL: UPDATE items SET value = value + 10 WHERE id = 1;
TEMPLATE: The item with id {id} has been updated.
""",
            "delete": """
Example: Data Deletion
SQL: DELETE FROM items WHERE id = 1;
TEMPLATE: The item with id {id} has been deleted.
""",
            "other": """
Example: Join Operation
SQL: SELECT a.col1, b.col2 FROM table_a a JOIN table_b b ON a.id = b.a_id;
TEMPLATE: The record for {col1} has detail {col2}.
"""
        }

        examples_text = examples.get(op_type, examples["other"])

        # Construct a generic prompt.
        prompt = f"""
Given the following SQLite database schema:

{schema_context}

For the following question: "{user_query}"

Using the examples below as guidance, generate two parts in your response:
1. A SQL query that performs the requested operation.
2. A natural language template that describes the result.
Ensure that:
- The SQL query uses table and column names exactly as they appear in the schema.
- The template uses placeholders in single curly braces (e.g., {{name}}) that exactly match the columns returned by your SQL query.
- The template is generic and does not assume a specific data domain.
- The template should only reference columns present in the SQL query output.
- If the SQL query returns multiple rows, include a placeholder {{results}} in the template representing the full list of values (e.g., as a comma-separated string).
- Do not include any additional commentary or numbering in your response.

{examples_text}

Important:
- If the operation is not a SELECT query, the template should describe the outcome of the operation (e.g., confirmation message).
"""

        try:
            response = requests.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                },
                json={
                    "model": "gpt-3.5-turbo",  # Replace with "gpt-4" if you want to use GPT-4.
                    "messages": [
                        {"role": "system", "content": "You are a helpful assistant that generates SQL queries and corresponding result templates. Ensure your templates only use column names that appear in your SQL query."},
                        {"role": "user", "content": prompt}
                    ],
                    "temperature": 0.3
                }
            )
            
            if response.status_code != 200:
                return f"Error: API returned status code {response.status_code}. {response.text}"
            
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
            
        except Exception as e:
            return f"Error generating SQL query: {str(e)}"

    def load_csv(self, csv_path, table_name):
        """
        Load a CSV file into a SQLite table.
        
        Args:
            csv_path (str): Path to the CSV file.
            table_name (str): Name of the table to create.
        """
        try:
            df = pd.read_csv(csv_path)
            df.to_sql(table_name, self.conn, if_exists='replace', index=False)
            print(f"Successfully loaded {csv_path} into table {table_name}")
        except Exception as e:
            print(f"Error loading CSV file: {str(e)}")
            raise

    def run(self):
        """
        Run the ChatSheet application in interactive mode.
        """
        print("\nWelcome to ChatSheet!")
        print("Type 'exit' to quit, 'schema' to view database schema, 'load <csv_file> <table_name>' to load a CSV file, or enter a natural language query.")
        
        while self.running:
            try:
                user_input = input("\nEnter your query: ").strip()
                
                if user_input.lower() == 'exit':
                    self.running = False
                    break
                elif user_input.lower() == 'schema':
                    print("\nCurrent Database Schema:")
                    print(self.get_schema_context())
                    continue
                elif user_input.lower().startswith('load '):
                    try:
                        _, csv_file, table_name = user_input.split(' ', 2)
                        self.load_csv(csv_file, table_name)
                        continue
                    except ValueError:
                        print("Error: Please use format 'load <csv_file> <table_name>'")
                        continue
                
                if not self.api_key:
                    print("Note: LLM features are disabled. Please set OPENAI_API_KEY to use natural language queries.")
                    continue
                
                response = self.generate_sql_from_natural_language(user_input)
                # Look for either expected markers in the response.
                if "SQL:" in response and "TEMPLATE:" in response:
                    sql_marker = "SQL:"
                    template_marker = "TEMPLATE:"
                elif "SQL Query:" in response and "Template:" in response:
                    sql_marker = "SQL Query:"
                    template_marker = "Template:"
                else:
                    print("Error: Invalid response format from LLM. Response:", response)
                    continue

                sql_part = response.split(sql_marker)[1].split(template_marker)[0].strip()
                template_part = response.split(template_marker)[1].strip()

                # Remove Markdown code fences if present
                if sql_part.startswith("```"):
                    lines = sql_part.splitlines()
                    if lines[0].startswith("```"):
                        lines = lines[1:]
                    if lines and lines[-1].startswith("```"):
                        lines = lines[:-1]
                    sql_part = "\n".join(lines).strip()

                # Remove any leading numbering (e.g., "1. ", "2. ") from each line in the SQL part
                sql_part = re.sub(r'^\d+\.\s*', '', sql_part, flags=re.MULTILINE)
                    
                print("\nGenerated SQL query:", sql_part)
                    
                # Split the SQL into statements
                statements = [stmt.strip() for stmt in sql_part.split(';') if stmt.strip()]
                # If the last statement starts with SELECT, execute it for formatting.
                if statements and statements[-1].upper().startswith("SELECT"):
                    if len(statements) > 1:
                        non_select_sql = '; '.join(statements[:-1]) + ';'
                        self.conn.executescript(non_select_sql)
                        self.conn.commit()
                    select_sql = statements[-1]
                    try:
                        result = pd.read_sql_query(select_sql, self.conn)
                    except Exception as e:
                        print("Error executing SELECT query:", e)
                        continue

                    print("\nRaw Query Results:")
                    print(result)
                        
                    # Build a format dictionary that always includes a 'results' key.
                    results_list = []
                    for _, row in result.iterrows():
                        row_str = ", ".join([f"{col}: {row[col]}" for col in result.columns])
                        results_list.append(row_str)
                    aggregated_results = "; ".join(results_list)
                    
                    # For individual columns, join all values (even if one row) to be safe.
                    aggregated_columns = {col: ", ".join(result[col].astype(str).tolist()) for col in result.columns}
                    
                    format_dict = {**aggregated_columns, "results": aggregated_results}
                    format_dict["row_count"] = len(result)
                    format_dict["count"] = len(result)  # In case the template uses {count}.
                        
                    print("\nIn plain English:")
                    try:
                        template_clean = template_part.replace("{{", "{").replace("}}", "}")
                        formatted_response = template_clean.format(**format_dict)
                        print(formatted_response)
                    except KeyError as e:
                        missing_key = str(e).strip("'")
                        print(f"Warning: Missing key '{missing_key}' in template. Adjusting template...")
                        template_clean = template_clean.replace("{" + missing_key + "}", "[unknown]")
                        try:
                            formatted_response = template_clean.format(**format_dict)
                            print(formatted_response)
                        except Exception as e:
                            print(f"Error formatting response after adjustment: {str(e)}")
                            print(f"Template: {template_part}")
                            print(f"Available keys: {list(format_dict.keys())}")
                    except Exception as e:
                        print(f"Error formatting response: {str(e)}")
                        print(f"Template: {template_part}")
                        print(f"Available keys: {list(format_dict.keys())}")
                else:
                    # No SELECT in the last statement: execute entire script.
                    try:
                        self.conn.executescript(sql_part)
                        self.conn.commit()
                        print("\nOperation executed successfully.")
                        # If possible, try to format the template with an empty dictionary
                        try:
                            template_clean = template_part.replace("{{", "{").replace("}}", "}")
                            formatted_response = template_clean.format(**{})
                            print("\nMessage:")
                            print(formatted_response)
                        except Exception:
                            # Fall back to printing the raw template.
                            print("\nMessage:")
                            print(template_part)
                    except Exception as e:
                        print("Error executing non-SELECT query:", e)

            except KeyboardInterrupt:
                print("\nExiting...")
                self.running = False
            except Exception as e:
                print(f"Error: {str(e)}")

    def close(self):
        """
        Close the database connection.
        """
        if hasattr(self, 'conn'):
            self.conn.close()

if __name__ == "__main__":
    chat_sheet = ChatSheet()
    try:
        chat_sheet.run()
    finally:
        chat_sheet.close()

