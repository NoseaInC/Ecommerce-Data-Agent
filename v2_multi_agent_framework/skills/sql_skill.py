# skills/sql_skill.py
import json
import sqlite3
from openai import OpenAI
from core.state import AgentState
from core.config import DEEPSEEK_API_KEY, BASE_URL, MODEL_NAME, DB_PATH

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)

# ==========================================
# 工具箱 1：主动探查数据库结构
# ==========================================
def get_database_schema():
    print("   => [底层探查] Agent 正在读取数据库元数据(Schema)...")
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
    return schema_str.strip() or "当前数据库为空。"

# ==========================================
# 工具箱 2：执行 SQL
# ==========================================
def execute_sql(sql_query: str):
    # 生产级极简拦截示例
    forbidden_keywords = ["DROP", "DELETE", "UPDATE", "INSERT", "ALTER", "TRUNCATE"]
    upper_sql = sql_query.upper()
    if any(keyword in upper_sql for keyword in forbidden_keywords):
        return "🚨 拒绝访问：数据智能特工仅拥有数据库的【只读 (SELECT)】权限！"
    # ... 继续执行查询 ...
    print(f"   => [底层执行] 运行 SQL: {sql_query}")
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(sql_query)
        results = cursor.fetchall()
        conn.close()
        # 防止试探时结果过大，截断输出，保护上下文
        res_str = str(results)
        if len(res_str) > 1000:
            return res_str[:1000] + "...(数据截断，仅展示部分)"
        return res_str
    except Exception as e:
        return f"SQL Error: {str(e)}"

# ==========================================
# 核心节点逻辑：动态预算规划微循环
# ==========================================
def node_sql_skill(state: AgentState) -> AgentState:
    print("\n🧮 [SQL Skill Worker] 启动！开启 Plan-and-Solve 动态步数探索模式...")
    query = state["user_query"]
    
    # 💡 核心升级：读取法官的打回意见
    feedback = state.get("reviewer_feedback", "")
    feedback_prompt = ""
    if feedback:
        feedback_prompt = f"""
        \n\n【🚨 严重警告：你上一轮查出的数据被业务总监打回了！】
        总监的严厉批评意见是："{feedback}"
        请你务必仔细阅读上述意见，反思你上一轮 SQL 逻辑的漏洞。
        这一次，请调整你的探查方向和取数口径，务必把总监缺失的数据查出来！
        """
        print(f"   => ⚠️ [反思机制] 特工已接收到总监的打回意见，正在修正查询策略！")
        
        # 清理掉上一轮查出来的废弃数据，防止污染当前轮次
        if "sql_data" in state.get("analytics_results", {}):
            state["analytics_results"].pop("sql_data")
    
    tools = [
        {
            "type": "function",
            "function": {
                "name": "get_database_schema",
                "description": "第一步：获取当前数据库的表结构。",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "submit_plan",
                "description": "第二步：在拿到表结构后，提交你的试探计划和预估步数。必须调用此工具申请执行额度！",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "plan_details": {"type": "string", "description": "你打算怎么一步步查数据？"},
                        "estimated_steps": {"type": "integer", "description": "预估需要调用几次 execute_sql？"}
                    },
                    "required": ["plan_details", "estimated_steps"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "execute_sql",
                "description": "第三步：执行 SQL 语句进行试探或最终查询。你可以在分配的步数内多次调用。",
                "parameters": {
                    "type": "object",
                    "properties": {"sql_query": {"type": "string"}}
                },
                "required": ["sql_query"]
            }
        }
    ]

    messages = [
        {
            "role": "system", 
            "content": f"""你是极其严谨的数据特工。
            你必须严格遵循以下行动准则：
            1. 调用 get_database_schema 获取表名和字段。
            2. 仔细分析需要关联的表，调用 submit_plan 告诉系统你打算怎么查，并申请执行次数。
            3. 额度批复后，多次调用 execute_sql 进行数据试探。
            4. 最后一次调用 execute_sql 输出完整的聚合数据结果。
            5. 拿到最终数据后，直接结束行动，不要再调用工具。{feedback_prompt}""" # <--- 加上这句思想钢印
        },
        {"role": "user", "content": query}
    ]
    # 初始只给 3 步，用来获取 Schema 和提交 Plan
    max_steps = 3 
    current_step = 0
    final_data_found = False

    while current_step < max_steps:
        current_step += 1
        print(f"   ⏳ [微循环] 第 {current_step}/{max_steps} 步执行中...")
        
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            tools=tools,
            tool_choice="auto",
            temperature=0.2
        )
        msg = response.choices[0].message
        messages.append(msg)
        
        if msg.tool_calls:
            for tool_call in msg.tool_calls:
                func_name = tool_call.function.name
                
                if func_name == "get_database_schema":
                    result = get_database_schema()
                    
                elif func_name == "submit_plan":
                    args = json.loads(tool_call.function.arguments)
                    est_steps = args.get("estimated_steps", 2)
                    plan = args.get("plan_details", "")
                    
                    # 💡 核心机制：动态扩容步数 = 当前已走步数 + 预估步数 + 2步容错缓冲
                    new_max = current_step + est_steps + 2
                    max_steps = max(max_steps, new_max) 
                    
                    result = f"系统已收到计划: {plan}。已为您动态扩充最大执行步数至 {max_steps} 步，请开始执行 execute_sql 进行试探。"
                    print(f"   => 📝 [预算批复] 特工申请了 {est_steps} 步，系统追加了容错缓冲，当前总步数上限更新为: {max_steps}")
                    
                elif func_name == "execute_sql":
                    args = json.loads(tool_call.function.arguments)
                    sql_query = args.get("sql_query")
                    result = execute_sql(sql_query)
                    
                    if "SQL Error" not in result:
                        # 💡 核心修复：把每一次成功的 SQL 和结果都存下来，而不是覆盖！
                        if "sql_data" not in state["analytics_results"]:
                            state["analytics_results"]["sql_data"] = {}
                        
                        # 用步数作为 Key，把探查全过程交给写报告的 Agent
                        query_key = f"步骤_{current_step}_查询"
                        state["analytics_results"]["sql_data"][query_key] = {
                            "执行的SQL": sql_query,
                            "查询结果": result
                        }
                        final_data_found = True
                else:
                    result = "Unknown tool"

                messages.append({"role": "tool", "tool_call_id": tool_call.id, "content": result})
        else:
            print("   => [闭环完结] Agent 认为已经拿到最终数据，主动结束探查。")
            state["audit_log"].append(f"SQL Skill 经过 {current_step} 步动态探索完成拉取")
            break

    if current_step >= max_steps and not final_data_found:
         print("   => ⚠️ 警告：特工耗尽了所有动态申请的步数，探索被迫终止！")
         
    return state