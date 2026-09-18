-- Run this once in the Supabase SQL Editor for an existing CivicAI database.
-- New databases receive these fields from shared/schema.sql.

alter table public.reports
  add column if not exists description varchar(500),
  add column if not exists sentiment_score real,
  add column if not exists sentiment_label text,
  add column if not exists severity text;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'reports_sentiment_label_check'
  ) then
    alter table public.reports
      add constraint reports_sentiment_label_check
      check (sentiment_label is null or sentiment_label in ('negative', 'neutral', 'positive'));
  end if;

  if not exists (
    select 1 from pg_constraint where conname = 'reports_severity_check'
  ) then
    alter table public.reports
      add constraint reports_severity_check
      check (severity is null or severity in ('low', 'medium', 'high', 'critical'));
  end if;
end $$;
