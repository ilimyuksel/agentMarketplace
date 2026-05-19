"""initial schema — 11 tables + pgvector extension + HNSW index

Revision ID: 0001_initial
Revises:
Create Date: 2026-05-18

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql

revision: str = "0001_initial"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- pgvector extension ---
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    # --- agents ---
    op.create_table(
        "agents",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("display_name", sa.String(128), nullable=False),
        sa.Column("tier", sa.String(16), nullable=False),
        sa.Column("role", sa.String(64), nullable=False),
        sa.Column("skill_keywords", sa.Text(), nullable=False),
        sa.Column("skill_embedding", Vector(768), nullable=True),
        sa.Column("system_prompt", sa.Text(), nullable=False),
        sa.Column("base_price", sa.Numeric(10, 2), nullable=True),
        sa.Column("min_acceptance", sa.Numeric(10, 2), nullable=False),
        sa.Column("pricing_config", postgresql.JSONB(), nullable=False),
        sa.Column("bidding_style", sa.String(32), nullable=False),
        sa.Column("reputation", sa.Numeric(4, 3), nullable=False, server_default="0.750"),
        sa.Column("success_rate", sa.Numeric(4, 3), nullable=False, server_default="0.750"),
        sa.Column("completed_jobs", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("wallet_id", sa.String(64), nullable=False),
        sa.Column("can_hire_subagents", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_ghost", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_agents_tier", "agents", ["tier"])
    op.create_index("idx_agents_active", "agents", ["is_active"])
    # HNSW index for cosine similarity over skill_embedding.
    op.execute(
        "CREATE INDEX idx_agents_skill_embedding ON agents "
        "USING hnsw (skill_embedding vector_cosine_ops)"
    )

    # --- wallets ---
    op.create_table(
        "wallets",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("owner_type", sa.String(16), nullable=False),
        sa.Column("owner_id", sa.String(64), nullable=True),
        sa.Column("balance", sa.Numeric(12, 2), nullable=False, server_default="0.00"),
        sa.Column("currency", sa.String(8), nullable=False, server_default="USD"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_wallets_owner", "wallets", ["owner_type", "owner_id"])

    # --- users ---
    op.create_table(
        "users",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("display_name", sa.String(128), nullable=True),
        sa.Column("wallet_id", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )

    # --- jobs ---
    op.create_table(
        "jobs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("user_id", sa.String(64), nullable=False),
        sa.Column("user_prompt", sa.Text(), nullable=False),
        sa.Column("budget", sa.Numeric(10, 2), nullable=False),
        sa.Column("budget_tier", sa.String(16), nullable=True),
        sa.Column("escrow_wallet_id", sa.String(64), nullable=True),
        sa.Column("assigned_manager_id", sa.String(64), nullable=True),
        sa.Column("manager_bid_amount", sa.Numeric(10, 2), nullable=True),
        sa.Column("manager_profit_margin", sa.Numeric(4, 3), nullable=True),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("final_output_id", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("failure_reason", sa.Text(), nullable=True),
    )
    op.create_index("idx_jobs_state", "jobs", ["state"])
    op.create_index("idx_jobs_user", "jobs", ["user_id"])

    # --- tasks ---
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("parent_task_id", sa.String(64), nullable=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("required_skills", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("skill_embedding", Vector(768), nullable=True),
        sa.Column("budget", sa.Numeric(10, 2), nullable=False),
        sa.Column("final_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("state", sa.String(20), nullable=False),
        sa.Column("dependencies", postgresql.ARRAY(sa.Text()), nullable=False, server_default="{}"),
        sa.Column("assigned_agent_id", sa.String(64), nullable=True),
        sa.Column("output_json", postgresql.JSONB(), nullable=True),
        sa.Column("judge_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("judge_verdict", sa.String(32), nullable=True),
        sa.Column("judge_feedback", sa.Text(), nullable=True),
        sa.Column("revision_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("idx_tasks_job", "tasks", ["job_id"])
    op.create_index("idx_tasks_state", "tasks", ["state"])
    op.create_index("idx_tasks_agent", "tasks", ["assigned_agent_id"])

    # --- bids ---
    op.create_table(
        "bids",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("task_id", sa.String(64), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("bid_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(4, 3), nullable=True),
        sa.Column("estimated_time_seconds", sa.Integer(), nullable=True),
        sa.Column("scope_assumption", sa.Text(), nullable=True),
        sa.Column("is_winner", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("selection_score", sa.Numeric(6, 4), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_bids_task", "bids", ["task_id"])
    op.create_index("idx_bids_agent", "bids", ["agent_id"])

    # --- transactions (ledger) ---
    # NOTE: `block_number` uses GENERATED BY DEFAULT AS IDENTITY (start with 0)
    # so the seeder can insert the genesis block as block_number=0, and
    # subsequent ledger writes that omit `block_number` auto-increment.
    op.create_table(
        "transactions",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("task_id", sa.String(64), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("from_wallet_id", sa.String(64), nullable=False),
        sa.Column("to_wallet_id", sa.String(64), nullable=False),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("transaction_type", sa.String(32), nullable=False),
        sa.Column("milestone", sa.String(32), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "block_number",
            sa.BigInteger(),
            # MINVALUE=0 is mandatory because Postgres identity columns
            # default MINVALUE to 1; the spec requires block_number=0 for
            # the genesis block.
            sa.Identity(start=0, increment=1, minvalue=0, always=False),
            nullable=False,
            unique=True,
        ),
        sa.Column("block_hash", sa.String(64), nullable=False),
        sa.Column("previous_block_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_tx_job", "transactions", ["job_id"])
    op.create_index("idx_tx_wallets", "transactions", ["from_wallet_id", "to_wallet_id"])
    op.create_index("idx_tx_type", "transactions", ["transaction_type"])
    op.create_index("idx_tx_block", "transactions", ["block_number"])

    # --- events (audit log) ---
    op.create_table(
        "events",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("task_id", sa.String(64), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_events_job", "events", ["job_id"])
    op.create_index("idx_events_type", "events", ["event_type"])
    op.create_index("idx_events_created", "events", ["created_at"])

    # --- reputation_history ---
    op.create_table(
        "reputation_history",
        sa.Column("id", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("agent_id", sa.String(64), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id"), nullable=True),
        sa.Column("task_id", sa.String(64), sa.ForeignKey("tasks.id"), nullable=True),
        sa.Column("old_reputation", sa.Numeric(4, 3), nullable=True),
        sa.Column("new_reputation", sa.Numeric(4, 3), nullable=True),
        sa.Column("delta", sa.Numeric(4, 3), nullable=True),
        sa.Column("reason", sa.String(64), nullable=True),
        sa.Column("judge_score", sa.Numeric(4, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_rep_agent", "reputation_history", ["agent_id"])

    # --- judge_evaluations ---
    op.create_table(
        "judge_evaluations",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("task_id", sa.String(64), sa.ForeignKey("tasks.id"), nullable=False),
        sa.Column("evaluated_agent_id", sa.String(64), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("scope_completeness", sa.Numeric(4, 3), nullable=True),
        sa.Column("structural_quality", sa.Numeric(4, 3), nullable=True),
        sa.Column("content_quality", sa.Numeric(4, 3), nullable=True),
        sa.Column("brief_fidelity", sa.Numeric(4, 3), nullable=True),
        sa.Column("final_score", sa.Numeric(4, 3), nullable=False),
        sa.Column("decision", sa.String(32), nullable=False),
        sa.Column("reasoning", sa.Text(), nullable=True),
        sa.Column("feedback_for_revision", sa.Text(), nullable=True),
        sa.Column("confidence_in_judgment", sa.Numeric(4, 3), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )
    op.create_index("idx_eval_task", "judge_evaluations", ["task_id"])

    # --- job_outputs ---
    op.create_table(
        "job_outputs",
        sa.Column("id", sa.String(64), primary_key=True),
        sa.Column("job_id", sa.String(64), sa.ForeignKey("jobs.id"), nullable=False),
        sa.Column("output_type", sa.String(32), nullable=True),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column("html_artifact", sa.Text(), nullable=True),
        sa.Column("contributing_agents", postgresql.ARRAY(sa.Text()), nullable=True),
        sa.Column("total_cost", sa.Numeric(10, 2), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("job_outputs")
    op.drop_index("idx_eval_task", table_name="judge_evaluations")
    op.drop_table("judge_evaluations")
    op.drop_index("idx_rep_agent", table_name="reputation_history")
    op.drop_table("reputation_history")
    op.drop_index("idx_events_created", table_name="events")
    op.drop_index("idx_events_type", table_name="events")
    op.drop_index("idx_events_job", table_name="events")
    op.drop_table("events")
    op.drop_index("idx_tx_block", table_name="transactions")
    op.drop_index("idx_tx_type", table_name="transactions")
    op.drop_index("idx_tx_wallets", table_name="transactions")
    op.drop_index("idx_tx_job", table_name="transactions")
    op.drop_table("transactions")
    op.drop_index("idx_bids_agent", table_name="bids")
    op.drop_index("idx_bids_task", table_name="bids")
    op.drop_table("bids")
    op.drop_index("idx_tasks_agent", table_name="tasks")
    op.drop_index("idx_tasks_state", table_name="tasks")
    op.drop_index("idx_tasks_job", table_name="tasks")
    op.drop_table("tasks")
    op.drop_index("idx_jobs_user", table_name="jobs")
    op.drop_index("idx_jobs_state", table_name="jobs")
    op.drop_table("jobs")
    op.drop_table("users")
    op.drop_index("idx_wallets_owner", table_name="wallets")
    op.drop_table("wallets")
    op.execute("DROP INDEX IF EXISTS idx_agents_skill_embedding")
    op.drop_index("idx_agents_active", table_name="agents")
    op.drop_index("idx_agents_tier", table_name="agents")
    op.drop_table("agents")
    # extension intentionally left in place — it's cheap to keep, and other
    # objects may depend on it.
