-- Baseline — encrypted backup store
--
-- The server holds ONE row per user and cannot read it. The app encrypts the
-- whole dataset in the browser with AES-GCM under a key derived from a
-- passphrase that is never uploaded, so `blob` is ciphertext plus the salt and
-- nonce needed to decrypt it on a device that knows the passphrase.
--
-- There is therefore nothing here to mine, sell, subpoena usefully, or leak:
-- a dump of this table is a list of user ids and opaque bytes.

create table if not exists public.backups (
  user_id     uuid primary key references auth.users(id) on delete cascade,
  -- {v, kdf, iter, salt, iv, ct} — ct is the ciphertext, base64.
  blob        jsonb not null,
  bytes       integer not null default 0,
  updated_at  timestamptz not null default now(),
  created_at  timestamptz not null default now(),
  -- A backup is a backup, not a file-hosting service.
  constraint backups_size_cap check (bytes >= 0 and bytes <= 25000000)
);

comment on table  public.backups is
  'One end-to-end encrypted snapshot per user. The server cannot read blob.';
comment on column public.backups.blob is
  'AES-GCM ciphertext with its salt and nonce. Key derived in the browser from a passphrase that is never sent here.';

-- ---------------------------------------------------------------------------
--  ROW LEVEL SECURITY
--  The browser holds only the publishable key, which grants nothing on its
--  own. Every statement below is scoped to auth.uid(), so a signed-in user can
--  reach exactly one row: their own. With RLS enabled and no permissive
--  policy, the default is deny.
-- ---------------------------------------------------------------------------
alter table public.backups enable row level security;

drop policy if exists "read own backup"   on public.backups;
drop policy if exists "insert own backup" on public.backups;
drop policy if exists "update own backup" on public.backups;
drop policy if exists "delete own backup" on public.backups;

create policy "read own backup"   on public.backups
  for select using (auth.uid() = user_id);

create policy "insert own backup" on public.backups
  for insert with check (auth.uid() = user_id);

create policy "update own backup" on public.backups
  for update using (auth.uid() = user_id)
              with check (auth.uid() = user_id);

-- Deleting the server copy is the user's own decision and needs no support
-- ticket. Deleting the ACCOUNT cascades to this row (see the FK above).
create policy "delete own backup" on public.backups
  for delete using (auth.uid() = user_id);

-- Keep updated_at honest rather than trusting the client's clock.
create or replace function public.backups_touch()
returns trigger language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end $$;

drop trigger if exists backups_touch on public.backups;
create trigger backups_touch before insert or update on public.backups
  for each row execute function public.backups_touch();
