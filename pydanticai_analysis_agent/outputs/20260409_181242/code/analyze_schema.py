import pandas as pd
import os
import json

data_dir = r"C:\Users\tjfan\Desktop\text-analysis-llm\pydanticai_analysis_agent\data/tourism_data"
files = ['미국_202001_202301.csv', '일본_202001_202301.csv', '중국_202001_202301.csv']

results = []

for file in files:
    file_path = os.path.join(data_dir, file)
    try:
        df = pd.read_csv(file_path, encoding='utf-8-sig')
    except:
        df = pd.read_csv(file_path, encoding='cp949')
    
    columns_info = []
    for col in df.columns:
        unique_count = df[col].nunique()
        is_categorical = unique_count <= 20
        
        col_info = {
            "name": col,
            "dtype": str(df[col].dtype),
            "null_count": int(df[col].isnull().sum()),
            "unique_count": int(unique_count),
            "is_categorical": is_categorical,
            "sample_values": [str(x) for x in df[col].dropna().sample(min(3, len(df))).tolist()]
        }
        if is_categorical:
            col_info["categorical_values"] = [str(x) for x in df[col].unique().tolist()[:20]]
        
        columns_info.append(col_info)
        
    results.append({
        "source_name": file,
        "source_path": file_path,
        "source_type": "csv",
        "row_count": len(df),
        "column_count": len(df.columns),
        "columns": columns_info
    })

print(json.dumps(results, indent=2, ensure_ascii=False))
