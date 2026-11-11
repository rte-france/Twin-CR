/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use log::{error, warn};
use serde_json::{Map, Value};
use sqlx::{Column, Row, SqlitePool, TypeInfo, ValueRef};
use std::collections::HashMap;
use tauri::{AppHandle, Emitter};
use tokio::sync::{mpsc, oneshot};
use tokio::task::JoinSet;

use super::command::DbCommand;
use super::error::{Error, Result};

struct ActiveDbTask {
    cancel_tx: oneshot::Sender<()>,
}

pub(crate) async fn run_db_actor(
    pool: SqlitePool,
    mut cmd_rx: mpsc::Receiver<DbCommand>,
    app_handle: AppHandle,
) {
    let mut child_tasks = JoinSet::new();
    let mut active_requests: HashMap<String, ActiveDbTask> = HashMap::new();

    loop {
        tokio::select! {
            Some(join_result) = child_tasks.join_next() => {
                if let Err(panic_err) = join_result {
                    error!("CRITICAL: A supervised DB task panicked: {}", panic_err);
                }
                active_requests.retain(|_, task| !task.cancel_tx.is_closed());
            }

            cmd_opt = cmd_rx.recv() => {
                let Some(cmd) = cmd_opt else {
                    break;
                };

                dispatch_db_cmd(cmd, &pool, &mut active_requests, &mut child_tasks, app_handle.clone());
            }
        }
    }

    child_tasks.abort_all();
}

fn dispatch_db_cmd(
    cmd: DbCommand,
    pool: &SqlitePool,
    active_requests: &mut HashMap<String, ActiveDbTask>,
    child_tasks: &mut JoinSet<()>,
    app_handle: AppHandle,
) {
    match cmd {
        DbCommand::Cancel { req_id } => {
            if let Some(task) = active_requests.remove(&req_id) {
                let _ = task.cancel_tx.send(());
            }
        }
        DbCommand::Select {
            req_id,
            query,
            responder,
        } => {
            let (cancel_tx, cancel_rx) = oneshot::channel();
            active_requests.insert(req_id.clone(), ActiveDbTask { cancel_tx });

            let pool_clone = pool.clone();

            child_tasks.spawn(execute_cancellable_select(
                pool_clone, query, req_id, responder, cancel_rx,
            ));
        }
        DbCommand::Execute {
            req_id,
            query,
            responder,
        } => {
            let (cancel_tx, cancel_rx) = oneshot::channel();
            active_requests.insert(req_id.clone(), ActiveDbTask { cancel_tx });

            let pool_clone = pool.clone();
            child_tasks.spawn(execute_cancellable_action(
                pool_clone, query, req_id, responder, cancel_rx, app_handle,
            ));
        }
    }
}

async fn execute_cancellable_select(
    pool: SqlitePool,
    query: String,
    req_id: String,
    responder: oneshot::Sender<Result<Vec<Value>>>,
    mut cancel_rx: oneshot::Receiver<()>,
) {
    let db_future = async {
        let rows = sqlx::query(&query)
            .fetch_all(&pool)
            .await
            .map_err(|e| Error::QueryExecution(e.to_string()))?;

        let mut results = vec![];

        for row in rows {
            let mut map = Map::new();
            for col in row.columns() {
                let col_name = col.name().to_string();

                let raw_val = row
                    .try_get_raw(col.ordinal())
                    .map_err(|e| Error::QueryExecution(e.to_string()))?;

                let json_val = if raw_val.is_null() {
                    Value::Null
                } else {
                    match col.type_info().name() {
                        "TEXT" | "VARCHAR" => {
                            let v: String = row.try_get(col.ordinal()).unwrap_or_default();
                            Value::String(v)
                        }
                        "INTEGER" | "INT" => {
                            let v: i64 = row.try_get(col.ordinal()).unwrap_or(0);
                            serde_json::json!(v)
                        }
                        "REAL" | "NUMERIC" | "FLOAT" | "DOUBLE" => {
                            let v: f64 = row.try_get(col.ordinal()).unwrap_or(0.0);
                            serde_json::json!(v)
                        }
                        "BOOLEAN" => {
                            let v: bool = row.try_get(col.ordinal()).unwrap_or(false);
                            Value::Bool(v)
                        }
                        "BLOB" => Value::String("<BLOB DATA>".to_string()),
                        _ => {
                            let v: String = row.try_get(col.ordinal()).unwrap_or_default();
                            Value::String(v)
                        }
                    }
                };

                map.insert(col_name, json_val);
            }
            results.push(Value::Object(map));
        }
        Ok(results)
    };

    let result = tokio::select! {
        res = db_future => res,
        _ = &mut cancel_rx => {
            warn!("DB Request {} was explicitly cancelled.", req_id);
            Err(Error::Aborted)
        }
    };

    let _ = responder.send(result);
}

async fn execute_cancellable_action(
    pool: SqlitePool,
    query: String,
    req_id: String,
    responder: oneshot::Sender<Result<u64>>,
    mut cancel_rx: oneshot::Receiver<()>,
    app_handle: AppHandle,
) {
    let db_future = async {
        let result = sqlx::query(&query)
            .execute(&pool)
            .await
            .map_err(|e| Error::QueryExecution(e.to_string()))?;

        let rows_affected = result.rows_affected();

        if rows_affected > 0 {
            let _ = app_handle.emit(
                "db-changed",
                serde_json::json!({
                    "action": "execute",
                    "rows_affected": rows_affected,
                    "query_preview": query.chars().take(50).collect::<String>()
                }),
            );
        }

        Ok(rows_affected)
    };

    let result = tokio::select! {
        res = db_future => res,
        _ = &mut cancel_rx => {
            warn!("DB Action Request {} was explicitly cancelled.", req_id);
            Err(Error::Aborted)
        },
    };

    let _ = responder.send(result);
}
