# -*- coding: utf-8 -*-
"""手册正文内容。build_content(doc, h) 由 build_manual.py 调用，h 为辅助函数字典。"""


def build_content(doc, h):
    para = h['para']; h1 = h['h1']; h2 = h['h2']; h3 = h['h3']
    body = h['body']; bullet = h['bullet']; step = h['step']; note = h['note']
    figure = h['figure']; table = h['table']; code_block = h['code_block']
    setf = h['set_run_font']; AL = h['WD_ALIGN_PARAGRAPH']
    Pt = h['Pt']; RGB = h['RGBColor']
    CN_HEAD = h['CN_HEAD']

    # ════════════════════════════ 封面 ════════════════════════════
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph(); p.alignment = AL.CENTER
    r = p.add_run("单细胞细胞类型注释与稀有细胞识别\n多方法评估系统")
    setf(r, cn=CN_HEAD, size=26, bold=True, color=h['C_H1'])
    doc.add_paragraph()
    p = doc.add_paragraph(); p.alignment = AL.CENTER
    r = p.add_run("scAnnoRare")
    setf(r, size=20, bold=True, color=h['C_MUTE'])
    for _ in range(3):
        doc.add_paragraph()
    p = doc.add_paragraph(); p.alignment = AL.CENTER
    r = p.add_run("用 户 操 作 手 册")
    setf(r, cn=CN_HEAD, size=24, bold=True, color=h['C_TITLE'])
    doc.add_paragraph()
    p = doc.add_paragraph(); p.alignment = AL.CENTER
    r = p.add_run("Version 1.0")
    setf(r, size=16, color=h['C_MUTE'])
    for _ in range(6):
        doc.add_paragraph()
    for line in ["软件名称：单细胞细胞类型注释与稀有细胞识别多方法评估系统",
                 "软件版本：V1.0",
                 "英文简称：scAnnoRare",
                 "文档类型：用户操作手册",
                 "文档版本：第一版"]:
        p = doc.add_paragraph(); p.alignment = AL.CENTER
        r = p.add_run(line)
        setf(r, size=12, color=h['C_BODY'] if 'C_BODY' in h else h['C_MUTE'])

    # ════════════════════════════ 版本修订记录 ════════════════════════════
    doc.add_page_break()
    h2(doc, "版本修订记录")
    table(doc,
          ["文档版本", "对应软件版本", "修订日期", "修订说明"],
          [["第一版", "V1.0", "2026-06", "首次发布，覆盖登录、节点配对、数据集注册、实验配置、"
                                          "方法评估、多方法对比、报告中心等核心功能的操作说明。"]],
          widths=[2.5, 3.0, 3.0, 7.0])
    body(doc, "本手册随软件版本迭代持续更新。后续版本将补充内置算法调用、远程服务器计算、"
              "团队协作等功能的操作说明。")

    # ════════════════════════════ 目录 ════════════════════════════
    doc.add_page_break()
    h2(doc, "目　录")
    toc_items = [
        "第 1 章  软件概述", "第 2 章  系统架构", "第 3 章  运行环境与部署",
        "第 4 章  快速入门", "第 5 章  用户登录与账号管理", "第 6 章  计算节点配对",
        "第 7 章  首页控制台", "第 8 章  数据集注册与管理", "第 9 章  实验配置管理",
        "第 10 章  方法评估与运行", "第 11 章  多方法对比分析", "第 12 章  报告中心",
        "第 13 章  输入文件格式规范", "第 14 章  评估指标说明", "第 15 章  常见问题与故障排除",
        "附录 A  系统功能清单", "附录 B  API 接口一览", "附录 C  术语表",
    ]
    for it in toc_items:
        p = doc.add_paragraph()
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.left_indent = Pt(12)
        r = p.add_run(it)
        setf(r, size=12, color=h['C_BODY'] if 'C_BODY' in h else h['C_MUTE'])

    # ════════════════════════════ 第 1 章 软件概述 ════════════════════════════
    h1(doc, 1, "软件概述")

    h2(doc, "1.1 软件简介")
    body(doc, "单细胞细胞类型注释与稀有细胞识别多方法评估系统（英文简称 scAnnoRare）是一款面向"
              "单细胞 RNA 测序（scRNA-seq）数据分析的多方法评估平台。在单细胞数据分析中，细胞类型"
              "注释和稀有细胞识别是两类常见而重要的分析任务。现有方法众多，包括 CellTypist、scANVI、"
              "scNym、scBalance、sc-SynO、RaceID、GiniClust 等，但不同方法的输入格式、运行环境、"
              "输出格式和评估指标各不统一，科研人员在进行多方法横向比较时往往需要大量的手工处理。")
    body(doc, "scAnnoRare 通过统一的数据格式、统一的任务流程和统一的评估指标，帮助研究人员便捷地"
              "完成不同细胞注释与稀有细胞识别方法之间的比较分析。系统提供数据导入、数据概览、细胞类型"
              "分布统计、稀有类候选筛选、预测结果导入、多方法统一评估、多方法横向对比、可视化展示、"
              "实验报告生成以及本地计算资源检测等完整功能。")

    h2(doc, "1.2 软件名称与版本信息")
    table(doc, ["项目", "内容"],
          [["软件全称", "单细胞细胞类型注释与稀有细胞识别多方法评估系统"],
           ["英文简称", "scAnnoRare"],
           ["软件版本", "V1.0"],
           ["系统形态", "Web 主平台 + 桌面 Local Agent + 本地 Python 生信计算引擎"],
           ["前端技术", "Vue 3、TypeScript、Vite、Element Plus、ECharts"],
           ["后端技术", "FastAPI、SQLAlchemy、MySQL、Pydantic、Uvicorn"],
           ["计算引擎", "Python、scanpy、anndata、pandas、scikit-learn、matplotlib"]],
          widths=[4.0, 11.5])

    h2(doc, "1.3 系统定位")
    body(doc, "本系统是一个面向单细胞 RNA-seq 数据的细胞类型注释与稀有细胞识别多方法评估平台，"
              "支持 Web 实验管理、本地算力调用、预测结果导入、稀有类候选筛选、多方法对比、可视化"
              "展示与实验报告生成。")
    body(doc, "系统采用 Web 主平台与桌面客户端协同的架构。Web 主平台负责项目管理、实验配置、"
              "方法结果管理、任务状态展示、可视化展示和报告管理；桌面 Local Agent 负责本地 CPU/GPU "
              "环境检测、本地文件访问、本地 Python 生信环境检测和本地分析任务执行。原始单细胞数据"
              "默认保存在本地，不上传至云端服务器，从而兼顾数据安全与计算性能。")

    h2(doc, "1.4 主要功能特性")
    feats = [
        ("用户登录与账号管理", "提供用户注册、登录、退出等基础账号功能，并内置默认管理员账号便于快速上手。"),
        ("本地计算节点配对", "通过一次性配对码安全地将 Web 平台与本地 Agent 关联，实时检测本地 CPU、内存、"
                          "GPU 及单细胞生信依赖包的状态。"),
        ("数据集注册与管理", "支持本地 .h5ad 文件的轻量级检测、标签分布统计、稀有细胞候选自动筛选与可视化展示。"),
        ("实验配置管理", "支持创建细胞类型注释评估实验与稀有细胞识别评估实验，并提供三种稀有评估模式。"),
        ("方法评估与运行", "支持导入方法预测结果 CSV，在本地节点上自动进行 cell_id 对齐与指标计算。"),
        ("多方法对比分析", "在同一实验下聚合多个方法的评估结果，提供可排序的对比排行榜与交互式图表重绘。"),
        ("报告中心", "自动生成自包含的 HTML 评估报告，支持在线查看与本地下载。"),
    ]
    for name, desc in feats:
        h3(doc, "● " + name)
        body(doc, desc)

    h2(doc, "1.5 典型应用场景")
    bullet(doc, "科研人员对同一单细胞数据集运行多种细胞注释方法后，需要统一比较各方法的准确率、宏平均 F1 等指标；")
    bullet(doc, "研究稀有细胞类型（如 ASDC、ILC、ionocyte 等）识别能力时，需要专门评估稀有类的精确率、召回率、AUROC/AUPRC；")
    bullet(doc, "方法开发者希望在标准化的评估框架下，对新方法与已有基线方法进行公平比较；")
    bullet(doc, "教学场景中，需要直观展示不同注释方法在混淆矩阵、ROC/PR 曲线上的差异。")

    h2(doc, "1.6 系统特点")
    bullet(doc, "Web-Agent 协同架构：管理与计算分离，原始数据本地化，兼顾安全与性能；")
    bullet(doc, "统一评估标准：对所有导入方法采用相同的指标计算口径，保证比较的公平性；")
    bullet(doc, "稀有细胞专项评估：提供 single_rare、multi_rare_per_class、pooled_rare_vs_nonrare 三种评估模式；")
    bullet(doc, "可视化丰富：混淆矩阵热图、ROC/PR 曲线、细胞类型分布柱状图等，并支持交互式重绘；")
    bullet(doc, "自包含报告：生成的 HTML 报告内嵌图表，可离线查看与归档。")

    # ════════════════════════════ 第 2 章 系统架构 ════════════════════════════
    h1(doc, 2, "系统架构")

    h2(doc, "2.1 总体架构")
    body(doc, "scAnnoRare 由三层组件构成：Web 主平台、桌面 Local Agent 客户端、本地 Python 生信计算引擎。"
              "三者之间通过 HTTP 接口协同工作，整体架构如下：")
    code_block(doc, [
        "┌─────────────────────────────────────────────┐",
        "│              Web 主平台（浏览器）              │",
        "│   项目管理 / 实验配置 / 方法对比 / 报告展示    │",
        "└─────────────────────────────────────────────┘",
        "        │  配对 / 任务下发 / 状态查询 / 结果同步",
        "        ▼",
        "┌─────────────────────────────────────────────┐",
        "│            桌面 Local Agent 客户端            │",
        "│   环境检测 / 文件授权 / 任务执行 / 日志采集    │",
        "└─────────────────────────────────────────────┘",
        "        │  调用",
        "        ▼",
        "┌─────────────────────────────────────────────┐",
        "│          本地 Python 生信计算引擎             │",
        "│   h5ad 解析 / 指标计算 / 图表与报告生成        │",
        "└─────────────────────────────────────────────┘",
    ])

    h2(doc, "2.2 Web 主平台")
    body(doc, "Web 主平台是用户进行日常操作的主要界面，运行于浏览器中。它主要负责用户登录、项目与实验"
              "管理、数据集元数据管理、方法运行（method_run）管理、任务状态展示、多方法结果对比以及"
              "报告展示。Web 平台本身不直接承担繁重的计算任务，也不存储原始 .h5ad 文件，仅保存数据摘要、"
              "实验配置、指标结果和报告元数据。")

    h2(doc, "2.3 桌面 Local Agent")
    body(doc, "桌面 Local Agent 是运行在用户本地计算机上的轻量级服务，监听本地回环地址 127.0.0.1 的 "
              "17890 端口。它负责本地 CPU/内存/GPU 检测、本地 Python 及生信依赖检测、本地 .h5ad 文件"
              "的选择与读取、本地任务执行、任务日志采集、结果 JSON 生成以及本地 HTML 报告生成。Agent "
              "仅监听本地回环地址，配合一次性配对码与会话令牌（session_token）机制保证访问安全。")

    h2(doc, "2.4 本地 Python 生信计算引擎")
    body(doc, "本地计算引擎是真正执行单细胞数据解析与指标计算的部分，基于 scanpy、anndata、pandas、"
              "scikit-learn、matplotlib 等成熟的科学计算库构建。引擎以独立 Python 脚本（runner）的"
              "形式被 Local Agent 调用，分别负责注释评估、稀有细胞识别评估和报告生成。")

    h2(doc, "2.5 组件职责一览")
    table(doc, ["组件", "主要职责"],
          [["Web 前端", "用户交互、项目管理、数据概览展示、任务创建、方法对比、报告展示"],
           ["Web 后端", "用户、项目、数据集摘要、实验、method_run、结果、报告元数据管理"],
           ["桌面客户端", "启动 Local Agent、显示配对码、维护本地连接状态、展示运行状态"],
           ["Local Agent", "本地 API 服务，负责环境检测、文件访问、任务执行、日志与结果管理"],
           ["本地计算引擎", "实际运行 h5ad 解析、指标计算、图表生成和 HTML 报告生成"],
           ["数据库", "保存用户、项目、实验、任务、结果、报告等元数据（MySQL）"]],
          widths=[3.5, 12.0])

    h2(doc, "2.6 数据流与任务流")
    body(doc, "一次完整的评估任务，其数据与任务流转过程如下：")
    step(doc, 1, "用户在 Web 平台创建实验，并添加一个方法运行（method_run），上传预测结果 CSV 路径；")
    step(doc, 2, "Web 后端将任务下发给 Local Agent，携带数据集本地路径、预测 CSV 路径、标签列等参数；")
    step(doc, 3, "Local Agent 创建本地任务，调用计算引擎执行 cell_id 对齐与指标计算；")
    step(doc, 4, "计算引擎生成 result.json 结构化结果与 report.html 报告；")
    step(doc, 5, "Web 后端通过同步接口拉取结果，写入数据库并生成报告记录；")
    step(doc, 6, "Web 前端轮询任务状态，任务完成后自动刷新对比排行榜并渲染可视化图表。")

    # ════════════════════════════ 第 3 章 运行环境与部署 ════════════════════════════
    h1(doc, 3, "运行环境与部署")

    h2(doc, "3.1 硬件环境要求")
    table(doc, ["项目", "最低配置", "推荐配置"],
          [["CPU", "双核", "四核及以上"],
           ["内存", "8 GB", "16 GB 及以上"],
           ["硬盘", "10 GB 可用空间", "50 GB 及以上"],
           ["GPU", "非必需", "NVIDIA GPU（用于后续内置算法加速）"]],
          widths=[3.0, 6.0, 6.5])

    h2(doc, "3.2 软件环境要求")
    bullet(doc, "操作系统：Windows 10/11、macOS 或主流 Linux 发行版；")
    bullet(doc, "Python：3.10 或 3.11（建议）；本手册环境为 Python 3.x；")
    bullet(doc, "数据库：MySQL 8.0 及以上；")
    bullet(doc, "浏览器：Chrome、Edge、Firefox、Safari 等现代浏览器；")
    bullet(doc, "Python 依赖：fastapi、uvicorn、sqlalchemy、pymysql、scanpy、anndata、pandas、"
                "scikit-learn、matplotlib、seaborn、jinja2 等。")

    h2(doc, "3.3 数据库配置")
    body(doc, "系统使用 MySQL 存储用户、项目、数据集摘要、实验、任务、结果与报告等元数据。Web 后端"
              "通过环境变量或默认配置连接数据库，首次启动时会自动创建所需的数据表。数据库连接参数"
              "包括主机地址、端口、用户名、密码和数据库名，可在后端配置文件 db.py 中查看或通过环境"
              "变量覆盖：")
    code_block(doc, [
        "MYSQL_HOST = 数据库主机地址",
        "MYSQL_PORT = 3306",
        "MYSQL_USER = 数据库用户名",
        "MYSQL_PASSWORD = 数据库密码",
        "MYSQL_DB = scannorare",
    ])
    note(doc, "首次启动后端时会自动执行建表操作，并创建默认管理员账号 admin。")

    h2(doc, "3.4 Web 后端启动")
    body(doc, "进入 web-backend 目录，执行以下命令启动 Web 后端服务，默认监听 127.0.0.1:8000：")
    code_block(doc, [
        "cd web-backend",
        "python -m uvicorn app.main:app --host 127.0.0.1 --port 8000",
    ])
    body(doc, "启动成功后，可在浏览器访问 http://127.0.0.1:8000/docs 查看自动生成的 API 文档页面，"
              "以确认后端服务正常运行。")

    h2(doc, "3.5 Local Agent 启动")
    body(doc, "进入 local-agent 目录，执行以下命令启动本地 Agent 服务，默认监听 127.0.0.1:17890：")
    code_block(doc, [
        "cd local-agent",
        "python -m uvicorn main:app --host 127.0.0.1 --port 17890",
    ])
    body(doc, "启动成功后，可访问 http://127.0.0.1:17890/api/v1/local/health 查看健康检查结果，"
              "返回 status 为 healthy 即表示 Agent 正常运行。")

    h2(doc, "3.6 前端启动")
    body(doc, "进入 web-frontend 目录，安装依赖并启动前端开发服务器，默认监听 5173 端口：")
    code_block(doc, [
        "cd web-frontend",
        "npm install",
        "npm run dev",
    ])
    body(doc, "启动后在浏览器访问 http://localhost:5173 即可进入系统登录页面。")

    h2(doc, "3.7 启动顺序与验证")
    body(doc, "推荐的启动顺序为：先启动数据库，再启动 Web 后端，然后启动 Local Agent，最后启动前端。"
              "各服务的验证方式如下：")
    table(doc, ["服务", "端口", "验证方式"],
          [["Web 后端", "8000", "访问 /docs 出现 API 文档"],
           ["Local Agent", "17890", "访问 /api/v1/local/health 返回 healthy"],
           ["前端", "5173", "浏览器打开出现登录页"]],
          widths=[4.0, 3.0, 8.5])

    # ════════════════════════════ 第 4 章 快速入门 ════════════════════════════
    h1(doc, 4, "快速入门")

    h2(doc, "4.1 完整使用流程概览")
    body(doc, "scAnnoRare 的典型使用流程包含以下几个阶段，依次完成即可得到一份多方法评估报告：")
    step(doc, 1, "登录系统：使用默认账号或注册新账号登录 Web 平台；")
    step(doc, 2, "配对计算节点：启动本地 Agent，在 Web 平台输入配对码完成授权；")
    step(doc, 3, "注册数据集：选择本地 .h5ad 文件，检测数据结构并注册；")
    step(doc, 4, "配置实验：选定数据集与标签列，创建注释评估或稀有识别实验；")
    step(doc, 5, "导入并运行方法：上传方法预测结果 CSV，提交至本地节点计算；")
    step(doc, 6, "查看对比与报告：在对比排行榜中比较各方法，查看并下载评估报告。")

    h2(doc, "4.2 五分钟快速体验")
    body(doc, "系统在本地工作区预置了一个 tiny 测试数据集和对应的预测结果 CSV，便于首次使用者快速"
              "跑通完整流程。在数据集注册页和方法导入页均提供了「快速测试路径」一键填入功能，点击即可"
              "自动填充测试文件路径，无需手动输入。建议首次使用时先用测试数据走通全流程，再切换到真实数据。")

    h2(doc, "4.3 界面总体布局")
    body(doc, "登录后进入系统主界面。界面左侧为导航侧边栏，包含「首页控制台、计算节点配对、数据集注册、"
              "实验配置管理、评估与对比、报告中心」六个主要功能入口；侧边栏底部显示当前登录用户与退出按钮。"
              "界面顶部为面包屑导航与 Local Agent 连接状态徽章；右侧主区域为各功能页面的内容区。")

    # ════════════════════════════ 第 5 章 用户登录与账号管理 ════════════════════════════
    h1(doc, 5, "用户登录与账号管理")

    h2(doc, "5.1 登录页面")
    body(doc, "在浏览器中访问系统地址后，若尚未登录，系统会自动跳转至登录页面。登录页采用居中卡片式"
              "布局，包含「登录」与「注册」两个标签页，并在底部提供默认账号提示。")
    figure(doc, "test-01-login-page.png", "图 5-1　系统登录页面", width_cm=12.5)

    h2(doc, "5.2 用户登录")
    step(doc, 1, "在「登录」标签页中输入用户名与密码；")
    step(doc, 2, "点击「登录系统」按钮提交；")
    step(doc, 3, "登录成功后系统提示欢迎信息，并自动跳转至首页控制台。")
    note(doc, "首次使用可点击页面底部的「admin / admin」提示，自动填入默认管理员账号的用户名与密码。")

    h2(doc, "5.3 注册新账号")
    body(doc, "若需要使用独立账号，可切换到「注册」标签页：")
    step(doc, 1, "填写邮箱、用户名、密码三项信息；")
    step(doc, 2, "点击「创建账号」按钮提交注册；")
    step(doc, 3, "注册成功后系统自动切换回登录标签页，并预填刚注册的用户名与密码。")
    note(doc, "用户名具有唯一性，若注册时提示「用户名已存在」，请更换其他用户名。")

    h2(doc, "5.4 退出登录")
    body(doc, "在任意功能页面，点击左侧侧边栏底部的「退出」按钮即可退出登录。退出后系统会清除本地登录"
              "状态并跳回登录页面。出于安全考虑，退出登录的同时也会解除当前的本地 Agent 配对状态。")

    h2(doc, "5.5 路由访问控制")
    body(doc, "系统对页面访问进行登录态校验。未登录用户访问任何功能页面时，都会被自动重定向到登录页；"
              "已登录用户访问登录页时，则会自动跳转回首页控制台，避免重复登录。")

    # ════════════════════════════ 第 6 章 计算节点配对 ════════════════════════════
    h1(doc, 6, "计算节点配对")

    h2(doc, "6.1 为什么需要配对")
    body(doc, "由于原始单细胞数据默认保存在本地、计算任务也在本地执行，Web 平台需要与本地 Agent 建立"
              "可信连接，才能下发任务、读取本地文件并获取计算结果。配对机制通过一次性配对码与会话令牌，"
              "确保只有经过用户授权的 Web 页面才能访问本地 Agent，保障本地数据与计算资源的安全。")

    h2(doc, "6.2 启动 Local Agent")
    body(doc, "在进行配对前，请确保本地 Agent 服务已经启动并监听 127.0.0.1:17890。系统会自动检测 "
              "Agent 的在线状态：若检测到 Agent 在线，配对页面顶部的连接诊断会显示绿色状态；若未检测到，"
              "则提示在终端启动 Agent 服务。")
    figure(doc, "test-05-agent-after-fix.png", "图 6-1　计算节点配对页面（等待配对验证）", width_cm=14.0)

    h2(doc, "6.3 生成配对码")
    body(doc, "配对码由本地 Agent 生成，是一段 6 位的大写字母与数字组合，有效期为 5 分钟，且仅可使用一次。"
              "为防止暴力猜测，连续 5 次输入错误后该配对码即失效，需要重新生成。")

    h2(doc, "6.4 输入配对码完成授权")
    step(doc, 1, "在「节点配对授权」区域的输入框中填入 6 位配对码；")
    step(doc, 2, "点击「发起节点配对」按钮；")
    step(doc, 3, "校验通过后，Agent 返回会话令牌，页面状态变为「已授权配对」。")
    note(doc, "会话令牌仅保存在当前浏览器会话与 Agent 进程内存中；Agent 重启后令牌自动失效，需要重新配对。")

    h2(doc, "6.5 一键快速配对")
    body(doc, "为方便本机调试，配对页面提供了「一键在本地生成配对码并授权」的快捷按钮。点击后系统会"
              "自动在本地 Agent 生成配对码并立即完成配对，无需手动输入。该功能适用于开发与演示场景。")

    h2(doc, "6.6 本地算力与依赖环境诊断")
    body(doc, "配对成功后，页面右侧会实时展示本地计算节点的硬件与依赖环境信息，包括操作系统、Python "
              "版本、CPU 逻辑核心数、物理内存使用情况、GPU 型号与显存占用（若有），以及 scanpy、anndata、"
              "celltypist、scvi-tools、torch 等关键单细胞生信依赖包的安装版本。")
    figure(doc, "test-06-agent-paired-env.png", "图 6-2　配对成功后的本地算力与依赖环境诊断", width_cm=14.0)

    h2(doc, "6.7 解除配对")
    body(doc, "如需断开与本地节点的连接，可点击「解除节点配对授权」按钮。解除后会话令牌失效，需要"
              "重新配对才能继续使用本地计算功能。")

    h2(doc, "6.8 配对状态说明")
    table(doc, ["状态", "含义"],
          [["未检测到 Agent", "本地 Agent 服务未启动或端口不可达"],
           ["等待配对验证", "Agent 在线但尚未完成配对授权"],
           ["已授权配对", "配对成功，可正常下发本地计算任务"]],
          widths=[4.5, 11.0])

    # ════════════════════════════ 第 7 章 首页控制台 ════════════════════════════
    h1(doc, 7, "首页控制台")

    h2(doc, "7.1 控制台概览")
    body(doc, "登录后默认进入首页控制台。控制台是系统的总览页面，顶部为欢迎横幅与「配对本地计算节点」"
              "快捷入口，中部为统计指标卡片，下方为评估流程说明。")
    figure(doc, "test-02-dashboard.png", "图 7-1　首页控制台", width_cm=14.5)

    h2(doc, "7.2 统计指标卡片")
    body(doc, "统计卡片实时展示系统中的关键数量指标，数据来自后端统计接口，包括：")
    table(doc, ["指标", "含义"],
          [["注册数据集", "已在平台注册的数据集数量"],
           ["配置实验主题", "已创建的实验数量"],
           ["已完成评估结果", "状态为成功的方法运行数量"],
           ["生成报告数", "已生成的评估报告数量"]],
          widths=[4.5, 11.0])

    h2(doc, "7.3 评估流程说明")
    body(doc, "控制台下方以流程节点的形式直观展示系统的标准使用流程：启动 Local Agent → 注册 H5AD 数据 "
              "→ 配置评估实验 → 导入并运行计算 → 查看报告与对比。新用户可据此快速了解操作顺序。")

    # ════════════════════════════ 第 8 章 数据集注册与管理 ════════════════════════════
    h1(doc, 8, "数据集注册与管理")

    h2(doc, "8.1 数据集概念")
    body(doc, "数据集（Dataset）表示一个单细胞数据集的元数据记录。原始 .h5ad 文件默认保存在本地，"
              "平台仅保存数据集的摘要信息，包括数据集名称、本地文件路径、细胞数、基因数、obs 字段、"
              "var 字段、标签分布、稀有类候选等。")

    h2(doc, "8.2 检测 H5AD 数据结构")
    body(doc, "进入「数据集注册」页面，左侧为导入与注册表单，右侧为数据概览展示区。")
    figure(doc, "test-07-datasets.png", "图 8-1　数据集注册页面初始状态", width_cm=14.5)
    step(doc, 1, "在「本地 H5AD 绝对路径」输入框中填入 .h5ad 文件的完整路径；")
    step(doc, 2, "点击「检测 H5AD 数据结构」按钮；")
    step(doc, 3, "Agent 以 backed 模式轻量读取文件，返回细胞数、基因数、obs 列与 var 列。")
    note(doc, "页面提供「快速测试指引」，点击预置路径可一键填入本地测试数据集路径。")
    figure(doc, "test-08-dataset-inspect.png", "图 8-2　H5AD 数据结构检测结果", width_cm=14.5)

    h2(doc, "8.3 选择标签列与批次列")
    body(doc, "检测成功后，表单会展开字段绑定选项。请从 obs 列中选择真实细胞类型注释列（label_col），"
              "该列将作为评估时的真值标签；如有批次信息，可选择批次来源列（batch_col）。")

    h2(doc, "8.4 设置稀有细胞阈值")
    body(doc, "通过滑块设置稀有细胞定义阈值（默认 5%）。占比低于该阈值的细胞类型将被自动判定为稀有"
              "细胞候选类。该阈值可按数据特点调整，常用取值为 1%、3%、5%。")

    h2(doc, "8.5 注册数据集")
    body(doc, "填写数据集别名后，点击「分析标签分布并注册数据集」按钮。Agent 会统计标签分布、筛选稀有"
              "候选，并将摘要同步至 Web 平台完成注册。")

    h2(doc, "8.6 数据集概览与可视化")
    body(doc, "注册成功后，页面右侧展示数据集概览，包括细胞数、基因数、有效标签细胞数、无效标签比例、"
              "细胞类型分布柱状图，以及稀有细胞候选列表。")
    figure(doc, "test-10-dataset-result.png", "图 8-3　数据集注册成功后的概览与分布可视化", width_cm=14.5)

    h2(doc, "8.7 稀有细胞候选筛选")
    body(doc, "系统根据设定的阈值，自动列出所有占比低于阈值的细胞类型作为稀有候选，并展示其细胞数与"
              "占比。这些候选类将在后续创建稀有细胞识别实验时，作为可选的目标稀有类。")

    # ════════════════════════════ 第 9 章 实验配置管理 ════════════════════════════
    h1(doc, 9, "实验配置管理")

    h2(doc, "9.1 实验概念")
    body(doc, "实验（Experiment）表示同一数据集、同一标签列、同一评估设置下的一个评估主题。一个实验"
              "下可以聚合多个方法运行（method_run），从而进行多方法横向比较。实验本身不等于某个具体"
              "方法的一次运行。")

    h2(doc, "9.2 创建注释评估实验")
    body(doc, "进入「实验配置管理」页面，左侧为实验配置表单，右侧为已配置实验列表。")
    figure(doc, "test-11-experiments.png", "图 9-1　实验配置管理页面", width_cm=14.5)
    step(doc, 1, "在「选择基准数据集」下拉框中选择已注册的数据集；")
    step(doc, 2, "填写实验名称；")
    step(doc, 3, "在「评估任务主要维度」中选择「细胞类型注释评估」；")
    step(doc, 4, "点击「发布实验基准配置」完成创建。")
    figure(doc, "test-15-exp-label-col.png", "图 9-2　选择数据集后显示绑定的标签列", width_cm=14.5)

    h2(doc, "9.3 创建稀有细胞识别实验")
    body(doc, "若选择「稀有细胞识别评估」，表单会展开稀有专项设置，需要进一步选择稀有评估模式与目标"
              "稀有类。系统仅在目标稀有类下拉中展示该数据集占比低于阈值的候选类。")

    h2(doc, "9.4 Rare Mode 评估模式")
    body(doc, "系统支持三种稀有评估模式，适用于不同的评估目标：")
    table(doc, ["模式", "说明", "适用场景"],
          [["single_rare", "指定单一目标稀有类，按该类 vs 其余进行二分类评估",
            "ASDC vs 非 ASDC 等单一稀有类评估"],
           ["multi_rare_per_class", "对每个目标稀有类分别进行 one-vs-rest 评估并汇总",
            "需要分别评估多个稀有类的识别能力"],
           ["pooled_rare_vs_nonrare", "将所有目标稀有类合并为正样本进行评估",
            "评估整体稀有细胞发现能力"]],
          widths=[3.8, 6.0, 5.7])
    note(doc, "pooled 模式反映整体稀有细胞发现能力，不代表稀有细胞类型精细注释准确率。")

    h2(doc, "9.5 目标稀有类选择")
    body(doc, "在 multi_rare_per_class 与 pooled_rare_vs_nonrare 模式下，可从候选列表中多选目标稀有类，"
              "下拉项会显示每个类的占比，便于判断其稀有程度。")

    h2(doc, "9.6 实验列表管理")
    body(doc, "已创建的实验会展示在右侧的「平台活跃实验主题列表」中，列出实验名称、评估类型、绑定标签列"
              "及具体配置，便于后续在评估页面中选择。")
    figure(doc, "test-18-exp-list.png", "图 9-3　已配置实验列表", width_cm=14.5)

    # ════════════════════════════ 第 10 章 方法评估与运行 ════════════════════════════
    h1(doc, 10, "方法评估与运行")

    h2(doc, "10.1 Method Run 概念")
    body(doc, "方法运行（Method Run）表示某个方法在某个实验下的一次结果导入或一次运行。例如「CellTypist "
              "预测结果导入」「scANVI 预测结果导入」等。V1.0 通过导入预测结果 CSV 的方式接入各方法的输出。")

    h2(doc, "10.2 导入方法预测结果")
    body(doc, "进入「评估与对比」页面，先在顶部选择一个实验，页面随即展示该实验的方法导入区与对比区。")
    figure(doc, "test-19-evaluation-panel.png", "图 10-1　评估与对比页面", width_cm=14.5)
    step(doc, 1, "在「评估方法名称」中填写方法名称（如 CellTypist）；")
    step(doc, 2, "在「方法预测 CSV 文件绝对路径」中填入预测结果 CSV 的本地路径；")
    step(doc, 3, "（稀有识别实验）如需计算 FRR 指标，可填写修正前基线 CSV 路径；")
    step(doc, 4, "点击「提交并在本地节点运行评估」。")
    note(doc, "页面提供「快速测试 CSV 路径」一键填入功能，便于使用预置测试数据。")

    h2(doc, "10.3 提交评估任务")
    body(doc, "提交后，Web 平台先创建方法运行记录，再将评估任务下发至本地 Agent。Agent 调用计算引擎"
              "执行 cell_id 对齐与指标计算，并生成结构化结果与 HTML 报告。")

    h2(doc, "10.4 任务队列与进度监控")
    body(doc, "任务提交后会出现在左侧「任务队列与同步」区域，实时显示任务状态（running/success/failed）"
              "与进度百分比。前端会自动轮询任务状态，任务完成后自动刷新对比排行榜并渲染图表。")
    figure(doc, "test-23-eval-running.png", "图 10-2　评估完成后的任务状态与结果展示", width_cm=14.5)

    h2(doc, "10.5 查看运行日志")
    body(doc, "在任务条目上点击「查看运行日志」，可弹出日志对话框，展示该任务在本地节点上的标准输出"
              "（stdout）与错误输出（stderr），便于排查问题。")

    h2(doc, "10.6 任务同步与取消")
    body(doc, "点击「同步进度」可手动向 Agent 拉取最新任务状态。对于尚在运行的任务，系统也支持取消操作；"
              "任务取消后状态变为 cancelled。")

    # ════════════════════════════ 第 11 章 多方法对比分析 ════════════════════════════
    h1(doc, 11, "多方法对比分析")

    h2(doc, "11.1 多方法对比概念")
    body(doc, "多方法对比是 scAnnoRare 的核心能力之一。在同一实验下，用户可以添加多个方法运行，系统对"
              "各方法采用统一的指标口径进行计算，并在对比排行榜中并排展示、排序与比较。")

    h2(doc, "11.2 对比排行榜")
    body(doc, "右侧「多方法指标横向对比与排序」区域以表格形式展示各方法的评估指标，包括 Accuracy、"
              "Macro-F1、Rare-F1、AUPRC、AUROC 等。排名前三的方法会以特殊的奖牌样式标识。")

    h2(doc, "11.3 指标排序")
    body(doc, "通过「排序依据」下拉框，可按 Accuracy、Macro-F1、Rare-F1、AUPRC、AUROC 等任一指标对"
              "方法进行降序排列。当某指标对某方法不可计算时，显示为 N/A，且不会被当作 0 参与排序。")

    h2(doc, "11.4 交互式图表重绘")
    body(doc, "在排行榜中点击某个方法的「图表」按钮，系统会拉取该方法的结构化结果，并使用 ECharts 在"
              "下方进行交互式图表重绘，同时展示该方法的指标汇总卡片。")

    h2(doc, "11.5 混淆矩阵")
    body(doc, "对于细胞类型注释评估，交互式图表展示混淆矩阵热图，横轴为预测类别、纵轴为真实类别，"
              "颜色深浅表示对应的细胞数量，鼠标悬停可查看具体数值。")

    h2(doc, "11.6 ROC / PR 曲线")
    body(doc, "对于稀有细胞识别评估，若预测结果包含连续稀有得分（rare_score），系统会绘制 ROC 曲线"
              "与 PR 曲线，用于评估稀有细胞识别的整体判别能力。")

    # ════════════════════════════ 第 12 章 报告中心 ════════════════════════════
    h1(doc, 12, "报告中心")

    h2(doc, "12.1 报告概念")
    body(doc, "每个成功完成的方法运行都会生成一份 HTML 评估报告。报告由本地计算引擎生成，内嵌可视化"
              "图表，为自包含的单文件 HTML，可在线查看，也可下载归档。")

    h2(doc, "12.2 报告列表")
    body(doc, "进入「报告中心」页面，以卡片形式展示所有评估报告。每张卡片显示方法名称、所属实验、关键"
              "指标（Accuracy、Macro-F1、Rare-F1、AUROC 等）与生成时间，并提供操作按钮。顶部支持按实验"
              "筛选报告。")
    figure(doc, "test-24-reports.png", "图 12-1　报告中心", width_cm=14.5)

    h2(doc, "12.3 在线查看报告")
    body(doc, "点击报告卡片上的「在线查看报告」按钮，系统会在新标签页中打开该 HTML 报告。报告通过 Web "
              "后端代理获取，自动携带访问凭证，无需手动认证。")
    figure(doc, "test-28-report-final.png", "图 12-2　HTML 评估报告（含混淆矩阵图表）", width_cm=11.5)

    h2(doc, "12.4 下载报告")
    body(doc, "点击「下载 HTML」按钮，可将报告以 .html 文件形式保存到本地。由于报告中的图表已内嵌为 "
              "base64 数据，下载后的报告可离线打开，图表正常显示。")

    h2(doc, "12.5 报告内容结构")
    body(doc, "一份单方法评估报告通常包含以下内容：")
    bullet(doc, "实验基本信息：评估方法、任务类型、数据配对率、评估时间；")
    bullet(doc, "整体评估指标：Accuracy、Balanced Accuracy、Macro-F1、Weighted-F1 等；")
    bullet(doc, "分类详细指标：各细胞类型的精确率、召回率、F1 分数与细胞数；")
    bullet(doc, "可视化图表：混淆矩阵热图，或稀有识别的 ROC/PR 曲线。")

    # ════════════════════════════ 第 13 章 输入文件格式规范 ════════════════════════════
    h1(doc, 13, "输入文件格式规范")

    h2(doc, "13.1 注释预测 CSV 格式")
    body(doc, "细胞类型注释评估的预测结果 CSV 文件，必需字段为 cell_id 与 pred_label，可选字段包括 "
              "confidence、baseline_label、method_name。字段含义如下：")
    table(doc, ["字段", "是否必需", "含义"],
          [["cell_id", "必需", "细胞 ID，需与 AnnData.obs_names 或指定 cell_id 列匹配"],
           ["pred_label", "必需", "方法输出的最终预测标签"],
           ["confidence", "可选", "对预测标签的置信度，建议为 0–1 的概率"],
           ["baseline_label", "可选", "修正前标签，主要用于 rescue 类方法评估"],
           ["method_name", "可选", "方法名称，缺省时由系统配置补充"]],
          widths=[3.2, 2.3, 10.0])
    body(doc, "示例：")
    code_block(doc, [
        "cell_id,pred_label,confidence,baseline_label",
        "cell_001,T cell,0.91,T cell",
        "cell_002,B cell,0.88,B cell",
        "cell_003,ASDC,0.76,pDC",
    ])

    h2(doc, "13.2 稀有检测预测 CSV 格式")
    body(doc, "稀有细胞识别评估的预测结果 CSV，必需字段为 cell_id 与 pred_label；可选字段包括 "
              "is_pred_rare、rare_score、target_rare_class、confidence、baseline_label、decision_type。")
    table(doc, ["字段", "含义"],
          [["is_pred_rare", "是否被预测为稀有细胞"],
           ["rare_score", "连续稀有细胞得分，用于计算 AUROC / AUPRC"],
           ["target_rare_class", "目标稀有类"],
           ["decision_type", "keep / rescue / abstain / reject"]],
          widths=[4.0, 11.5])

    h2(doc, "13.3 cell_id 匹配策略")
    body(doc, "系统按以下优先级匹配预测结果与 AnnData：① 精确匹配 AnnData.obs_names；② 精确匹配用户"
              "指定的 cell_id 列；③ 可选启用 barcode 标准化后匹配。默认仅执行去除首尾空格的轻量标准化，"
              "避免错误匹配。评估前会生成匹配报告，记录总预测细胞数、匹配细胞数、未匹配数与匹配率。")

    h2(doc, "13.4 标签异常值处理")
    body(doc, "系统默认将以下取值视为缺失或无效标签：NaN、None、空字符串、NA、Unknown、unknown、"
              "unassigned、Unassigned。评估指标仅在有效标签细胞上计算，报告中会记录有效标签细胞数与"
              "无效标签比例。")

    h2(doc, "13.5 匹配失败处理")
    body(doc, "系统提供严格模式与宽松模式两种匹配策略。严格模式下，若匹配率低于 95% 即报错，要求用户"
              "确认或修正；宽松模式下仅在已匹配细胞子集上计算指标，并在报告中注明本次指标基于匹配细胞"
              "子集计算。若零匹配，则直接报错终止。")

    # ════════════════════════════ 第 14 章 评估指标说明 ════════════════════════════
    h1(doc, 14, "评估指标说明")

    h2(doc, "14.1 细胞类型注释指标")
    body(doc, "细胞类型注释评估固定计算以下指标：")
    bullet(doc, "accuracy（准确率）、balanced_accuracy（平衡准确率）；")
    bullet(doc, "macro_f1（宏平均 F1）、weighted_f1（加权 F1）；")
    bullet(doc, "per_class_precision / recall / f1（各类别精确率、召回率、F1）；")
    bullet(doc, "confusion_matrix（混淆矩阵）。")
    body(doc, "当预测结果包含 confidence 字段时，还会计算置信度校准相关的统计信息。")

    h2(doc, "14.2 稀有细胞阈值型指标")
    body(doc, "只要存在 pred_label 即可计算稀有细胞阈值型指标：rare_precision（稀有精确率）、"
              "rare_recall（稀有召回率）、rare_f1、rare_confusion_matrix、false_positive_count、"
              "false_negative_count、missed_rare_count 等。")

    h2(doc, "14.3 稀有细胞曲线型指标")
    body(doc, "仅当预测结果包含连续 rare_score 时，才会计算曲线型指标：auroc、auprc、roc_curve、"
              "pr_curve。若未提供 rare_score，报告中会注明「AUROC/AUPRC 未计算：当前预测结果未提供"
              "连续 rare_score，仅支持阈值型指标」。")

    h2(doc, "14.4 False Rescue Rate")
    body(doc, "False Rescue Rate（错误挽救率，FRR）仅在提供 baseline_label 或 decision_type 时计算，"
              "用于评估 rescue 类方法。其定义为：")
    code_block(doc, [
        "false_rescue_rate = false_rescue_count / max(rescue_attempt_count, 1)",
        "其中：",
        "rescue_attempt_count = count(baseline_label != r 且 pred_label = r)",
        "false_rescue_count   = count(true_label != r 且 baseline_label != r 且 pred_label = r)",
    ])
    body(doc, "若未提供 baseline_label，报告中会注明 False Rescue Rate 未计算的原因。")

    h2(doc, "14.5 指标不可计算的情况")
    body(doc, "系统对退化情况进行了稳健处理，包括：目标稀有类在真值中数量为 0、预测结果中没有任何稀有"
              "预测、真值只有一个类别、所有预测都是同一标签、rare_score 全部相同、confidence 不在 0–1 "
              "范围、CSV 存在重复 cell_id 等。处理原则为：能计算的指标继续计算，不能计算的指标返回 null "
              "并在报告中说明原因，禁止静默输出错误数值。")

    # ════════════════════════════ 第 15 章 常见问题与故障排除 ════════════════════════════
    h1(doc, 15, "常见问题与故障排除")

    h2(doc, "15.1 Agent 连接问题")
    qa(doc, h, "配对页面提示「未检测到本地 Agent 服务」？",
       "请确认本地 Agent 已启动并监听 127.0.0.1:17890。可在终端执行 Agent 启动命令，并访问健康检查"
       "接口确认服务状态。")
    qa(doc, h, "配对成功后环境信息不显示？",
       "可能是会话令牌已失效（如 Agent 曾重启）。系统会自动检测并清除失效令牌、回到等待配对状态，"
       "重新配对即可。")

    h2(doc, "15.2 数据集检测问题")
    qa(doc, h, "检测 H5AD 提示文件不存在或无法解析？",
       "请检查填写的是否为 .h5ad 文件的完整绝对路径，且文件确实存在、可被 anndata 正常读取。")
    qa(doc, h, "注册数据集时提示 label_col 未找到？",
       "请确认所选标签列确实存在于该数据集的 obs 列中。")

    h2(doc, "15.3 评估任务失败")
    qa(doc, h, "评估任务状态变为 failed？",
       "可点击「查看运行日志」查看 stderr 输出。常见原因包括：预测 CSV 缺少必需字段、cell_id 与数据集"
       "完全不匹配、标签列名称不正确等。")
    qa(doc, h, "提示零匹配？",
       "说明预测 CSV 的 cell_id 与数据集 obs_names 没有任何交集，请确认预测结果对应的是同一数据集。")

    h2(doc, "15.4 报告查看问题")
    qa(doc, h, "在线查看报告时图表不显示？",
       "V1.0 已将报告图表内嵌为 base64 数据，报告为自包含单文件，正常情况下图表均可显示。若仍异常，"
       "请确认评估任务已成功完成并生成了报告。")
    qa(doc, h, "查看报告提示需要配对？",
       "在线查看与下载报告需要本地 Agent 处于在线且已配对状态，请先完成节点配对。")

    h2(doc, "15.5 数据库连接问题")
    qa(doc, h, "后端启动报数据库连接错误？",
       "请检查 MySQL 服务是否正常、连接参数（主机、端口、用户名、密码、数据库名）是否正确，以及网络"
       "是否可达。")

    # ════════════════════════════ 附录 A ════════════════════════════
    h1(doc, "A", "附录 A　系统功能清单")
    table(doc, ["功能模块", "功能项"],
          [["账号管理", "用户注册、用户登录、退出登录、路由访问控制"],
           ["节点配对", "配对码生成、配对授权、一键配对、环境诊断、解除配对"],
           ["数据集", "H5AD 结构检测、标签/批次选择、稀有阈值设置、数据集注册、分布可视化"],
           ["实验", "注释评估实验、稀有识别实验、三种 Rare Mode、目标稀有类选择、实验列表"],
           ["方法评估", "预测 CSV 导入、任务下发、进度监控、日志查看、任务同步与取消"],
           ["多方法对比", "对比排行榜、指标排序、交互式图表、混淆矩阵、ROC/PR 曲线"],
           ["报告中心", "报告列表、按实验筛选、在线查看、下载 HTML"],
           ["首页控制台", "统计指标卡片、评估流程说明、快捷入口"]],
          widths=[3.2, 12.3])

    # ════════════════════════════ 附录 B ════════════════════════════
    h1(doc, "B", "附录 B　API 接口一览")
    h2(doc, "B.1 Web 后端主要接口")
    code_block(doc, [
        "POST /api/v1/auth/register      用户注册",
        "POST /api/v1/auth/login         用户登录",
        "GET  /api/v1/auth/me            获取当前用户",
        "GET  /api/v1/datasets           数据集列表",
        "POST /api/v1/datasets           创建数据集",
        "GET  /api/v1/experiments        实验列表",
        "POST /api/v1/experiments        创建实验",
        "POST /api/v1/experiments/{id}/method-runs   添加方法运行",
        "POST /api/v1/jobs               下发评估任务",
        "POST /api/v1/jobs/{id}/sync     同步任务状态",
        "GET  /api/v1/experiments/{id}/comparison    多方法对比",
        "GET  /api/v1/reports            报告列表",
        "GET  /api/v1/reports/{id}/download          下载/查看报告",
        "GET  /api/v1/stats/summary      统计汇总",
    ])
    h2(doc, "B.2 Local Agent 主要接口")
    code_block(doc, [
        "GET  /api/v1/local/health                   健康检查",
        "POST /api/v1/local/pair                     配对授权",
        "GET  /api/v1/local/env                      环境检测",
        "POST /api/v1/local/files/select             选择 h5ad 文件",
        "POST /api/v1/local/files/register-dataset   注册数据集",
        "POST /api/v1/local/tasks/inspect-dataset    数据集检查任务",
        "POST /api/v1/local/tasks/evaluate-annotation 注释评估任务",
        "POST /api/v1/local/tasks/evaluate-rare      稀有识别评估任务",
        "POST /api/v1/local/tasks/generate-report    报告生成任务",
        "GET  /api/v1/local/tasks/{id}               任务状态",
        "GET  /api/v1/local/tasks/{id}/report        获取报告",
    ])

    # ════════════════════════════ 附录 C ════════════════════════════
    h1(doc, "C", "附录 C　术语表")
    table(doc, ["术语", "说明"],
          [["scRNA-seq", "单细胞 RNA 测序，single-cell RNA sequencing"],
           ["h5ad", "AnnData 对象的标准存储格式，单细胞数据常用文件格式"],
           ["AnnData", "单细胞分析中用于存储表达矩阵及注释的数据结构"],
           ["obs / var", "AnnData 中的观测（细胞）注释与变量（基因）注释"],
           ["label_col", "真实细胞类型注释列，作为评估真值"],
           ["稀有细胞", "在数据集中占比很低的细胞类型"],
           ["Method Run", "某方法在某实验下的一次结果导入或运行"],
           ["session_token", "配对成功后用于本地 Agent 访问鉴权的会话令牌"],
           ["Macro-F1", "各类别 F1 分数的宏平均"],
           ["AUROC / AUPRC", "ROC 曲线下面积 / PR 曲线下面积"],
           ["FRR", "False Rescue Rate，错误挽救率"]],
          widths=[3.5, 12.0])

    # 结尾
    doc.add_paragraph()
    p = doc.add_paragraph(); p.alignment = AL.CENTER
    r = p.add_run("—— 本手册完 ——")
    setf(r, cn=CN_HEAD, size=12, bold=True, color=h['C_MUTE'])
    p = doc.add_paragraph(); p.alignment = AL.CENTER
    r = p.add_run("单细胞细胞类型注释与稀有细胞识别多方法评估系统 V1.0")
    setf(r, size=10, color=h['C_MUTE'])


def qa(doc, h, question, answer):
    """问答样式：问题加粗，答案缩进。"""
    setf = h['set_run_font']; Pt = h['Pt']
    pq = doc.add_paragraph()
    pq.paragraph_format.left_indent = Pt(12)
    pq.paragraph_format.space_before = Pt(6)
    pq.paragraph_format.space_after = Pt(2)
    rq = pq.add_run("问：" + question)
    setf(rq, cn=h['CN_HEAD'], size=12, bold=True, color=h['C_H1'])
    pa = doc.add_paragraph()
    pa.paragraph_format.left_indent = Pt(12)
    pa.paragraph_format.space_after = Pt(6)
    pa.paragraph_format.line_spacing = Pt(22)
    ra = pa.add_run("答：" + answer)
    setf(ra, size=12, color=h['C_MUTE'])
