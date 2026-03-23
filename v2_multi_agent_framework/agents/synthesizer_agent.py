import json
from openai import OpenAI
from core.state import AgentState
from core.config import DEEPSEEK_API_KEY, BASE_URL, MODEL_NAME

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)

def node_synthesizer(state: AgentState) -> AgentState:
    print("\n✍️ [Synthesizer Agent] 启动！正在将底层冷数据提炼为商业洞察报告...")
    
    query = state["user_query"]
    # 从大白板上获取所有底层 Skill 跑出来的硬核数据
    raw_results = state.get("analytics_results", {})
    
    # 防御性编程：如果底层没跑出任何数据，提早给出提示
    if not raw_results:
        state["draft_report"] = "⚠️ 分析终止：底层执行节点未能成功获取有效数据，请检查 SQL 或模型运行日志。"
        print("   => ⚠️ 未发现底层数据，生成中止。")
        return state

    # 把字典格式的原始数据转成格式化的字符串，喂给大模型
    results_str = json.dumps(raw_results, ensure_ascii=False, indent=2)
    
    # 构造高级商业分析师的 Prompt
    system_prompt = f"""
    你是某一线电商平台的资深商业分析专家（BI）。
    你的任务是将底层数据执行引擎跑出来的“冷冰冰的机器数据”，翻译成高管能一眼看懂的“商业洞察报告”。
    
    【输入信息】
    1. 业务老板的原始提问：{query}
    2. 底层引擎抓取的真实数据：{results_str}
    
    【撰写规范】
    1. 必须使用 Markdown 格式排版，包含清晰的标题、加粗的核心指标和分点说明。
    2. 严禁罗列代码或 SQL 数组（如 [(3150.0, 2700.0)]），必须将其转化为具体的业务数值和单位（如 3,150元）。
    3. 报告结构建议：
       - 核心结论 (一句话总结)
       - 数据表现 (列出关键指标)
       - 业务洞察 (根据数据给出你的专业推测或建议)
    4. 语气要专业、客观、具有极强的商业 Sense。
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请根据以上信息，生成最终的商业洞察战报。"}
            ],
            temperature=0.3 # 稍微给一点温度，让它的语言表达更流畅自然，但不过度发散
        )
        
        report = response.choices[0].message.content
        state["draft_report"] = report
        state["audit_log"].append("Synthesizer: 报告合成完毕")
        print("   => ✅ 商业洞察报告已生成！")
        
    except Exception as e:
         print(f"   => ❌ Synthesizer 调用异常: {e}")
         state["draft_report"] = f"生成报告时发生系统错误: {e}"
         
    return state