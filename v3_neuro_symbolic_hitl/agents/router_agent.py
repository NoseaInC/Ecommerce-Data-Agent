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
    你需要首先判断用户的核心意图，并严格遵循【最小可用工具（Least Privilege）】原则来分配算力：
    
    【场景 A：日常闲聊或通用问答】
    如果用户只是在打招呼（如“你好”、“在吗”）、问候、或者问一些与当前电商业务数据毫无关联的通用问题（如“写首诗”、“1+1等于几”）。
    -> 动作：不需要调用底层技能。`is_direct_chat` 设为 true，在 `direct_response` 中直接高情商回复。
    
    【场景 B：电商数据分析 (🚨必须严格区分“描述性统计”与“深度建模”)】
    如果问题涉及业务数据，`is_direct_chat` 设为 false。请严格参考以下 SOP 规划 `tasks`：
    
    - 🟢 级别 1：描述性统计与常规战报 -> 仅分发给: ["sql_skill"]
      适用条件：用户想知道【发生了什么 (What)】。例如"查数据"、"统计数量/金额"、"看趋势"、"对比"、"产出分析报告"、"写战报"。
      🚨【红线警告】：即使用户的提问中包含了“分析报告”、“洞察”、“总结”等字眼，只要他的核心诉求只是看客观数据，就绝对【禁止】调用 ml_analysis_skill！纯 SQL 特工完全具备处理复杂聚合和产出高管报告的能力。
      
    - 🔴 级别 2：诊断性归因与预测建模 -> 分发给: ["sql_skill", "ml_analysis_skill"]
      适用条件：只有当用户明确提出寻找【为什么发生 (Why)】或【预测未来】的深度需求时才触发。例如：“为什么GMV会下降？”、“核心驱动因子是什么？”、“请做特征重要性归因”、“量化各维度的影响权重”。
      🚨【算力控制】：拉起机器学习引擎极其昂贵！只有在必须量化特征（Feature Engineering）时才能使用。
    
    你必须且只能返回一个合法的 JSON，严格遵循以下结构：
    {{
        "is_direct_chat": true 或 false,
        "direct_response": "如果是场景A，在这里写出你直接回复的话。如果是场景B，请务必填空字符串 \"\"。",
        "task_category": "<简短概括任务类型，如：闲聊问答 / 基础聚合与战报 / 深度特征归因>",
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
            temperature=1
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