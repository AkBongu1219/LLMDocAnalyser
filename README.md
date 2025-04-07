# LLMDocAnalyser: Natural Language SQL Interface

LLM_Excel is a Streamlit-based application that allows users to interact with CSV data using natural language queries. The application converts natural language into SQL queries and provides both structured and natural language responses.

## Features

- Upload and manage CSV files with custom table names
- View database schema and sample data
- Query data using natural language
- Toggle between SQL and natural language responses
- Interactive web interface

## Prerequisites

- Python 3.8+
- OpenAI API key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/AkBongu1219/LLMDocAnalyser.git
cd LLM_Excel
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Open the `.env` file in the project root directory and add your OpenAI API key

## Usage
The simple way would be to run the following in the project directory and follow the instructions that follow
```bash
python3 main.py
```
### Streamlit Interface
1. Start the Streamlit application:
```bash
streamlit run app.py
```

2. Access the application through your web browser (typically at `http://localhost:8501`)

### Using the Application

1. **Upload Data**:
   - Click the "Choose a CSV file" button to upload your data
   - Enter a name for the table in the "Table name" field
   - Click "Load CSV" to import the data

2. **View Schema**:
   - Click "Show Schema" to view the current database structure and sample data

3. **Query Data**:
   - Enter your question in natural language in the query text area
   - Toggle "Show SQL Query" to see the generated SQL
   - Toggle "Show Natural Language Response" to see the results in plain English
   - Click "Execute Query" to run the query

### Example Queries

- "Show me all columns from table_name"
- "What is the average value of column_name?"
- "How many rows are there in table_name?"
- "Find all records where column_name is greater than 100"

## Project Structure
```bash
LLM_EXCEL/
├── __pycache__/
├── modules/
│   ├── __pycache__/
│   ├── csv_sql_mapper.py # Maps CSV files to SQL database tables.
│   ├── schema_inferrer.py # Infers the database schema from CSV data.
│   ├── validator.py # Validates schemas and SQL queries.
│   └── chat_sheet.py # Converts natural language queries into SQL and result templates.
├── .env  # Environment configuration file (e.g., API keys).
├── app.py # Streamlit app providing a web interface.
├── main.py # Terminal/CLI entry point for the ChatSheet application.
├── requirements.txt # List of required Python packages.
```

