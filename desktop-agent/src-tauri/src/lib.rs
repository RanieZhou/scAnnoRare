// scAnnoRare 桌面 Agent 外壳：负责启动/停止本地 Agent 进程 + 系统托盘。
// 与 Agent 的 HTTP 通信由前端 webview 直接 fetch（Agent 放行所有 CORS）。

use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Mutex, OnceLock};

use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager, RunEvent, WindowEvent,
};

/// 全局持有 Agent 子进程句柄，供 Tauri 退出事件与信号处理器共同清理。
static AGENT: OnceLock<Mutex<Option<Child>>> = OnceLock::new();

fn agent_slot() -> &'static Mutex<Option<Child>> {
    AGENT.get_or_init(|| Mutex::new(None))
}

/// 解析 Agent 可执行文件路径：
/// 1) 环境变量 SCANNORARE_AGENT_PATH（开发/测试覆盖）
/// 2) 打包资源目录 <resource>/agent/scannorare-agent（正式发布）
/// 3) 开发默认：PyInstaller 产物路径
fn agent_exe_name() -> &'static str {
    if cfg!(target_os = "windows") {
        "scannorare-agent.exe"
    } else {
        "scannorare-agent"
    }
}

fn agent_exe_path(app: &tauri::AppHandle) -> PathBuf {
    // 1) 环境变量覆盖（开发/测试）
    if let Ok(p) = std::env::var("SCANNORARE_AGENT_PATH") {
        return PathBuf::from(p);
    }
    // 2) 打包资源目录（正式发布）：<resource>/agent/scannorare-agent[.exe]
    if let Ok(dir) = app.path().resource_dir() {
        let p = dir.join("agent").join(agent_exe_name());
        if p.exists() {
            return p;
        }
    }
    // 3) 开发默认：PyInstaller 产物
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../local-agent/packaging/dist/scannorare-agent")
        .join(agent_exe_name())
}

fn start_agent(app: &tauri::AppHandle) {
    let path = agent_exe_path(app);
    let mut cmd = Command::new(&path);

    // Windows：抑制 Agent 的黑色控制台窗口（CREATE_NO_WINDOW）。
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000);
    }

    match cmd.spawn() {
        Ok(child) => {
            println!("[shell] Agent 已启动: {:?} (pid {})", path, child.id());
            *agent_slot().lock().unwrap() = Some(child);
        }
        Err(e) => eprintln!("[shell] 启动 Agent 失败 {:?}: {}", path, e),
    }
}

fn stop_agent() {
    let child_opt = agent_slot().lock().unwrap().take();
    if let Some(mut child) = child_opt {
        let _ = child.kill();
        let _ = child.wait();
        println!("[shell] Agent 已停止");
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // 兜底①：捕获 SIGINT/SIGTERM（如被 kill），先杀 Agent 再退出，避免遗弃孤儿进程。
    let _ = ctrlc::set_handler(|| {
        stop_agent();
        std::process::exit(0);
    });

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            start_agent(&app.handle().clone());

            // 系统托盘
            let show = MenuItem::with_id(app, "show", "显示主界面", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "退出 scAnnoRare Agent", true, None::<&str>)?;
            let menu = Menu::with_items(app, &[&show, &quit])?;

            TrayIconBuilder::new()
                .icon(app.default_window_icon().unwrap().clone())
                .tooltip("scAnnoRare Local Agent")
                .menu(&menu)
                .show_menu_on_left_click(true)
                .on_menu_event(|app, event| match event.id.as_ref() {
                    "show" => {
                        if let Some(w) = app.get_webview_window("main") {
                            let _ = w.show();
                            let _ = w.set_focus();
                        }
                    }
                    "quit" => {
                        stop_agent();
                        app.exit(0);
                    }
                    _ => {}
                })
                .build(app)?;

            Ok(())
        })
        // 关闭窗口时隐藏到托盘，而非退出
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                let _ = window.hide();
                api.prevent_close();
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    // 兜底②：进程优雅退出（Cmd+Q / app.exit）时确保杀掉 Agent。
    app.run(|_app_handle, event| {
        if let RunEvent::Exit = event {
            stop_agent();
        }
    });
}
