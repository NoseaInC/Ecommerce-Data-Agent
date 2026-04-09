import json
import sqlite3
from openai import OpenAI
from core.state import AgentState
from core.config import DEEPSEEK_API_KEY, BASE_URL, MODEL_NAME, DB_PATH

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)

# ==========================================
# 动态能力：实时探查数据库当前真实的 Schema
# ==========================================
def _get_dynamic_schema():
    try:
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
        return schema_str.strip() or "当前数据库为空，没有任何表。"
    except Exception as e:
        return f"获取数据库元数据失败: {e}"

def node_validator(state: AgentState) -> AgentState:
    print("\n🛡️ [Validator Agent] 启动！正在动态拉取底层数据资产进行校验...")
    
    query = state["user_query"]
    tasks = state.get("tasks", [])
    
    # 1. 动态获取当前数据库真实的表结构！彻底告别硬编码！
    current_db_schema = _get_dynamic_schema()
    
    # 2. 构造 Validator 的专属 Prompt
    system_prompt = f"""
        你是数据智能中枢的“数据资产守门人”。
        你的任务是判断用户的提问，是否能够用当前数据库里已有的字段，或者结合下游的机器学习算法解答。
        
        当前可用的底层表结构如下（这是系统刚刚动态拉取的）：
        {current_db_schema}
        
        规则：
        1. 基础事实拦截：如果用户问了我们根本没有的数据维度（例如：用户的身高、天气、其他公司的竞品数据），请判定为不可执行。
        2. 衍生指标放行：如果用户的问题可以通过上述字段关联计算得出（例如：净GMV = 实际支付额扣除退款），请判定为可执行。
        3. 🤖 算法引擎放行（核心）：系统下游配备了强大的 XGBoost 机器学习与归因引擎。如果用户提到“归因分析”、“特征重要性”、“核心驱动因子”或“预测趋势”，**只要底层表中有足以提取特征的基础维度**（如用户画像、商品类目、价格等），就必须判定为【可执行】！不要因为表里没有现成的“归因”字段就将其打回。
        
        你必须且只能返回一个合法的 JSON，严格遵循以下结构：
        {{
            "is_valid": true 或 false,
            "reason": "如果为false，给出一句简短理由；如果为true，填'校验通过'"
        }}
        """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"用户提问：{query}\n分配的任务流：{tasks}"}
            ],
            response_format={"type": "json_object"},
            temperature=0.0
        )
        
        result_str = response.choices[0].message.content
        validation_result = json.loads(result_str)
        
        is_valid = validation_result.get("is_valid", False)
        reason = validation_result.get("reason", "未知原因")
        
        state["is_info_sufficient"] = is_valid
        
        if is_valid:
            print(f"   => ✅ 校验通过，底层数据支持本次分析。")
            state["audit_log"].append("Validator: 校验通过")
        else:
            print(f"   => ❌ 拦截成功！打回理由: {reason}")
            state["audit_log"].append(f"Validator: 拦截，原因 - {reason}")
            
    except Exception as e:
         print(f"   => ⚠️ Validator 调用异常: {e}，为保证业务运转，默认放行。")
         state["is_info_sufficient"] = True
         
    return state