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
    2. 严禁罗列代码或 SQL 数组（如 [(3150.0, 2700.0)]），必须将其转化为具体的业务数值和单位（如 3,150元）。但注意数据底线：所有的百分比、环比、倍数，必须优先在底层 SQL 结果中获取！如果你必须自己计算比例或换算单位（如换算成万元），请务必在旁边保留精确到个位的原始绝对数值（例如：957.6万元(9576400.8元)），以免触发机器质检拦截！
    
    3 请在 synthesizer_agent.py 的 system_prompt 中使用这段最新的规范：
    
    【🚨 极其严格的数据血缘规范 (Data Provenance) 2.0 版】：
    你的报告将被极其严格的 Python 正则表达式逐字质检。你之前对数字标签的定性严重错误，请你现在必须死死记住以下打标原则：

    3.1 什么是 <raw> (绝对底线)：
       - 只有在【底层真实数据】中原封不动、连小数点都一模一样存在的数字，才能打 <raw>！
       - <raw> 的本质是“纯粹的复制粘贴”，绝对不能经过你大脑的哪怕一丝一毫加工！
       - 例如：底层结果给出 `9576400.8`，你就只能写 `<raw>9576400.8</raw>`。

    3.2 什么是 <calc> (凡有加工，皆为计算)：
       - 只要你动用了数学逻辑（加法求和、减法求差、除法算占比、算倍数），这个结果统统都是 <calc>！
       - 只要你做了四舍五入、抹零、单位换算（如把 9576400.8 写成了 957.6 万），只要长得不一样了，统统都是 <calc>！
       - 只要你把几个时段/几个状态的数据自己合并求和了（比如算0-6点的累计销量），这个总和也必须是 <calc>！

    【致命错误示范与纠正（你必须避免）】：
    ❌ 错误示范：你把双十一当天GMV和预热期GMV相加得到总GMV，并标记为 <raw>21561860.25</raw>。
    ✅ 正确做法：这是你做加法算出来的，底层并没有这个数字，必须标记为 <calc>21561860.25</calc>！

    ❌ 错误示范：你算出预热期比当天客单价高 17.14 元，标记为 <raw>17.14</raw>。
    ✅ 正确做法：这是你做减法算出来的差值，必须标记为 <calc>17.14</calc>！

    ❌ 错误示范：为了行文好看，你把 2330.21 约等于 2329，并标记为 <raw>2329</raw>。
    ✅ 正确做法：任何近似值和四舍五入都是加工，必须标记为 <calc>2329</calc>！

    【最高生存法则】：
    如果你不确定一个数字是不是底表里直接原原本本给出的，宁可打 <calc>，也绝对不要打 <raw>！乱打 <raw> 标签会被质检系统当场拦截并判定为捏造数据！
    
    4. 报告结构建议：
       - 核心结论 (一句话总结)
       - 数据表现 (列出关键指标)
       - 业务洞察 (根据数据给出你的专业推测或建议)
    5. 语气要专业、客观、具有极强的商业 Sense。
    """
    # 在 synthesizer_agent.py 中：
    feedback = state.get("reviewer_feedback", "")
    if feedback:
        system_prompt += f"\n\n【🚨 严重警告：你上一版的报告被打回了！】\n打回意见：{feedback}\n请你严格按照上述意见修改你的报告视角和数据！"
    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": "请根据以上信息，生成最终的商业洞察战报。"}
            ],
            temperature=1 # 稍微给一点温度，让它的语言表达更流畅自然，但不过度发散
        )
        
        report = response.choices[0].message.content
        state["draft_report"] = report
        state["audit_log"].append("Synthesizer: 报告合成完毕")
        print("   => ✅ 商业洞察报告已生成！")
        
    except Exception as e:
         print(f"   => ❌ Synthesizer 调用异常: {e}")
         state["draft_report"] = f"生成报告时发生系统错误: {e}"
         
    return state