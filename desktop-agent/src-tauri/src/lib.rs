// scAnnoRare Desktop Agent shell: launches/stops the local agent process and manages the system tray.
// The webview communicates with the agent directly via HTTP fetch (agent allows all CORS origins).

use std::path::PathBuf;
use std::process::{Child, Command};
use std::sync::{Mutex, OnceLock};

use tauri::{
    menu::{Menu, MenuItem},
    tray::TrayIconBuilder,
    Manager, RunEvent, WindowEvent,
};

// Global agent child-process handle shared between the Tauri exit event and the signal handler.
static AGENT: OnceLock<Mutex<Option<Child>>> = OnceLock::new();

fn agent_slot() -> &'static Mutex<Option<Child>> {
    AGENT.get_or_init(|| Mutex::new(None))
}

// Resolve the agent executable path:
//   1) SCANNORARE_AGENT_PATH env var (dev/test override)
//   2) Packaged resource dir: <resource>/agent/scannorare-agent[.exe]
//   3) Dev fallback: PyInstaller output path relative to manifest
fn agent_exe_name() -> &'static str {
    if cfg!(target_os = "windows") {
        "scannorare-agent.exe"
    } else {
        "scannorare-agent"
    }
}

fn agent_exe_path(app: &tauri::AppHandle) -> PathBuf {
    if let Ok(p) = std::env::var("SCANNORARE_AGENT_PATH") {
        return PathBuf::from(p);
    }
    if let Ok(dir) = app.path().resource_dir() {
        let p = dir.join("agent").join(agent_exe_name());
        if p.exists() {
            return p;
        }
    }
    PathBuf::from(env!("CARGO_MANIFEST_DIR"))
        .join("../../local-agent/packaging/dist/scannorare-agent")
        .join(agent_exe_name())
}

fn start_agent(app: &tauri::AppHandle) {
    let path = agent_exe_path(app);
    let mut cmd = Command::new(&path);

    // Suppress the black console window on Windows (CREATE_NO_WINDOW).
    #[cfg(windows)]
    {
        use std::os::windows::process::CommandExt;
        cmd.creation_flags(0x08000000);
    }

    match cmd.spawn() {
        Ok(child) => {
            println!("[shell] Agent started: {:?} (pid {})", path, child.id());
            *agent_slot().lock().unwrap() = Some(child);
        }
        Err(e) => eprintln!("[shell] Failed to start agent {:?}: {}", path, e),
    }
}

fn stop_agent() {
    let child_opt = agent_slot().lock().unwrap().take();
    if let Some(mut child) = child_opt {
        let _ = child.kill();
        let _ = child.wait();
        println!("[shell] Agent stopped.");
    }
}

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    // Catch SIGINT/SIGTERM so that killing the shell also cleans up the agent subprocess.
    let _ = ctrlc::set_handler(|| {
        stop_agent();
        std::process::exit(0);
    });

    let app = tauri::Builder::default()
        .plugin(tauri_plugin_opener::init())
        .setup(|app| {
            start_agent(&app.handle().clone());

            // System tray menu
            let show = MenuItem::with_id(app, "show", "Show Window", true, None::<&str>)?;
            let quit = MenuItem::with_id(app, "quit", "Quit scAnnoRare Agent", true, None::<&str>)?;
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
        // Hide to tray on window close instead of quitting
        .on_window_event(|window, event| {
            if let WindowEvent::CloseRequested { api, .. } = event {
                let _ = window.hide();
                api.prevent_close();
            }
        })
        .build(tauri::generate_context!())
        .expect("error while building tauri application");

    // Ensure agent is killed on graceful exit (Cmd+Q / app.exit).
    app.run(|_app_handle, event| {
        if let RunEvent::Exit = event {
            stop_agent();
        }
    });
}
