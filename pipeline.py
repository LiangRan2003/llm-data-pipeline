import os
import pandas as pd
import sqlite3
from prefect import flow, task, get_run_logger
from generate_data import generate_messy_data, generate_messy_logs
from llm_coder import generate_cleaning_script
from executor import execute_cleaning_script

@task(name="Generate Mock Messy Data", retries=0)
def generate_mock_data_task(file_path: str, num_rows: int = 100):
    logger = get_run_logger()
    logger.info(f"Generating {num_rows} rows of messy data at {file_path}")
    generate_messy_data(num_rows=num_rows, output_file=file_path)
    return file_path

@task(name="Read Raw Data")
def read_data_task(file_path: str) -> pd.DataFrame:
    logger = get_run_logger()
    logger.info(f"Reading data from {file_path}")
    return pd.read_csv(file_path)

@task(name="Generate Mock Messy Logs", retries=0)
def generate_mock_logs_task(file_path: str, num_rows: int = 100):
    logger = get_run_logger()
    logger.info(f"Generating {num_rows} rows of messy logs at {file_path}")
    generate_messy_logs(num_rows=num_rows, output_file=file_path)
    return file_path

@task(name="LLM Clean Data with Self-Healing", retries=0)
def llm_clean_data_task(df: pd.DataFrame, requirements: str, max_attempts: int = 3) -> pd.DataFrame:
    logger = get_run_logger()
    logger.info("Starting LLM cleaning process...")
    
    current_code = None
    last_error = None
    
    for attempt in range(1, max_attempts + 1):
        logger.info(f"Attempt {attempt}/{max_attempts} to generate and execute code.")
        try:
            # Step 1: Generate or fix code
            if attempt == 1:
                current_code = generate_cleaning_script(df, requirements)
            else:
                logger.warning("Requesting LLM to fix previous error...")
                current_code = generate_cleaning_script(df, requirements, error_feedback=last_error, previous_code=current_code)
                
            logger.info("Generated Code:\n" + current_code)
            
            # Step 2: Execute code
            cleaned_df = execute_cleaning_script(current_code, df)
            
            # Step 3: Data Quality Validation
            # 如果存在全为 NaN 的列，说明大模型的正则或提取逻辑写错了
            empty_cols = cleaned_df.columns[cleaned_df.isna().all()].tolist()
            if empty_cols and attempt < max_attempts:
                error_msg = f"Data Quality Error: The following extracted columns are entirely NaN (NULL): {empty_cols}. Your parsing logic (e.g. regex) is incorrect and failed to match the raw data. Please fix your parsing logic."
                raise ValueError(error_msg)
            
            logger.info("Successfully cleaned data!")
            return cleaned_df
            
        except Exception as e:
            last_error = str(e)
            logger.error(f"Execution failed on attempt {attempt}:\n{last_error}")
            
            if attempt == max_attempts:
                logger.error("Max attempts reached. Failed to clean data.")
                raise e

@task(name="Save Cleaned Data")
def save_data_task(df: pd.DataFrame, output_path: str):
    logger = get_run_logger()
    logger.info(f"Saving cleaned data to {output_path}")
    
    # Save as CSV
    df.to_csv(output_path, index=False)
    
    # Also save as Parquet to demonstrate DE skills
    parquet_path = output_path.replace(".csv", ".parquet")
    try:
        df.to_parquet(parquet_path, index=False)
        logger.info(f"Also saved as Parquet: {parquet_path}")
    except ImportError:
        logger.warning("pyarrow or fastparquet not installed, skipping parquet export.")

@task(name="Save to SQLite DB")
def save_to_db_task(df: pd.DataFrame, db_path: str, table_name: str):
    logger = get_run_logger()
    logger.info(f"Saving data to SQLite database {db_path}, table {table_name}")
    conn = sqlite3.connect(db_path)
    df.to_sql(table_name, conn, if_exists='replace', index=False)
    conn.close()
    logger.info(f"Successfully saved to table {table_name}!")

@flow(name="LLM Powered Data Pipeline V2")
def main_flow():
    logger = get_run_logger()
    db_path = "cleaned_data.db"
    
    # --- Part 1: Sales Data ---
    sales_req = """
1. `date`: 转换为标准日期时间格式 (YYYY-MM-DD)。如果遇到无效日期请优雅处理（例如设置为 NaT）。
2. `price_string`: 提取出数字金额 (float类型) 并将列重命名为 `price`。例如：'$19.99' -> 19.99, 'USD 20' -> 20.0。如果是 'FREE' 或者无效字符串，设置为 0.0 或 NaN。
3. `user_id`: 统一格式（强制以 'U-' 开头，后面跟着数字）。
4. `product_name`: 转换为每个单词首字母大写 (Title Case)。
5. `metadata`: 解析其中的 JSON 字符串，并展平拆分为两列：`metadata_category` 和 `metadata_warranty_years`。最后删除原始的 `metadata` 列。
    """
    logger.info("=== Processing Sales Data ===")
    raw_sales = generate_mock_data_task("raw_sales_data.csv", num_rows=30)
    sales_df = read_data_task(raw_sales)
    clean_sales = llm_clean_data_task(sales_df, sales_req)
    save_data_task(clean_sales, "cleaned_sales_data.csv")
    save_to_db_task(clean_sales, db_path, "sales")
    
    # --- Part 2: Server Logs Data ---
    logs_req = """
这个数据框只有一列 `raw_log`，里面是未结构化的服务器日志。
1. 将 IP 地址提取到名为 `ip` 的新列中。
2. 将时间戳提取到名为 `timestamp` 的新列中，并将其转换为 datetime 类型。
3. 提取 HTTP 请求方法（如 GET, POST 等），并转换为大写，存入新列 `http_method`。
4. 提取请求的 URL 路径，存入新列 `endpoint`。
5. 提取 HTTP 状态码（转换为整数类型），存入新列 `status_code`。
6. 最后删除原始的 `raw_log` 列。如果某行日志无法被完全解析，请将未能提取的字段填充为 NaN。
    """
    logger.info("=== Processing Server Logs ===")
    raw_logs = generate_mock_logs_task("raw_server_logs.csv", num_rows=30)
    logs_df = read_data_task(raw_logs)
    clean_logs = llm_clean_data_task(logs_df, logs_req)
    save_data_task(clean_logs, "cleaned_server_logs.csv")
    save_to_db_task(clean_logs, db_path, "server_logs")

    logger.info("Pipeline V2 completed successfully!")

if __name__ == "__main__":
    main_flow()
