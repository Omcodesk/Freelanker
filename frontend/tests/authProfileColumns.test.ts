import assert from 'node:assert/strict';
import fs from 'node:fs';
import path from 'node:path';
import test from 'node:test';
import { fileURLToPath } from 'node:url';

const __filename = fileURLToPath(import.meta.url);
const __dirname = path.dirname(__filename);
const repoRoot = path.resolve(__dirname, '../..');
const authContextPath = path.join(repoRoot, 'frontend/src/features/auth/AuthContext.tsx');
const schemaMigrationPath = path.join(repoRoot, 'database/migrations/001_initial_schema.sql');
const frontendSrcDir = path.join(repoRoot, 'frontend/src');

const EXPECTED_SAFE_COLUMNS = [
  'id',
  'display_name',
  'headline',
  'bio',
  'avatar_url',
  'skills',
  'portfolio_links',
  'is_available',
  'created_at',
  'updated_at',
] as const;

function parseSafeProfileColumns(source: string): string[] {
  const match = source.match(/export\s+const\s+SAFE_PROFILE_COLUMNS\s*=\s*\n?\s*['"`]([^'"`]+)['"`]/);
  assert.ok(match, 'SAFE_PROFILE_COLUMNS export constant must exist in AuthContext.tsx');
  return match[1]
    .split(',')
    .map((col) => col.trim())
    .filter(Boolean);
}

function parseGrantedProfileSelectColumns(sql: string): string[] {
  const match = sql.match(
    /GRANT\s+SELECT\s*\(([\s\S]*?)\)\s*ON\s+TABLE\s+public\.profiles\s+TO\s+authenticated\s*;/i
  );
  assert.ok(match, 'Column-level GRANT SELECT on public.profiles TO authenticated must exist in migration');
  return match[1]
    .split(',')
    .map((col) => col.trim())
    .filter(Boolean);
}

function listTsFiles(dir: string): string[] {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  const files: string[] = [];
  for (const entry of entries) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...listTsFiles(fullPath));
    } else if (/\.(ts|tsx)$/.test(entry.name)) {
      files.push(fullPath);
    }
  }
  return files;
}

test('AuthContext exports SAFE_PROFILE_COLUMNS matching authenticated DB column grants', () => {
  const authSource = fs.readFileSync(authContextPath, 'utf8');
  const migrationSql = fs.readFileSync(schemaMigrationPath, 'utf8');

  const selectedColumns = parseSafeProfileColumns(authSource);
  const grantedColumns = parseGrantedProfileSelectColumns(migrationSql);

  assert.deepEqual(selectedColumns, [...EXPECTED_SAFE_COLUMNS]);
  assert.deepEqual([...selectedColumns].sort(), [...grantedColumns].sort());
  assert.equal(selectedColumns.includes('is_admin'), false);
});

test('AuthContext queries profiles using SAFE_PROFILE_COLUMNS without wildcard or is_admin', () => {
  const authSource = fs.readFileSync(authContextPath, 'utf8');

  assert.match(authSource, /\.from\(\s*['"]profiles['"]\s*\)\s*\.select\(\s*SAFE_PROFILE_COLUMNS\s*\)/);
  assert.doesNotMatch(authSource, /\.from\(\s*['"]profiles['"]\s*\)[\s\S]{0,120}\.select\(\s*['"]\*['"]\s*\)/);
  assert.doesNotMatch(authSource, /\bis_admin\b/);
});

test('No frontend source file runs a wildcard select or selects is_admin on profiles', () => {
  const files = listTsFiles(frontendSrcDir);
  assert.ok(files.length > 0, 'Expected frontend TypeScript files');

  for (const file of files) {
    const content = fs.readFileSync(file, 'utf8');
    const relPath = path.relative(repoRoot, file);
    assert.doesNotMatch(
      content,
      /\.from\(\s*['"]profiles['"]\s*\)[\s\S]{0,120}\.select\(\s*['"]\*['"]\s*\)/,
      `Wildcard profile select found in ${relPath}`
    );
    assert.doesNotMatch(
      content,
      /\bis_admin\b/,
      `Restricted column is_admin referenced in ${relPath}`
    );
  }
});

