import os
import argparse
from dotenv import load_dotenv

# Import our modules
from modules.csv_sql_mapper import CSVSQLMapper
from modules.schema_inferrer import SchemaInferrer
from modules.validator import SchemaValidator
from modules.chat_sheet import ChatSheet

def main():
    """Main entry point for the ChatSheet application."""
    # Load environment variables from .env file if it exists
    load_dotenv()
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="ChatSheet - Natural Language Spreadsheet")
    parser.add_argument("--db", default="sheet_data.db", help="Path to SQLite database file")
    parser.add_argument("--api-key", help="API key for LLM service (overrides env variable)")
    parser.add_argument("--csv", help="CSV file to load at startup")
    parser.add_argument("--table", help="Table name for loading CSV")
    args = parser.parse_args()
    
    # Get API key from args or environment
    api_key = args.api_key or os.environ.get("OPENAI_API_KEY")
    
    # Initialize the application
    app = ChatSheet(db_path=args.db, api_key=api_key)
    
    try:
        # If CSV file provided at startup, load it
        if args.csv and os.path.exists(args.csv):
            table_name = args.table or os.path.splitext(os.path.basename(args.csv))[0]
            print(f"Loading {args.csv} into table {table_name}...")
            app.load_csv(args.csv, table_name)
        
        # Run the application
        app.run()
    finally:
        app.close()

if __name__ == "__main__":
    main()