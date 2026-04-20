from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import JSON, Column
from sqlmodel import Field, SQLModel


class Tag(SQLModel, table=True):
    """标签数据模型。

    name 为规范化标准名（小写英文，唯一），display_name 为前端展示名称。
    metadata_ 字段以 JSON 存储可扩展信息，数据库列名为 metadata（加下划线以
    避免与 SQLModel 内部属性冲突）。
    """

    id: Optional[int] = Field(default=None, primary_key=True)

    # 对外暴露的稳定标识符，格式 tag_{id}，导入完成后写入
    public_id: Optional[str] = Field(default=None, index=True, unique=True)

    # 规范化名称：全小写英文，数据库唯一约束
    name: str = Field(index=True, unique=True, max_length=256)

    # 前端展示名称
    display_name: str = Field(default="", max_length=256)

    # 标签种类：normal / artist / artwork / series
    type: str = Field(default="normal", index=True, max_length=32)

    # 描述（最大 1024 字节）
    description: Optional[str] = Field(default="", max_length=1024)

    # 主分类
    category_id: int = Field(default=1, index=True)

    # 缓存：当前被多少张图片关联（由写入侧负责维护）
    usage_count: int = Field(default=0)

    # 最后一次被关联或访问的时间，格式 YYYYMMDDHHMMSS
    last_used_at: Optional[str] = Field(default=None, max_length=14)

    # 扩展元信息，结构：
    # {
    #   "schema_version": 1,
    #   "color": "#FF9900",
    #   "created_via": "manual|auto:filename|import|merge|split|sync|migration",
    #   "ui_hint": {"badge": "city", "promote": true},
    #   "notes": ""
    # }
    metadata_: Optional[dict] = Field(
        default_factory=dict,
        sa_column=Column("metadata", JSON),
    )

    created_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str = Field(default="admin", max_length=64)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
