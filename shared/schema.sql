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
  category text check (category in ('pothole', 'waterlogging', 'garbage')),
  confidence real,
  priority_score real,
  status text check (status in ('pending', 'in-progress', 'resolved')) default 'pending',
  duplicate_of uuid references reports(id),
  created_at timestamp default now()
);
