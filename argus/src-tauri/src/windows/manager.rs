/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use crate::database::manager::DbManager;
use tauri::{AppHandle, Manager, WebviewUrl, WebviewWindowBuilder};
use uuid::Uuid;

pub async fn get_all_descendants(
    db: &DbManager,
    root_label: &str,
) -> Result<Vec<String>, String> {
    let query = r#"
        WITH RECURSIVE descendants(label) AS (
            SELECT label FROM window_hierarchy WHERE parent_label = ?
            UNION ALL
            SELECT w.label FROM window_hierarchy w
            INNER JOIN descendants d ON w.parent_label = d.label
        )
        SELECT label FROM descendants;
    "#;

    let rows: Vec<(String,)> = db
        .fetch_all_with_args(query, vec![root_label.to_string()])
        .await
        .map_err(|e| e.to_string())?;

    Ok(rows.into_iter().map(|(label,)| label).collect())
}

pub struct WindowManager {
    app_handle: AppHandle,
}

impl WindowManager {
    pub fn new(app_handle: AppHandle) -> Self {
        Self { app_handle }
    }

    pub async fn register_main_window(&self, label: &str) -> Result<(), String> {
        let db = self.app_handle.state::<DbManager>();

        db.execute_with_args(
            "INSERT OR IGNORE INTO window_hierarchy (label, parent_label, is_parent) VALUES (?, NULL, 1)",
            &[label]
        ).await.map_err(|e| e.to_string())?;

        self.setup_window_listeners(label.to_string(), true);
        Ok(())
    }

    pub async fn create_parent(&self, title: &str, route: &str) -> Result<(), String> {
        let label = format!("parent_{}", Uuid::new_v4());
        let db = self.app_handle.state::<DbManager>();

        db.execute_with_args(
            "INSERT INTO window_hierarchy (label, parent_label, is_parent) VALUES (?, NULL, 1)",
            &[&label],
        )
        .await
        .map_err(|e| e.to_string())?;

        let url = format!("/?route={}", route);
        WebviewWindowBuilder::new(&self.app_handle, &label, WebviewUrl::App(url.into()))
            .title(title)
            .decorations(false)
            .build()
            .map_err(|e| e.to_string())?;

        self.setup_window_listeners(label, true);
        Ok(())
    }

    pub async fn create_child(
        &self,
        parent_label: &str,
        title: &str,
        route: &str,
    ) -> Result<(), String> {
        let label = format!("child_{}", Uuid::new_v4());
        let db = self.app_handle.state::<DbManager>();

        db.execute_with_args(
            "INSERT INTO window_hierarchy (label, parent_label, is_parent) VALUES (?, ?, 0)",
            &[&label, parent_label],
        )
        .await
        .map_err(|e| e.to_string())?;

        let url = format!("/?parent={}&route={}", parent_label, route);
        WebviewWindowBuilder::new(&self.app_handle, &label, WebviewUrl::App(url.into()))
            .title(title)
            .build()
            .map_err(|e| e.to_string())?;

        self.setup_window_listeners(label, false);
        Ok(())
    }

    fn setup_window_listeners(&self, label: String, is_parent: bool) {
        let handle = self.app_handle.clone();
        let current_label = label.clone();

        if let Some(window) = self.app_handle.get_webview_window(&label) {
            window.on_window_event(move |event| {
                match event {
                    tauri::WindowEvent::CloseRequested { .. } | tauri::WindowEvent::Destroyed => {
                        let h = handle.clone();
                        let l = current_label.clone();

                        tauri::async_runtime::spawn(async move {
                            let db = h.state::<DbManager>();

                            if is_parent {
                                if let Ok(descendants) = get_all_descendants(&db, &l).await {
                                    for child_label in descendants {
                                        if let Some(child_win) = h.get_webview_window(&child_label) {
                                            let _ = child_win.close();
                                        }
                                    }
                                }
                            }

                            let _ = db
                                .execute_with_args(
                                    "DELETE FROM window_hierarchy WHERE label = ?",
                                    &[&l],
                                )
                                .await;
                        });
                    }
                    _ => {}
                }
            });
        }
    }
}
