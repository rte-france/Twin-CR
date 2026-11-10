"""
Copyright (c) 2025-2026, RTE (http://www.rte-france.com)
This Source Code Form is subject to the terms of the Mozilla Public
License, v. 2.0. If a copy of the MPL was not distributed with this
file, You can obtain one at http://mozilla.org/MPL/2.0/.
SPDX-License-Identifier: MPL-2.0
This file is part of the Twin-CR project.
"""

import uuid
from typing import Annotated

from botocore.exceptions import ClientError
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import PlainTextResponse, Response

from app.dependencies import templates_repo as repo
from app.dependencies.aliases import (
    CurrentUserDep,
    DbSessionDep,
    S3ClientDep,
    SettingsDep,
)
from app.dependencies.file_tree import build_file_tree
from app.schemas import DirectoryCreate, ItemUpdate

files_router = APIRouter(
    prefix="/api/v1/projects/{project_id}/files", tags=["File System"]
)
directories_router = APIRouter(
    prefix="/api/v1/projects/{project_id}/directories", tags=["File System"]
)


@files_router.get("")
async def list_files(
    project_id: str, db_session: DbSessionDep, current_user: CurrentUserDep
):
    if not await repo.check_project_read_access(
        db_session, project_id, current_user.id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    rows = await repo.fetch_all_nodes_for_project(db_session, project_id)
    _, roots = build_file_tree(rows)
    return roots


@directories_router.get("")
async def list_directories(
    project_id: str, db_session: DbSessionDep, current_user: CurrentUserDep
):
    if not await repo.check_project_read_access(
        db_session, project_id, current_user.id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    rows = await repo.fetch_all_nodes_for_project(db_session, project_id)
    return [
        {"id": r["id"], "name": r["name"], "parent_id": r["parent_id"]}
        for r in rows
        if r["is_directory"]
    ]


@directories_router.get("/{dir_id}/tree")
async def get_directory_tree(
    project_id: str, dir_id: str, db_session: DbSessionDep, current_user: CurrentUserDep
):
    if not await repo.check_project_read_access(
        db_session, project_id, current_user.id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")
    rows = await repo.fetch_all_nodes_for_project(db_session, project_id)
    nodes, _ = build_file_tree(rows)

    if dir_id not in nodes:
        raise HTTPException(status_code=404, detail="Directory not found")
    if not nodes[dir_id]["is_directory"]:
        raise HTTPException(status_code=400, detail="Requested ID is not a directory")

    return nodes[dir_id]


@files_router.post("/upload")
async def upload_file(
    project_id: str,
    name: Annotated[str, Form(...)],
    file: Annotated[UploadFile, File(...)],
    db_session: DbSessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
    s3_client: S3ClientDep,
    parent_id: Annotated[str | None, Form()] = None,
):
    if not parent_id or parent_id == "" or parent_id == "null":
        parent_id = None

    has_access = await repo.check_project_write_access(
        db_session, project_id, current_user.id
    )
    if not has_access:
        raise HTTPException(status_code=403, detail="Forbidden")

    file_id = str(uuid.uuid4())
    file_content = await file.read()
    s3_key = f"projects/{project_id}/{file_id}"

    try:
        await s3_client.put_object(
            Bucket=settings.s3_bucket_name, Key=s3_key, Body=file_content
        )
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"S3 Upload failed. Error: {str(e)}"
        )

    try:
        await repo.upsert_file(
            db_session,
            file_id=file_id,
            project_id=project_id,
            name=name,
            s3_key=s3_key,
            parent_id=parent_id,
        )
        await db_session.commit()
    except Exception as e:
        await db_session.rollback()
        await s3_client.delete_object(Bucket=settings.s3_bucket_name, Key=s3_key)
        raise HTTPException(
            status_code=500, detail=f"Database insertion failed. Error: {str(e)}"
        )

    return {"id": file_id, "name": name, "is_directory": False}


@files_router.post("/directories")
async def create_directory(
    project_id: str,
    payload: DirectoryCreate,
    db_session: DbSessionDep,
    current_user: CurrentUserDep,
):
    if not payload.parent_id or payload.parent_id == "" or payload.parent_id == "null":
        payload.parent_id = None

    if not await repo.check_project_write_access(
        db_session, project_id, current_user.id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    dir_id = str(uuid.uuid4())

    try:
        await repo.insert_directory(
            db_session,
            dir_id=dir_id,
            project_id=project_id,
            name=payload.name,
            parent_id=payload.parent_id,
        )
        await db_session.commit()
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=500, detail=f"DB Error: {str(e)}")

    return {"id": dir_id, "name": payload.name, "is_directory": True}


@files_router.patch("/{item_id}")
async def update_item(
    project_id: str,
    item_id: str,
    update_data: ItemUpdate,
    db_session: DbSessionDep,
    current_user: CurrentUserDep,
):
    if update_data.parent_id == item_id:
        raise HTTPException(status_code=400, detail="Invalid parent reference")

    if not await repo.check_project_write_access(
        db_session, project_id, current_user.id
    ):
        has_access = await repo.check_write_access(db_session, item_id, current_user.id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Forbidden")

    update_dict = update_data.model_dump(exclude_unset=True)

    try:
        updated = await repo.update_item_fields(
            db_session, item_id=item_id, update_dict=update_dict
        )

        if not updated:
            raise HTTPException(status_code=404, detail="Item not found")

        await db_session.commit()
    except HTTPException:
        raise
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=500, detail=f"DB Update Error: {str(e)}")

    return {"message": "Item updated", "id": item_id}


@files_router.delete("/{item_id}")
async def delete_item(
    project_id: str,
    item_id: str,
    db_session: DbSessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
    s3_client: S3ClientDep,
):
    if not await repo.check_project_write_access(
        db_session, project_id, current_user.id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    items_to_delete = await repo.fetch_item_and_descendants(
        db_session, item_id, current_user.id
    )
    if not items_to_delete:
        raise HTTPException(status_code=404, detail="Item not found or forbidden")

    s3_keys = [
        row["s3_object_key"]
        for row in items_to_delete
        if row.get("s3_object_key") is not None
    ]
    db_ids = [row["id"] for row in items_to_delete]

    for key in s3_keys:
        try:
            await s3_client.delete_object(Bucket=settings.s3_bucket_name, Key=key)
        except ClientError:
            pass

    try:
        await repo.delete_items(db_session, db_ids)
        await db_session.commit()
    except Exception as e:
        await db_session.rollback()
        raise HTTPException(status_code=500, detail=f"DB Delete Error: {str(e)}")

    return {
        "message": "Item and all its descendants deleted",
        "deleted_s3_files": len(s3_keys),
        "deleted_db_records": len(db_ids),
    }


@files_router.get("/{file_id}/raw", response_class=PlainTextResponse)
async def get_raw_file_content(
    project_id: str,
    file_id: str,
    db_session: DbSessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
    s3_client: S3ClientDep,
):
    if not await repo.check_project_read_access(
        db_session, project_id, current_user.id
    ):
        raise HTTPException(status_code=403, detail="Forbidden")

    row = await repo.fetch_file_or_404(db_session, file_id, current_user.id)
    try:
        s3_response = await s3_client.get_object(
            Bucket=settings.s3_bucket_name, Key=row["s3_object_key"]
        )

        async with s3_response["Body"] as stream:
            content = await stream.read()

        return Response(content=content, media_type="application/octet-stream")

    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"S3 Read Error: {e}")



@files_router.put("/{file_id}/raw")
async def update_raw_file_content(
    project_id: str,
    file_id: str,
    request: Request,
    db_session: DbSessionDep,
    current_user: CurrentUserDep,
    settings: SettingsDep,
    s3_client: S3ClientDep,
):
    if not await repo.check_project_write_access(
        db_session, project_id, current_user.id
    ):
        has_access = await repo.check_write_access(db_session, file_id, current_user.id)
        if not has_access:
            raise HTTPException(status_code=403, detail="Forbidden")

    row = await repo.fetch_file_or_404(
        db_session, file_id, current_user.id, detail="File not found or is a directory"
    )
    body_bytes = await request.body()

    try:
        await s3_client.put_object(
            Bucket=settings.s3_bucket_name,
            Key=row["s3_object_key"],
            Body=body_bytes,
        )
    except ClientError as e:
        raise HTTPException(status_code=500, detail=f"S3 Write Error: {e}")

    return {"message": "File updated successfully", "file_id": file_id}
