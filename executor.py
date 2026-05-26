import pandas as pd
import traceback
import json

def execute_cleaning_script(code_string: str, df: pd.DataFrame) -> pd.DataFrame:
    """
    Executes the dynamically generated Python code to clean the dataframe.
    """
    # Create an isolated namespace for execution
    local_namespace = {
        'pd': pd,
        'json': json
    }
    
    try:
        # Execute the code string to define the clean_data function in local_namespace
        exec(code_string, local_namespace)
        
        # Verify the function was defined
        if 'clean_data' not in local_namespace:
            raise ValueError("The generated code did not define a 'clean_data' function.")
        
        # Call the function
        clean_data_func = local_namespace['clean_data']
        cleaned_df = clean_data_func(df.copy())
        
        # Basic validation
        if not isinstance(cleaned_df, pd.DataFrame):
            raise TypeError(f"Expected clean_data to return a DataFrame, got {type(cleaned_df)}")
            
        return cleaned_df
        
    except Exception as e:
        # Format the traceback so we can send it back to the LLM
        error_msg = f"Exception type: {type(e).__name__}\n"
        error_msg += f"Exception message: {str(e)}\n"
        error_msg += f"Traceback:\n{traceback.format_exc()}"
        raise RuntimeError(error_msg)
