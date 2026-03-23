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
    system_prompt = f"""
    你是某一线电商平台极其严厉的数据分析总监。
    你的下属（Synthesizer）刚刚提交了一份商业洞察报告草稿。
    你需要对照【业务方的原始提问】和【底层跑出的真实数据】，对这份报告进行打分（0-100分）。
    
    【业务方原始提问】: {query}
    【底层真实数据】: {json.dumps(raw_results, ensure_ascii=False)}
    【下属提交的报告草稿】:
    {draft}
    
    【打分标准】
    1. 准确性（40分）：是否准确引用了底层数据？严禁出现幻觉或编造数字。
    2. 完整性（30分）：是否完全回答了业务方的所有提问？
    3. 专业性（30分）：是否有极其干瘪的程序语言（如中括号、元组）？语言是否符合高管汇报的商业 Sense？
    
    你必须且只能返回一个合法的 JSON，格式如下：
    {{
        "score": 85,
        "feedback": "如果低于 80 分，请给出极其具体、尖锐的修改指导意见。如果大于等于 80 分，填'审核通过，准许交付'。"
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
        

        score = review_result.get("score", 0)
        feedback = review_result.get("feedback", "未知意见")
        
        state["reviewer_score"] = score
        state["reviewer_feedback"] = feedback  # <--- 把意见落盘到全局状态中
        

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