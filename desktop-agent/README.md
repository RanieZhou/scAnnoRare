# scAnnoRare 桌面 Agent（Tauri）

将 Local Agent 打包为**本机桥接服务**桌面应用。
用户双击即用：自动启动本地 Agent、显示配对码、常驻系统托盘；实际计算使用用户本机已选择的 Python 环境。

```
┌─────────────────────────────────────┐
│   Tauri 外壳（Rust + 系统 WebView）   │  ← 托盘 / 配对码 / 状态面板
│   ─ 启动并守护 Agent 进程            │
│   ─ 退出时清理（含 SIGTERM 兜底）    │
└─────────────────────────────────────┘
            │ 内置打包
            ▼
┌─────────────────────────────────────┐
│   Local Agent（PyInstaller 独立包）  │  ← 监听 127.0.0.1:17890
│   scannorare-agent[.exe] + _internal │
└─────────────────────────────────────┘
```

---

## 一、架构要点

- **桌面壳**：`desktop-agent/`，Tauri v2（Rust + 前端状态面板）。
- **Agent**：`local-agent/`，用 PyInstaller 打成独立可执行（onedir）。
  - 打包后仅负责配对、文件浏览、环境扫描和任务调度。
  - runner 脚本由用户在设置中选择的本机 Python 环境执行。
  - workspace 落在**用户数据目录**（非 app bundle 内）：
    - macOS：`~/Library/Application Support/scAnnoRare/workspace`
    - Windows：`%APPDATA%\scAnnoRare\workspace`
- **Agent 嵌入方式**：经 `tauri.conf.json` 的 `bundle.resources` 把 `dist/scannorare-agent`
  整个目录打入安装包的 `Resources/agent/`；Rust 端按
  `<resource>/agent/scannorare-agent[.exe]` 解析并启动。
- **计算环境**：不随安装包内置 `scanpy/anndata/celltypist/scvi/torch` 等依赖；
  用户需在 Web 设置页扫描并选择本机 Python 环境。

---

## 二、构建安装包

> ⚠️ **不能跨平台编译**：PyInstaller 与 Tauri 都只能产出当前操作系统的包。
> 要 Windows 安装包，必须在 **Windows 机器**上构建；要 macOS 包，在 **Mac** 上构建。

### macOS（产出 .app / .dmg）

前置：Python 3.10/3.11、Node 18+、Rust、Xcode CLT。

```bash
bash packaging/build_desktop_macos.sh
```

产物：
- `desktop-agent/src-tauri/target/release/bundle/macos/scAnnoRare Agent.app`
- `desktop-agent/src-tauri/target/release/bundle/dmg/scAnnoRare Agent_1.0.0_*.dmg`

### Windows（产出 .msi / .exe）

前置：Python 3.10/3.11、Node 18+、Rust、Microsoft C++ Build Tools、WebView2 Runtime。

```powershell
powershell -ExecutionPolicy Bypass -File packaging\build_desktop_windows.ps1
```

产物：
- `desktop-agent\src-tauri\target\release\bundle\msi\*.msi`
- `desktop-agent\src-tauri\target\release\bundle\nsis\*.exe`

---

## 三、开发模式（不打包，热重载）

桌面壳开发时无需每次打包 Agent，可让壳启动外部已打包的 Agent：

```bash
cd desktop-agent
npm install
# 方式 A：壳自动启动 local-agent/packaging/dist 下已打包的 Agent
npm run tauri dev
# 方式 B：用环境变量指定任意 Agent 可执行
SCANNORARE_AGENT_PATH=/abs/path/to/scannorare-agent npm run tauri dev
```

Agent 路径解析优先级：`SCANNORARE_AGENT_PATH` 环境变量 → 安装包内置资源 → 开发默认
（`local-agent/packaging/dist/...`）。

---

## 四、分发注意事项

- **macOS 签名/公证**：对外分发 .app/.dmg 需 Apple 开发者证书签名 + 公证，
  否则用户首次打开会被 Gatekeeper 拦截（提示「无法验证开发者」）。
- **Windows 签名**：未签名安装包会触发 SmartScreen 警告，建议申请代码签名证书。
- **包体积**：显著小于旧版自带计算环境包；主要包含 Tauri 外壳与 FastAPI 桥接服务。
- **架构**：macOS 包区分 Apple Silicon (aarch64) 与 Intel (x86_64)；
  Windows 包为 x64。需各自在对应架构上构建。
