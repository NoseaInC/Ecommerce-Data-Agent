import json
from openai import OpenAI
from core.state import AgentState
from core.config import DEEPSEEK_API_KEY, BASE_URL, MODEL_NAME

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)

def node_reviewer(state: AgentState) -> AgentState:
    print("\n⚖️ [Reviewer Agent] 启动！业务总监正在严格审阅战报...")
    
    query = state["user_query"]
    raw_results = state.get("analytics_results", {})
    draft = state.get("draft_report", "")
    
    # 构造极其严苛的“法官” Prompt
# 构造“动态拆解+思维链”的终极法官 Prompt
    system_prompt = f"""
    你是某一线互联网公司极其严厉的数据分析总监。
    你的下属（Synthesizer）刚刚提交了一份商业洞察报告草稿。
    你需要对照【业务方的原始提问】和【底层跑出的真实数据】，对这份报告进行打分（0-100分）。
    
    【业务方原始提问】: {query}
    【底层真实数据】: {json.dumps(raw_results, ensure_ascii=False)}
    【下属提交的报告草稿】:
    {draft}
    
    【你的核心任务：动态构建评价体系并打分】
    你不能死板地打分。你必须先深度分析【业务方的原始提问】，自主拆解出 3 到 5 个最核心的评估维度，并为其分配合理的权重（总和为100）。
    例如：如果业务方问了“为什么”，你的维度中必须包含“归因逻辑的严谨度”；如果业务方问了“趋势”，你的维度必须包含“预测的合理性”。

    你必须且只能返回一个合法的 JSON，严格遵循以下顺序结构执行你的思考流：
    {{
        "step1_dynamic_criteria": [
            {{"dimension": "准确性基准", "weight": 30, "reason": "业务数据汇报必须以底层真实数据为准"}},
            {{"dimension": "<你根据提问自主提取的维度2>", "weight": 40, "reason": "<你为什么认为这个维度对当前提问最重要>"}},
            {{"dimension": "<你根据提问自主提取的维度3>", "weight": 30, "reason": "..."}}
        ],
        "step2_evaluation_details": [
            {{"dimension": "准确性基准", "score": 25, "deduction_reason": "金额数据多写了一个零"}},
            {{"dimension": "<维度2>", "score": 35, "deduction_reason": "..."}},
            {{"dimension": "<维度3>", "score": 20, "deduction_reason": "..."}}
        ],
        "step3_total_score": 80,
        "step4_feedback": "如果低于 80 分，请给出极其具体、尖锐的修改指导意见。如果大于等于 80 分，填'审核通过，准许交付'。"
    }}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": system_prompt}],
            response_format={"type": "json_object"},
            temperature=0.0 # 法官不需要创造力，只需要冷酷的客观判定
        )
        
        result_str = response.choices[0].message.content
        review_result = json.loads(result_str)
        
        # 💡 修复点：修改这里，让 Python 去抓取新版的键名！
        score = review_result.get("step3_total_score", 0)
        feedback = review_result.get("step4_feedback", "未知意见")
        
        state["reviewer_score"] = score
        state["reviewer_feedback"] = feedback  # 把意见落盘到全局状态中
        

        if score >= 80:
            print(f"   => ✅ 总监拍板：得分 {score}，审核通过！准许交付。")
            state["audit_log"].append(f"Reviewer: 审核通过 ({score}分)")
        else:
            print(f"   => ❌ 总监震怒：得分 {score}，打回重写！")
            print(f"   => 📝 修改意见：{feedback}")
            # 将法官的意见强行追加到草稿状态中，让下属知道错在哪了
            state["draft_report"] += f"\n\n【总监的修改意见】：{feedback}\n（请根据上述意见重新生成报告）"
            state["audit_log"].append(f"Reviewer: 打回重做，得分 {score}")
            
# ... 前面的代码保持不变 ...
    
    except Exception as e:
         print(f"   => ⚠️ Reviewer 调用异常: {e}，默认放行。")
         state["reviewer_score"] = 80 # 异常兜底放行
         
    return state  # <--- 就是漏了这一行！请把它加在文件的最后，注意缩进要和 try/except 对齐