import os
import re
import tempfile
import streamlit as st
import pandas as pd
from dotenv import load_dotenv
from modules.chat_sheet import ChatSheet

# Load environment variables (e.g. OPENAI_API_KEY)
load_dotenv()

def main():
    st.title("ChatSheet - Natural Language Spreadsheet")

    # Sidebar options
    st.sidebar.header("Options")
    
    # CSV file uploader with drag-and-drop
    csv_file = st.sidebar.file_uploader("Upload CSV file", type=["csv"])
    table_name_input = st.sidebar.text_input("Table Name (optional)")
    if csv_file is not None:
        if st.sidebar.button("Load CSV"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".csv") as tmp_file:
                tmp_file.write(csv_file.getvalue())
                tmp_csv_path = tmp_file.name
            table_name = table_name_input if table_name_input else os.path.splitext(csv_file.name)[0]
            st.sidebar.info(f"Loading CSV into table '{table_name}'...")
            app = ChatSheet(db_path="sheet_data.db", api_key=os.environ.get("OPENAI_API_KEY"))
            app.load_csv(tmp_csv_path, table_name)
            st.sidebar.success(f"CSV loaded into table '{table_name}'.")
            app.close()

    # Button to view current database schema
    if st.sidebar.button("Show Schema"):
        app = ChatSheet(db_path="sheet_data.db", api_key=os.environ.get("OPENAI_API_KEY"))
        st.sidebar.subheader("Database Schema")
        st.sidebar.text(app.get_schema_context())
        app.close()

    # Main area: Query input
    st.header("Enter your natural language query")
    user_query = st.text_area("Query", placeholder="Type your query here...")
    if st.button("Submit Query"):
        if not user_query.strip():
            st.warning("Please enter a query.")
        else:
            app = ChatSheet(db_path="sheet_data.db", api_key=os.environ.get("OPENAI_API_KEY"))
            # Generate SQL and template response from the LLM
            response = app.generate_sql_from_natural_language(user_query)
            # Try to support alternative markers from the LLM output.
            if "SQL:" in response and "TEMPLATE:" in response:
                sql_marker = "SQL:"
                template_marker = "TEMPLATE:"
            elif "SQL Query:" in response and "Template:" in response:
                sql_marker = "SQL Query:"
                template_marker = "Template:"
            else:
                st.error("Invalid response format from LLM. Response:\n" + response)
                return

            sql_part = response.split(sql_marker)[1].split(template_marker)[0].strip()
            template_part = response.split(template_marker)[1].strip()

            # Remove markdown code fences if present
            if sql_part.startswith("```"):
                lines = sql_part.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                sql_part = "\n".join(lines).strip()

            # Remove any leading numbering from each line (e.g. "1. " or "2. ")
            sql_part = re.sub(r'^\d+\.\s*', '', sql_part, flags=re.MULTILINE)

            st.subheader("Generated SQL Query")
            st.code(sql_part, language="sql")

            # Split the SQL into statements
            statements = [stmt.strip() for stmt in sql_part.split(';') if stmt.strip()]
            if statements and statements[-1].upper().startswith("SELECT"):
                # If there are preceding non-SELECT statements, execute them first.
                if len(statements) > 1:
                    non_select_sql = '; '.join(statements[:-1]) + ';'
                    app.conn.executescript(non_select_sql)
                    app.conn.commit()
                select_sql = statements[-1]
                try:
                    result_df = pd.read_sql_query(select_sql, app.conn)
                except Exception as e:
                    st.error("Error executing SQL query: " + str(e))
                    app.close()
                    return

                st.subheader("Raw Query Results")
                st.dataframe(result_df)

                # Build a format dictionary for the natural language template.
                results_list = []
                for _, row in result_df.iterrows():
                    row_str = ", ".join([f"{col}: {row[col]}" for col in result_df.columns])
                    results_list.append(row_str)
                aggregated_results = "; ".join(results_list)
                aggregated_columns = {col: ", ".join(result_df[col].astype(str).tolist()) for col in result_df.columns}
                format_dict = {**aggregated_columns, "results": aggregated_results}
                format_dict["row_count"] = len(result_df)
                format_dict["count"] = len(result_df)  # In case template uses {count}

                st.subheader("In Plain English")
                try:
                    template_clean = template_part.replace("{{", "{").replace("}}", "}")
                    formatted_response = template_clean.format(**format_dict)
                    st.write(formatted_response)
                except Exception as e:
                    st.error("Error formatting natural language response: " + str(e))
                    st.write("Raw template:")
                    st.write(template_part)
            else:
                # For non-SELECT queries, execute the entire script.
                try:
                    app.conn.executescript(sql_part)
                    app.conn.commit()
                    st.success("Operation executed successfully.")
                    try:
                        template_clean = template_part.replace("{{", "{").replace("}}", "}")
                        formatted_response = template_clean.format(**{})
                        st.subheader("Message")
                        st.write(formatted_response)
                    except Exception:
                        st.subheader("Message")
                        st.write(template_part)
                except Exception as e:
                    st.error("Error executing non-SELECT query: " + str(e))
            app.close()

if __name__ == "__main__":
    main()
