# Database Configuration

The RAG system uses a database to persist chat history and conversations. You have two options:

## Option 1: SQLite (Default - Recommended for Getting Started)

**No setup required!** SQLite is file-based and works out of the box.

The database file is automatically created at: `data/chainlit.db`

### Advantages
- ✅ Zero configuration
- ✅ No server setup needed
- ✅ Perfect for single-user, local development
- ✅ Easy backup (just copy the file)
- ✅ Portable

### Limitations
- ❌ Not suitable for concurrent users
- ❌ Limited scalability
- ❌ No network access

### Configuration

Already configured by default! No changes needed.

```bash
# .env file (default)
CHAINLIT_DATABASE_URL=sqlite:///data/chainlit.db
```

---

## Option 2: PostgreSQL (Optional - For Production)

Use PostgreSQL when you need:
- Multiple concurrent users
- Network access
- Production deployment
- Better scalability

### Installation

**macOS:**
```bash
brew install postgresql
brew services start postgresql
```

**Ubuntu/Debian:**
```bash
sudo apt-get install postgresql postgresql-contrib
sudo systemctl start postgresql
```

**Windows:**
- Download installer from: https://www.postgresql.org/download/windows/
- Run installer and follow setup wizard

### Setup Database

```bash
# Create database
createdb ragcorpus

# Or using psql
psql -U postgres
CREATE DATABASE ragcorpus;
\q
```

### Configuration

Update your `.env` file:

```bash
# Change this line
CHAINLIT_DATABASE_URL=postgresql://username:password@localhost:5432/ragcorpus
```

Replace:
- `username` - Your PostgreSQL username (default: `postgres`)
- `password` - Your PostgreSQL password
- `localhost` - Database host (use `localhost` for local)
- `5432` - PostgreSQL port (default: 5432)
- `ragcorpus` - Database name

### Test Connection

```python
from sqlalchemy import create_engine

url = "postgresql://username:password@localhost:5432/ragcorpus"
engine = create_engine(url)

# Test connection
with engine.connect() as conn:
    print("✅ PostgreSQL connection successful!")
```

---

## Migrating from SQLite to PostgreSQL

### 1. Export SQLite Data

```bash
# Dump SQLite database
sqlite3 data/chainlit.db .dump > backup.sql
```

### 2. Convert SQL Syntax

SQLite and PostgreSQL have slight differences. You may need to:
- Convert `AUTOINCREMENT` to `SERIAL`
- Adjust date/time formats
- Update boolean types

### 3. Import to PostgreSQL

```bash
psql -U username -d ragcorpus -f backup.sql
```

### 4. Update Configuration

Change `CHAINLIT_DATABASE_URL` in `.env` to your PostgreSQL URL.

### 5. Restart Application

```bash
chainlit run src/ui/app.py
```

---

## Database Schema

Chainlit automatically creates these tables:

- `threads` - Conversation threads
- `messages` - Chat messages
- `users` - User information
- `feedbacks` - User feedback on messages
- `elements` - File uploads and attachments

You don't need to create these manually - Chainlit handles migrations automatically.

---

## Backup Strategies

### SQLite Backup

**Simple file copy:**
```bash
cp data/chainlit.db data/chainlit.backup.db
```

**Automated backup script:**
```bash
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
cp data/chainlit.db "backups/chainlit_${DATE}.db"
```

### PostgreSQL Backup

**Full database dump:**
```bash
pg_dump ragcorpus > backup_$(date +%Y%m%d).sql
```

**Compressed backup:**
```bash
pg_dump ragcorpus | gzip > backup_$(date +%Y%m%d).sql.gz
```

**Automated daily backup:**
```bash
#!/bin/bash
# Add to crontab: 0 2 * * * /path/to/backup.sh

DATE=$(date +%Y%m%d)
BACKUP_DIR="/backups/postgres"
FILENAME="ragcorpus_${DATE}.sql.gz"

pg_dump ragcorpus | gzip > "${BACKUP_DIR}/${FILENAME}"

# Keep only last 7 days
find ${BACKUP_DIR} -name "ragcorpus_*.sql.gz" -mtime +7 -delete
```

---

## Troubleshooting

### SQLite Issues

**"Database is locked"**
- Another process is using the database
- Close other instances of the app
- Check for lingering processes: `lsof data/chainlit.db`

**"Unable to open database file"**
- Check file permissions
- Ensure `data/` directory exists
- Verify path in `.env` is correct

### PostgreSQL Issues

**"Connection refused"**
- Check PostgreSQL is running: `pg_isready`
- Verify port 5432 is open
- Check firewall settings

**"Authentication failed"**
- Verify username and password
- Check `pg_hba.conf` authentication settings
- Try: `psql -U username -d ragcorpus` to test

**"Database does not exist"**
- Create database: `createdb ragcorpus`
- Or in psql: `CREATE DATABASE ragcorpus;`

---

## Performance Tips

### SQLite
- Use WAL mode for better concurrency:
  ```sql
  PRAGMA journal_mode=WAL;
  ```
- Regular VACUUM to optimize:
  ```sql
  VACUUM;
  ```

### PostgreSQL
- Create indexes on frequently queried columns
- Run ANALYZE regularly
- Adjust connection pool size
- Monitor query performance with `EXPLAIN`

---

## Security Best Practices

### SQLite
- Set appropriate file permissions: `chmod 600 data/chainlit.db`
- Encrypt the file system for sensitive data
- Regular backups to secure location

### PostgreSQL
- Use strong passwords
- Enable SSL connections
- Restrict network access in `pg_hba.conf`
- Regular security updates
- Use connection pooling (pgBouncer)

---

## Recommendation

**For this project (ADHD academic researcher):**

✅ **Use SQLite** (default)

Why?
- Single user
- Local machine
- No setup complexity
- Easy backup
- Portable
- Perfect for research workflow

**Switch to PostgreSQL only if:**
- Deploying to cloud
- Multiple users needed
- Sharing across devices
- Network access required

---

**Current Status:** ✅ SQLite configured and ready to use (no action needed)
