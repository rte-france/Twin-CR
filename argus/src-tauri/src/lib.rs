/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use crate::config::app_config::load_config;
use tauri::Manager;

mod auth;
mod channel;
mod common;
mod config;
mod database;
mod dsl;
mod game_master;
mod herge;
mod http;
pub mod http_client;
mod lobby;
mod scada;
mod sidecars;
mod windows;

const SIDECARS: [&str; 0] = [];

#[cfg_attr(mobile, tauri::mobile_entry_point)]
pub fn run() {
    let config = load_config();

    let mut builder = tauri::Builder::default();

    #[cfg(desktop)]
    {
        builder = builder.plugin(tauri_plugin_single_instance::init(|app, argv, _cwd| {
            #[cfg(not(debug_assertions))]
            if let Some(window) = app.get_webview_window("main") {
                let _ = window.unminimize();
                let _ = window.show();
                let _ = window.set_focus();
            }

            if argv.len() > 1 {
                use tauri::Emitter;
                let deep_link = &argv[1];
                let _ = app.emit("deep-link-received", deep_link.clone());
            }
        }));
    }

    builder
        .plugin(tauri_plugin_deep_link::init())
        .plugin(tauri_plugin_window_state::Builder::new().build())
        .plugin(tauri_plugin_fs::init())
        .plugin(tauri_plugin_shell::init())
        .plugin(tauri_plugin_http::init())
        .plugin(tauri_plugin_opener::init())
        .plugin(tauri_plugin_dialog::init())
        .plugin(
            tauri_plugin_log::Builder::new()
                .level_for("async_nats", log::LevelFilter::Info)
                .level_for("reqwest", log::LevelFilter::Info)
                .level_for("hyper_util", log::LevelFilter::Info)
                .filter(|metadata| {
                    !metadata.target().starts_with("sqlx") && metadata.level() != log::Level::Trace
                })
                .timezone_strategy(tauri_plugin_log::TimezoneStrategy::UseLocal)
                .build(),
        )
        .setup(|app| {
            #[cfg(any(windows, target_os = "linux"))]
            {
                use tauri_plugin_deep_link::DeepLinkExt;
                let _ = app.deep_link().register_all();
            }

            let handle = app.handle().clone();

            tauri::async_runtime::block_on(async {
                let config = config::manager::ConfigManager::new(handle.clone())
                    .expect("Failed to initialize Config Manager");
                config.load();
                handle.manage(config);

                let db_manager = database::manager::DbManager::new(handle.clone())
                    .await
                    .expect("Failed to start database");
                handle.manage(db_manager.clone());

                let window_manager = windows::manager::WindowManager::new(handle.clone());
                let _ = window_manager.register_main_window("main").await;
                handle.manage(window_manager);

                let http_manager = http::manager::HttpManager::with_resolver(None);
                http::manager::HttpManager::start_proxy_watcher(
                    http_manager.clone(),
                    handle.clone(),
                );
                handle.manage(http_manager.clone());
            });

            tauri::async_runtime::spawn(async move {
                if let Ok(sidecars) = sidecars::state::SidecarsState::new(&handle, &SIDECARS).await
                {
                    handle.manage(sidecars);
                }

                handle.manage(herge::manager::HergeManager::new(handle.clone()).await);
                handle.manage(game_master::manager::GmManager::new(handle.clone()).await);
                handle.manage(scada::manager::ScadaManager::new(handle.clone()).await);
                handle.manage(dsl::manager::DslManager::new(handle.clone()).await);
                handle.manage(lobby::manager::LobbyManager::new(handle.clone()).await);

                handle.manage(channel::manager::ChannelTaskManager::new().await);
            });

            Ok(())
        })
        .manage(config)
        .invoke_handler(tauri::generate_handler![
            // auth
            auth::commands::exchange_code,
            auth::commands::refresh_token,
            auth::commands::start_oauth_server,
            // sidecars
            sidecars::commands::start_sidecar,
            sidecars::commands::shutdown_sidecar,
            // config
            config::commands::get_config,
            // herge
            herge::commands::set_herge_url,
            herge::commands::fetch_request,
            herge::commands::cancel_request,
            // game master
            game_master::commands::set_gm_url,
            game_master::commands::get_gm_url,
            game_master::commands::get_gm_status,
            game_master::commands::get_gm_endpoint,
            game_master::commands::get_gm_tasks,
            game_master::commands::cancel_gm_task,
            game_master::commands::connect_gm,
            game_master::commands::disconnect_gm,
            game_master::commands::start_gm_sse,
            game_master::commands::post_gm_endpoint,
            // scada
            scada::commands::set_scada_url,
            scada::commands::get_scada_url,
            scada::commands::get_scada_status,
            scada::commands::get_scada_endpoint,
            scada::commands::get_scada_tasks,
            scada::commands::cancel_scada_task,
            scada::commands::connect_scada,
            scada::commands::start_scada_sse,
            scada::commands::post_scada_endpoint,
            // dsl
            dsl::commands::set_dsl_url,
            dsl::commands::get_dsl_url,
            dsl::commands::get_dsl_status,
            dsl::commands::get_dsl_endpoint,
            dsl::commands::get_dsl_tasks,
            dsl::commands::post_dsl_endpoint,
            dsl::commands::cancel_dsl_task,
            dsl::commands::connect_dsl,
            dsl::commands::get_dsl_text_endpoint,
            dsl::commands::delete_dsl_endpoint,
            dsl::commands::put_dsl_endpoint,
            // lobby
            lobby::commands::set_lobby_url,
            lobby::commands::get_lobby_url,
            lobby::commands::get_lobby_status,
            lobby::commands::connect_lobby,
            lobby::commands::disconnect_lobby,
            lobby::commands::get_lobby_endpoint,
            lobby::commands::get_lobby_tasks,
            lobby::commands::cancel_lobby_task,
            // windows
            windows::commands::create_parent_window,
            windows::commands::create_child_window,
            // http
            http::commands::get,
            http::commands::post,
            http::commands::post_multipart_stream,
            http::commands::put,
            http::commands::delete,
            http::commands::patch,
            http::commands::head,
            http::commands::options,
            http::commands::trace,
            http::commands::sse,
            http::commands::active_ping,
            http::commands::get_registered_clients,
            http::commands::cancel_http_request,
        ])
        .build(tauri::generate_context!())
        .expect("error while running tauri application")
        .run(|app_handle, event| {
            if let tauri::RunEvent::ExitRequested { .. } = event {
                if let Some(sidecars_state) =
                    app_handle.try_state::<tokio::sync::Mutex<sidecars::state::SidecarsState>>()
                {
                    tauri::async_runtime::block_on(async {
                        let mut sidecars = sidecars_state.lock().await;
                        for s in SIDECARS {
                            let _ = sidecars.despawn_sidecar(s);
                        }
                    });
                }
            }
        });
}
