"""Create the complete Phase 1 PostgreSQL schema."""

from alembic import op

revision = "0001_init"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE daily_aggregates (
            student_id UUID NOT NULL, 
            day DATE NOT NULL, 
            active_minutes INTEGER NOT NULL, 
            tasks_answered INTEGER NOT NULL, 
            messages INTEGER NOT NULL, 
            payload JSONB NOT NULL, 
            PRIMARY KEY (student_id, day)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE events (
            id BIGSERIAL NOT NULL, 
            student_id UUID NOT NULL, 
            session_id UUID, 
            exam_id TEXT, 
            set_id UUID, 
            topic_skill_id TEXT, 
            chat_id UUID, 
            type TEXT NOT NULL, 
            payload JSONB NOT NULL, 
            occurred_at TIMESTAMP WITH TIME ZONE NOT NULL, 
            ingested_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
            processed_at TIMESTAMP WITH TIME ZONE, 
            extractor_version TEXT, 
            source_event_ids BIGINT[], 
            PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_events_chat_unprocessed
        ON events (chat_id, processed_at) WHERE processed_at IS NULL
        """
    )
    op.execute(
        """
        CREATE INDEX ix_events_student_occurred ON events (student_id, occurred_at)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_events_type ON events (type)
        """
    )
    op.execute(
        """
        CREATE TABLE generated_texts (
            id UUID NOT NULL, 
            kind TEXT NOT NULL, 
            input_hash TEXT NOT NULL, 
            text TEXT NOT NULL, 
            model TEXT NOT NULL, 
            prompt_version TEXT NOT NULL, 
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
            PRIMARY KEY (id), 
            UNIQUE (kind, input_hash)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE messages (
            id UUID NOT NULL, 
            chat_id UUID NOT NULL, 
            student_id UUID NOT NULL, 
            role TEXT NOT NULL, 
            text TEXT NOT NULL, 
            markup JSONB, 
            event_id BIGINT NOT NULL, 
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
            PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_messages_chat_created ON messages (chat_id, created_at)
        """
    )
    op.execute(
        """
        CREATE TABLE profiles (
            student_id UUID NOT NULL, 
            questionnaire JSONB NOT NULL, 
            traits JSONB NOT NULL, 
            updated_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
            PRIMARY KEY (student_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE programs_cache (
            id TEXT NOT NULL, 
            university TEXT NOT NULL, 
            country TEXT NOT NULL, 
            city TEXT NOT NULL, 
            direction TEXT NOT NULL, 
            language TEXT NOT NULL, 
            duration_months INTEGER, 
            tuition_per_year INTEGER, 
            living_per_year INTEGER, 
            currency TEXT NOT NULL, 
            scholarships_note TEXT, 
            environment_text TEXT, 
            source_url TEXT NOT NULL, 
            checked_at DATE NOT NULL, 
            is_demo BOOLEAN NOT NULL, 
            extracted_auto BOOLEAN NOT NULL, 
            flagged BOOLEAN NOT NULL, 
            payload JSONB NOT NULL, 
            PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_programs_cache_country ON programs_cache (country)
        """
    )
    op.execute(
        """
        CREATE INDEX ix_programs_cache_direction ON programs_cache (direction)
        """
    )
    op.execute(
        """
        CREATE TABLE recommendations (
            id UUID NOT NULL, 
            student_id UUID NOT NULL, 
            kind TEXT NOT NULL, 
            payload JSONB NOT NULL, 
            status TEXT NOT NULL, 
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
            decided_at TIMESTAMP WITH TIME ZONE, 
            PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE saved_programs (
            student_id UUID NOT NULL, 
            program_id TEXT NOT NULL, 
            saved_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
            PRIMARY KEY (student_id, program_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE seen_templates (
            student_id UUID NOT NULL, 
            template_id TEXT NOT NULL, 
            n_seen INTEGER NOT NULL, 
            last_seen_at TIMESTAMP WITH TIME ZONE NOT NULL, 
            PRIMARY KEY (student_id, template_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE set_summaries (
            id UUID NOT NULL, 
            student_id UUID NOT NULL, 
            set_id UUID NOT NULL, 
            text TEXT NOT NULL, 
            stats JSONB NOT NULL, 
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
            PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE task_instances (
            id UUID NOT NULL, 
            template_id TEXT NOT NULL, 
            seed BIGINT NOT NULL, 
            exam_id TEXT NOT NULL, 
            type TEXT NOT NULL, 
            stem_rendered TEXT NOT NULL, 
            options JSONB, 
            answer JSONB NOT NULL, 
            trap_answers JSONB, 
            solution_rendered JSONB NOT NULL, 
            figure_url TEXT, 
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
            student_id UUID NOT NULL, 
            skill_id TEXT NOT NULL, 
            time_reference_sec INTEGER NOT NULL, 
            difficulty INTEGER NOT NULL, 
            tags TEXT[] NOT NULL, 
            PRIMARY KEY (id), 
            UNIQUE (template_id, seed, student_id)
        )
        """
    )
    op.execute(
        """
        CREATE TABLE task_templates (
            id TEXT NOT NULL, 
            exam_id TEXT NOT NULL, 
            skill_id TEXT NOT NULL, 
            type TEXT NOT NULL, 
            difficulty INTEGER NOT NULL, 
            kind TEXT NOT NULL, 
            spec JSONB NOT NULL, 
            PRIMARY KEY (id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX ix_task_templates_skill_exam ON task_templates (skill_id, exam_id)
        """
    )
    op.execute(
        """
        CREATE TABLE users (
            id UUID NOT NULL, 
            email TEXT NOT NULL, 
            password_hash TEXT NOT NULL, 
            created_at TIMESTAMP WITH TIME ZONE DEFAULT now() NOT NULL, 
            PRIMARY KEY (id), 
            UNIQUE (email)
        )
        """
    )


def downgrade() -> None:
    op.drop_table("users")
    op.drop_table("task_templates")
    op.drop_table("task_instances")
    op.drop_table("set_summaries")
    op.drop_table("seen_templates")
    op.drop_table("saved_programs")
    op.drop_table("recommendations")
    op.drop_table("programs_cache")
    op.drop_table("profiles")
    op.drop_table("messages")
    op.drop_table("generated_texts")
    op.drop_table("events")
    op.drop_table("daily_aggregates")
