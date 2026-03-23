import json
from openai import OpenAI
from core.state import AgentState
from core.config import DEEPSEEK_API_KEY, BASE_URL, MODEL_NAME

# 初始化 DeepSeek 客户端 (直接从咱们的 config 里拿配置，优雅！)
client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)

def node_router(state: AgentState) -> AgentState:
    print("\n🧠 [Router Agent] 正在思考并调用大模型进行意图路由...")
    
    query = state["user_query"]
    
    # 1. 模拟 RAG 知识库注入 (大厂 SOP)
    rag_context = """
    【大促分析 SOP 字典】
    - 若问题仅涉及"查数据"、"对比指标"、"多少钱"，分发给: ["sql_skill"]
    - 若问题涉及"归因"、"为什么跌了"、"核心因素"，分发给: ["sql_skill", "xgboost_skill"]
    - 若问题涉及"真实增量"、"因果效应"、"AB测试"，分发给: ["sql_skill", "did_skill"]
    - 若问题明确要求"画图"、"趋势图"，请在上述基础上追加: "plot_skill"
    """
    
    # 2. 构造 Router 专属的高级 Prompt
    system_prompt = f"""
    你是数据智能中枢的高级路由分发专家。
    请根据用户的提问和以下业务 SOP，决定调用的底层 Skill。
    
    {rag_context}
    
    你必须且只能返回一个合法的 JSON，严格遵循以下结构：
    {{
        "task_category": "<用简短的词概括任务类型，如：基础取数 / 多维归因 / 策略评估>",
        "tasks": ["skill_name_1", "skill_name_2"]
    }}
    """

    try:
        # 3. 发起真实的 API 调用 (开启强制 JSON 模式)
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            response_format={"type": "json_object"}, # ⚠️ 杀手锏：强制输出 JSON
            temperature=0.0 # 路由任务需要绝对客观，消除大模型的随机幻觉
        )
        
        # 4. 解析结果并写回“大白板”
        result_str = response.choices[0].message.content
        router_decision = json.loads(result_str)
        
        state["task_category"] = router_decision.get("task_category", "未知类型")
        state["tasks"] = router_decision.get("tasks", ["sql_skill"]) # 兜底策略
        
        log_msg = f"Router 判定类型: {state['task_category']}, 规划路径: {state['tasks']}"
        state["audit_log"].append(log_msg)
        
        print(f"   => 📊 任务定级: {state['task_category']}")
        print(f"   => 🛤️ 规划的执行流: {state['tasks']}")
        
    except Exception as e:
         print(f"   => ❌ Router 调用异常: {e}")
         state["tasks"] = ["sql_skill"] # 如果 API 挂了或者断网，默认只给基础 SQL 工具保底
         state["audit_log"].append(f"Router 异常: {e}")
         
    return state