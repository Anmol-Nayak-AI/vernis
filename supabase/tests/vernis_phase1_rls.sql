begin;

create extension if not exists pgtap;
select plan(8);

select has_schema('vernis', 'Vernis application schema exists');
select has_table('vernis', 'artworks', 'Artwork registry table exists');
select is(
  (select relrowsecurity from pg_class where oid = 'vernis.artworks'::regclass),
  true,
  'Artwork registry has row-level security enabled'
);

insert into vernis.users (id, email, display_name) values
  ('10000000-0000-0000-0000-000000000001', 'owner-a@example.test', 'Owner A'),
  ('20000000-0000-0000-0000-000000000002', 'owner-b@example.test', 'Owner B'),
  ('30000000-0000-0000-0000-000000000003', 'viewer-a@example.test', 'Viewer A');

insert into vernis.organizations (id, name, slug, plan, created_by) values
  ('a0000000-0000-0000-0000-000000000001', 'Tenant A', 'rls-tenant-a', 'gallery', '10000000-0000-0000-0000-000000000001'),
  ('b0000000-0000-0000-0000-000000000002', 'Tenant B', 'rls-tenant-b', 'gallery', '20000000-0000-0000-0000-000000000002');

insert into vernis.organization_memberships (organization_id, user_id, role) values
  ('a0000000-0000-0000-0000-000000000001', '10000000-0000-0000-0000-000000000001', 'owner'),
  ('a0000000-0000-0000-0000-000000000001', '30000000-0000-0000-0000-000000000003', 'viewer'),
  ('b0000000-0000-0000-0000-000000000002', '20000000-0000-0000-0000-000000000002', 'owner');

insert into vernis.artworks (id, organization_id, title, attribution_status, date_precision, dimensions, status, created_by) values
  ('aa000000-0000-0000-0000-000000000001', 'a0000000-0000-0000-0000-000000000001', 'Tenant A work', 'unknown', 'unknown', '{}', 'draft', '10000000-0000-0000-0000-000000000001'),
  ('bb000000-0000-0000-0000-000000000002', 'b0000000-0000-0000-0000-000000000002', 'Tenant B work', 'unknown', 'unknown', '{}', 'draft', '20000000-0000-0000-0000-000000000002');

set local role authenticated;
select set_config('request.jwt.claim.sub', '10000000-0000-0000-0000-000000000001', true);

select is((select count(*) from vernis.organizations), 1::bigint, 'A member sees only their organization');
select is((select count(*) from vernis.artworks), 1::bigint, 'A member sees only tenant-scoped artworks');
select is((select title from vernis.artworks limit 1), 'Tenant A work', 'Cross-tenant artwork content remains hidden');
select lives_ok(
  $$insert into vernis.artworks (organization_id, title, attribution_status, date_precision, dimensions, status, created_by)
    values ('a0000000-0000-0000-0000-000000000001', 'Owner-created work', 'unknown', 'unknown', '{}', 'draft', '10000000-0000-0000-0000-000000000001')$$,
  'An owner can create an artwork in their own organization'
);

select set_config('request.jwt.claim.sub', '30000000-0000-0000-0000-000000000003', true);
select throws_ok(
  $$insert into vernis.artworks (organization_id, title, attribution_status, date_precision, dimensions, status, created_by)
    values ('a0000000-0000-0000-0000-000000000001', 'Viewer-created work', 'unknown', 'unknown', '{}', 'draft', '30000000-0000-0000-0000-000000000003')$$,
  '42501',
  null,
  'A viewer cannot create an artwork'
);

select * from finish();
rollback;
