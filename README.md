# 🚀 E-commerce Data Agent: AI 驱动的电商数据分析与归因工作流

> 本项目主打一个“用魔法打败魔法”：探索如何用 LLM 叠加机器学习与因果推断算法，把传统电商数据科学的工作流给“重做一遍”。

在这里，你可以看到代码从初出茅庐的“单体智能”，一路打怪升级到“多 Agent 协作”的完整进化史。表面上，这套框架是为了解决海量数据查询、复杂业务归因（比如让人头秃的 GMV 异动）以及商品策略分析等硬核痛点；但实不相瞒，这本质上也是一个热爱折腾的数据人，为了满足好奇心（顺便幻想一下未来能少写几行 SQL）的自娱自乐之作！😎💻

---

## 🌟 项目愿景与痛点解决

在真实的电商业务场景中，数据分析师往往被困于繁琐的“取数”工作中，而针对核心业务指标（如大促期间的 GMV 异动、新商品冷启动效果、盘货策略复盘），传统的基于规则的归因往往难以量化各维度的真实驱动力。

本项目旨在构建一个自动化的 Data Agent 框架，实现：
1. **数据获取自动化**：通过精准的 NL2SQL（自然语言转 SQL）实现秒级取数。
2. **分析链路闭环**：不仅能“查出数据”，更能自动调用 ML 算法（如基于 XGBoost 的特征重要性分析）甚至因果推断模型，给出具有统计学意义的归因结论。
3. **高可用与防幻觉**：引入多 Agent 交叉校验机制，确保生成 SQL 的语法正确性与业务逻辑的严谨性。

---

## 📂 版本导航与架构演进

### 📊 系统架构与工作流 (System Architecture)

```mermaid
graph TD
    User((用户提问)) --> Router[🧠 Router Agent <br> 意图网关]
    
    Router -- "场景A: 日常闲聊" --> Direct[直接回复并阻断]
    Router -- "场景B: 数据分析" --> Validator[🛡️ Validator Agent <br> 动态 Schema 探查]
    
    Validator -- "无可用字段" --> Stop[拦截熔断，防幻觉]
    Validator -- "校验通过" --> Dispatch{动态调度层}
    
    subgraph ⚡ 专家执行层 (并发执行)
        Dispatch --> SQL[🛠️ SQL Skill <br> 取数与沙盒校验]
        Dispatch --> ML[🤖 ML Skill <br> XGBoost 算法归因]
    end
    
    SQL -- "真实业务数据" --> Whiteboard[(全局大白板 <br> Global State)]
    ML -- "特征重要性/预测" --> Whiteboard
    
    Whiteboard --> Synth[📝 Synthesizer Agent <br> 商业洞察合成]
    
    Synth --> Reviewer[⚖️ Reviewer Agent <br> 总监级逻辑审计]
    
    Reviewer -- "得分 < 80 (附带尖锐反馈)" --> Synth
    Reviewer -- "得分 >= 80" --> Output((高管级商业战报))
    
    classDef agent fill:#f9f0ff,stroke:#b19cd9,stroke-width:2px;
    classDef skill fill:#e6f3ff,stroke:#6baed6,stroke-width:2px;
    classDef state fill:#fff3e0,stroke:#ffb74d,stroke-width:2px;
    
    class Router,Validator,Synth,Reviewer agent;
    class SQL,ML skill;
    class Whiteboard state;
```

本项目完整保留了架构演进的历史，分为以下两个核心阶段：

### 📍 [v2_multi_agent_framework](./v2_multi_agent_framework) (当前主干版本)
**聚焦：智能体编排 (Multi-Agent) 与 深度商业洞察 (Deep Insight)**

这是当前的最优解版本，采用模块化设计，将意图识别、数据查询、算法归因与结果校验端到端解耦：
* **🤖 Router Agent (路由网关)**：精准识别用户意图，判断是简单的基础数据探查，还是复杂的指标异动归因。
* **🛠️ ML Analysis Skill (智能归因引擎)**：超越传统取数逻辑。内置机器学习分析模块，面对 GMV 波动等复杂场景，能自动提取特征，量化各维度（如流量、转化率、客单价等）对全局指标的贡献度。*(未来规划：接入 DML/DID 等因果推断方法进行策略评估)*。
* **🛡️ Validator & Reviewer (质量保障防线)**：Validator 负责对生成的 SQL 进行语法预检和沙盒执行，Reviewer 则从业务逻辑层面综合评估最终的分析洞察，极大降低了 LLM 在严肃商业场景下的“幻觉”风险。
* **📊 Synthesizer (综合输出)**：将冰冷的数据和算法输出，转化为结构化、可落地的业务复盘报告。

### 📍 [v1_single_agent_baseline](./v1_single_agent_baseline) (基础探索版)
**聚焦：NL2SQL 跑通与轻量级业务探查**

这是项目早期的基础形态，验证了 LLM 直接对接业务数据库的可行性：
* **Text-to-Insight**：利用 Function Calling 将业务需求（如“查询上个月复购率最高的 Top 10 商品”）转化为 SQL。
* **电商数据沙盒**：内置轻量级的电商测试数据库生成脚本（`setup_ecommerce_db.py`），包含用户、订单、商品等基础表结构，用于快速验证。

---

## 🛠️ 技术栈与核心能力

* **大模型框架**: 基于主流 LLM API，结合 Function Calling / Tool Use 机制。
* **算法与数据处理**: Python, SQL, XGBoost (用于异常归因分析), Pandas.
* **工程架构**: 面向对象设计的 Agent 抽象层，隔离了状态管理 (`core/state.py`)、技能调用 (`skills/`) 与角色设定 (`agents/`)。

---

## 💡 演进思考：为什么要做从 V1 到 V2 的重构？

在 V1 阶段的单体 Agent 测试中，我发现单一模型在面对复杂的电商表关联（Join）和带有极强业务 Know-how 的口径定义时，极易产生幻觉，且仅仅“把数取出来”并不等于“解决业务问题”。

因此，V2 架构的诞生不仅仅是工程代码的重构，更是**对数据科学工作流范式的重新理解**。通过引入多 Agent 机制（Validator/Reviewer），系统具备了“自我纠错”的能力；而通过引入独立的 ML Skill，Agent 的能力边界从“数据提取器”正式跃升为“策略参谋”，能够真正服务于商品盘货策略、大促复盘等高价值商业决策。

---

## 🚀 快速开始

*(如果你想在本地运行 V2 框架，请参考以下步骤)*

```bash
# 1. 克隆仓库
git clone [https://github.com/YourUsername/ecommerce-data-agent.git](https://github.com/YourUsername/ecommerce-data-agent.git)
cd ecommerce-data-agent/v2_multi_agent_framework

# 2. 安装依赖 (建议使用虚拟环境)
pip install -r requirements.txt # 请确保你后续补齐了这个文件

# 3. 初始化电商 Mock 数据库
python init_db.py

# 4. 运行主程序
python main.py
