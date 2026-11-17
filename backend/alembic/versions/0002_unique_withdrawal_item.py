"""Prevent multiple withdrawals for the same inventory item."""
from alembic import op
from sqlalchemy import inspect

revision = "0002_withdrawal_item_unique"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    connection = op.get_bind()
    existing = inspect(connection).get_unique_constraints("withdrawal_requests")
    if not any(row["name"] == "uq_withdrawal_inventory_item" for row in existing):
        with op.batch_alter_table("withdrawal_requests") as batch_op:
            batch_op.create_unique_constraint("uq_withdrawal_inventory_item", ["inventory_item_id"])


def downgrade() -> None:
    connection = op.get_bind()
    existing = inspect(connection).get_unique_constraints("withdrawal_requests")
    if any(row["name"] == "uq_withdrawal_inventory_item" for row in existing):
        with op.batch_alter_table("withdrawal_requests") as batch_op:
            batch_op.drop_constraint("uq_withdrawal_inventory_item", type_="unique")
