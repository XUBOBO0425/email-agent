# Email Agent 项目思维导图

> 基于当前代码、README、设计文档与测试整理。主图适合快速建立全局认知，后面的流程图用于理解运行链路。

```mermaid
mindmap
  root((Email Agent))
    项目定位
      本地智能邮件助手
      163 邮箱接入
      邮件分类与优先级判断
      自动提取待办
      日报 周报 时间段报告
      用户角色自适应
    用户入口
      setup
        读取近 30 天邮件元数据
        自动推测用户角色
        用户确认后写入配置
      check
        拉取未读邮件
        Message-ID 去重
        分类并提取待办
        dry-run 成本预估
      scan
        按日期或本周扫描
        最多处理 100 封
        生成时间段报告
      report
        默认日报
        周报
        自定义日期范围
      daemon
        周期检查新邮件
        指定时间生成日报
      help
        命令与示例
    核心架构
      CLI 编排层
        参数解析
        配置校验
        组件初始化
        结果展示
      Email 接入层
        EmailAdapter 抽象接口
        IMAPAdapter 实现
        搜索未读邮件
        按日期搜索
        读取邮件头与正文
        MIME HTML 编码解析
      Agent 决策层
        注入角色 System Prompt
        注入发件人历史
        注入当前待办
        LLM 决定工具调用
        最多 max_turns 轮
        批量逐封处理
        失败邮件跳过并记录
      Tool 工具层
        ToolRegistry
          注册定义和处理器
          暴露工具 Schema
          执行工具并封装异常
        classify_email
          分类
          优先级
          摘要
          判断依据
        extract_todos
          待办内容
          截止日期
          来源邮件
        generate_report
          daily
          weekly
          scan
        扫描期查询工具
          search_by_date
          get_sender_history
          get_pending_tasks
      LLM 适配层
        ClaudeClient
          Anthropic Messages API
          原生工具调用格式
          超时与限流重试
        DeepSeekClient
          OpenAI 兼容接口
          消息格式转换
          工具 Schema 转换
          响应统一为 ClaudeResponse
      Memory 记忆层
        SQLite
        processed_emails
          原始正文
          分类和优先级
          摘要和判断依据
        tasks
          pending 或 done
          截止日期
          来源 Message-ID
        skipped_emails
          失败原因
          邮件基本信息
        reports
          报告类型
          时间范围
          Markdown 正文
    核心数据流
      感知 PERCEIVE
        IMAP 获取 UID
        Message-ID 判重
        拉取完整邮件
      推理 THINK
        邮件正文
        用户角色
        发件人历史
        历史待办
      行动 ACT
        调用分类工具
        调用待办工具
        继续推理或结束
      记忆 MEMORY
        保存处理后邮件
        保存待办
        保存失败项
        保存报告
      输出 OUTPUT
        CLI 汇总
        报告正文
        守护进程日志
    配置体系
      config.yaml
      provider
        claude
        deepseek
      profile
        worker
        jobseeker
        professor
      email
        IMAP 服务器与端口
        邮箱地址
        授权码
        SMTP 字段暂未参与发送
      agent
        max_turns
      daemon
        check_interval
        report_at
      memory
        db_path
      环境变量覆盖
        EMAIL_AGENT_PROVIDER
        EMAIL_AGENT_API_KEY
        EMAIL_AGENT_MODEL
        EMAIL_AGENT_EMAIL_ADDRESS
        EMAIL_AGENT_EMAIL_PASSWORD
        EMAIL_AGENT_PROFILE
    工程与质量
      Python 3.12+
      src 目录布局
      uv 或 pip
      pytest
        配置与模型
        SQLite Store
        IMAP 适配器
        Agent 循环
        DeepSeek 格式转换
        Tool 集成
      Ruff
      设计文档
      实施计划
    当前范围与边界
      单邮箱单用户
      当前仅实现 IMAP 接收
      不自动发送或回复邮件
      不使用向量数据库
      不做多用户权限系统
      邮件按顺序逐封处理
      SQLite 本地持久化
```

## 主运行链路

```mermaid
flowchart LR
    U[用户执行 CLI] --> C[加载并校验配置]
    C --> M[初始化 SQLite MemoryStore]
    C --> L{选择 LLM Provider}
    L --> CA[ClaudeClient]
    L --> DS[DeepSeekClient]
    C --> I[连接 163 IMAP]
    I --> S[搜索 UID]
    S --> D{Message-ID 已处理?}
    D -- 是 --> SK[跳过重复邮件]
    D -- 否 --> F[拉取完整邮件]
    F --> A[Agent.process_email]
    M -->|发件人历史与待办| A
    CA --> A
    DS --> A
    A --> T{LLM 请求工具?}
    T -- classify_email --> CL[分类 优先级 摘要]
    T -- extract_todos --> TD[提取并保存待办]
    CL --> T
    TD --> T
    T -- 否或达到轮次上限 --> P[保存处理结果]
    P --> M
    P --> O[CLI 汇总输出]
```

## 模块依赖关系

```mermaid
flowchart TB
    CLI[src/email_agent/cli.py]
    CONFIG[config.py]
    CORE[agent/core.py]
    REG[agent/tools/registry.py]
    TOOLS[agent/tools/*]
    PROMPTS[prompts/*]
    EMAIL[email/base.py + imap_.py]
    LLM[llm/client.py + deepseek_client.py]
    STORE[memory/store.py]
    MODELS[memory/models.py]

    CLI --> CONFIG
    CLI --> CORE
    CLI --> EMAIL
    CLI --> LLM
    CLI --> STORE
    CLI --> REG
    CORE --> PROMPTS
    CORE --> REG
    CORE --> LLM
    CORE --> STORE
    CORE --> MODELS
    TOOLS --> REG
    TOOLS --> STORE
    TOOLS --> MODELS
    EMAIL --> MODELS
    STORE --> MODELS
```

## 一句话理解

Email Agent 以 CLI 为入口，从 163 邮箱通过 IMAP 感知邮件，把邮件、用户角色和历史记忆交给 Claude 或 DeepSeek 推理，由模型选择“分类、提取待办、生成报告”等工具执行，最后将结果持久化到本地 SQLite，并通过命令行或守护进程持续输出。
