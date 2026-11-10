# 🗄️ Workspace & Fine-Grained Access Control (FGAC) Schema

This repository contains the core PostgreSQL database schema for managing Groups, Projects, Templates, and a hierarchical File System. 

The architecture is heavily inspired by the **Zanzibar model** (Google's authorization system) and is designed to handle Fine-Grained Access Control (FGAC) natively. It relies on Keycloak purely for Authentication (Identity), while this database schema handles all Authorization (Permissions) and Attribute-Based Access Control (ABAC) using PostgreSQL's `JSONB`.

---

## 🏛️ Core Architecture & Hierarchy

Permissions in this system cascade top-down but can be overridden at a granular level:
`Group ➔ Project ➔ Directory ➔ File`

* **Groups:** Top-level organizational units (e.g., "Engineering", "Client A").
* **Projects:** Workspaces belonging to a Group.
* **Templates:** Reusable blueprints (catalogs) attached to a Group.
* **Project Files:** An S3-backed hierarchical file system belonging to a Project.

---

## 📊 Database Schema Documentation

### 1. Core Containers
* **`groups`**: The highest-level container. 
* **`projects`**: Child workspaces belonging to a specific `group_id`. If a group is deleted, all its projects are cascaded.

### 2. Authorization & Roles (Zanzibar Tuples)
Instead of relying on Keycloak for complex logic, roles and permissions are stored as direct relationship tuples: `(User, Role, Resource)`.

* **`group_roles`**: Defines a user's role at the group level (e.g., `admin`, `viewer`). 
  * *ABAC Support:* Includes an `attributes` JSONB column for custom business rules (e.g., `{"budget_limit": 5000}`).
* **`project_roles`**: Allows granular access to a specific project without granting access to the entire group.
* **`file_roles`**: The deepest level of permissions. Grants a user access to a specific file or folder.

> **Note on Identity:** `user_id` columns store UUIDs issued by the Identity Provider (Keycloak). There is no local `users` table, decoupling authentication from authorization.

### 3. Template Engine
Templates are immutable blueprints generated from projects. 

* **`templates`**: The catalog entry for a blueprint. It belongs to a Group and must have a unique name within that group.
* **`template_versions`**: Represents immutable snapshots of a template.
  * Uses Semantic Versioning (`version_tag` like `v1.0.0`).
  * Stores the parsed infrastructure schema in `variables_schema` (`JSONB`) and raw content in `hcl_content`.
  * Maintains an `origin_project_id` reference (with `ON DELETE SET NULL`) to track which project spawned this template version, ensuring that deleting the original project does not break the template.

### 4. File System
A robust, hierarchical virtual file system linked to S3 object storage.

* **`project_files`**: Represents both files and directories.
  * **`project_id`**: Denormalized at every level to ensure lightning-fast authorization queries (avoids recursive permission checks).
  * **`parent_id`**: Creates the folder hierarchy. `NULL` means the file is at the root of the project.
  * **`s3_object_key`**: The actual physical path in the S3 bucket (NULL if the node is a directory).

---

## 💡 Key Design Principles

1. **Cascading Permissions:** A user with an `admin` role in `group_roles` implicitly gains access to all downstream `projects` and `project_files`.
2. **Immutability of Releases:** The separation between `templates` and `template_versions` ensures that deployed blueprints remain stable even if the source project evolves or is deleted.
3. **High-Performance Hierarchy:** The `project_files` table includes indexes on both `project_id` and `parent_id`, allowing O(1) permission checks at the project level while maintaining a strict tree structure.
4. **Future-Proof for ReBAC:** The `_roles` tables are designed as relational triplets. If the infrastructure ever transitions to a dedicated ReBAC engine (like SpiceDB/OpenFGA), these tables map 1:1 to graph relationships.
