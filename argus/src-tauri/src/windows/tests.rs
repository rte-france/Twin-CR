/*
Copyright (c) 2025-2026, RTE (https://www.rte-france.com)
See AUTHORS.md
SPDX-License-Identifier: MPL-2.0
This file is part of Twin-CR, a platform for real-time cyber-physical
co-simulation of power systems.
*/

#[cfg(test)]
mod tests {
    use sqlx::sqlite::SqlitePoolOptions;
    use sqlx::Row;

    async fn create_test_db() -> sqlx::SqlitePool {
        let pool = SqlitePoolOptions::new()
            .max_connections(1)
            .connect("sqlite::memory:")
            .await
            .expect("Failed to connect to in-memory sqlite");

        sqlx::query("PRAGMA foreign_keys = ON;")
            .execute(&pool)
            .await
            .unwrap();

        sqlx::query(
            r#"
            CREATE TABLE window_hierarchy (
                label TEXT PRIMARY KEY,
                parent_label TEXT,
                is_parent BOOLEAN NOT NULL DEFAULT 0,
                FOREIGN KEY(parent_label) REFERENCES window_hierarchy(label) ON DELETE CASCADE
            );
            "#,
        )
        .execute(&pool)
        .await
        .unwrap();

        pool
    }

    async fn query_descendants(pool: &sqlx::SqlitePool, root: &str) -> Vec<String> {
        let query = r#"
            WITH RECURSIVE descendants(label) AS (
                SELECT label FROM window_hierarchy WHERE parent_label = ?
                UNION ALL
                SELECT w.label FROM window_hierarchy w
                INNER JOIN descendants d ON w.parent_label = d.label
            )
            SELECT label FROM descendants;
        "#;

        let rows = sqlx::query(query)
            .bind(root)
            .fetch_all(pool)
            .await
            .unwrap();

        rows.into_iter()
            .map(|r| r.get::<String, _>("label"))
            .collect()
    }

    #[tokio::test]
    async fn test_window_hierarchy_multi_level_descendants() {
        let pool = create_test_db().await;

        // Tree structure:
        // main (parent)
        // └── child_1
        //     ├── child_1_1
        //     │   └── child_1_1_1
        //     └── child_1_2
        // other_parent
        // └── other_child

        sqlx::query("INSERT INTO window_hierarchy VALUES ('main', NULL, 1)")
            .execute(&pool)
            .await
            .unwrap();
        sqlx::query("INSERT INTO window_hierarchy VALUES ('child_1', 'main', 1)")
            .execute(&pool)
            .await
            .unwrap();
        sqlx::query("INSERT INTO window_hierarchy VALUES ('child_1_1', 'child_1', 1)")
            .execute(&pool)
            .await
            .unwrap();
        sqlx::query("INSERT INTO window_hierarchy VALUES ('child_1_1_1', 'child_1_1', 0)")
            .execute(&pool)
            .await
            .unwrap();
        sqlx::query("INSERT INTO window_hierarchy VALUES ('child_1_2', 'child_1', 0)")
            .execute(&pool)
            .await
            .unwrap();

        sqlx::query("INSERT INTO window_hierarchy VALUES ('other_parent', NULL, 1)")
            .execute(&pool)
            .await
            .unwrap();
        sqlx::query("INSERT INTO window_hierarchy VALUES ('other_child', 'other_parent', 0)")
            .execute(&pool)
            .await
            .unwrap();

        let main_descendants = query_descendants(&pool, "main").await;
        assert_eq!(main_descendants.len(), 4);
        assert!(main_descendants.contains(&"child_1".to_string()));
        assert!(main_descendants.contains(&"child_1_1".to_string()));
        assert!(main_descendants.contains(&"child_1_1_1".to_string()));
        assert!(main_descendants.contains(&"child_1_2".to_string()));
        assert!(!main_descendants.contains(&"other_child".to_string()));

        let child1_descendants = query_descendants(&pool, "child_1").await;
        assert_eq!(child1_descendants.len(), 3);
        assert!(child1_descendants.contains(&"child_1_1".to_string()));
        assert!(child1_descendants.contains(&"child_1_1_1".to_string()));
        assert!(child1_descendants.contains(&"child_1_2".to_string()));

        let leaf_descendants = query_descendants(&pool, "child_1_1_1").await;
        assert!(leaf_descendants.is_empty());
    }
}
