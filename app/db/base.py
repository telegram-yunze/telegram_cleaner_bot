from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


# 统一命名约定，便于 Alembic 和 MySQL 约束名保持稳定。
naming_convention = {
	"ix": "ix_%(column_0_label)s",
	"uq": "uq_%(table_name)s_%(column_0_name)s",
	"ck": "ck_%(table_name)s_%(constraint_name)s",
	"fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
	"pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
	metadata = MetaData(naming_convention=naming_convention)


class TimestampMixin:
	"""提供创建和更新时间字段。"""

	created_at: Mapped[datetime] = mapped_column(
		DateTime,
		nullable=False,
		server_default=func.now(),
		comment="创建时间",
	)
	updated_at: Mapped[datetime] = mapped_column(
		DateTime,
		nullable=False,
		server_default=func.now(),
		onupdate=func.now(),
		comment="更新时间",
	)
