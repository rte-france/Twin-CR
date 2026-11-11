/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

use sqlx::sqlite::SqlitePoolOptions;
use sqlx::{SqlitePool};
use tauri::{AppHandle, Manager};
use tokio::sync::{mpsc};

use super::actor::run_db_actor;
use super::command::DbCommand;
use super::error::{Error, Result};

const DATABASE_NAME: &str = "argus.db";

#[derive(Clone)]
pub struct DbManager {
    sender: mpsc::Sender<DbCommand>,
    pool: SqlitePool,
}

impl DbManager {
    pub async fn new(app_handle: AppHandle) -> Result<Self> {
        let app_dir = app_handle
            .path()
            .app_data_dir()
            .expect("failed to get app dir");

        std::fs::create_dir_all(&app_dir)?;
        let pool_path = app_dir.join(DATABASE_NAME);
        let db_name = pool_path.to_string_lossy().to_string();

        log::info!("Setup argus database at: {:?}", pool_path);

        let conn_options = sqlx::sqlite::SqliteConnectOptions::new()
            .filename(&db_name)
            .create_if_missing(true)
            .shared_cache(false)
            .locking_mode(sqlx::sqlite::SqliteLockingMode::Normal)
            .journal_mode(sqlx::sqlite::SqliteJournalMode::Wal);

        let pool = SqlitePoolOptions::new()
            .max_connections(50)
            .connect_with(conn_options)
            .await
            .map_err(|e| Error::Connection(e.to_string()))?;

        sqlx::migrate!("../migrations")
            .run(&pool)
            .await
            .map_err(|e| Error::Migration(e.to_string()))?;

        let (sender, cmd_rx) = mpsc::channel(1024);

        let pool_clone = pool.clone();
        tokio::spawn(async move {
            run_db_actor(pool_clone, cmd_rx, app_handle).await;
        });

        Ok(Self { sender, pool })
    }

    pub async fn fetch_optional<T>(&self, query: &str) -> Result<Option<T>>
    where
        T: for<'r> sqlx::FromRow<'r, sqlx::sqlite::SqliteRow> + Send + Unpin + 'static,
    {
        let result = sqlx::query_as::<_, T>(query)
            .fetch_optional(&self.pool)
            .await?;
        Ok(result)
    }

    pub async fn fetch_all_with_args<T>(&self, query: &str, args: Vec<String>) -> Result<Vec<T>>
    where
        T: for<'r> sqlx::FromRow<'r, sqlx::sqlite::SqliteRow> + Send + Unpin + 'static,
    {
        let mut q = sqlx::query_as::<_, T>(query);
        for arg in args {
            q = q.bind(arg);
        }
        let results = q.fetch_all(&self.pool).await?;
        Ok(results)
    }

    pub async fn execute_with_args(&self, query: impl AsRef<str>, args: &[&str]) -> Result<u64> {
        let mut q = sqlx::query(query.as_ref());

        for &arg in args {
            q = q.bind(arg);
        }

        let result = q.execute(&self.pool).await?;
        Ok(result.rows_affected())
    }
}
