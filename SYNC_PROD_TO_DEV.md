# Sync Production → Development Database

## On the production server

1. Run the backup script  
   ```bash
   ./dump_db
   ```
   This creates:
   - `<timestamp>_postgres_dump.sql`
   - `<timestamp>_django_dump.json`
   - `<timestamp>_git_info.txt`

2. Copy the JSON dump to your dev machine  

---

## On the development machine

1. Create a new empty SQLite database  
   ```bash
   python manage.py migrate
   ```

2. Flush any default data  
   ```bash
   python manage.py flush
   ```

3. Load the latest JSON dump  
   ```bash
   python manage.py loaddata ../db_dumps/latest_django_dump.json
   ```


---

## Notes

- The JSON dump works across databases (PostgreSQL → SQLite).  
- The `.sql` dump is a full PostgreSQL backup.  
- The `git_info.txt` file records which code version the dump was made from.  
- If you add unmanaged models, exclude them in `dump_db` or `loaddata` will fail.  
- The fixture used after `flush` is named `latest_django_dump.json` for simplicity.