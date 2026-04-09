# main.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import uuid
import copy
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from core.state import AgentState
from core.config import LOG_PATH

from agents.router_agent import node_router
from agents.validator_agent import node_validator
from agents.synthesizer_agent import node_synthesizer
from agents.reviewer_agent import node_reviewer

# 💡 核心改动：像导入 SQL 特工一样，优雅地导入 ML 特工
from skills.sql_skill import node_sql_skill
from skills.ml_analysis_skill import node_ml_analysis_skill


import json
from datetime import datetime
from core.config import EXPERIENCE_DB_PATH, ENABLE_HUMAN_IN_THE_LOOP

# ========================================================
# ⚙️ 飞轮引擎：将人类偏好沉淀至本地 JSONL (未来的 RLHF 燃料)
# ========================================================
def save_to_experience_db(state: AgentState, is_positive: bool):
    """记录每一次的高管审核结果，用于系统长期进化"""
    os.makedirs(os.path.dirname(EXPERIENCE_DB_PATH), exist_ok=True)
    
    record = {
        "timestamp": datetime.now().isoformat(),
        "query": state.get("user_query", ""),
        "draft_report": state.get("draft_report", ""),
        "is_positive": is_positive,
        "reject_type": state.get("human_reject_reason_type", ""),
        "human_feedback": state.get("human_feedback", "")
    }
    
    try:
        with open(EXPERIENCE_DB_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
        print(f"   => 💾 [数据飞轮] 已成功将该 Case (正向:{is_positive}) 存入本地经验池！")
    except Exception as e:
        print(f"   => ⚠️ 经验池写入失败: {e}")

# ========================================================
# 👨‍⚖️ 人类法庭：系统挂起与终端交互拦截
# ========================================================
def human_intervention_node(state: AgentState) -> AgentState:
    """如果机器质检放行，最后必须由人类专家点头"""
    if not ENABLE_HUMAN_IN_THE_LOOP:
        state["human_approved"] = True
        return state
        
    print("\n" + "="*65)
    print("👨‍⚖️ [人类专家介入] AI 质检机已放行，请您进行最终的商业复核！")
    print("="*65)
    print(f"【底层特工获取的绝对真实数据】:\n{state.get('analytics_results')}")
    print("-" * 65)
    print(f"【待审核的商业战报草稿】:\n{state.get('draft_report')}")
    print("="*65)
    
    while True:
        choice = input("\n您是否同意放行并交付该报告？(y/n): ").strip().lower()
        if choice in ['y', 'n']:
            break
        print("输入无效，请输入 y 或 n。")
        
    if choice == 'y':
        state["human_approved"] = True
        state["human_feedback"] = "人类专家审核通过。"
        print("\n✅ 人类专家已放行，准许对外交付！")
        save_to_experience_db(state, is_positive=True)
    else:
        state["human_approved"] = False
        print("\n❌ 请选择打回原因分类 (将用于后续微调对齐)：")
        print("  1. 分析思路存在偏差")
        print("  2. SQL提取或计算逻辑错误")
        print("  3. 报告中仍存在数据不准确/幻觉")
        print("  4. 缺乏深度，商业Sense不足")
        print("  5. 其他问题")
        
        reason_map = {"1": "思路偏差", "2": "代码逻辑错误", "3": "数据幻觉", "4": "商业Sense不足", "5": "其他"}
        reason_code = input("请输入对应序号 (1-5): ").strip()
        reason_type = reason_map.get(reason_code, "其他")
        
        detailed_feedback = input("请填写极其具体的修改指导意见 (将直接喂给底层特工作为重写依据): ").strip()
        
        state["human_reject_reason_type"] = reason_type
        state["human_feedback"] = detailed_feedback
        
        # ⚠️ 核心拦截机制：剥夺放行权，强制将总分降为 0！
        state["reviewer_score"] = 0 
        state["reviewer_feedback"] = f"[人类高管终极驳回] 错误类型：{reason_type}。具体意见：{detailed_feedback}"
        
        # 把人类的怒吼贴到草稿末尾，让底层 Agent 看着改
        state["draft_report"] += f"\n\n【人类高管终极批示】：\n方向错误（{reason_type}），{detailed_feedback}\n（请立即反思并重写！）"
        
        print("\n🔄 已触发回炉重造机制，前线特工正在重新集结...")
        save_to_experience_db(state, is_positive=False)
        
    return state

# ==========================================
# ⚡ 技能注册中心 (Skill Registry) - 真正的可插拔架构
# ==========================================
SKILL_REGISTRY = {
    "sql_skill": node_sql_skill,
    "ml_analysis_skill": node_ml_analysis_skill
}

def run_workflow(query: str):
    print("="*60)
    print(f"🚀 任务启动: {query}")
    print("="*60)
    
    state: AgentState = {
        "session_id": str(uuid.uuid4()),
        "user_query": query,
        "is_direct_chat": False,
        "direct_response": "",
        "is_info_sufficient": True,
        "task_category": "",
        "tasks": [], # <--- 移除之前的硬编码，完全听从主脑的安排！
        "data_reference": "",
        "analytics_results": {},
        "generated_plots": [],
        "draft_report": "",
        "reviewer_score": 0,
        "reviewer_feedback": "",
        "audit_log": []
    }
    
    state["audit_log"].append(f"初始化任务: {query}")
    
    # ==========================================
    # 🌟 第一关：主脑拦截网关
    # ==========================================
    state = node_router(state)
    
    if state.get("is_direct_chat"):
        print("\n" + "="*60)
        print(f"🤖 [主脑直答]:\n{state['direct_response']}")
        print("="*60)
        return # <--- 提前下班！不再执行后续的 Validator 和 并发 Agent！
        
    # ==========================================
    # 🌟 第二关：数据资产守门人
    # ==========================================
    state = node_validator(state)
    
    if not state["is_info_sufficient"]:
        print("🛑 拦截：信息不足，任务终止。")
        return
        
    # ... 后面的 DAG 并发逻辑 (while attempt < max_retries:) 保持不变 ...
        
    max_retries = 3
    attempt = 0
    
    while attempt < max_retries:
        attempt += 1
        print(f"\n" + "="*40)
        print(f"--- 🔄 开始第 {attempt} 轮全局执行与审核 ---")
        print("="*40)
        
        # ==========================================
        # ⚡ DAG 并发调度引擎 (Fan-out / Fan-in)
        # ==========================================
        skills_to_run = [skill for skill in state["tasks"] if skill in SKILL_REGISTRY]
        
        if skills_to_run:
            print(f"   => ⚡ [DAG 调度器] 正在并发拉起 {len(skills_to_run)} 个分析节点: {skills_to_run}")
            
            with ThreadPoolExecutor(max_workers=len(skills_to_run)) as executor:
                # 深拷贝隔离状态
                futures = {
                    executor.submit(SKILL_REGISTRY[skill_name], copy.deepcopy(state)): skill_name 
                    for skill_name in skills_to_run
                }
                
                state["analytics_results"] = {}
                
                for future in as_completed(futures):
                    skill_name = futures[future]
                    try:
                        completed_state = future.result()
                        if "analytics_results" in completed_state:
                            state["analytics_results"].update(completed_state["analytics_results"])
                        if "audit_log" in completed_state:
                            for log in completed_state["audit_log"]:
                                if log not in state["audit_log"]:
                                    state["audit_log"].append(log)
                                    
                        print(f"   => ✅ [{skill_name}] 并发任务执行完毕，数据已安全挂载至全局白板！")
                    except Exception as e:
                        print(f"   => ❌ [{skill_name}] 并发执行崩溃: {e}")
        else:
            print("   => ⚠️ [DAG 调度器] 未发现需要执行的底层技能。")

        # 报告合成与机器质检评审
        state = node_synthesizer(state)
        state = node_reviewer(state)
        
        # 判断一：机器质检是否及格？
        if state.get("reviewer_score", 0) >= 80:
            # 判断二：机器及格了，移交给人类专家进行终极复核 (HITL 拦截)
            state = human_intervention_node(state)
            
            # 判断三：人类专家是否也同意放行？
            if state.get("human_approved", True):
                break  # 人机双重认证通过，彻底跳出重试循环！
            else:
                # 人类拒绝。此时 human_intervention_node 已经把分数重置为 0，并加上了人类怒吼
                print("   ⏳ 报告被人类高管驳回，指导意见已下发，准备回炉重造...")
                import time
                time.sleep(1) 
        else:
            # 机器质检就没及格，直接重做
            print("   ⏳ 报告被机器质检打回，机器拦截意见已下发，准备回炉重造...")
            import time
            time.sleep(1) 
            
    # ================= 循环外：最终交付结算 =================
    print("\n" + "="*60)
    print(f"🎯 终极交付：高管级商业洞察报告 (最终状态: 人机双重审核通过)")
    print("="*60)
    print(state.get("draft_report", "生成失败"))
    print("="*60)
    
    # 记录本地的全量流转日志
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(state, ensure_ascii=False) + "\n")
        print(f"\n💾 本次完整流转日志已保存至: {LOG_PATH}")
    except Exception as e:
        pass

if __name__ == "__main__":
    test_query = """
帮我查一下双十一期间总共有多少订单？并产出分析报告
    """
    run_workflow(test_query)