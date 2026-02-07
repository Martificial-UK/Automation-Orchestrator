# Backup and Recovery Procedures

## Database Backup (PostgreSQL)

To back up the database:

1. Run the following command to create a backup:

   ```powershell
   docker exec johnengine-db-1 pg_dump -U user -d mydb > backup/db_backup_$(Get-Date -Format yyyyMMddHHmmss).sql
   ```

2. Store backups in the `backup/` directory.

## Database Restore

To restore from a backup:

1. Place the backup file in the `backup/` directory.
2. Run:

   ```powershell
   docker exec -i johnengine-db-1 psql -U user -d mydb < backup/db_backup_<timestamp>.sql
   ```

## Application Files Backup

- Regularly copy the `src/`, `frontend/`, and `config/` directories to a secure location.

## Recovery Checklist

- Verify database restore.
- Restore application files.
- Restart Docker Compose services.

## Automated Backup (Optional)

- Schedule the above commands using Windows Task Scheduler or a cron job in a Linux environment.
