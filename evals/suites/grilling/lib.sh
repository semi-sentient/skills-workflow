# Shared fixture scaffolding for the `grilling` suite.
# Sourced by each fixture's setup.sh, which runs with cwd = a fresh empty dir.
#
# One small Express service with facts planted for the interviewer to find:
#   - docker-compose runs 3 replicas       (process-local state is wrong)
#   - /health and /webhooks skip auth      (contradicts "every route is authed")
#   - express-session with the MemoryStore (contradicts "sessions are in Postgres")
#   - node:test is the test runner; no Redis dependency
# Personas reference these by name; check.py never reads them.

init_repo() {
  git init -q
  git config user.email "fixture@example.com"
  git config user.name "Fixture"
  git config commit.gpgsign false
  # The harness materialises the skill under test into .claude/ AFTER setup.
  printf '.claude/\n' >> "$(git rev-parse --git-path info/exclude)"

  mkdir -p src/routes test
  cat > README.md <<'EOF'
# Ledger API

Internal HTTP API for recording and reconciling account entries. Express 4,
Postgres for the ledger tables, `node --test` for tests. Deployed as three
replicas behind the load balancer (see docker-compose.yml).
EOF
  cat > package.json <<'EOF'
{
  "name": "ledger-api",
  "type": "module",
  "scripts": { "test": "node --test test/" },
  "dependencies": {
    "express": "^4.19.0",
    "express-session": "^1.18.0",
    "pg": "^8.11.0"
  }
}
EOF
  cat > docker-compose.yml <<'EOF'
services:
  api:
    build: .
    deploy:
      replicas: 3
    environment:
      DATABASE_URL: postgres://ledger:ledger@db:5432/ledger
      SESSION_SECRET: change-me
  db:
    image: postgres:16
EOF
  cat > src/app.js <<'EOF'
import express from 'express';
import session from 'express-session';
import { requireUser } from './auth.js';
import { health } from './routes/health.js';
import { webhooks } from './routes/webhooks.js';
import { entries } from './routes/entries.js';

export function createApp() {
  const app = express();
  app.use(express.json());
  // Default MemoryStore: sessions live in this process only.
  app.use(session({ secret: process.env.SESSION_SECRET, resave: false, saveUninitialized: false }));

  app.use('/health', health);       // public: load balancer probe
  app.use('/webhooks', webhooks);   // public: signed payloads from the bank
  app.use('/entries', requireUser, entries);
  return app;
}
EOF
  cat > src/auth.js <<'EOF'
export function requireUser(req, res, next) {
  if (!req.session?.userId) return res.status(401).json({ error: 'unauthenticated' });
  next();
}
EOF
  cat > src/routes/health.js <<'EOF'
import { Router } from 'express';
export const health = Router().get('/', (_req, res) => res.json({ ok: true }));
EOF
  cat > src/routes/webhooks.js <<'EOF'
import { Router } from 'express';
import { verifySignature } from '../signing.js';
export const webhooks = Router().post('/bank', (req, res) => {
  if (!verifySignature(req)) return res.status(400).json({ error: 'bad signature' });
  res.status(202).end();
});
EOF
  cat > src/routes/entries.js <<'EOF'
import { Router } from 'express';
export const entries = Router()
  .get('/', (_req, res) => res.json([]))
  .post('/', (req, res) => res.status(201).json(req.body));
EOF
  cat > src/signing.js <<'EOF'
export function verifySignature(req) {
  return typeof req.get('x-signature') === 'string';
}
EOF
  cat > test/app.test.js <<'EOF'
import { test } from 'node:test';
import assert from 'node:assert/strict';
import { createApp } from '../src/app.js';

test('creates an app', () => {
  assert.ok(createApp());
});
EOF
  git add -A
  git commit -q -m "chore: Initial commit"
}

# A single-context repo that already has a glossary (grill-with-docs fixtures).
add_context_md() {
  cat > CONTEXT.md <<'EOF'
# Ledger — Ubiquitous Language

## Terms

**Order** — A customer's request to purchase one or more items. Has a lifecycle: Placed → Paid → Fulfilled.

**Cancellation** — The customer voids an Order *before* fulfilment. No money has moved, so nothing is refunded; the Order simply ends. _Avoid_: "void", "abort".

**Customer** — The paying party. Distinct from a User, which is a login. One Customer may have several Users.

**Entry** — One immutable line in the ledger. Entries are never edited; corrections are new Entries.
EOF
  git add CONTEXT.md
  git commit -q -m "docs: Add CONTEXT.md glossary"
}
