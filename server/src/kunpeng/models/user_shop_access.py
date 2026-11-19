from sqlalchemy import Column, ForeignKey, Index, Integer, UniqueConstraint

from kunpeng.models.base import BaseModel


class UserShopAccess(BaseModel):
    """Read-only access granted to a user for an existing shop."""

    __tablename__ = "user_shop_access"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(
        Integer,
        ForeignKey("users.id", name="fk_user_shop_access_user_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="被授权用户ID",
    )
    shop_id = Column(
        Integer,
        ForeignKey("shops.id", name="fk_user_shop_access_shop_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="授权店铺ID",
    )

    __table_args__ = (
        UniqueConstraint("user_id", "shop_id", name="uq_user_shop_access_user_shop"),
        Index("idx_user_shop_access_user_shop", "user_id", "shop_id"),
        {"comment": "用户店铺只读授权关系"},
    )
