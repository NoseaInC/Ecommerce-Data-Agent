import json
import re
from openai import OpenAI
from core.state import AgentState
from core.config import DEEPSEEK_API_KEY, BASE_URL, MODEL_NAME

client = OpenAI(api_key=DEEPSEEK_API_KEY, base_url=BASE_URL)

def node_reviewer(state: AgentState) -> AgentState:
    print("\n⚖️ [Reviewer Agent] 启动！神经-符号联合质检机正在扫描...")
    
    query = state["user_query"]
    raw_results = state.get("analytics_results", {})
    draft = state.get("draft_report", "")
    
    # 1. 降维打击：让大模型只做结构化事实提取，绝对不准打分！
    extraction_prompt = f"""
    你是一个极其客观的文本事实提取器。
    你需要阅读下属提交的商业报告草稿，并提取其中的关键元素。
    
    【报告草稿】:
    {draft}
    
    请严格按照以下 JSON 格式输出：
    {{
        "extracted_metric_numbers": [
            "提取草稿中提到的核心【原始绝对数值】（如 '4461', '9576400' 等）。",
            "【🚨绝对禁止提取】：带有 '%' 的百分比（如 85.6%）、带有 '倍' 的倍数（如 8.6）、环比增幅（如 +741%）、以及经过单位换算的数字（如 957.6万元，只提取精确到元的原始数字）。",
            "如果没有符合条件的绝对数值则输出空列表 []"
        ],
        "has_sql_or_json_symbols": true/false,
        "has_actionable_advice": true/false
    }}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_NAME,
            messages=[{"role": "system", "content": extraction_prompt}],
            response_format={"type": "json_object"},
            temperature=1 # 保持 0.0，只要稳定提取
        )
        
        result_str = response.choices[0].message.content
        extracted_data = json.loads(result_str)
        
        # ========================================================
        # 🐍 核心改造区：Python 符号逻辑绝对判决 (Neuro-Symbolic)
        # ========================================================
        final_score = 100
        feedback_reasons = []
        
        # 提取草稿中的标签
        raw_numbers_in_draft = re.findall(r'<raw>(.*?)</raw>', draft)
        calc_numbers_in_draft = re.findall(r'<calc>(.*?)</calc>', draft)
        
        # 规则 0：血缘规范强制校验 (逼迫 Synthesizer 必须打标签)
        if not raw_numbers_in_draft and not calc_numbers_in_draft:
            final_score -= 50
            feedback_reasons.append("❌ 规范违规：报告中缺少 <raw> 或 <calc> 数据血缘标签。你必须严格标记数字来源！")
            
        # 规则 1：格式违规排查（防止输出成堆的 SQL 语句）
        if "SELECT " in draft.upper() or "FROM orders" in draft.upper():
            final_score -= 20
            feedback_reasons.append("❌ 规范违规：报告中残存底层代码或SQL语句，缺乏高管汇报的专业性。")
            
        # 规则 2：底层冷数据 100% 绝对对齐校验 (只校验 <raw> 标签)
        raw_results_str = str(raw_results)
        
        for num_str in raw_numbers_in_draft:
            # 去除可能存在的空格
            clean_num = num_str.strip()
            # 粗粒度匹配：被标记为 <raw> 的数字，必须在底层数据字符串中出现过
            if clean_num not in raw_results_str:
                final_score -= 30
                feedback_reasons.append(f"❌ 原始数据幻觉致命错误：你用 <raw> 标记了数据 '{clean_num}'，但在底层真实的 SQL 结果中根本找不到这个原始数值！")

        # 规则 3：业务完整性排查 (让 LLM 依然负责看有没有策略)
        if not extracted_data.get("has_actionable_advice", False):
            final_score -= 15
            feedback_reasons.append("⚠️ 洞察缺失：没有基于数据给出实质性的商业建议或下一步策略。")

        # 兜底：防止分数被扣成负数
        score = max(0, final_score)
        feedback = "\n".join(feedback_reasons) if feedback_reasons else "✅ 质量极佳，格式合规，事实 100% 对齐，准许交付。"
        # ========================================================

        state["reviewer_score"] = score
        state["reviewer_feedback"] = feedback
        
        if score >= 80:
            print(f"   => ✅ Python 质检通过：最终得分 {score}！")
            state["audit_log"].append(f"Reviewer: 神经符号质检通过 ({score}分)")
        else:
            print(f"   => ❌ Python 质检打回：最终得分 {score}！")
            print(f"   => 📝 扣分账本详单：\n{feedback}")
            # 将 Python 算出来的无情账本贴回给特工
            state["draft_report"] += f"\n\n【质检系统自动拦截日志】：\n{feedback}\n（请严格修正上述错误，严禁捏造数据！）"
            state["audit_log"].append(f"Reviewer: 触发机器质检拦截，得分 {score}")
            
    except Exception as e:
         print(f"   => ⚠️ Reviewer 神经符号评估组件异常: {e}")
         print(f"   => 🛡️ 异常兜底策略：放行交给后续人类复核。")
         state["reviewer_score"] = 80 
         state["reviewer_feedback"] = f"质检组件代码运行异常放行：{str(e)}"
         
    return state