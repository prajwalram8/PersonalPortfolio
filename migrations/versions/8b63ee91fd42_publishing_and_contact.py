"""Add publishing metadata and bring the contact table under migration control."""

import re
import unicodedata

from alembic import op
import sqlalchemy as sa


revision = "8b63ee91fd42"
down_revision = "10b29f2a3de3"
branch_labels = None
depends_on = None


def upgrade():
    connection = op.get_bind()
    if not sa.inspect(connection).has_table("contact_submissions"):
        op.create_table(
            "contact_submissions",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("name", sa.String(150)),
            sa.Column("email", sa.String(150)),
            sa.Column("subject", sa.String(300)),
            sa.Column("message", sa.Text()),
        )

    with op.batch_alter_table("markdown_file") as batch:
        batch.add_column(sa.Column("slug", sa.String(120)))
        batch.add_column(sa.Column("summary", sa.String(300), server_default="", nullable=False))
        batch.add_column(sa.Column("published_at", sa.DateTime()))

    posts = sa.table(
        "markdown_file", sa.column("id"), sa.column("name"), sa.column("upload_date"),
        sa.column("modification_date"), sa.column("slug"), sa.column("published_at", sa.DateTime()),
    )
    rows = connection.execute(
        sa.select(posts.c.id, posts.c.name, posts.c.upload_date, posts.c.modification_date).order_by(posts.c.id)
    ).all()
    used_slugs = set()
    for post in rows:
        ascii_title = unicodedata.normalize("NFKD", post.name or "").encode("ascii", "ignore").decode()
        base = re.sub(r"[^a-z0-9]+", "-", ascii_title.lower()).strip("-") or "post"
        slug = base
        number = 2
        while slug in used_slugs:
            slug = f"{base}-{number}"
            number += 1
        used_slugs.add(slug)
        published_at = post.upload_date or post.modification_date or "1970-01-01 00:00:00"
        connection.execute(
            posts.update().where(posts.c.id == post.id).values(
                slug=slug, published_at=sa.cast(sa.literal(published_at), sa.String())
            )
        )

    with op.batch_alter_table("markdown_file") as batch:
        batch.alter_column("slug", existing_type=sa.String(120), nullable=False)
        batch.alter_column("summary", existing_type=sa.String(300), server_default=None)
        batch.create_unique_constraint("uq_markdown_file_slug", ["slug"])


def downgrade():
    with op.batch_alter_table("markdown_file") as batch:
        batch.drop_constraint("uq_markdown_file_slug", type_="unique")
        batch.drop_column("published_at")
        batch.drop_column("summary")
        batch.drop_column("slug")
    # Preserve submissions in environments where the contact table predated this revision.
