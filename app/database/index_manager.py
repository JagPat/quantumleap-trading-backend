"""
Intelligent Index Management System for Railway Trading Platform

Automated index analysis, creation, and optimization based on query patterns
and performance metrics with Railway-specific optimizations.
"""

import os
import re
import time
import logging
import hashlib
from typing import Dict, Any, List, Optional, Set, Tuple
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict, Counter
import json

logger = logging.getLogger(__name__)

@dataclass
class IndexAnalysis:
    """Analysis of an existing or potential index"""
    table_name: str
    columns: List[str]
    index_type: str  # 'btree', 'hash', 'unique', 'composite'
    usage_frequency: int
    performance_impact: float  # 0.0 to 1.0
    size_estimate_mb: float
    creation_cost: float  # 0.0 to 1.0
    maintenance_cost: float  # 0.0 to 1.0
    recommendation_score: float  # 0.0 to 1.0
    query_patterns: List[str]
    created_at: datetime
    last_analyzed: datetime

@dataclass
class IndexUsageStats:
    """Statistics for index usage"""
    index_name: str
    table_name: str
    columns: List[str]
    scan_count: int
    seek_count: int
    update_count: int
    last_used: Optional[datetime]
    efficiency_score: float  # 0.0 to 1.0
    
@dataclass
class TableAnalysis:
    """Analysis of table structure and query patterns"""
    table_name: str
    row_count_estimate: int
    column_stats: Dict[str, Dict[str, Any]]
    query_patterns: List[str]
    frequent_where_columns: List[str]
    frequent_join_columns: List[str]
    frequent_order_columns: List[str]
    missing_indexes: List[str]
    redundant_indexes: List[str]
    optimization_opportunities: List[str]class I
ntelligentIndexManager:
    """Intelligent index management system for Railway deployment"""
    
    def __init__(self, database_manager=None):
        self.database_manager = database_manager
        self.index_analyses = {}
        self.table_analyses = {}
        self.usage_stats = {}
        self.query_patterns = defaultdict(list)
        self.performance_history = defaultdict(list)
        
        # Railway-specific settings
        self.is_postgresql = self._detect_postgresql()
        self.max_index_size_mb = 100 if self.is_postgresql else 50  # Railway limits
        self.max_indexes_per_table = 10
        
        # Index creation templates
        self.index_templates = self._initialize_index_templates()
        
        logger.info("🔍 Intelligent index manager initialized for Railway")
    
    def _detect_postgresql(self) -> bool:
        """Detect if we're using PostgreSQL (Railway production)"""
        if self.database_manager:
            return getattr(self.database_manager, 'is_postgresql', False)
        
        database_url = os.getenv('DATABASE_URL', '')
        return database_url.startswith(('postgresql://', 'postgres://'))
    
    def _initialize_index_templates(self) -> Dict[str, Dict[str, Any]]:
        """Initialize index creation templates for different scenarios"""
        return {
            'equality_where': {
                'type': 'btree',
                'priority': 0.8,
                'description': 'Index for equality conditions in WHERE clauses'
            },
            'range_where': {
                'type': 'btree',
                'priority': 0.7,
                'description': 'Index for range conditions in WHERE clauses'
            },
            'join_condition': {
                'type': 'btree',
                'priority': 0.9,
                'description': 'Index for JOIN conditions between tables'
            },
            'order_by': {
                'type': 'btree',
                'priority': 0.6,
                'description': 'Index for ORDER BY clauses'
            },
            'composite': {
                'type': 'btree',
                'priority': 0.8,
                'description': 'Composite index for multiple column conditions'
            },
            'unique_constraint': {
                'type': 'unique',
                'priority': 1.0,
                'description': 'Unique index for data integrity'
            }
        }
    
    def analyze_query_for_indexes(self, query: str, execution_time_ms: float = 0):
        """Analyze a query to identify potential index opportunities"""
        try:
            query_hash = hashlib.md5(query.encode()).hexdigest()
            
            # Extract query components
            tables = self._extract_tables_from_query(query)
            where_conditions = self._extract_where_conditions(query)
            join_conditions = self._extract_join_conditions(query)
            order_by_columns = self._extract_order_by_columns(query)
            
            # Record query pattern
            self.query_patterns[query_hash].append({
                'query': query,
                'execution_time_ms': execution_time_ms,
                'timestamp': datetime.now(),
                'tables': tables,
                'where_conditions': where_conditions,
                'join_conditions': join_conditions,
                'order_by_columns': order_by_columns
            })
            
            # Analyze each table involved
            for table in tables:
                self._analyze_table_usage(table, query, where_conditions, 
                                        join_conditions, order_by_columns)
            
            # Generate index recommendations
            recommendations = self._generate_index_recommendations(
                tables, where_conditions, join_conditions, order_by_columns
            )
            
            return recommendations
            
        except Exception as e:
            logger.error(f"Error analyzing query for indexes: {e}")
            return []
    
    def _extract_tables_from_query(self, query: str) -> List[str]:
        """Extract table names from SQL query"""
        tables = []
        
        # FROM clause
        from_match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        if from_match:
            tables.append(from_match.group(1).lower())
        
        # JOIN clauses
        join_matches = re.findall(r'JOIN\s+(\w+)', query, re.IGNORECASE)
        tables.extend([t.lower() for t in join_matches])
        
        # INSERT INTO
        insert_match = re.search(r'INSERT\s+INTO\s+(\w+)', query, re.IGNORECASE)
        if insert_match:
            tables.append(insert_match.group(1).lower())
        
        # UPDATE
        update_match = re.search(r'UPDATE\s+(\w+)', query, re.IGNORECASE)
        if update_match:
            tables.append(update_match.group(1).lower())
        
        return list(set(tables))
    
    def _extract_where_conditions(self, query: str) -> List[Dict[str, str]]:
        """Extract WHERE conditions with column and operator info"""
        conditions = []
        
        where_match = re.search(r'WHERE\s+(.*?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|$)', 
                               query, re.IGNORECASE | re.DOTALL)
        if not where_match:
            return conditions
        
        where_clause = where_match.group(1).strip()
        
        # Simple condition patterns
        patterns = [
            (r'(\w+)\s*=\s*', 'equality'),
            (r'(\w+)\s*>\s*', 'greater_than'),
            (r'(\w+)\s*<\s*', 'less_than'),
            (r'(\w+)\s*>=\s*', 'greater_equal'),
            (r'(\w+)\s*<=\s*', 'less_equal'),
            (r'(\w+)\s+LIKE\s+', 'like'),
            (r'(\w+)\s+IN\s*\(', 'in_list')
        ]
        
        for pattern, operator in patterns:
            matches = re.findall(pattern, where_clause, re.IGNORECASE)
            for column in matches:
                conditions.append({
                    'column': column.lower(),
                    'operator': operator,
                    'indexable': operator in ['equality', 'greater_than', 'less_than', 
                                            'greater_equal', 'less_equal', 'in_list']
                })
        
        return conditions    def
 _extract_join_conditions(self, query: str) -> List[Dict[str, str]]:
        """Extract JOIN conditions"""
        conditions = []
        
        join_pattern = r'JOIN\s+(\w+)\s+(?:\w+\s+)?ON\s+(.*?)(?=\s+(?:INNER|LEFT|RIGHT|FULL)?\s*JOIN|\s+WHERE|\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|$)'
        
        for match in re.finditer(join_pattern, query, re.IGNORECASE | re.DOTALL):
            table = match.group(1).lower()
            condition = match.group(2).strip()
            
            # Parse join condition (simplified)
            if '=' in condition:
                parts = condition.split('=')
                if len(parts) == 2:
                    left_col = parts[0].strip()
                    right_col = parts[1].strip()
                    
                    conditions.append({
                        'table': table,
                        'condition': condition,
                        'left_column': left_col,
                        'right_column': right_col,
                        'indexable': True
                    })
        
        return conditions
    
    def _extract_order_by_columns(self, query: str) -> List[str]:
        """Extract ORDER BY columns"""
        order_match = re.search(r'ORDER\s+BY\s+(.*?)(?:\s+LIMIT|$)', 
                               query, re.IGNORECASE | re.DOTALL)
        if not order_match:
            return []
        
        order_clause = order_match.group(1).strip()
        columns = []
        
        for col in order_clause.split(','):
            col = col.strip()
            # Remove ASC/DESC
            col = re.sub(r'\s+(ASC|DESC)$', '', col, flags=re.IGNORECASE)
            # Remove table prefix if present
            if '.' in col:
                col = col.split('.')[1]
            columns.append(col.lower())
        
        return columns
    
    def _analyze_table_usage(self, table: str, query: str, where_conditions: List[Dict],
                           join_conditions: List[Dict], order_by_columns: List[str]):
        """Analyze how a table is being used in queries"""
        if table not in self.table_analyses:
            self.table_analyses[table] = TableAnalysis(
                table_name=table,
                row_count_estimate=0,
                column_stats={},
                query_patterns=[],
                frequent_where_columns=[],
                frequent_join_columns=[],
                frequent_order_columns=[],
                missing_indexes=[],
                redundant_indexes=[],
                optimization_opportunities=[]
            )
        
        analysis = self.table_analyses[table]
        
        # Update query patterns
        analysis.query_patterns.append(query)
        
        # Track column usage
        for condition in where_conditions:
            analysis.frequent_where_columns.append(condition['column'])
        
        for condition in join_conditions:
            if condition.get('left_column'):
                analysis.frequent_join_columns.append(condition['left_column'])
            if condition.get('right_column'):
                analysis.frequent_join_columns.append(condition['right_column'])
        
        analysis.frequent_order_columns.extend(order_by_columns)
    
    def _generate_index_recommendations(self, tables: List[str], where_conditions: List[Dict],
                                      join_conditions: List[Dict], order_by_columns: List[str]) -> List[IndexAnalysis]:
        """Generate index recommendations based on query analysis"""
        recommendations = []
        
        for table in tables:
            # WHERE clause indexes
            for condition in where_conditions:
                if condition['indexable']:
                    rec = self._create_index_recommendation(
                        table, [condition['column']], 'equality_where',
                        f"Index for WHERE {condition['column']} {condition['operator']}"
                    )
                    recommendations.append(rec)
            
            # JOIN indexes
            for condition in join_conditions:
                if condition['indexable']:
                    # Index on left side of join
                    if condition.get('left_column'):
                        rec = self._create_index_recommendation(
                            table, [condition['left_column']], 'join_condition',
                            f"Index for JOIN on {condition['left_column']}"
                        )
                        recommendations.append(rec)
            
            # ORDER BY indexes
            if order_by_columns:
                rec = self._create_index_recommendation(
                    table, order_by_columns, 'order_by',
                    f"Index for ORDER BY {', '.join(order_by_columns)}"
                )
                recommendations.append(rec)
        
        # Remove duplicates and score recommendations
        unique_recommendations = self._deduplicate_recommendations(recommendations)
        scored_recommendations = self._score_recommendations(unique_recommendations)
        
        return scored_recommendations
    
    def _create_index_recommendation(self, table: str, columns: List[str], 
                                   template_key: str, description: str) -> IndexAnalysis:
        """Create an index recommendation"""
        template = self.index_templates.get(template_key, self.index_templates['equality_where'])
        
        return IndexAnalysis(
            table_name=table,
            columns=columns,
            index_type=template['type'],
            usage_frequency=1,
            performance_impact=template['priority'],
            size_estimate_mb=self._estimate_index_size(table, columns),
            creation_cost=0.3,  # Default creation cost
            maintenance_cost=0.1,  # Default maintenance cost
            recommendation_score=template['priority'],
            query_patterns=[],
            created_at=datetime.now(),
            last_analyzed=datetime.now()
        )
    
    def _estimate_index_size(self, table: str, columns: List[str]) -> float:
        """Estimate index size in MB"""
        # Simplified estimation
        base_size = 1.0  # 1MB base
        column_factor = len(columns) * 0.5
        
        # Try to get actual table stats if available
        if self.database_manager:
            try:
                if self.is_postgresql:
                    # PostgreSQL size estimation
                    result = self.database_manager.execute_query(
                        "SELECT pg_total_relation_size($1) as size", (table,)
                    )
                    if result:
                        table_size_bytes = result[0].get('size', 0)
                        # Index is typically 10-30% of table size
                        estimated_size = (table_size_bytes * 0.2) / (1024 * 1024)
                        return max(base_size, estimated_size)
                else:
                    # SQLite size estimation
                    result = self.database_manager.execute_query(
                        f"SELECT COUNT(*) as row_count FROM {table}"
                    )
                    if result:
                        row_count = result[0].get('row_count', 0)
                        # Rough estimation: 50 bytes per row per column
                        estimated_size = (row_count * len(columns) * 50) / (1024 * 1024)
                        return max(base_size, estimated_size)
            except Exception as e:
                logger.debug(f"Could not estimate size for {table}: {e}")
        
        return base_size + column_factor
    
    def _deduplicate_recommendations(self, recommendations: List[IndexAnalysis]) -> List[IndexAnalysis]:
        """Remove duplicate index recommendations"""
        seen = set()
        unique_recs = []
        
        for rec in recommendations:
            # Create a key based on table and columns
            key = (rec.table_name, tuple(sorted(rec.columns)))
            
            if key not in seen:
                seen.add(key)
                unique_recs.append(rec)
            else:
                # Merge with existing recommendation
                for existing in unique_recs:
                    if (existing.table_name == rec.table_name and 
                        tuple(sorted(existing.columns)) == tuple(sorted(rec.columns))):
                        existing.usage_frequency += rec.usage_frequency
                        existing.performance_impact = max(existing.performance_impact, rec.performance_impact)
                        break
        
        return unique_recs
    
    def _score_recommendations(self, recommendations: List[IndexAnalysis]) -> List[IndexAnalysis]:
        """Score and rank index recommendations"""
        for rec in recommendations:
            # Calculate recommendation score based on multiple factors
            usage_score = min(rec.usage_frequency / 10.0, 1.0)  # Normalize usage
            impact_score = rec.performance_impact
            size_penalty = max(0, (rec.size_estimate_mb - 10) / 100)  # Penalty for large indexes
            cost_penalty = (rec.creation_cost + rec.maintenance_cost) / 2
            
            # Final score (0.0 to 1.0)
            rec.recommendation_score = max(0, 
                (usage_score * 0.3 + impact_score * 0.5 - size_penalty * 0.1 - cost_penalty * 0.1)
            )
        
        # Sort by recommendation score
        recommendations.sort(key=lambda x: x.recommendation_score, reverse=True)
        
        return recommendations 
   def get_existing_indexes(self, table_name: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get information about existing indexes"""
        if not self.database_manager:
            return []
        
        try:
            if self.is_postgresql:
                # PostgreSQL index query
                if table_name:
                    query = """
                        SELECT schemaname, tablename, indexname, indexdef
                        FROM pg_indexes 
                        WHERE tablename = $1
                        ORDER BY tablename, indexname
                    """
                    params = (table_name,)
                else:
                    query = """
                        SELECT schemaname, tablename, indexname, indexdef
                        FROM pg_indexes 
                        WHERE schemaname = 'public'
                        ORDER BY tablename, indexname
                    """
                    params = ()
                
                result = self.database_manager.execute_query(query, params)
                
                indexes = []
                for row in result:
                    indexes.append({
                        'table_name': row['tablename'],
                        'index_name': row['indexname'],
                        'definition': row['indexdef'],
                        'columns': self._parse_index_columns(row['indexdef']),
                        'type': self._determine_index_type(row['indexdef'])
                    })
                
                return indexes
            
            else:
                # SQLite index query
                if table_name:
                    query = f"PRAGMA index_list({table_name})"
                    result = self.database_manager.execute_query(query)
                    
                    indexes = []
                    for row in result:
                        index_name = row['name']
                        # Get index info
                        info_query = f"PRAGMA index_info({index_name})"
                        info_result = self.database_manager.execute_query(info_query)
                        
                        columns = [col['name'] for col in info_result]
                        
                        indexes.append({
                            'table_name': table_name,
                            'index_name': index_name,
                            'columns': columns,
                            'unique': bool(row['unique']),
                            'type': 'unique' if row['unique'] else 'btree'
                        })
                    
                    return indexes
                else:
                    # Get all tables first, then their indexes
                    tables_query = "SELECT name FROM sqlite_master WHERE type='table'"
                    tables_result = self.database_manager.execute_query(tables_query)
                    
                    all_indexes = []
                    for table_row in tables_result:
                        table_indexes = self.get_existing_indexes(table_row['name'])
                        all_indexes.extend(table_indexes)
                    
                    return all_indexes
        
        except Exception as e:
            logger.error(f"Error getting existing indexes: {e}")
            return []
    
    def _parse_index_columns(self, index_definition: str) -> List[str]:
        """Parse column names from PostgreSQL index definition"""
        # Extract columns from CREATE INDEX statement
        match = re.search(r'\((.*?)\)', index_definition)
        if match:
            columns_str = match.group(1)
            columns = [col.strip() for col in columns_str.split(',')]
            return columns
        return []
    
    def _determine_index_type(self, index_definition: str) -> str:
        """Determine index type from definition"""
        if 'UNIQUE' in index_definition.upper():
            return 'unique'
        elif 'BTREE' in index_definition.upper():
            return 'btree'
        elif 'HASH' in index_definition.upper():
            return 'hash'
        else:
            return 'btree'  # Default
    
    def create_recommended_indexes(self, recommendations: List[IndexAnalysis], 
                                 max_indexes: int = 5, dry_run: bool = True) -> List[Dict[str, Any]]:
        """Create recommended indexes"""
        if not self.database_manager:
            return []
        
        results = []
        created_count = 0
        
        # Sort by recommendation score
        sorted_recs = sorted(recommendations, key=lambda x: x.recommendation_score, reverse=True)
        
        for rec in sorted_recs[:max_indexes]:
            if created_count >= max_indexes:
                break
            
            try:
                # Generate index name
                index_name = self._generate_index_name(rec.table_name, rec.columns)
                
                # Check if index already exists
                existing_indexes = self.get_existing_indexes(rec.table_name)
                if any(idx['index_name'] == index_name for idx in existing_indexes):
                    results.append({
                        'table': rec.table_name,
                        'columns': rec.columns,
                        'index_name': index_name,
                        'status': 'already_exists',
                        'message': 'Index already exists'
                    })
                    continue
                
                # Generate CREATE INDEX statement
                create_sql = self._generate_create_index_sql(
                    index_name, rec.table_name, rec.columns, rec.index_type
                )
                
                if dry_run:
                    results.append({
                        'table': rec.table_name,
                        'columns': rec.columns,
                        'index_name': index_name,
                        'sql': create_sql,
                        'status': 'dry_run',
                        'recommendation_score': rec.recommendation_score,
                        'estimated_size_mb': rec.size_estimate_mb
                    })
                else:
                    # Actually create the index
                    start_time = time.time()
                    self.database_manager.execute_query(create_sql)
                    creation_time = (time.time() - start_time) * 1000
                    
                    results.append({
                        'table': rec.table_name,
                        'columns': rec.columns,
                        'index_name': index_name,
                        'sql': create_sql,
                        'status': 'created',
                        'creation_time_ms': creation_time,
                        'recommendation_score': rec.recommendation_score
                    })
                    
                    created_count += 1
                    logger.info(f"✅ Created index {index_name} on {rec.table_name}({', '.join(rec.columns)})")
            
            except Exception as e:
                results.append({
                    'table': rec.table_name,
                    'columns': rec.columns,
                    'status': 'error',
                    'error': str(e)
                })
                logger.error(f"❌ Failed to create index on {rec.table_name}: {e}")
        
        return results
    
    def _generate_index_name(self, table_name: str, columns: List[str]) -> str:
        """Generate a standard index name"""
        # Format: idx_tablename_col1_col2
        column_part = '_'.join(columns[:3])  # Limit to first 3 columns
        index_name = f"idx_{table_name}_{column_part}"
        
        # Ensure name is not too long (PostgreSQL limit is 63 chars)
        if len(index_name) > 60:
            # Hash the columns if name is too long
            column_hash = hashlib.md5('_'.join(columns).encode()).hexdigest()[:8]
            index_name = f"idx_{table_name}_{column_hash}"
        
        return index_name
    
    def _generate_create_index_sql(self, index_name: str, table_name: str, 
                                 columns: List[str], index_type: str) -> str:
        """Generate CREATE INDEX SQL statement"""
        columns_str = ', '.join(columns)
        
        if index_type == 'unique':
            return f"CREATE UNIQUE INDEX {index_name} ON {table_name} ({columns_str})"
        else:
            # Both PostgreSQL and SQLite support this syntax
            return f"CREATE INDEX {index_name} ON {table_name} ({columns_str})"
    
    def analyze_index_usage(self) -> Dict[str, Any]:
        """Analyze current index usage and effectiveness"""
        if not self.database_manager:
            return {'status': 'no_database_manager'}
        
        try:
            analysis = {
                'timestamp': datetime.now().isoformat(),
                'database_type': 'postgresql' if self.is_postgresql else 'sqlite',
                'total_indexes': 0,
                'tables_analyzed': 0,
                'recommendations_count': 0,
                'index_efficiency': {},
                'optimization_opportunities': []
            }
            
            # Get all existing indexes
            all_indexes = self.get_existing_indexes()
            analysis['total_indexes'] = len(all_indexes)
            
            # Analyze each table
            tables = set(idx['table_name'] for idx in all_indexes)
            analysis['tables_analyzed'] = len(tables)
            
            for table in tables:
                table_indexes = [idx for idx in all_indexes if idx['table_name'] == table]
                
                # Check for redundant indexes
                redundant = self._find_redundant_indexes(table_indexes)
                if redundant:
                    analysis['optimization_opportunities'].extend(redundant)
                
                # Check for missing indexes based on query patterns
                if table in self.table_analyses:
                    missing = self._find_missing_indexes(table, table_indexes)
                    if missing:
                        analysis['optimization_opportunities'].extend(missing)
            
            # Count total recommendations
            total_recommendations = sum(
                len(self._generate_index_recommendations(
                    [table], [], [], []
                )) for table in tables
            )
            analysis['recommendations_count'] = total_recommendations
            
            return analysis
        
        except Exception as e:
            logger.error(f"Error analyzing index usage: {e}")
            return {'status': 'error', 'error': str(e)}
    
    def _find_redundant_indexes(self, table_indexes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find redundant indexes on a table"""
        redundant = []
        
        for i, idx1 in enumerate(table_indexes):
            for j, idx2 in enumerate(table_indexes[i+1:], i+1):
                # Check if one index is a prefix of another
                cols1 = idx1.get('columns', [])
                cols2 = idx2.get('columns', [])
                
                if len(cols1) < len(cols2) and cols2[:len(cols1)] == cols1:
                    redundant.append({
                        'type': 'redundant_prefix',
                        'redundant_index': idx1['index_name'],
                        'superseded_by': idx2['index_name'],
                        'table': idx1['table_name'],
                        'recommendation': f"Consider dropping {idx1['index_name']} as it's covered by {idx2['index_name']}"
                    })
                elif len(cols2) < len(cols1) and cols1[:len(cols2)] == cols2:
                    redundant.append({
                        'type': 'redundant_prefix',
                        'redundant_index': idx2['index_name'],
                        'superseded_by': idx1['index_name'],
                        'table': idx2['table_name'],
                        'recommendation': f"Consider dropping {idx2['index_name']} as it's covered by {idx1['index_name']}"
                    })
        
        return redundant
    
    def _find_missing_indexes(self, table: str, existing_indexes: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Find missing indexes based on query patterns"""
        missing = []
        
        if table not in self.table_analyses:
            return missing
        
        analysis = self.table_analyses[table]
        existing_columns = set()
        
        # Get all columns covered by existing indexes
        for idx in existing_indexes:
            existing_columns.update(idx.get('columns', []))
        
        # Check frequently used WHERE columns
        where_counter = Counter(analysis.frequent_where_columns)
        for column, frequency in where_counter.most_common(5):
            if column not in existing_columns and frequency > 2:
                missing.append({
                    'type': 'missing_where_index',
                    'table': table,
                    'column': column,
                    'frequency': frequency,
                    'recommendation': f"Consider adding index on {table}({column}) for WHERE conditions"
                })
        
        # Check frequently used JOIN columns
        join_counter = Counter(analysis.frequent_join_columns)
        for column, frequency in join_counter.most_common(3):
            if column not in existing_columns and frequency > 1:
                missing.append({
                    'type': 'missing_join_index',
                    'table': table,
                    'column': column,
                    'frequency': frequency,
                    'recommendation': f"Consider adding index on {table}({column}) for JOIN operations"
                })
        
        return missing
    
    def get_optimization_summary(self) -> Dict[str, Any]:
        """Get comprehensive index optimization summary"""
        return {
            'timestamp': datetime.now().isoformat(),
            'database_type': 'postgresql' if self.is_postgresql else 'sqlite',
            'tables_analyzed': len(self.table_analyses),
            'query_patterns_tracked': len(self.query_patterns),
            'index_recommendations_available': sum(
                len(self._generate_index_recommendations([table], [], [], []))
                for table in self.table_analyses.keys()
            ),
            'railway_optimized': True,
            'max_index_size_mb': self.max_index_size_mb,
            'max_indexes_per_table': self.max_indexes_per_table
        }

# Global index manager instance
_index_manager = None

def get_index_manager(database_manager=None) -> IntelligentIndexManager:
    """Get the global index manager instance"""
    global _index_manager
    if _index_manager is None:
        _index_manager = IntelligentIndexManager(database_manager)
    return _index_manager