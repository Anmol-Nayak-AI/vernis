-- Vernis enterprise art platform: identity, creation, provenance, commerce, and billing.
create extension if not exists pgcrypto;

create type public.workspace_role as enum ('owner', 'admin', 'curator', 'artist', 'finance', 'viewer');
create type public.artwork_state as enum ('draft', 'review', 'approved', 'published', 'archived');
create type public.listing_kind as enum ('fixed_price', 'auction', 'digital_collectible');
create type public.listing_state as enum ('draft', 'scheduled', 'live', 'sold', 'withdrawn', 'expired');
create type public.order_state as enum ('pending', 'awaiting_payment', 'paid', 'fulfilled', 'refunded', 'cancelled');

create table public.profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  display_name text not null default '',
  avatar_url text,
  artist_bio text,
  country_code text check (country_code is null or length(country_code) = 2),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.workspaces (
  id uuid primary key default gen_random_uuid(),
  owner_id uuid not null references auth.users(id) on delete restrict,
  name text not null check (char_length(name) between 2 and 120),
  slug text not null unique check (slug ~ '^[a-z0-9][a-z0-9-]{1,62}$'),
  plan text not null default 'creator' check (plan in ('creator', 'studio', 'enterprise')),
  currency text not null default 'USD' check (char_length(currency) = 3),
  stripe_customer_id text unique,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.workspace_members (
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  user_id uuid not null references auth.users(id) on delete cascade,
  role public.workspace_role not null default 'viewer',
  invited_by uuid references auth.users(id) on delete set null,
  joined_at timestamptz not null default now(),
  primary key (workspace_id, user_id)
);

create table public.generation_jobs (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  requested_by uuid not null references auth.users(id) on delete restrict,
  status text not null default 'queued' check (status in ('queued', 'running', 'succeeded', 'failed', 'cancelled')),
  model text not null,
  parameters jsonb not null default '{}'::jsonb,
  provider_request_id text,
  credit_cost integer not null default 0 check (credit_cost >= 0),
  error_code text,
  created_at timestamptz not null default now(),
  completed_at timestamptz
);

create table public.artworks (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  creator_id uuid not null references auth.users(id) on delete restrict,
  generation_job_id uuid references public.generation_jobs(id) on delete set null,
  title text not null default 'Untitled work' check (char_length(title) <= 240),
  description text,
  prompt text,
  style_id text,
  image_url text not null,
  preview_url text,
  state public.artwork_state not null default 'draft',
  commercial_rights_declared boolean not null default false,
  rights_notes text,
  metadata jsonb not null default '{}'::jsonb,
  checksum_sha256 text check (checksum_sha256 is null or checksum_sha256 ~ '^[a-f0-9]{64}$'),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.collections (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  created_by uuid not null references auth.users(id) on delete restrict,
  name text not null check (char_length(name) between 1 and 160),
  description text,
  visibility text not null default 'private' check (visibility in ('private', 'workspace', 'public')),
  created_at timestamptz not null default now()
);

create table public.collection_artworks (
  collection_id uuid not null references public.collections(id) on delete cascade,
  artwork_id uuid not null references public.artworks(id) on delete cascade,
  position integer not null default 0,
  added_at timestamptz not null default now(),
  primary key (collection_id, artwork_id)
);

create table public.listings (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  artwork_id uuid not null references public.artworks(id) on delete restrict,
  seller_id uuid not null references auth.users(id) on delete restrict,
  kind public.listing_kind not null,
  status public.listing_state not null default 'draft',
  currency text not null default 'USD' check (char_length(currency) = 3),
  price_minor bigint check (price_minor is null or price_minor >= 0),
  reserve_minor bigint check (reserve_minor is null or reserve_minor >= 0),
  bid_increment_minor bigint check (bid_increment_minor is null or bid_increment_minor > 0),
  edition_size integer check (edition_size is null or edition_size > 0),
  neft_enabled boolean not null default false,
  starts_at timestamptz,
  ends_at timestamptz,
  terms jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  check (ends_at is null or starts_at is null or ends_at > starts_at)
);

create table public.bids (
  id uuid primary key default gen_random_uuid(),
  listing_id uuid not null references public.listings(id) on delete cascade,
  bidder_id uuid not null references auth.users(id) on delete restrict,
  amount_minor bigint not null check (amount_minor > 0),
  currency text not null check (char_length(currency) = 3),
  status text not null default 'active' check (status in ('active', 'outbid', 'winning', 'won', 'cancelled')),
  created_at timestamptz not null default now()
);

create table public.orders (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null references public.workspaces(id) on delete restrict,
  listing_id uuid references public.listings(id) on delete set null,
  buyer_id uuid not null references auth.users(id) on delete restrict,
  seller_id uuid not null references auth.users(id) on delete restrict,
  status public.order_state not null default 'pending',
  currency text not null check (char_length(currency) = 3),
  subtotal_minor bigint not null check (subtotal_minor >= 0),
  platform_fee_minor bigint not null default 0 check (platform_fee_minor >= 0),
  tax_minor bigint not null default 0 check (tax_minor >= 0),
  payment_provider text,
  payment_reference text,
  settlement_method text check (settlement_method is null or settlement_method in ('stripe', 'neft', 'wire', 'manual')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table public.provenance_events (
  id uuid primary key default gen_random_uuid(),
  artwork_id uuid not null references public.artworks(id) on delete cascade,
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  actor_id uuid references auth.users(id) on delete set null,
  event_type text not null check (event_type in ('created', 'rights_declared', 'approved', 'edition_opened', 'listed', 'sold', 'transferred', 'certificate_issued', 'archived')),
  details jsonb not null default '{}'::jsonb,
  checksum_sha256 text check (checksum_sha256 is null or checksum_sha256 ~ '^[a-f0-9]{64}$'),
  occurred_at timestamptz not null default now()
);

create table public.subscriptions (
  id uuid primary key default gen_random_uuid(),
  workspace_id uuid not null unique references public.workspaces(id) on delete cascade,
  plan text not null check (plan in ('creator', 'studio', 'enterprise')),
  status text not null check (status in ('trialing', 'active', 'past_due', 'cancelled', 'paused')),
  stripe_subscription_id text unique,
  credits_included integer not null default 0 check (credits_included >= 0),
  credits_used integer not null default 0 check (credits_used >= 0),
  period_end timestamptz,
  updated_at timestamptz not null default now()
);

create table public.audit_events (
  id bigint generated always as identity primary key,
  workspace_id uuid not null references public.workspaces(id) on delete cascade,
  actor_id uuid references auth.users(id) on delete set null,
  action text not null,
  entity_type text not null,
  entity_id uuid,
  payload jsonb not null default '{}'::jsonb,
  occurred_at timestamptz not null default now()
);

create index workspace_members_user_idx on public.workspace_members(user_id, workspace_id);
create index generation_jobs_workspace_created_idx on public.generation_jobs(workspace_id, created_at desc);
create index artworks_workspace_created_idx on public.artworks(workspace_id, created_at desc);
create index artworks_creator_idx on public.artworks(creator_id);
create index listings_status_ends_idx on public.listings(status, ends_at) where status in ('scheduled', 'live');
create index listings_workspace_idx on public.listings(workspace_id, created_at desc);
create index bids_listing_amount_idx on public.bids(listing_id, amount_minor desc);
create index orders_buyer_idx on public.orders(buyer_id, created_at desc);
create index orders_seller_idx on public.orders(seller_id, created_at desc);
create index provenance_artwork_idx on public.provenance_events(artwork_id, occurred_at);
create index audit_workspace_time_idx on public.audit_events(workspace_id, occurred_at desc);

create schema if not exists app_private;
revoke all on schema app_private from public;
grant usage on schema app_private to authenticated;

create or replace function app_private.is_workspace_member(target_workspace uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.workspace_members
    where workspace_id = target_workspace and user_id = (select auth.uid())
  );
$$;

create or replace function app_private.is_workspace_manager(target_workspace uuid)
returns boolean language sql stable security definer set search_path = '' as $$
  select exists (
    select 1 from public.workspace_members
    where workspace_id = target_workspace
      and user_id = (select auth.uid())
      and role in ('owner', 'admin')
  );
$$;

revoke all on function app_private.is_workspace_member(uuid) from public;
revoke all on function app_private.is_workspace_manager(uuid) from public;
grant execute on function app_private.is_workspace_member(uuid) to authenticated;
grant execute on function app_private.is_workspace_manager(uuid) to authenticated;

alter table public.profiles enable row level security;
alter table public.workspaces enable row level security;
alter table public.workspace_members enable row level security;
alter table public.generation_jobs enable row level security;
alter table public.artworks enable row level security;
alter table public.collections enable row level security;
alter table public.collection_artworks enable row level security;
alter table public.listings enable row level security;
alter table public.bids enable row level security;
alter table public.orders enable row level security;
alter table public.provenance_events enable row level security;
alter table public.subscriptions enable row level security;
alter table public.audit_events enable row level security;

create policy "profiles_read_own" on public.profiles for select to authenticated using (id = (select auth.uid()));
create policy "profiles_insert_own" on public.profiles for insert to authenticated with check (id = (select auth.uid()));
create policy "profiles_update_own" on public.profiles for update to authenticated using (id = (select auth.uid())) with check (id = (select auth.uid()));

create policy "workspaces_read_member" on public.workspaces for select to authenticated using (owner_id = (select auth.uid()) or app_private.is_workspace_member(id));
create policy "workspaces_insert_owner" on public.workspaces for insert to authenticated with check (owner_id = (select auth.uid()));
create policy "workspaces_update_manager" on public.workspaces for update to authenticated using (owner_id = (select auth.uid()) or app_private.is_workspace_manager(id)) with check (owner_id = (select auth.uid()) or app_private.is_workspace_manager(id));
create policy "workspaces_delete_owner" on public.workspaces for delete to authenticated using (owner_id = (select auth.uid()));

create policy "members_read_workspace" on public.workspace_members for select to authenticated using (user_id = (select auth.uid()) or app_private.is_workspace_manager(workspace_id));
create policy "members_insert_manager" on public.workspace_members for insert to authenticated with check (
  app_private.is_workspace_manager(workspace_id)
  or (user_id = (select auth.uid()) and role = 'owner' and exists (select 1 from public.workspaces w where w.id = workspace_id and w.owner_id = (select auth.uid())))
);
create policy "members_update_manager" on public.workspace_members for update to authenticated using (app_private.is_workspace_manager(workspace_id)) with check (app_private.is_workspace_manager(workspace_id));
create policy "members_delete_manager" on public.workspace_members for delete to authenticated using (app_private.is_workspace_manager(workspace_id) and user_id <> (select auth.uid()));

create policy "generation_read_member" on public.generation_jobs for select to authenticated using (app_private.is_workspace_member(workspace_id));
create policy "generation_insert_self" on public.generation_jobs for insert to authenticated with check (requested_by = (select auth.uid()) and app_private.is_workspace_member(workspace_id));
create policy "generation_update_self" on public.generation_jobs for update to authenticated using (requested_by = (select auth.uid())) with check (requested_by = (select auth.uid()) and app_private.is_workspace_member(workspace_id));

create policy "artworks_read_member_or_public" on public.artworks for select to authenticated using (state = 'published' or app_private.is_workspace_member(workspace_id));
create policy "artworks_insert_creator" on public.artworks for insert to authenticated with check (creator_id = (select auth.uid()) and app_private.is_workspace_member(workspace_id));
create policy "artworks_update_creator_or_manager" on public.artworks for update to authenticated using (creator_id = (select auth.uid()) or app_private.is_workspace_manager(workspace_id)) with check (app_private.is_workspace_member(workspace_id));
create policy "artworks_delete_creator_or_manager" on public.artworks for delete to authenticated using (creator_id = (select auth.uid()) or app_private.is_workspace_manager(workspace_id));

create policy "collections_read_visible" on public.collections for select to authenticated using (visibility = 'public' or app_private.is_workspace_member(workspace_id));
create policy "collections_insert_member" on public.collections for insert to authenticated with check (created_by = (select auth.uid()) and app_private.is_workspace_member(workspace_id));
create policy "collections_update_creator_or_manager" on public.collections for update to authenticated using (created_by = (select auth.uid()) or app_private.is_workspace_manager(workspace_id)) with check (app_private.is_workspace_member(workspace_id));
create policy "collections_delete_creator_or_manager" on public.collections for delete to authenticated using (created_by = (select auth.uid()) or app_private.is_workspace_manager(workspace_id));

create policy "collection_items_read_visible" on public.collection_artworks for select to authenticated using (exists (select 1 from public.collections c where c.id = collection_id));
create policy "collection_items_insert_member" on public.collection_artworks for insert to authenticated with check (exists (select 1 from public.collections c where c.id = collection_id and app_private.is_workspace_member(c.workspace_id)));
create policy "collection_items_delete_member" on public.collection_artworks for delete to authenticated using (exists (select 1 from public.collections c where c.id = collection_id and app_private.is_workspace_member(c.workspace_id)));

create policy "listings_read_live_or_member" on public.listings for select to authenticated using (status = 'live' or app_private.is_workspace_member(workspace_id));
create policy "listings_insert_seller" on public.listings for insert to authenticated with check (seller_id = (select auth.uid()) and app_private.is_workspace_member(workspace_id));
create policy "listings_update_seller_or_manager" on public.listings for update to authenticated using (seller_id = (select auth.uid()) or app_private.is_workspace_manager(workspace_id)) with check (app_private.is_workspace_member(workspace_id));
create policy "listings_delete_draft" on public.listings for delete to authenticated using (status = 'draft' and (seller_id = (select auth.uid()) or app_private.is_workspace_manager(workspace_id)));

create policy "bids_read_own_or_seller" on public.bids for select to authenticated using (bidder_id = (select auth.uid()) or exists (select 1 from public.listings l where l.id = listing_id and l.seller_id = (select auth.uid())));
create policy "bids_insert_self_live" on public.bids for insert to authenticated with check (bidder_id = (select auth.uid()) and exists (select 1 from public.listings l where l.id = listing_id and l.status = 'live' and l.kind = 'auction' and l.seller_id <> (select auth.uid())));

create policy "orders_read_party_or_manager" on public.orders for select to authenticated using (buyer_id = (select auth.uid()) or seller_id = (select auth.uid()) or app_private.is_workspace_manager(workspace_id));
create policy "orders_insert_buyer" on public.orders for insert to authenticated with check (buyer_id = (select auth.uid()));

create policy "provenance_read_published_or_member" on public.provenance_events for select to authenticated using (app_private.is_workspace_member(workspace_id) or exists (select 1 from public.artworks a where a.id = artwork_id and a.state = 'published'));
create policy "provenance_insert_member" on public.provenance_events for insert to authenticated with check (actor_id = (select auth.uid()) and app_private.is_workspace_member(workspace_id));

create policy "subscriptions_read_manager" on public.subscriptions for select to authenticated using (app_private.is_workspace_manager(workspace_id));
create policy "audit_read_manager" on public.audit_events for select to authenticated using (app_private.is_workspace_manager(workspace_id));

-- Public catalog reads are intentionally limited to published artwork/listings.
create policy "public_artworks_read" on public.artworks for select to anon using (state = 'published');
create policy "public_listings_read" on public.listings for select to anon using (status = 'live');
create policy "public_provenance_read" on public.provenance_events for select to anon using (exists (select 1 from public.artworks a where a.id = artwork_id and a.state = 'published'));

grant select, insert, update on public.profiles to authenticated;
grant select, insert, update, delete on public.workspaces, public.workspace_members, public.artworks, public.collections, public.collection_artworks, public.listings to authenticated;
grant select, insert, update on public.generation_jobs to authenticated;
grant select, insert on public.bids, public.orders, public.provenance_events to authenticated;
grant select on public.subscriptions, public.audit_events to authenticated;
grant select on public.artworks, public.listings, public.provenance_events to anon;

-- Object storage: public, optimized previews and private full-resolution masters.
insert into storage.buckets (id, name, public, file_size_limit, allowed_mime_types)
values
  ('artwork-previews', 'artwork-previews', true, 10485760, array['image/webp', 'image/jpeg', 'image/png']),
  ('artwork-masters', 'artwork-masters', false, 104857600, array['image/webp', 'image/jpeg', 'image/png', 'image/tiff'])
on conflict (id) do nothing;

create policy "previews_public_read" on storage.objects for select to anon, authenticated
using (bucket_id = 'artwork-previews');
create policy "previews_member_insert" on storage.objects for insert to authenticated
with check (bucket_id = 'artwork-previews' and app_private.is_workspace_member(((storage.foldername(name))[1])::uuid));
create policy "previews_member_update" on storage.objects for update to authenticated
using (bucket_id = 'artwork-previews' and app_private.is_workspace_member(((storage.foldername(name))[1])::uuid))
with check (bucket_id = 'artwork-previews' and app_private.is_workspace_member(((storage.foldername(name))[1])::uuid));
create policy "previews_manager_delete" on storage.objects for delete to authenticated
using (bucket_id = 'artwork-previews' and app_private.is_workspace_manager(((storage.foldername(name))[1])::uuid));

create policy "masters_member_read" on storage.objects for select to authenticated
using (bucket_id = 'artwork-masters' and app_private.is_workspace_member(((storage.foldername(name))[1])::uuid));
create policy "masters_member_insert" on storage.objects for insert to authenticated
with check (bucket_id = 'artwork-masters' and app_private.is_workspace_member(((storage.foldername(name))[1])::uuid));
create policy "masters_member_update" on storage.objects for update to authenticated
using (bucket_id = 'artwork-masters' and app_private.is_workspace_member(((storage.foldername(name))[1])::uuid))
with check (bucket_id = 'artwork-masters' and app_private.is_workspace_member(((storage.foldername(name))[1])::uuid));
create policy "masters_manager_delete" on storage.objects for delete to authenticated
using (bucket_id = 'artwork-masters' and app_private.is_workspace_manager(((storage.foldername(name))[1])::uuid));
