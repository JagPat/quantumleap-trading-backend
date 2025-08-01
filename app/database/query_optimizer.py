"""
Advanced Query Optimizer for Railway Trading System

Intelligent query optimization with execution plan analysis,
caching, and performance recommendations.
"""

import os
import re
import time
import hashlib
import logging
from typing import Dict, Any, List, Optional, Tuple, Set
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from collections import defaultdict
import json

logger = logging.getLogger(__name__)

@dataclass
class QueryPlan:
    """Query execution plan analysis"""
    query_hash: str
    original_query: str
    optimized_query: Optional[str]
    execution_time_ms: float
    plan_details: Dict[str, Any]
    indexes_used: List[str]
    table_scans: List[str]
    optimization_suggestions: List[str]
    created_at: datetime

@dataclass
class QueryPattern:
    """Common query pattern for optimization"""
    pattern_type: str
    regex_pattern: str
    optimization_rule: str
    description: str
    priority: int

@dataclass
class IndexRecommendation:
    """Index recommendation based on query analysis"""
    table_name: str
    columns: List[str]
    index_type: str  # 'btree', 'hash', 'composite'
    reason: str
    estimated_benefit: float
    query_patterns: List[str]
    created_at: datetime

class QueryOptimizer:
    """Advanced query optimizer for Railway deployment"""
    
    def __init__(self, database_manager=None):
        self.database_manager = database_manager
        self.query_cache = {}
        self.execution_plans = {}
        self.query_patterns = self._initialize_patterns()
        self.index_recommendations = []
        self.performance_history = defaultdict(list)
        self._lock = None
        
        # Initialize threading lock if available
        try:
            import threading
            self._lock = threading.Lock()
        except ImportError:
            pass
        
        logger.info("🔧 Query optimizer initialized for Railway")
    
    def _initialize_patterns(self) -> List[QueryPattern]:
        """Initialize common query optimization patterns"""
        return [
            QueryPattern(
                pattern_type="SELECT_ALL",
                regex_pattern=r"SELECT\s+\*\s+FROM\s+(\w+)",
                optimization_rule="Specify columns instead of SELECT *",
                description="Avoid SELECT * for better performance",
                priority=3
            ),
            QueryPattern(
                pattern_type="MISSING_WHERE",
                regex_pattern=r"SELECT\s+.+\s+FROM\s+(\w+)(?!\s+WHERE)",
                optimization_rule="Add WHERE clause to limit results",
                description="Queries without WHERE clause scan entire table",
                priority=5
            ),
            QueryPattern(
                pattern_type="INEFFICIENT_LIKE",
                regex_pattern=r"WHERE\s+\w+\s+LIKE\s+'%.*%'",
                optimization_rule="Use full-text search or prefix matching",
                description="Leading wildcard LIKE queries cannot use indexes",
                priority=4
            ),
            QueryPattern(
                pattern_type="MISSING_LIMIT",
                regex_pattern=r"SELECT\s+.+\s+FROM\s+\w+.*ORDER\s+BY(?!\s+.*LIMIT)",
                optimization_rule="Add LIMIT clause to ORDER BY queries",
                description="ORDER BY without LIMIT can be expensive",
                priority=3
            ),
            QueryPattern(
                pattern_type="INEFFICIENT_JOIN",
                regex_pattern=r"FROM\s+(\w+)\s+.*JOIN\s+(\w+)\s+ON\s+(\w+\.\w+)\s*=\s*(\w+\.\w+)",
                optimization_rule="Ensure JOIN columns are indexed",
                description="JOINs on unindexed columns are slow",
                priority=5
            ),
            QueryPattern(
                pattern_type="SUBQUERY_IN_SELECT",
                regex_pattern=r"SELECT\s+.*\(\s*SELECT\s+.*\)\s*.*FROM",
                optimization_rule="Consider using JOINs instead of subqueries",
                description="Subqueries in SELECT can be inefficient",
                priority=4
            )
        ]
    
    def analyze_query(self, query: str, execution_time_ms: float = 0) -> QueryPlan:
        """Analyze query and create execution plan"""
        query_hash = self._hash_query(query)
        
        # Check cache first
        if query_hash in self.execution_plans:
            cached_plan = self.execution_plans[query_hash]
            # Update execution time if provided
            if execution_time_ms > 0:
                cached_plan.execution_time_ms = execution_time_ms
            return cached_plan
        
        # Analyze query structure
        plan_details = self._analyze_query_structure(query)
        indexes_used = self._identify_indexes_used(query, plan_details)
        table_scans = self._identify_table_scans(query, plan_details)
        optimization_suggestions = self._generate_optimization_suggestions(query, plan_details)
        
        # Generate optimized query if possible
        optimized_query = self._optimize_query(query, optimization_suggestions)
        
        plan = QueryPlan(
            query_hash=query_hash,
            original_query=query,
            optimized_query=optimized_query,
            execution_time_ms=execution_time_ms,
            plan_details=plan_details,
            indexes_used=indexes_used,
            table_scans=table_scans,
            optimization_suggestions=optimization_suggestions,
            created_at=datetime.now()
        )
        
        # Cache the plan
        self.execution_plans[query_hash] = plan
        
        # Update performance history
        self._update_performance_history(query_hash, execution_time_ms)
        
        # Generate index recommendations
        self._analyze_for_index_recommendations(query, plan_details)
        
        return plan
    
    def _hash_query(self, query: str) -> str:
        """Generate hash for query caching"""
        # Normalize query for consistent hashing
        normalized = re.sub(r'\s+', ' ', query.strip().upper())
        # Remove parameter values for pattern matching
        normalized = re.sub(r"'[^']*'", "'?'", normalized)
        normalized = re.sub(r'\b\d+\b', '?', normalized)
        
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def _analyze_query_structure(self, query: str) -> Dict[str, Any]:
        """Analyze query structure and complexity"""
        query_upper = query.upper()
        
        analysis = {
            'query_type': self._identify_query_type(query_upper),
            'tables_involved': self._extract_tables(query),
            'columns_selected': self._extract_columns(query),
            'where_conditions': self._extract_where_conditions(query),
            'joins': self._extract_joins(query),
            'order_by': self._extract_order_by(query),
            'group_by': self._extract_group_by(query),
            'has_limit': 'LIMIT' in query_upper,
            'has_subquery': self._has_subquery(query),
            'complexity_score': self._calculate_complexity_score(query)
        }
        
        return analysis
    
    def _identify_query_type(self, query: str) -> str:
        """Identify the type of SQL query"""
        query = query.strip()
        if query.startswith('SELECT'):
            return 'SELECT'
        elif query.startswith('INSERT'):
            return 'INSERT'
        elif query.startswith('UPDATE'):
            return 'UPDATE'
        elif query.startswith('DELETE'):
            return 'DELETE'
        elif query.startswith('CREATE'):
            return 'CREATE'
        else:
            return 'OTHER'
    
    def _extract_tables(self, query: str) -> List[str]:
        """Extract table names from query"""
        tables = []
        
        # FROM clause
        from_match = re.search(r'FROM\s+(\w+)', query, re.IGNORECASE)
        if from_match:
            tables.append(from_match.group(1))
        
        # JOIN clauses
        join_matches = re.findall(r'JOIN\s+(\w+)', query, re.IGNORECASE)
        tables.extend(join_matches)
        
        # INSERT INTO
        insert_match = re.search(r'INSERT\s+INTO\s+(\w+)', query, re.IGNORECASE)
        if insert_match:
            tables.append(insert_match.group(1))
        
        # UPDATE
        update_match = re.search(r'UPDATE\s+(\w+)', query, re.IGNORECASE)
        if update_match:
            tables.append(update_match.group(1))
        
        return list(set(tables))  # Remove duplicates
    
    def _extract_columns(self, query: str) -> List[str]:
        """Extract column names from SELECT query"""
        if not query.upper().strip().startswith('SELECT'):
            return []
        
        # Handle SELECT *
        if re.search(r'SELECT\s+\*', query, re.IGNORECASE):
            return ['*']
        
        # Extract column list
        select_match = re.search(r'SELECT\s+(.*?)\s+FROM', query, re.IGNORECASE | re.DOTALL)
        if not select_match:
            return []
        
        columns_str = select_match.group(1)
        
        # Simple column extraction (can be enhanced)
        columns = []
        for col in columns_str.split(','):
            col = col.strip()
            # Remove aliases and functions
            col = re.sub(r'\s+AS\s+\w+', '', col, flags=re.IGNORECASE)
            col = re.sub(r'\w+\((.*?)\)', r'\1', col)  # Remove function wrappers
            if col and col != '*':
                columns.append(col)
        
        return columns
    
    def _extract_where_conditions(self, query: str) -> List[str]:
        """Extract WHERE conditions"""
        where_match = re.search(r'WHERE\s+(.*?)(?:\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|$)', 
                               query, re.IGNORECASE | re.DOTALL)
        if not where_match:
            return []
        
        where_clause = where_match.group(1).strip()
        
        # Split by AND/OR (simple approach)
        conditions = re.split(r'\s+(?:AND|OR)\s+', where_clause, flags=re.IGNORECASE)
        return [cond.strip() for cond in conditions if cond.strip()]
    
    def _extract_joins(self, query: str) -> List[Dict[str, str]]:
        """Extract JOIN information"""
        joins = []
        
        join_pattern = r'((?:INNER|LEFT|RIGHT|FULL)?\s*JOIN)\s+(\w+)\s+ON\s+(.*?)(?=\s+(?:INNER|LEFT|RIGHT|FULL)?\s*JOIN|\s+WHERE|\s+GROUP\s+BY|\s+ORDER\s+BY|\s+LIMIT|$)'
        
        for match in re.finditer(join_pattern, query, re.IGNORECASE | re.DOTALL):
            joins.append({
                'type': match.group(1).strip(),
                'table': match.group(2),
                'condition': match.group(3).strip()
            })
        
        return joins
    
    def _extract_order_by(self, query: str) -> List[str]:
        """Extract ORDER BY columns"""
        order_match = re.search(r'ORDER\s+BY\s+(.*?)(?:\s+LIMIT|$)', query, re.IGNORECASE | re.DOTALL)
        if not order_match:
            return []
        
        order_clause = order_match.group(1).strip()
        columns = [col.strip() for col in order_clause.split(',')]
        return columns
    
    def _extract_group_by(self, query: str) -> List[str]:
        """Extract GROUP BY columns"""
        group_match = re.search(r'GROUP\s+BY\s+(.*?)(?:\s+ORDER\s+BY|\s+LIMIT|$)', 
                               query, re.IGNORECASE | re.DOTALL)
        if not group_match:
            return []
        
        group_clause = group_match.group(1).strip()
        columns = [col.strip() for col in group_clause.split(',')]
        return columns
    
    def _has_subquery(self, query: str) -> bool:
        """Check if query contains subqueries"""
        # Count parentheses to detect subqueries
        paren_count = 0
        in_string = False
        
        for char in query:
            if char == "'" and not in_string:
                in_string = True
            elif char == "'" and in_string:
                in_string = False
            elif not in_string:
                if char == '(':
                    paren_count += 1
                elif char == ')':
                    paren_count -= 1
        
        # Simple heuristic: if we have nested SELECT statements
        return query.upper().count('SELECT') > 1
    
    def _calculate_complexity_score(self, query: str) -> int:
        """Calculate query complexity score (1-10)"""
        score = 1
        query_upper = query.upper()
        
        # Base complexity factors
        if 'JOIN' in query_upper:
            score += query_upper.count('JOIN')
        
        if 'WHERE' in query_upper:
            score += 1
        
        if 'GROUP BY' in query_upper:
            score += 2
        
        if 'ORDER BY' in query_upper:
            score += 1
        
        if 'HAVING' in query_upper:
            score += 2
        
        if self._has_subquery(query):
            score += 3
        
        # Function calls add complexity
        score += len(re.findall(r'\w+\(', query))
        
        return min(score, 10)  # Cap at 10
    
    def _identify_indexes_used(self, query: str, plan_details: Dict[str, Any]) -> List[str]:
        """Identify which indexes might be used (heuristic)"""
        indexes = []
        
        # This is a simplified heuristic - in a real system, you'd use EXPLAIN
        where_conditions = plan_details.get('where_conditions', [])
        
        for condition in where_conditions:
            # Look for equality conditions that could use indexes
            if '=' in condition:
                column = condition.split('=')[0].strip()
                indexes.append(f"idx_{column}")
        
        # JOIN conditions
        for join in plan_details.get('joins', []):
            condition = join.get('condition', '')
            if '=' in condition:
                parts = condition.split('=')
                for part in parts:
                    part = part.strip()
                    if '.' in part:  # table.column format
                        table, column = part.split('.', 1)
                        indexes.append(f"idx_{table}_{column}")
        
        return indexes
    
    def _identify_table_scans(self, query: str, plan_details: Dict[str, Any]) -> List[str]:
        """Identify potential full table scans"""
        scans = []
        
        # Heuristic: queries without WHERE clause likely do table scans
        if not plan_details.get('where_conditions'):
            for table in plan_details.get('tables_involved', []):
                scans.append(table)
        
        # LIKE with leading wildcard
        for condition in plan_details.get('where_conditions', []):
            if re.search(r"LIKE\s+'%", condition, re.IGNORECASE):
                scans.append("wildcard_scan")
        
        return scans
    
    def _generate_optimization_suggestions(self, query: str, plan_details: Dict[str, Any]) -> List[str]:
        """Generate optimization suggestions based on query analysis"""
        suggestions = []
        
        # Check against known patterns
        for pattern in self.query_patterns:
            if re.search(pattern.regex_pattern, query, re.IGNORECASE):
                suggestions.append({
                    'type': pattern.pattern_type,
                    'suggestion': pattern.optimization_rule,
                    'description': pattern.description,
                    'priority': pattern.priority
                })
        
        # Specific suggestions based on analysis
        if plan_details.get('complexity_score', 0) > 7:
            suggestions.append({
                'type': 'HIGH_COMPLEXITY',
                'suggestion': 'Consider breaking down complex query into simpler parts',
                'description': 'High complexity queries can be hard to optimize',
                'priority': 4
            })
        
        if len(plan_details.get('tables_involved', [])) > 3:
            suggestions.append({
                'type': 'MANY_TABLES',
                'suggestion': 'Review if all JOINs are necessary',
                'description': 'Queries with many tables can be slow',
                'priority': 3
            })
        
        if not plan_details.get('has_limit') and plan_details.get('order_by'):
            suggestions.append({
                'type': 'MISSING_LIMIT',
                'suggestion': 'Add LIMIT clause to ORDER BY query',
                'description': 'ORDER BY without LIMIT can be expensive',
                'priority': 4
            })
        
        return suggestions
    
    def _optimize_query(self, query: str, suggestions: List[Dict[str, Any]]) -> Optional[str]:
        """Generate optimized version of query based on suggestions"""
        optimized = query
        
        for suggestion in suggestions:
            if suggestion['type'] == 'SELECT_ALL':
                # This would require knowing the table schema
                # For now, just flag it
                pass
            elif suggestion['type'] == 'MISSING_LIMIT' and 'ORDER BY' in query.upper():
                if 'LIMIT' not in query.upper():
                    optimized += ' LIMIT 1000'  # Add reasonable default
        
        return optimized if optimized != query else None
    
    def _update_performance_history(self, query_hash: str, execution_time_ms: float):
        """Update performance history for query"""
        if execution_time_ms > 0:
            with self._lock if self._lock else self._dummy_context():
                self.performance_history[query_hash].append({
                    'execution_time_ms': execution_time_ms,
                    'timestamp': datetime.now()
                })
                
                # Keep only last 100 entries per query
                if len(self.performance_history[query_hash]) > 100:
                    self.performance_history[query_hash] = self.performance_history[query_hash][-100:]
    
    def _dummy_context(self):
        """Dummy context manager when threading is not available"""
        class DummyContext:
            def __enter__(self): return self
            def __exit__(self, *args): pass
        return DummyContext()
    
    def _analyze_for_index_recommendations(self, query: str, plan_details: Dict[str, Any]):
        """Analyze query for index recommendations"""
        # WHERE clause columns
        for condition in plan_details.get('where_conditions', []):
            if '=' in condition:
                column = condition.split('=')[0].strip()
                table = plan_details.get('tables_involved', ['unknown'])[0]
                
                # Check if we already have this recommendation
                existing = any(
                    rec.table_name == table and column in rec.columns 
                    for rec in self.index_recommendations
                )
                
                if not existing:
                    self.index_recommendations.append(IndexRecommendation(
                        table_name=table,
                        columns=[column],
                        index_type='btree',
                        reason=f'WHERE clause equality condition on {column}',
                        estimated_benefit=0.7,
                        query_patterns=[self._hash_query(query)],
                        created_at=datetime.now()
                    ))
        
        # JOIN columns
        for join in plan_details.get('joins', []):
            condition = join.get('condition', '')
            if '=' in condition:
                parts = condition.split('=')
                for part in parts:
                    part = part.strip()
                    if '.' in part:
                        table, column = part.split('.', 1)
                        
                        existing = any(
                            rec.table_name == table and column in rec.columns 
                            for rec in self.index_recommendations
                        )
                        
                        if not existing:
                            self.index_recommendations.append(IndexRecommendation(
                                table_name=table,
                                columns=[column],
                                index_type='btree',
                                reason=f'JOIN condition on {table}.{column}',
                                estimated_benefit=0.8,
                                query_patterns=[self._hash_query(query)],
                                created_at=datetime.now()
                            ))
        
        # ORDER BY columns
        for order_col in plan_details.get('order_by', []):
            # Remove ASC/DESC
            column = re.sub(r'\s+(ASC|DESC)$', '', order_col, flags=re.IGNORECASE).strip()
            table = plan_details.get('tables_involved', ['unknown'])[0]
            
            existing = any(
                rec.table_name == table and column in rec.columns 
                for rec in self.index_recommendations
            )
            
            if not existing:
                self.index_recommendations.append(IndexRecommendation(
                    table_name=table,
                    columns=[column],
                    index_type='btree',
                    reason=f'ORDER BY clause on {column}',
                    estimated_benefit=0.6,
                    query_patterns=[self._hash_query(query)],
                    created_at=datetime.now()
                ))
    
    def get_query_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top query optimization recommendations"""
        recommendations = []
        
        # Get slow queries
        slow_queries = []
        for query_hash, history in self.performance_history.items():
            if history:
                avg_time = sum(h['execution_time_ms'] for h in history) / len(history)
                if avg_time > 50:  # Slower than 50ms
                    plan = self.execution_plans.get(query_hash)
                    if plan:
                        slow_queries.append((avg_time, plan))
        
        # Sort by execution time
        slow_queries.sort(reverse=True)
        
        for avg_time, plan in slow_queries[:limit]:
            recommendations.append({
                'query_hash': plan.query_hash,
                'query': plan.original_query[:200] + '...' if len(plan.original_query) > 200 else plan.original_query,
                'avg_execution_time_ms': avg_time,
                'suggestions': plan.optimization_suggestions,
                'optimized_query': plan.optimized_query,
                'complexity_score': plan.plan_details.get('complexity_score', 0)
            })
        
        return recommendations
    
    def get_index_recommendations(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get top index recommendations"""
        # Sort by estimated benefit
        sorted_recommendations = sorted(
            self.index_recommendations, 
            key=lambda x: x.estimated_benefit, 
            reverse=True
        )
        
        return [asdict(rec) for rec in sorted_recommendations[:limit]]
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary statistics"""
        total_queries = len(self.performance_history)
        
        if total_queries == 0:
            return {
                'total_queries_analyzed': 0,
                'avg_execution_time_ms': 0,
                'slow_queries_count': 0,
                'optimization_opportunities': 0
            }
        
        all_times = []
        for history in self.performance_history.values():
            all_times.extend(h['execution_time_ms'] for h in history)
        
        if not all_times:
            return {
                'total_queries_analyzed': total_queries,
                'avg_execution_time_ms': 0,
                'slow_queries_count': 0,
                'optimization_opportunities': 0
            }
        
        avg_time = sum(all_times) / len(all_times)
        slow_queries = sum(1 for t in all_times if t > 50)
        
        return {
            'total_queries_analyzed': total_queries,
            'total_executions': len(all_times),
            'avg_execution_time_ms': round(avg_time, 2),
            'slow_queries_count': slow_queries,
            'optimization_opportunities': len(self.index_recommendations),
            'cached_plans': len(self.execution_plans)
        }
    
    def clear_cache(self):
        """Clear query cache and plans"""
        with self._lock if self._lock else self._dummy_context():
            self.query_cache.clear()
            self.execution_plans.clear()
            self.performance_history.clear()
            self.index_recommendations.clear()
        
        logger.info("🧹 Query optimizer cache cleared")

# Global query optimizer instance
_query_optimizer = None

def get_query_optimizer(database_manager=None) -> QueryOptimizer:
    """Get the global query optimizer instance"""
    global _query_optimizer
    if _query_optimizer is None:
        _query_optimizer = QueryOptimizer(database_manager)
    return _query_optimizer