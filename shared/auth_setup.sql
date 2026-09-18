-- Run this once in the Supabase SQL Editor after shared/schema.sql.
-- It creates a citizen profile row safely whenever Supabase Auth creates a user.
-- The browser never writes directly to public.users, so RLS can remain enabled.

create or replace function public.handle_new_citizen()
returns trigger
language plpgsql
security definer set search_path = ''
as $$
begin
  insert into public.users (id, name, email, role)
  values (
    new.id,
    coalesce(new.raw_user_meta_data ->> 'name', ''),
    new.email,
    'citizen'
  );
  return new;
end;
$$;

drop trigger if exists on_auth_user_created on auth.users;

create trigger on_auth_user_created
  after insert on auth.users
  for each row execute function public.handle_new_citizen();
