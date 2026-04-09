# main.py
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import uuid
import json
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

        # 报告合成与法官评审
        state = node_synthesizer(state)
        state = node_reviewer(state)
        
        if state["reviewer_score"] >= 80:
            break 
        else:
            print("   ⏳ 报告被打回，总监意见已下发给底层特工，准备回炉重造...")
            time.sleep(1) 
            
    print("\n" + "="*60)
    print(f"🎯 终极输出：高管级商业洞察报告 (最终得分: {state['reviewer_score']})")
    print("="*60)
    print(state["draft_report"])
    print("="*60)
    
    try:
        with open(LOG_PATH, "a", encoding="utf-8") as f:
            f.write(json.dumps(state, ensure_ascii=False) + "\n")
        print(f"\n💾 本次流转日志已保存至: {LOG_PATH}")
    except Exception as e:
        pass

if __name__ == "__main__":
    test_query = """
帮我查一下双十一期间总共有多少订单？并产出分析报告
    """
    run_workflow(test_query)