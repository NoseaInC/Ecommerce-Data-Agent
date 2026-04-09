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
    
    # 2. 构造 Router 专属的高级 Prompt (升级版：加入闲聊拦截)
    system_prompt = f"""
    你是数据智能中枢的“主脑（Master Router）”。
    你需要首先判断用户的核心意图：
    
    【场景 A：日常闲聊或通用问答】
    如果用户只是在打招呼（如“你好”、“在吗”）、问候、或者问一些与当前电商业务数据毫无关联的通用问题（如“写首诗”、“1+1等于几”）。
    -> 动作：直接由你回答，不需要调用底层技能。
    
    【场景 B：电商数据分析】
    如果用户的问题涉及“取数”、“查数据”、“GMV对比”、“归因”、“预测”等。
    -> 动作：规划底层 Skill。参考以下SOP：
    - 若问题仅涉及"查数据"、"多少钱"，分发给: ["sql_skill"]
    - 若问题涉及"归因"、"驱动因子"、"预测"，分发给: ["sql_skill", "ml_analysis_skill"]
    
    你必须且只能返回一个合法的 JSON，严格遵循以下结构：
    {{
        "is_direct_chat": true 或 false,
        "direct_response": "如果是场景A，在这里写出你直接回复给用户的话（高情商一点）。如果是场景B，请填空字符串。",
        "task_category": "<简短概括任务类型，如：闲聊问答 / 基础取数 / 多维归因>",
        "tasks": ["如果是场景B，填写需要的技能列表，如 sql_skill"] 
    }}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": query}
            ],
            response_format={"type": "json_object"}, 
            temperature=0.0 
        )
        
        result_str = response.choices[0].message.content
        router_decision = json.loads(result_str)
        
        # 将主脑的判断写入大白板
        state["is_direct_chat"] = router_decision.get("is_direct_chat", False)
        state["direct_response"] = router_decision.get("direct_response", "")
        state["task_category"] = router_decision.get("task_category", "未知类型")
        state["tasks"] = router_decision.get("tasks", []) 
        
        if state["is_direct_chat"]:
            print(f"   => 🧠 主脑判定：这是日常交流，无需消耗底层计算资源。")
            state["audit_log"].append("Router: 判定为直接对话")
        else:
            print(f"   => 📊 主脑判定：触发数据分析流。定级: {state['task_category']}")
            print(f"   => 🛤️ 规划的执行流: {state['tasks']}")
            state["audit_log"].append(f"Router: 规划路径 {state['tasks']}")
            
    except Exception as e:
         print(f"   => ❌ Router 调用异常: {e}")
         state["is_direct_chat"] = False
         state["tasks"] = ["sql_skill"] 
         
    return state