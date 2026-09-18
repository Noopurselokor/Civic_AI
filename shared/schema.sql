-- Enable PostGIS
create extension if not exists postgis;

create table wards (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  nagarpalika_id uuid,
  boundary geometry(Polygon, 4326)
);

create table users (
  id uuid primary key default gen_random_uuid(),
  name text,
  email text unique,
  phone text,
  role text check (role in ('citizen', 'admin')) default 'citizen',
  ward_id uuid references wards(id)
);

create table reports (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id),
  image_url text,
  lat double precision,
  lng double precision,
  address text,
  ward_id uuid references wards(id),
  category text check (category in ('pothole', 'waterlogging', 'garbage', 'dead_animals', 'illegal_dumping', 'sewer', 'streetlight')),
  confidence real,
  description varchar(500),
  sentiment_score real,
  sentiment_label text check (sentiment_label in ('negative', 'neutral', 'positive')),
  severity text check (severity in ('low', 'medium', 'high', 'critical')),
  priority_score real,
  status text check (status in ('pending', 'in-progress', 'resolved')) default 'pending',
  duplicate_of uuid references reports(id),
  created_at timestamp default now()
);

-- Point-in-polygon ward lookup, callable from the backend as:
--   supabase.rpc('find_ward', {'lat': 21.14, 'lng': 79.08})
create or replace function find_ward(lat double precision, lng double precision)
returns uuid as $$
  select id from wards
  where ST_Contains(boundary, ST_SetSRID(ST_MakePoint(lng, lat), 4326))
  limit 1;
$$ language sql stable;
