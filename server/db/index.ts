import Database from 'better-sqlite3'
import path from 'path'
import { fileURLToPath } from 'url'
import fs from 'fs'

const __dirname = path.dirname(fileURLToPath(import.meta.url))

// In production (Docker), use /app/data, otherwise use local data folder
const isProduction = process.env.NODE_ENV === 'production'
const dataDir = isProduction 
  ? '/app/data' 
  : path.join(__dirname, '../../data')

// Ensure data directory exists
if (!fs.existsSync(dataDir)) {
  fs.mkdirSync(dataDir, { recursive: true })
}

const dbPath = path.join(dataDir, 'mycoach.db')
console.log(`[DB] Using database at: ${dbPath}`)

const db = new Database(dbPath)

// Initialize database schema
db.exec(`
  CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT
  );

  CREATE TABLE IF NOT EXISTS synced_records (
    id TEXT PRIMARY KEY,
    intervals_data TEXT NOT NULL,
    local_record_id TEXT,
    synced_at INTEGER NOT NULL,
    start_date TEXT NOT NULL
  );

  CREATE INDEX IF NOT EXISTS idx_synced_records_start_date 
    ON synced_records(start_date);
  
  CREATE INDEX IF NOT EXISTS idx_synced_records_local_record_id
    ON synced_records(local_record_id);

  CREATE TABLE IF NOT EXISTS strava_synced_records (
    id TEXT PRIMARY KEY,
    strava_data TEXT NOT NULL,
    local_record_id TEXT,
    synced_at INTEGER NOT NULL,
    start_date TEXT NOT NULL
  );

  CREATE INDEX IF NOT EXISTS idx_strava_synced_records_start_date 
    ON strava_synced_records(start_date);
  
  CREATE INDEX IF NOT EXISTS idx_strava_synced_records_local_record_id
    ON strava_synced_records(local_record_id);
`)

// Settings operations
export function getSetting(key: string): string | null {
  const row = db.prepare('SELECT value FROM settings WHERE key = ?').get(key) as { value: string } | undefined
  return row?.value ?? null
}

export function setSetting(key: string, value: string): void {
  db.prepare('INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)').run(key, value)
}

export function deleteSetting(key: string): void {
  db.prepare('DELETE FROM settings WHERE key = ?').run(key)
}

export function getAllSettings(): Record<string, string> {
  const rows = db.prepare('SELECT key, value FROM settings').all() as { key: string; value: string }[]
  return Object.fromEntries(rows.map(r => [r.key, r.value]))
}

// Synced records operations
export interface SyncedRecord {
  id: string
  intervals_data: string
  local_record_id: string | null
  synced_at: number
  start_date: string
}

export function getSyncedRecord(id: string): SyncedRecord | null {
  return db.prepare('SELECT * FROM synced_records WHERE id = ?').get(id) as SyncedRecord | null
}

export function upsertSyncedRecord(record: Omit<SyncedRecord, 'local_record_id'> & { local_record_id?: string | null }): void {
  db.prepare(`
    INSERT OR REPLACE INTO synced_records (id, intervals_data, local_record_id, synced_at, start_date)
    VALUES (?, ?, ?, ?, ?)
  `).run(
    record.id,
    record.intervals_data,
    record.local_record_id ?? null,
    record.synced_at,
    record.start_date
  )
}

export function getAllSyncedRecords(): SyncedRecord[] {
  return db.prepare('SELECT * FROM synced_records ORDER BY start_date DESC').all() as SyncedRecord[]
}

export function getSyncedRecordsByDateRange(oldest: string, newest: string): SyncedRecord[] {
  return db.prepare(
    'SELECT * FROM synced_records WHERE start_date >= ? AND start_date <= ? ORDER BY start_date DESC'
  ).all(oldest, newest) as SyncedRecord[]
}

export function deleteSyncedRecord(id: string): void {
  db.prepare('DELETE FROM synced_records WHERE id = ?').run(id)
}

export function updateLocalRecordId(intervalsId: string, localRecordId: string | null): void {
  db.prepare('UPDATE synced_records SET local_record_id = ? WHERE id = ?').run(localRecordId, intervalsId)
}

export function clearLocalRecordId(intervalsId: string): void {
  db.prepare('UPDATE synced_records SET local_record_id = NULL WHERE id = ?').run(intervalsId)
}

export function getSyncedRecordByLocalId(localRecordId: string): SyncedRecord | null {
  return db.prepare('SELECT * FROM synced_records WHERE local_record_id = ?').get(localRecordId) as SyncedRecord | null
}

// Strava synced records operations
export interface StravaSyncedRecord {
  id: string
  strava_data: string
  local_record_id: string | null
  synced_at: number
  start_date: string
}

export function getStravaSyncedRecord(id: string): StravaSyncedRecord | null {
  return db.prepare('SELECT * FROM strava_synced_records WHERE id = ?').get(id) as StravaSyncedRecord | null
}

export function upsertStravaSyncedRecord(record: Omit<StravaSyncedRecord, 'local_record_id'> & { local_record_id?: string | null }): void {
  db.prepare(`
    INSERT OR REPLACE INTO strava_synced_records (id, strava_data, local_record_id, synced_at, start_date)
    VALUES (?, ?, ?, ?, ?)
  `).run(
    record.id,
    record.strava_data,
    record.local_record_id ?? null,
    record.synced_at,
    record.start_date
  )
}

export function getAllStravaSyncedRecords(): StravaSyncedRecord[] {
  return db.prepare('SELECT * FROM strava_synced_records ORDER BY start_date DESC').all() as StravaSyncedRecord[]
}

export function getStravaSyncedRecordsByDateRange(oldest: string, newest: string): StravaSyncedRecord[] {
  return db.prepare(
    'SELECT * FROM strava_synced_records WHERE start_date >= ? AND start_date <= ? ORDER BY start_date DESC'
  ).all(oldest, newest) as StravaSyncedRecord[]
}

export function deleteStravaSyncedRecord(id: string): void {
  db.prepare('DELETE FROM strava_synced_records WHERE id = ?').run(id)
}

export function updateStravaLocalRecordId(stravaId: string, localRecordId: string | null): void {
  db.prepare('UPDATE strava_synced_records SET local_record_id = ? WHERE id = ?').run(localRecordId, stravaId)
}

export function clearStravaLocalRecordId(stravaId: string): void {
  db.prepare('UPDATE strava_synced_records SET local_record_id = NULL WHERE id = ?').run(stravaId)
}

export function getStravaSyncedRecordByLocalId(localRecordId: string): StravaSyncedRecord | null {
  return db.prepare('SELECT * FROM strava_synced_records WHERE local_record_id = ?').get(localRecordId) as StravaSyncedRecord | null
}

export default db
