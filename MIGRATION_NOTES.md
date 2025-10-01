# SQLite Configuration Update

## What Changed

The system now uses **SQLite by default** instead of PostgreSQL for chat history storage.

### Why SQLite?

For a single-user ADHD academic research system:
- ✅ **Zero configuration** - works immediately
- ✅ **No server setup** - file-based database
- ✅ **Easy backup** - just copy the file
- ✅ **Portable** - move it anywhere
- ✅ **Perfect for local research** - exactly what you need

### What This Means

**Before:**
- Required PostgreSQL installation
- Required database creation
- Required connection configuration
- Extra complexity for single-user system

**Now:**
- SQLite works out of the box
- Database auto-created on first use
- Located at: `data/chainlit.db`
- **Zero setup required!** 🎉

## Updated Files

1. **`.env.example`**
   - Changed `DATABASE_URL` to `CHAINLIT_DATABASE_URL`
   - Default: `sqlite:///data/chainlit.db`
   - PostgreSQL option still available (commented)

2. **`src/config/settings.py`**
   - Updated field name to `chainlit_database_url`
   - Default value: SQLite path
   - Automatically works for new users

3. **`.chainlit/.chainlit`** (new)
   - Chainlit-specific database config
   - Points to SQLite by default

4. **`docs/DATABASE_SETUP.md`** (new)
   - Complete guide for both SQLite and PostgreSQL
   - Migration instructions if needed
   - Backup strategies
   - Troubleshooting

## For Existing Users

If you already have PostgreSQL set up:
- **No action needed** - your config will still work
- To switch to SQLite:
  1. Update `.env`: `CHAINLIT_DATABASE_URL=sqlite:///data/chainlit.db`
  2. Restart the app
  3. (Optional) Migrate data - see [docs/DATABASE_SETUP.md](docs/DATABASE_SETUP.md)

## For New Users

**Nothing to do!** SQLite is already configured and will work immediately when you run:

```bash
chainlit run src/ui/app.py
```

The database file will be automatically created at `data/chainlit.db`

## When to Use PostgreSQL

You might want PostgreSQL if:
- Deploying to cloud/production
- Multiple users accessing simultaneously
- Need network database access
- Building a shared team system

For **single-user academic research** (your use case): **SQLite is perfect!** ✅

## Migration Path

If you later need PostgreSQL:
1. See [docs/DATABASE_SETUP.md](docs/DATABASE_SETUP.md)
2. Install PostgreSQL
3. Create database: `createdb ragcorpus`
4. Update `.env` with PostgreSQL URL
5. (Optional) Migrate data from SQLite

## Benefits for ADHD-Friendly Design

This change aligns with ADHD-friendly principles:
- ✅ **Less cognitive load** - one less thing to set up
- ✅ **Immediate gratification** - works right away
- ✅ **Reduces setup friction** - get to actual work faster
- ✅ **Simpler mental model** - just a file, not a server
- ✅ **Lower barrier to entry** - no database expertise needed

## Technical Details

**SQLite advantages for this use case:**
- File-based: `data/chainlit.db`
- No daemon/server process
- ACID compliant
- Serverless
- Zero configuration
- Cross-platform
- Public domain (no licensing concerns)

**Performance:**
- More than adequate for single-user chat history
- Handles thousands of messages easily
- Local file access is fast
- No network latency

**Limitations:**
- Not suitable for concurrent writes from multiple users
- Not accessible over network (feature, not bug for local research)
- Limited to ~140 TB database size (more than enough!)

## Backup Recommendations

**SQLite (automatic):**
```bash
# Simple backup script
cp data/chainlit.db backups/chainlit_$(date +%Y%m%d).db
```

**Add to your research backup routine:**
```bash
#!/bin/bash
# backup_research.sh
rsync -av --exclude='*.pyc' RAGCorpus/ /backup/location/
```

## Summary

| Aspect | SQLite (New Default) | PostgreSQL (Optional) |
|--------|---------------------|----------------------|
| Setup | None | Install + Create DB |
| Users | Single user | Multi-user |
| Location | Local file | Network server |
| Backup | Copy file | pg_dump |
| Complexity | Low | Medium |
| Best For | **This project!** ✅ | Production/Cloud |

---

**Status:** ✅ Complete - SQLite is now the default and ready to use!

**Action Required:** None for new users | Optional migration for existing PostgreSQL users
