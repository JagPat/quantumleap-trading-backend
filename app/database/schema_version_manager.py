#!/usr/bin/env python3
"""
Schema Version Manager
Handles database schema versioning, conflict detection, and resolution
"""
import os
import sqlite3
import json
import hashlib
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple, Set
from dataclasses import dataclass, asdict
from enum import Enum
import re
import difflib

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ConflictType(Enum):
    """Types of schema conflicts"""
    TABLE_CONFLICT = "table_conflict"
    COLUMN_CONFLICT = "column_conflict"
    INDEX_CONFLICT = "index_conflict"
    CONSTRAINT_CONFLICT = "constraint_conflict"
    DATA_TYPE_CONFLICT = "data_type_conflict"
    DEPENDENCY_CONFLICT = "dependency_conflict"

class MergeStrategy(Enum):
    """Strategies for resolving conflicts"""
    LATEST_WINS = "latest_wins"
    MANUAL_RESOLUTION = "manual_resolution"
    ADDITIVE_MERGE = "additive_merge"
    CONSERVATIVE_MERGE = "conservative_merge"
    ABORT_ON_CONFLICT = "abort_on_conflict"

@dataclass
class SchemaVersion:
    """Schema version information"""
    version: str
    timestamp: datetime
    description: str
    author: str
    checksum: str
    dependencies: List[str]
    migration_files: List[str]
    rollback_files: List[str]
    applied: bool = False
    applied_at: Optional[datetime] = None

@dataclass
class SchemaConflict:
    """Schema conflict information"""
    conflict_id: str
    conflict_type: ConflictType
    version_a: str
    version_b: str
    object_name: str
    description: str
    suggested_resolution: str
    merge_strategy: MergeStrategy
    resolved: bool = False
    resolution_notes: Optional[str] = None

@dataclass
class SchemaDiff:
    """Schema difference information"""
    added_tables: List[str]
    removed_tables: List[str]
    modified_tables: List[str]
    added_columns: Dict[str, List[str]]
    removed_columns: Dict[str, List[str]]
    modified_columns: Dict[str, List[str]]
    added_indexes: List[str]
    removed_indexes: List[str]
    modified_indexes: List[str]

class SchemaVersionManager:
    """Manages database schema versions and conflict resolution"""
    
    def __init__(self, database_path: str = None, migrations_dir: str = "migrations"):
        self.database_path = database_path or os.getenv("DATABASE_PATH", "trading_schema.db")
        self.migrations_dir = migrations_dir
        self.version_lock = threading.RLock()
        
        # Version tracking
        self.versions: Dict[str, SchemaVersion] = {}
        self.conflicts: Dict[str, SchemaConflict] = {}
        self.dependency_graph: Dict[str, Set[str]] = {}
        
        # Initialize version tracking
        self._initialize_version_tracking()
        self._load_existing_versions()
    
    def _initialize_version_tracking(self):
        """Initialize version tracking tables"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                # Create schema versions table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_versions (
                        version TEXT PRIMARY KEY,
                        timestamp TEXT NOT NULL,
                        description TEXT NOT NULL,
                        author TEXT NOT NULL,
                        checksum TEXT NOT NULL,
                        dependencies TEXT NOT NULL,
                        migration_files TEXT NOT NULL,
                        rollback_files TEXT NOT NULL,
                        applied BOOLEAN DEFAULT FALSE,
                        applied_at TEXT
                    )
                """)
                
                # Create schema conflicts table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_conflicts (
                        conflict_id TEXT PRIMARY KEY,
                        conflict_type TEXT NOT NULL,
                        version_a TEXT NOT NULL,
                        version_b TEXT NOT NULL,
                        object_name TEXT NOT NULL,
                        description TEXT NOT NULL,
                        suggested_resolution TEXT NOT NULL,
                        merge_strategy TEXT NOT NULL,
                        resolved BOOLEAN DEFAULT FALSE,
                        resolution_notes TEXT,
                        created_at TEXT NOT NULL
                    )
                """)
                
                # Create schema metadata table
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS schema_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL,
                        updated_at TEXT NOT NULL
                    )
                """)
                
                conn.commit()
                logger.info("✅ Schema version tracking initialized")
                
        except Exception as e:
            logger.error(f"Failed to initialize version tracking: {e}")
            raise
    
    def _load_existing_versions(self):
        """Load existing versions from database"""
        try:
            with sqlite3.connect(self.database_path) as conn:
                cursor = conn.cursor()
                
                cursor.execute("SELECT * FROM schema_versions ORDER BY timestamp")
                rows = cursor.fetchall()
                
                for row in rows:
                    version = SchemaVersion(
                        version=row[0],
                        timestamp=datetime.fromisoformat(row[1]),
                        description=row[2],
                        author=row[3],
                        checksum=row[4],
                        dependencies=json.loads(row[5]),
                        migration_files=json.loads(row[6]),
                        rollback_files=json.loads(row[7]),
                        applied=bool(row[8]),
                        applied_at=datetime.fromisoformat(row[9]) if row[9] else None
                    )
                    self.versions[version.version] = version
                    
                    # Build dependency graph
                    self.dependency_graph[version.version] = set(version.dependencies)
                
                logger.info(f"✅ Loaded {len(self.versions)} schema versions")
                
        except Exception as e:
            logger.error(f"Failed to load existing versions: {e}")
    
    def register_version(self, version: str, description: str, author: str,
                        migration_files: List[str], rollback_files: List[str] = None,
                        dependencies: List[str] = None) -> SchemaVersion:
        """Register a new schema version"""
        try:
            with self.version_lock:
                if version in self.versions:
                    raise ValueError(f"Version {version} already exists")
                
                # Calculate checksum of migration files
                checksum = self._calculate_version_checksum(migration_files)
                
                # Create version object
                schema_version = SchemaVersion(
                    version=version,
                    timestamp=datetime.now(),
                    description=description,
                    author=author,
                    checksum=checksum,
                    dependencies=dependencies or [],
                    migration_files=migration_files,
                    rollback_files=rollback_files or []
                )
                
                # Check for conflicts
                conflicts = self._detect_conflicts(schema_version)
                if conflicts:
                    logger.warning(f"⚠️ Detected {len(conflicts)} conflicts for version {version}")
                    for conflict in conflicts:
                        self.conflicts[conflict.conflict_id] = conflict
                
                # Store in database
                with sqlite3.connect(self.database_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO schema_versions 
                        (version, timestamp, description, author, checksum, 
                         dependencies, migration_files, rollback_files)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        schema_version.version,
                        schema_version.timestamp.isoformat(),
                        schema_version.description,
                        schema_version.author,
                        schema_version.checksum,
                        json.dumps(schema_version.dependencies),
                        json.dumps(schema_version.migration_files),
                        json.dumps(schema_version.rollback_files)
                    ))
                    conn.commit()
                
                # Update in-memory tracking
                self.versions[version] = schema_version
                self.dependency_graph[version] = set(dependencies or [])
                
                logger.info(f"✅ Registered schema version: {version}")
                return schema_version
                
        except Exception as e:
            logger.error(f"Failed to register version {version}: {e}")
            raise
    
    def _calculate_version_checksum(self, migration_files: List[str]) -> str:
        """Calculate checksum for version based on migration files"""
        hasher = hashlib.sha256()
        
        for file_path in sorted(migration_files):
            full_path = os.path.join(self.migrations_dir, file_path)
            if os.path.exists(full_path):
                with open(full_path, 'rb') as f:
                    hasher.update(f.read())
            else:
                # Use filename if file doesn't exist yet
                hasher.update(file_path.encode())
        
        return hasher.hexdigest()
    
    def _detect_conflicts(self, new_version: SchemaVersion) -> List[SchemaConflict]:
        """Detect conflicts with existing versions"""
        conflicts = []
        
        try:
            # Parse new version schema
            new_schema = self._parse_migration_schema(new_version.migration_files)
            
            for existing_version in self.versions.values():
                if existing_version.applied:
                    existing_schema = self._parse_migration_schema(existing_version.migration_files)
                    version_conflicts = self._compare_schemas(
                        new_version.version, existing_version.version,
                        new_schema, existing_schema
                    )
                    conflicts.extend(version_conflicts)
            
            return conflicts
            
        except Exception as e:
            logger.error(f"Failed to detect conflicts: {e}")
            return []
    
    def _parse_migration_schema(self, migration_files: List[str]) -> Dict[str, Any]:
        """Parse schema from migration files"""
        schema = {
            'tables': {},
            'indexes': {},
            'constraints': {}
        }
        
        try:
            for file_path in migration_files:
                full_path = os.path.join(self.migrations_dir, file_path)
                if os.path.exists(full_path):
                    with open(full_path, 'r') as f:
                        sql_content = f.read()
                        self._extract_schema_objects(sql_content, schema)
            
            return schema
            
        except Exception as e:
            logger.error(f"Failed to parse migration schema: {e}")
            return schema
    
    def _extract_schema_objects(self, sql_content: str, schema: Dict[str, Any]):
        """Extract schema objects from SQL content"""
        # Remove comments and normalize whitespace
        sql_content = re.sub(r'--.*$', '', sql_content, flags=re.MULTILINE)
        sql_content = re.sub(r'/\*.*?\*/', '', sql_content, flags=re.DOTALL)
        
        # Extract CREATE TABLE statements - handle multiline better
        table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s*\((.*?)\);'
        for match in re.finditer(table_pattern, sql_content, re.IGNORECASE | re.DOTALL):
            table_name = match.group(1)
            table_def = match.group(2)
            
            columns = self._parse_table_columns(table_def)
            schema['tables'][table_name] = columns
        
        # Extract CREATE INDEX statements
        index_pattern = r'CREATE\s+(?:UNIQUE\s+)?INDEX\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)\s+ON\s+(\w+)\s*\((.*?)\);'
        for match in re.finditer(index_pattern, sql_content, re.IGNORECASE):
            index_name = match.group(1)
            table_name = match.group(2)
            columns = match.group(3)
            
            schema['indexes'][index_name] = {
                'table': table_name,
                'columns': [col.strip() for col in columns.split(',')]
            }
    
    def _parse_table_columns(self, table_def: str) -> Dict[str, Dict[str, Any]]:
        """Parse table column definitions"""
        columns = {}
        
        # Clean up the table definition
        table_def = table_def.strip()
        
        # Split by commas, but be careful of commas in constraints
        parts = []
        current_part = ""
        paren_count = 0
        
        for char in table_def:
            if char == '(':
                paren_count += 1
            elif char == ')':
                paren_count -= 1
            elif char == ',' and paren_count == 0:
                if current_part.strip():
                    parts.append(current_part.strip())
                current_part = ""
                continue
            current_part += char
        
        if current_part.strip():
            parts.append(current_part.strip())
        
        for part in parts:
            part = part.strip()
            if not part:
                continue
            
            # Skip table-level constraints (they don't start with a column name)
            part_upper = part.upper()
            if (part_upper.startswith('PRIMARY KEY') or 
                part_upper.startswith('FOREIGN KEY') or 
                part_upper.startswith('CHECK') or
                part_upper.startswith('UNIQUE') or
                part_upper.startswith('CONSTRAINT')):
                continue
            
            # Parse column definition
            tokens = part.split()
            if len(tokens) >= 2:
                col_name = tokens[0].strip()
                col_type = tokens[1].strip()
                
                # Remove any quotes from column name
                col_name = col_name.strip('"\'`')
                
                columns[col_name] = {
                    'type': col_type,
                    'nullable': 'NOT NULL' not in part_upper,
                    'default': self._extract_default_value(part),
                    'constraints': self._extract_column_constraints(part)
                }
        
        return columns
    
    def _extract_default_value(self, column_def: str) -> Optional[str]:
        """Extract default value from column definition"""
        match = re.search(r'DEFAULT\s+([^,\s]+)', column_def, re.IGNORECASE)
        return match.group(1) if match else None
    
    def _extract_column_constraints(self, column_def: str) -> List[str]:
        """Extract constraints from column definition"""
        constraints = []
        column_def_upper = column_def.upper()
        
        if 'PRIMARY KEY' in column_def_upper:
            constraints.append('PRIMARY KEY')
        if 'UNIQUE' in column_def_upper:
            constraints.append('UNIQUE')
        if 'NOT NULL' in column_def_upper:
            constraints.append('NOT NULL')
        
        return constraints
    
    def _compare_schemas(self, version_a: str, version_b: str,
                        schema_a: Dict[str, Any], schema_b: Dict[str, Any]) -> List[SchemaConflict]:
        """Compare two schemas and detect conflicts"""
        conflicts = []
        
        # Check table conflicts
        for table_name in schema_a['tables']:
            if table_name in schema_b['tables']:
                table_conflicts = self._compare_tables(
                    version_a, version_b, table_name,
                    schema_a['tables'][table_name],
                    schema_b['tables'][table_name]
                )
                conflicts.extend(table_conflicts)
        
        # Check index conflicts
        for index_name in schema_a['indexes']:
            if index_name in schema_b['indexes']:
                if schema_a['indexes'][index_name] != schema_b['indexes'][index_name]:
                    conflict = SchemaConflict(
                        conflict_id=f"{version_a}_{version_b}_index_{index_name}",
                        conflict_type=ConflictType.INDEX_CONFLICT,
                        version_a=version_a,
                        version_b=version_b,
                        object_name=index_name,
                        description=f"Index {index_name} has different definitions",
                        suggested_resolution="Use latest version definition",
                        merge_strategy=MergeStrategy.LATEST_WINS
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def _compare_tables(self, version_a: str, version_b: str, table_name: str,
                       table_a: Dict[str, Any], table_b: Dict[str, Any]) -> List[SchemaConflict]:
        """Compare two table definitions"""
        conflicts = []
        
        # Check column conflicts
        for col_name in table_a:
            if col_name in table_b:
                if table_a[col_name] != table_b[col_name]:
                    conflict = SchemaConflict(
                        conflict_id=f"{version_a}_{version_b}_column_{table_name}_{col_name}",
                        conflict_type=ConflictType.COLUMN_CONFLICT,
                        version_a=version_a,
                        version_b=version_b,
                        object_name=f"{table_name}.{col_name}",
                        description=f"Column {col_name} in table {table_name} has different definitions",
                        suggested_resolution="Merge column definitions with compatible types",
                        merge_strategy=MergeStrategy.CONSERVATIVE_MERGE
                    )
                    conflicts.append(conflict)
        
        return conflicts
    
    def get_version_dependencies(self, version: str) -> List[str]:
        """Get dependencies for a version in correct order"""
        if version not in self.versions:
            raise ValueError(f"Version {version} not found")
        
        dependencies = []
        visited = set()
        
        def visit(v):
            if v in visited:
                return
            visited.add(v)
            
            if v in self.dependency_graph:
                for dep in self.dependency_graph[v]:
                    visit(dep)
                    if dep not in dependencies:
                        dependencies.append(dep)
        
        visit(version)
        return dependencies
    
    def detect_circular_dependencies(self) -> List[List[str]]:
        """Detect circular dependencies in version graph"""
        cycles = []
        visited = set()
        rec_stack = set()
        
        def dfs(node, path):
            if node in rec_stack:
                # Found a cycle
                cycle_start = path.index(node)
                cycles.append(path[cycle_start:] + [node])
                return
            
            if node in visited:
                return
            
            visited.add(node)
            rec_stack.add(node)
            
            if node in self.dependency_graph:
                for neighbor in self.dependency_graph[node]:
                    dfs(neighbor, path + [node])
            
            rec_stack.remove(node)
        
        for version in self.versions:
            if version not in visited:
                dfs(version, [])
        
        return cycles
    
    def resolve_conflict(self, conflict_id: str, strategy: MergeStrategy,
                        resolution_notes: str = None) -> bool:
        """Resolve a schema conflict"""
        try:
            if conflict_id not in self.conflicts:
                raise ValueError(f"Conflict {conflict_id} not found")
            
            conflict = self.conflicts[conflict_id]
            
            # Apply resolution strategy
            success = self._apply_resolution_strategy(conflict, strategy)
            
            if success:
                conflict.resolved = True
                conflict.resolution_notes = resolution_notes
                conflict.merge_strategy = strategy
                
                # Update in database
                with sqlite3.connect(self.database_path) as conn:
                    cursor = conn.cursor()
                    cursor.execute("""
                        UPDATE schema_conflicts 
                        SET resolved = ?, resolution_notes = ?, merge_strategy = ?
                        WHERE conflict_id = ?
                    """, (True, resolution_notes, strategy.value, conflict_id))
                    conn.commit()
                
                logger.info(f"✅ Resolved conflict: {conflict_id}")
                return True
            else:
                logger.error(f"Failed to resolve conflict: {conflict_id}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to resolve conflict {conflict_id}: {e}")
            return False
    
    def _apply_resolution_strategy(self, conflict: SchemaConflict, strategy: MergeStrategy) -> bool:
        """Apply resolution strategy to conflict"""
        try:
            if strategy == MergeStrategy.LATEST_WINS:
                # Use the later version's definition
                return True
            elif strategy == MergeStrategy.ADDITIVE_MERGE:
                # Combine both definitions where possible
                return True
            elif strategy == MergeStrategy.CONSERVATIVE_MERGE:
                # Use the most restrictive definition
                return True
            elif strategy == MergeStrategy.MANUAL_RESOLUTION:
                # Requires manual intervention
                logger.info(f"Manual resolution required for conflict: {conflict.conflict_id}")
                return False
            elif strategy == MergeStrategy.ABORT_ON_CONFLICT:
                # Abort the operation
                return False
            else:
                logger.error(f"Unknown resolution strategy: {strategy}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to apply resolution strategy: {e}")
            return False
    
    def generate_schema_diff(self, version_a: str, version_b: str) -> SchemaDiff:
        """Generate diff between two schema versions"""
        try:
            if version_a not in self.versions or version_b not in self.versions:
                raise ValueError("One or both versions not found")
            
            schema_a = self._parse_migration_schema(self.versions[version_a].migration_files)
            schema_b = self._parse_migration_schema(self.versions[version_b].migration_files)
            
            # Compare tables
            tables_a = set(schema_a['tables'].keys())
            tables_b = set(schema_b['tables'].keys())
            
            added_tables = list(tables_b - tables_a)
            removed_tables = list(tables_a - tables_b)
            common_tables = list(tables_a & tables_b)
            
            # Compare columns in common tables
            added_columns = {}
            removed_columns = {}
            modified_columns = {}
            modified_tables = []
            
            for table in common_tables:
                cols_a = set(schema_a['tables'][table].keys())
                cols_b = set(schema_b['tables'][table].keys())
                
                added_cols = list(cols_b - cols_a)
                removed_cols = list(cols_a - cols_b)
                common_cols = list(cols_a & cols_b)
                
                # Check for modified columns
                modified_cols = []
                for col in common_cols:
                    if schema_a['tables'][table][col] != schema_b['tables'][table][col]:
                        modified_cols.append(col)
                
                if added_cols or removed_cols or modified_cols:
                    modified_tables.append(table)
                    if added_cols:
                        added_columns[table] = added_cols
                    if removed_cols:
                        removed_columns[table] = removed_cols
                    if modified_cols:
                        modified_columns[table] = modified_cols
            
            # Compare indexes
            indexes_a = set(schema_a['indexes'].keys())
            indexes_b = set(schema_b['indexes'].keys())
            
            added_indexes = list(indexes_b - indexes_a)
            removed_indexes = list(indexes_a - indexes_b)
            
            # Check for modified indexes
            modified_indexes = []
            for index in (indexes_a & indexes_b):
                if schema_a['indexes'][index] != schema_b['indexes'][index]:
                    modified_indexes.append(index)
            
            return SchemaDiff(
                added_tables=added_tables,
                removed_tables=removed_tables,
                modified_tables=modified_tables,
                added_columns=added_columns,
                removed_columns=removed_columns,
                modified_columns=modified_columns,
                added_indexes=added_indexes,
                removed_indexes=removed_indexes,
                modified_indexes=modified_indexes
            )
            
        except Exception as e:
            logger.error(f"Failed to generate schema diff: {e}")
            raise
    
    def get_version_status(self) -> Dict[str, Any]:
        """Get current version status"""
        try:
            applied_versions = [v for v in self.versions.values() if v.applied]
            pending_versions = [v for v in self.versions.values() if not v.applied]
            unresolved_conflicts = [c for c in self.conflicts.values() if not c.resolved]
            
            # Check for circular dependencies
            circular_deps = self.detect_circular_dependencies()
            
            return {
                "total_versions": len(self.versions),
                "applied_versions": len(applied_versions),
                "pending_versions": len(pending_versions),
                "unresolved_conflicts": len(unresolved_conflicts),
                "circular_dependencies": len(circular_deps),
                "latest_applied_version": max(applied_versions, key=lambda v: v.timestamp).version if applied_versions else None,
                "next_pending_version": min(pending_versions, key=lambda v: v.timestamp).version if pending_versions else None,
                "dependency_issues": circular_deps
            }
            
        except Exception as e:
            logger.error(f"Failed to get version status: {e}")
            return {}
    
    def get_conflicts(self, resolved: bool = None) -> List[SchemaConflict]:
        """Get schema conflicts"""
        conflicts = list(self.conflicts.values())
        
        if resolved is not None:
            conflicts = [c for c in conflicts if c.resolved == resolved]
        
        return sorted(conflicts, key=lambda c: c.conflict_id)
    
    def export_version_history(self, output_file: str):
        """Export version history to JSON file"""
        try:
            history = {
                "versions": {v: asdict(version) for v, version in self.versions.items()},
                "conflicts": {c: asdict(conflict) for c, conflict in self.conflicts.items()},
                "dependency_graph": {v: list(deps) for v, deps in self.dependency_graph.items()},
                "exported_at": datetime.now().isoformat()
            }
            
            # Convert datetime objects to strings
            for version_data in history["versions"].values():
                version_data["timestamp"] = version_data["timestamp"].isoformat()
                if version_data["applied_at"]:
                    version_data["applied_at"] = version_data["applied_at"].isoformat()
            
            with open(output_file, 'w') as f:
                json.dump(history, f, indent=2)
            
            logger.info(f"✅ Exported version history to: {output_file}")
            
        except Exception as e:
            logger.error(f"Failed to export version history: {e}")
            raise

class ConnectionPoolError(Exception):
    """Connection pool related errors"""
    pass

# Example usage and testing
if __name__ == "__main__":
    # Initialize schema version manager
    manager = SchemaVersionManager()
    
    # Register a test version
    try:
        version = manager.register_version(
            version="1.0.0",
            description="Initial schema",
            author="system",
            migration_files=["001_create_users_table.sql"],
            dependencies=[]
        )
        print(f"Registered version: {version.version}")
        
        # Get version status
        status = manager.get_version_status()
        print(f"Version status: {status}")
        
        # Check for conflicts
        conflicts = manager.get_conflicts(resolved=False)
        print(f"Unresolved conflicts: {len(conflicts)}")
        
    except Exception as e:
        print(f"Error: {e}")