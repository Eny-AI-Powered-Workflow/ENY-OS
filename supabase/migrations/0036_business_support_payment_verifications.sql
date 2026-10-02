-- C:\Users\Melody\Documents\ENY-OS\supabase\migrations\0036_business_support_payment_verifications.sql

create table if not exists payment_verification_events (
  id uuid primary key default gen_random_uuid(),
  provider text not null check (provider = 'paystack'),
  transaction_reference text not null,
  verification_status text not null check (verification_status in ('verified', 'not_confirmed')),
  provider_status text not null,
  reviewer_user_id uuid not null references auth.users(id) on delete restrict,
  idempotency_key uuid not null unique,
  created_at timestamptz not null default now()
);

create index if not exists payment_verification_events_reference_idx
  on payment_verification_events(provider, transaction_reference, created_at desc);

alter table payment_verification_events enable row level security;
drop policy if exists "service role reads payment verification events" on payment_verification_events;
create policy "service role reads payment verification events"
on payment_verification_events for select to service_role
using (true);
drop policy if exists "service role appends payment verification events" on payment_verification_events;
create policy "service role appends payment verification events"
on payment_verification_events for insert to service_role
with check (true);

revoke all on payment_verification_events from anon, authenticated;
grant select, insert on payment_verification_events to service_role;