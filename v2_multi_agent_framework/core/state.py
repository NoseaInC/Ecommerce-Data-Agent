# core/state.py
from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    """
    数科多智能体协作全局状态图 (The Global Whiteboard)
    """
    # 1. 基础信息层
    session_id: str               # 任务追踪ID，用于落地全局审计日志
    user_query: str               # 用户的原始提问
    
    # 2. 路由与控制层
    is_info_sufficient: bool      # Validator 判断数据/条件是否充足
    task_category: str            # Router 判定的任务类型
    tasks: List[str]              # Router 规划的并行执行节点 (如: ["sql_skill", "xgboost_skill"])
    
    # 3. 数据与结果层
    data_reference: str           # 存放拉取下来的本地临时数据路径 (不要直接存 DataFrame)
    analytics_results: Dict[str, Any] # 存放各个 Skill 跑出来的数字/特征结论
    generated_plots: List[str]    # 存放绘图 Skill 生成的本地图片路径
    
    # 4. 交付与质检层
    draft_report: str             # 分析师 Agent 合成的业务报告草稿
    reviewer_score: int           # 评审法官的打分 (0-100)       
    reviewer_feedback: str        # <--- 新增这行：存放法官的真实修改意见    

    # 5. 审计层
    audit_log: List[str]          # 全局流转日志