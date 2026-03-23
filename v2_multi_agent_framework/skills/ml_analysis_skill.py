# skills/ml_analysis_skill.py
import json
import sqlite3
import pandas as pd
import numpy as np
import xgboost as xgb
from sklearn.preprocessing import LabelEncoder
from openai import OpenAI

from core.state import AgentState
from core.config import DEEPSEEK_API_KEY, BASE_URL, MODEL_NAME, DB_PATH

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)

# ==========================================
# 工具 1：供 Agent 探查底层的 Schema
# ==========================================
def get_database_schema_for_ml():
    print("   => [ML 探查] Agent 正在读取数据库表结构，准备构建特征工程...")
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    schema_str = ""
    for table in tables:
        table_name = table[0]
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        col_names = [col[1] for col in columns]
        schema_str += f"表名: {table_name}, 字段: {', '.join(col_names)}\n"
    conn.close()
    return schema_str.strip()

# ==========================================
# 工具 2：极其硬核的 AutoML 动态执行引擎！
# 允许 Agent 传入 SQL (提取特征) 和 目标列 (Y)
# ==========================================
def run_automl_pipeline(sql_query: str, target_column: str, task_type: str = "regression"):
    print(f"   => [ML 引擎] 正在执行特征提取 SQL...\n      {sql_query}")
    try:
        # 1. 获取训练数据
        conn = sqlite3.connect(DB_PATH)
        df = pd.read_sql_query(sql_query, conn)
        conn.close()
        
        if df.empty or len(df) < 10:
            return "数据量太少，无法训练模型。请检查 SQL。"
        if target_column not in df.columns:
            return f"SQL 结果中缺失目标列 {target_column}。"

        print(f"   => [ML 引擎] 数据提取成功 (行数: {len(df)}, 特征数: {len(df.columns)-1})，正在训练 XGBoost...")
        
        # 2. 自动化特征预处理 (Label Encoding for categories)
        X = df.drop(columns=[target_column])
        y = df[target_column]
        
        for col in X.select_dtypes(include=['object']).columns:
            X[col] = LabelEncoder().fit_transform(X[col].astype(str))
            
        if y.dtype == 'object' or task_type == 'classification':
            y = LabelEncoder().fit_transform(y.astype(str))
            task_type = 'classification' # 强制转为分类
            
        # 3. 动态模型选择与训练
        if task_type == 'classification':
            model = xgb.XGBClassifier(n_estimators=50, max_depth=4, random_state=42)
        else:
            model = xgb.XGBRegressor(n_estimators=50, max_depth=4, random_state=42)
            
        model.fit(X, y)
        
        # 4. 基于树模型的特征重要性归因
        importance_df = pd.DataFrame({
            '特征': X.columns,
            '重要性得分': model.feature_importances_
        }).sort_values(by='重要性得分', ascending=False)
        
        top_features = importance_df.head(3).to_dict(orient='records')
        
        result_summary = {
            "模型类型": "XGBClassifier" if task_type == 'classification' else "XGBRegressor",
            "样本数量": len(df),
            "核心驱动特征 (Top 3)": top_features,
            "详细特征重要性": importance_df.to_dict(orient='records')
        }
        print("   => [ML 引擎] 训练与归因完成！")
        return json.dumps(result_summary, ensure_ascii=False)
        
    except Exception as e:
        return f"AutoML 引擎执行失败: {str(e)}"

# ==========================================
# 核心节点：算法科学家 Agent 思考流
# ==========================================
def node_ml_analysis_skill(state: AgentState) -> AgentState:
    print("\n🤖 [ML Analysis Worker] 启动！算法科学家 Agent 开始思考建模方案...")
    query = state["user_query"]
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_database_schema_for_ml",
                "description": "第一步：获取数据库表结构，用于构思特征工程。",
            }
        },
        {
            "type": "function",
            "function": {
                "name": "run_automl_pipeline",
                "description": "第二步：将你构思好的特征提取 SQL、预测目标传入机器学习管道，进行 XGBoost 训练和归因。",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "sql_query": {"type": "string", "description": "用于构建训练集的宽表 SQL。必须包含所有特征列和目标列(target_column)。"},
                        "target_column": {"type": "string", "description": "你要预测/归因的目标变量字段名，必须在 sql_query 的 SELECT 中。"},
                        "task_type": {"type": "string", "enum": ["classification", "regression"], "description": "分类任务还是回归任务？"}
                    },
                    "required": ["sql_query", "target_column", "task_type"]
                }
            }
        }
    ]

    messages = [
        {
            "role": "system", 
            "content": """你是极其资深的算法科学家 Agent。
            用户的需求中包含了“归因分析”、“预测”、“特征重要性”或“驱动因子”等机器学习任务。
            你的行动准则：
            1. 调用 schema 探查底表。
            2. 根据用户需求，写出一个能生成“大宽表”的特征提取 SQL。把可能相关的维度（如城市、是否VIP、类目等）和目标值一起 SELECT 出来。
            3. 调用 run_automl_pipeline，把你的 SQL、目标列和任务类型传进去，拿到特征重要性归因。
            4. 拿到结果后，结束执行。"""
        },
        {"role": "user", "content": query}
    ]

    max_steps = 4
    for step in range(max_steps):
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.1
        )
        msg = response.choices[0].message
        messages.append(msg)
        
        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                if func_name == "get_database_schema_for_ml":
                    result = get_database_schema_for_ml()
                elif func_name == "run_automl_pipeline":
                    args = json.loads(tool_call.function.arguments)
                    result = run_automl_pipeline(
                        sql_query=args.get("sql_query"),
                        target_column=args.get("target_column"),
                        task_type=args.get("task_type", "regression")
                    )
                    # 将真实的 ML 结果挂载到大白板
                    if "analytics_results" not in state:
                        state["analytics_results"] = {}
                    state["analytics_results"]["ml_attribution_data"] = result
                else:
                    result = "Unknown tool"

                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
        else:
            print("   => [算法完结] ML Agent 成功提取了特征驱动力。")
            state["audit_log"].append("ML XGBoost 真实归因分析已完成")
            break

    return state