"""
Database Performance Analysis Tools
Implements comprehensive database performance analysis with query performance analysis,
execution plan visualization, bottleneck identification, and optimization recommendations.
"""

import os
import time
import json
import sqlite3
import logging
import statistics
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any, Set
from dataclasses import dataclass, asdict
from pathlib import Path
from enum import Enum
import re
import hashlib

class QueryType(Enum):
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    CREATE = "CREATE"
    DROP = "DROP"
    ALTER = "ALTER"
    UNKNOWN = "UNKNOWN"

class PerformanceIssueType(Enum):
    SLOW_QUERY = "slow_query"
    MISSING_INDEX = "missing_index"
    INEFFICIENT_JOIN = "inefficient_join"
    FULL_TABLE_SCAN = "full_table_scan"
    EXCESSIVE_SORTING = "excessive_sorting"
    SUBOPTIMAL_WHERE = "suboptimal_where"
    LARGE_RESULT_SET = "large_result_set"
    FREQUENT_QUERY = "frequent_query"

@dataclass
class QueryMetrics:
    query_hash: str
    query_text: str
    query_type: QueryType
    execution_count: int
    total_execution_time_ms: float
    average_execution_time_ms: float
    min_execution_time_ms: float
    max_execution_time_ms: float
    median_execution_time_ms: float
    p95_execution_time_ms: float
    rows_examined: int
    rows_returned: int
    first_seen: datetime
    last_seen: datetime
    tables_accessed: List[str]
    indexes_used: List[str]

@dataclass
class ExecutionPlan:
    query_hash: str
    plan_text: str
    plan_json: Dict[str, Any]
    estimated_cost: float
    actual_rows: int
    estimated_rows: int
    scan_type: str
    index_usage: List[str]
    join_operations: List[str]
    sort_operations: List[str]
    temp_usage: bool

@dataclass
class PerformanceIssue:
    issue_id: str
    issue_type: PerformanceIssueType
    severity: str  # HIGH, MEDIUM, LOW
    query_hash: str
    description: str
    impact_score: float
    recommendation: str
    estimated_improvement: str
    detected_at: datetime
    affected_tables: List[str]

@dataclass
class DatabaseProfile:
    profile_id: str
    database_path: str
    profile_start: datetime
    profile_end: datetime
    total_queries: int
    unique_queries: int
    total_execution_time_ms: float
    average_query_time_ms: float
    slowest_queries: List[QueryMetrics]
    most_frequent_queries: List[QueryMetrics]
    performance_issues: List[PerformanceIssue]
    table_statistics: Dict[str, Dict[str, Any]]
    index_statistics: Dict[str, Dict[str, Any]]
    recommendations: List[str]class Q
ueryAnalyzer:
    """
    Analyzes individual queries for performance characteristics
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
    def parse_query_type(self, query: str) -> QueryType:
        """Determine the type of SQL query"""
        query_upper = query.strip().upper()
        
        if query_upper.startswith('SELECT'):
            return QueryType.SELECT
        elif query_upper.startswith('INSERT'):
            return QueryType.INSERT
        elif query_upper.startswith('UPDATE'):
            return QueryType.UPDATE
        elif query_upper.startswith('DELETE'):
            return QueryType.DELETE
        elif query_upper.startswith('CREATE'):
            return QueryType.CREATE
        elif query_upper.startswith('DROP'):
            return QueryType.DROP
        elif query_upper.startswith('ALTER'):
            return QueryType.ALTER
        else:
            return QueryType.UNKNOWN
    
    def extract_tables(self, query: str) -> List[str]:
        """Extract table names from SQL query"""
        tables = []
        query_upper = query.upper()
        
        # Simple regex patterns for table extraction
        patterns = [
            r'FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'JOIN\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'UPDATE\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)',
            r'DELETE\s+FROM\s+([a-zA-Z_][a-zA-Z0-9_]*)'
        ]
        
        for pattern in patterns:
            matches = re.findall(pattern, query_upper)
            tables.extend(matches)
        
        return list(set(tables))  # Remove duplicates
    
    def generate_query_hash(self, query: str) -> str:
        """Generate a hash for query normalization"""
        # Normalize query by removing literals and whitespace
        normalized = re.sub(r'\s+', ' ', query.strip())
        normalized = re.sub(r"'[^']*'", "'?'", normalized)  # Replace string literals
        normalized = re.sub(r'\b\d+\b', '?', normalized)    # Replace numbers
        
        return hashlib.md5(normalized.encode()).hexdigest()
    
    def analyze_query_complexity(self, query: str) -> Dict[str, Any]:
        """Analyze query complexity metrics"""
        query_upper = query.upper()
        
        complexity = {
            'has_joins': 'JOIN' in query_upper,
            'join_count': len(re.findall(r'\bJOIN\b', query_upper)),
            'has_subqueries': '(' in query and 'SELECT' in query_upper,
            'subquery_count': query_upper.count('SELECT') - 1,
            'has_aggregates': any(func in query_upper for func in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']),
            'has_group_by': 'GROUP BY' in query_upper,
            'has_order_by': 'ORDER BY' in query_upper,
            'has_having': 'HAVING' in query_upper,
            'where_conditions': len(re.findall(r'\bWHERE\b', query_upper)),
            'estimated_complexity': 'LOW'
        }
        
        # Calculate complexity score
        score = 0
        score += complexity['join_count'] * 2
        score += complexity['subquery_count'] * 3
        score += 1 if complexity['has_aggregates'] else 0
        score += 1 if complexity['has_group_by'] else 0
        score += 1 if complexity['has_order_by'] else 0
        score += complexity['where_conditions']
        
        if score <= 3:
            complexity['estimated_complexity'] = 'LOW'
        elif score <= 8:
            complexity['estimated_complexity'] = 'MEDIUM'
        else:
            complexity['estimated_complexity'] = 'HIGH'
        
        complexity['complexity_score'] = score
        
        return complexity

class ExecutionPlanAnalyzer:
    """
    Analyzes SQLite query execution plans
    """
    
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.logger = logging.getLogger(__name__)
    
    def get_execution_plan(self, query: str) -> Optional[ExecutionPlan]:
        """Get and analyze execution plan for a query"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get query plan using EXPLAIN QUERY PLAN
            cursor.execute(f"EXPLAIN QUERY PLAN {query}")
            plan_rows = cursor.fetchall()
            
            # Get detailed execution plan using EXPLAIN
            cursor.execute(f"EXPLAIN {query}")
            detailed_plan = cursor.fetchall()
            
            conn.close()
            
            if not plan_rows:
                return None
            
            # Parse execution plan
            plan_text = "\n".join([f"{row[0]}|{row[1]}|{row[2]}|{row[3]}" for row in plan_rows])
            
            # Analyze plan characteristics
            scan_type = self._analyze_scan_type(plan_text)
            index_usage = self._extract_index_usage(plan_text)
            join_operations = self._extract_join_operations(plan_text)
            sort_operations = self._extract_sort_operations(plan_text)
            temp_usage = 'TEMP' in plan_text.upper()
            
            # Estimate cost (simplified for SQLite)
            estimated_cost = self._estimate_query_cost(plan_text, detailed_plan)
            
            query_hash = QueryAnalyzer().generate_query_hash(query)
            
            return ExecutionPlan(
                query_hash=query_hash,
                plan_text=plan_text,
                plan_json={"plan_rows": plan_rows, "detailed_plan": detailed_plan},
                estimated_cost=estimated_cost,
                actual_rows=0,  # Would need actual execution to get this
                estimated_rows=self._estimate_rows_from_plan(plan_text),
                scan_type=scan_type,
                index_usage=index_usage,
                join_operations=join_operations,
                sort_operations=sort_operations,
                temp_usage=temp_usage
            )
            
        except Exception as e:
            self.logger.error(f"Failed to get execution plan: {e}")
            return None
    
    def _analyze_scan_type(self, plan_text: str) -> str:
        """Analyze the type of scan being performed"""
        plan_upper = plan_text.upper()
        
        if 'SCAN TABLE' in plan_upper:
            return 'TABLE_SCAN'
        elif 'SEARCH TABLE' in plan_upper and 'USING INDEX' in plan_upper:
            return 'INDEX_SCAN'
        elif 'SEARCH TABLE' in plan_upper:
            return 'TABLE_SEARCH'
        elif 'USE TEMP B-TREE' in plan_upper:
            return 'TEMP_BTREE'
        else:
            return 'UNKNOWN'
    
    def _extract_index_usage(self, plan_text: str) -> List[str]:
        """Extract indexes used in the execution plan"""
        indexes = []
        
        # Look for index usage patterns
        index_patterns = [
            r'USING INDEX ([a-zA-Z_][a-zA-Z0-9_]*)',
            r'USING COVERING INDEX ([a-zA-Z_][a-zA-Z0-9_]*)',
            r'USING AUTOMATIC INDEX ([a-zA-Z_][a-zA-Z0-9_]*)'
        ]
        
        for pattern in index_patterns:
            matches = re.findall(pattern, plan_text)
            indexes.extend(matches)
        
        return list(set(indexes))
    
    def _extract_join_operations(self, plan_text: str) -> List[str]:
        """Extract join operations from execution plan"""
        joins = []
        
        if 'NESTED LOOP' in plan_text.upper():
            joins.append('NESTED_LOOP')
        if 'HASH JOIN' in plan_text.upper():
            joins.append('HASH_JOIN')
        if 'MERGE JOIN' in plan_text.upper():
            joins.append('MERGE_JOIN')
        
        return joins
    
    def _extract_sort_operations(self, plan_text: str) -> List[str]:
        """Extract sort operations from execution plan"""
        sorts = []
        
        if 'USE TEMP B-TREE FOR ORDER BY' in plan_text.upper():
            sorts.append('ORDER_BY_SORT')
        if 'USE TEMP B-TREE FOR GROUP BY' in plan_text.upper():
            sorts.append('GROUP_BY_SORT')
        if 'USE TEMP B-TREE FOR DISTINCT' in plan_text.upper():
            sorts.append('DISTINCT_SORT')
        
        return sorts
    
    def _estimate_query_cost(self, plan_text: str, detailed_plan: List[Tuple]) -> float:
        """Estimate query execution cost"""
        # Simplified cost estimation for SQLite
        cost = 1.0
        
        # Add cost for table scans
        cost += plan_text.upper().count('SCAN TABLE') * 10
        
        # Add cost for sorts
        cost += plan_text.upper().count('USE TEMP B-TREE') * 5
        
        # Add cost for joins
        cost += plan_text.upper().count('NESTED LOOP') * 3
        
        # Add cost based on number of operations
        cost += len(detailed_plan) * 0.1
        
        return cost
    
    def _estimate_rows_from_plan(self, plan_text: str) -> int:
        """Estimate number of rows from execution plan"""
        # This is a simplified estimation
        # In a real implementation, you'd parse the plan more thoroughly
        if 'SCAN TABLE' in plan_text.upper():
            return 1000  # Assume table scan processes many rows
        elif 'SEARCH TABLE' in plan_text.upper():
            return 100   # Assume index search is more selective
        else:
            return 10    # Default estimatecla
ss PerformanceIssueDetector:
    """
    Detects performance issues and bottlenecks in database queries
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        
        # Configurable thresholds
        self.slow_query_threshold_ms = 1000
        self.frequent_query_threshold = 100
        self.large_result_threshold = 10000
    
    def detect_issues(self, query_metrics: QueryMetrics, execution_plan: Optional[ExecutionPlan] = None) -> List[PerformanceIssue]:
        """Detect performance issues for a query"""
        issues = []
        
        # Check for slow queries
        if query_metrics.average_execution_time_ms > self.slow_query_threshold_ms:
            issues.append(self._create_slow_query_issue(query_metrics))
        
        # Check for frequent queries
        if query_metrics.execution_count > self.frequent_query_threshold:
            issues.append(self._create_frequent_query_issue(query_metrics))
        
        # Check for large result sets
        if query_metrics.rows_returned > self.large_result_threshold:
            issues.append(self._create_large_result_issue(query_metrics))
        
        # Check execution plan issues
        if execution_plan:
            issues.extend(self._detect_plan_issues(query_metrics, execution_plan))
        
        return issues
    
    def _create_slow_query_issue(self, metrics: QueryMetrics) -> PerformanceIssue:
        """Create issue for slow query"""
        severity = "HIGH" if metrics.average_execution_time_ms > 5000 else "MEDIUM"
        
        return PerformanceIssue(
            issue_id=f"slow_query_{metrics.query_hash}",
            issue_type=PerformanceIssueType.SLOW_QUERY,
            severity=severity,
            query_hash=metrics.query_hash,
            description=f"Query has average execution time of {metrics.average_execution_time_ms:.2f}ms",
            impact_score=metrics.average_execution_time_ms * metrics.execution_count / 1000,
            recommendation="Consider adding indexes, optimizing WHERE clauses, or rewriting the query",
            estimated_improvement="20-80% performance improvement possible",
            detected_at=datetime.now(),
            affected_tables=metrics.tables_accessed
        )
    
    def _create_frequent_query_issue(self, metrics: QueryMetrics) -> PerformanceIssue:
        """Create issue for frequently executed query"""
        return PerformanceIssue(
            issue_id=f"frequent_query_{metrics.query_hash}",
            issue_type=PerformanceIssueType.FREQUENT_QUERY,
            severity="MEDIUM",
            query_hash=metrics.query_hash,
            description=f"Query executed {metrics.execution_count} times",
            impact_score=metrics.execution_count * metrics.average_execution_time_ms / 1000,
            recommendation="Consider caching results, adding indexes, or optimizing the query",
            estimated_improvement="10-50% performance improvement through caching",
            detected_at=datetime.now(),
            affected_tables=metrics.tables_accessed
        )
    
    def _create_large_result_issue(self, metrics: QueryMetrics) -> PerformanceIssue:
        """Create issue for queries returning large result sets"""
        return PerformanceIssue(
            issue_id=f"large_result_{metrics.query_hash}",
            issue_type=PerformanceIssueType.LARGE_RESULT_SET,
            severity="MEDIUM",
            query_hash=metrics.query_hash,
            description=f"Query returns {metrics.rows_returned} rows",
            impact_score=metrics.rows_returned / 1000,
            recommendation="Consider adding LIMIT clauses, pagination, or more selective WHERE conditions",
            estimated_improvement="Reduced memory usage and faster response times",
            detected_at=datetime.now(),
            affected_tables=metrics.tables_accessed
        )
    
    def _detect_plan_issues(self, metrics: QueryMetrics, plan: ExecutionPlan) -> List[PerformanceIssue]:
        """Detect issues from execution plan analysis"""
        issues = []
        
        # Check for full table scans
        if plan.scan_type == 'TABLE_SCAN':
            issues.append(PerformanceIssue(
                issue_id=f"table_scan_{metrics.query_hash}",
                issue_type=PerformanceIssueType.FULL_TABLE_SCAN,
                severity="HIGH",
                query_hash=metrics.query_hash,
                description="Query performs full table scan",
                impact_score=plan.estimated_cost,
                recommendation="Add appropriate indexes to avoid full table scans",
                estimated_improvement="50-90% performance improvement with proper indexing",
                detected_at=datetime.now(),
                affected_tables=metrics.tables_accessed
            ))
        
        # Check for missing indexes
        if not plan.index_usage and metrics.query_type == QueryType.SELECT:
            issues.append(PerformanceIssue(
                issue_id=f"missing_index_{metrics.query_hash}",
                issue_type=PerformanceIssueType.MISSING_INDEX,
                severity="MEDIUM",
                query_hash=metrics.query_hash,
                description="Query does not use any indexes",
                impact_score=plan.estimated_cost * 0.8,
                recommendation="Create indexes on columns used in WHERE, JOIN, and ORDER BY clauses",
                estimated_improvement="30-70% performance improvement with proper indexing",
                detected_at=datetime.now(),
                affected_tables=metrics.tables_accessed
            ))
        
        # Check for excessive sorting
        if plan.sort_operations:
            issues.append(PerformanceIssue(
                issue_id=f"excessive_sort_{metrics.query_hash}",
                issue_type=PerformanceIssueType.EXCESSIVE_SORTING,
                severity="MEDIUM",
                query_hash=metrics.query_hash,
                description=f"Query uses temporary sorting: {', '.join(plan.sort_operations)}",
                impact_score=len(plan.sort_operations) * 2,
                recommendation="Consider adding indexes to support ORDER BY and GROUP BY operations",
                estimated_improvement="20-50% performance improvement with proper indexing",
                detected_at=datetime.now(),
                affected_tables=metrics.tables_accessed
            ))
        
        return issues

class DatabaseProfiler:
    """
    Profiles database performance and generates comprehensive analysis
    """
    
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.query_analyzer = QueryAnalyzer()
        self.plan_analyzer = ExecutionPlanAnalyzer(database_path)
        self.issue_detector = PerformanceIssueDetector()
        self.logger = logging.getLogger(__name__)
        
        # Query tracking
        self.query_metrics: Dict[str, QueryMetrics] = {}
        self.execution_plans: Dict[str, ExecutionPlan] = {}
        self.performance_issues: List[PerformanceIssue] = []
    
    def start_profiling(self) -> str:
        """Start a new profiling session"""
        profile_id = f"profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.profile_start = datetime.now()
        self.logger.info(f"Started database profiling session: {profile_id}")
        return profile_id
    
    def record_query_execution(self, query: str, execution_time_ms: float, rows_returned: int = 0):
        """Record a query execution for profiling"""
        query_hash = self.query_analyzer.generate_query_hash(query)
        query_type = self.query_analyzer.parse_query_type(query)
        tables_accessed = self.query_analyzer.extract_tables(query)
        
        if query_hash in self.query_metrics:
            # Update existing metrics
            metrics = self.query_metrics[query_hash]
            metrics.execution_count += 1
            metrics.total_execution_time_ms += execution_time_ms
            metrics.average_execution_time_ms = metrics.total_execution_time_ms / metrics.execution_count
            metrics.min_execution_time_ms = min(metrics.min_execution_time_ms, execution_time_ms)
            metrics.max_execution_time_ms = max(metrics.max_execution_time_ms, execution_time_ms)
            metrics.rows_returned += rows_returned
            metrics.last_seen = datetime.now()
        else:
            # Create new metrics
            self.query_metrics[query_hash] = QueryMetrics(
                query_hash=query_hash,
                query_text=query,
                query_type=query_type,
                execution_count=1,
                total_execution_time_ms=execution_time_ms,
                average_execution_time_ms=execution_time_ms,
                min_execution_time_ms=execution_time_ms,
                max_execution_time_ms=execution_time_ms,
                median_execution_time_ms=execution_time_ms,
                p95_execution_time_ms=execution_time_ms,
                rows_examined=0,  # Would need query plan analysis
                rows_returned=rows_returned,
                first_seen=datetime.now(),
                last_seen=datetime.now(),
                tables_accessed=tables_accessed,
                indexes_used=[]  # Would be populated from execution plan
            )
    
    def analyze_query_performance(self, query: str) -> Tuple[QueryMetrics, Optional[ExecutionPlan], List[PerformanceIssue]]:
        """Analyze performance of a specific query"""
        query_hash = self.query_analyzer.generate_query_hash(query)
        
        # Get or create query metrics
        if query_hash not in self.query_metrics:
            # Simulate execution to get basic metrics
            self.record_query_execution(query, 0, 0)
        
        metrics = self.query_metrics[query_hash]
        
        # Get execution plan
        execution_plan = self.plan_analyzer.get_execution_plan(query)
        if execution_plan:
            self.execution_plans[query_hash] = execution_plan
            metrics.indexes_used = execution_plan.index_usage
        
        # Detect performance issues
        issues = self.issue_detector.detect_issues(metrics, execution_plan)
        self.performance_issues.extend(issues)
        
        return metrics, execution_plan, issues
    
    def generate_database_profile(self) -> DatabaseProfile:
        """Generate comprehensive database profile"""
        profile_end = datetime.now()
        
        # Calculate overall statistics
        total_queries = sum(m.execution_count for m in self.query_metrics.values())
        unique_queries = len(self.query_metrics)
        total_execution_time = sum(m.total_execution_time_ms for m in self.query_metrics.values())
        avg_query_time = total_execution_time / total_queries if total_queries > 0 else 0
        
        # Get slowest queries
        slowest_queries = sorted(
            self.query_metrics.values(),
            key=lambda x: x.average_execution_time_ms,
            reverse=True
        )[:10]
        
        # Get most frequent queries
        most_frequent_queries = sorted(
            self.query_metrics.values(),
            key=lambda x: x.execution_count,
            reverse=True
        )[:10]
        
        # Get table and index statistics
        table_stats = self._analyze_table_statistics()
        index_stats = self._analyze_index_statistics()
        
        # Generate recommendations
        recommendations = self._generate_recommendations()
        
        profile_id = f"profile_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        return DatabaseProfile(
            profile_id=profile_id,
            database_path=self.database_path,
            profile_start=getattr(self, 'profile_start', profile_end),
            profile_end=profile_end,
            total_queries=total_queries,
            unique_queries=unique_queries,
            total_execution_time_ms=total_execution_time,
            average_query_time_ms=avg_query_time,
            slowest_queries=slowest_queries,
            most_frequent_queries=most_frequent_queries,
            performance_issues=self.performance_issues,
            table_statistics=table_stats,
            index_statistics=index_stats,
            recommendations=recommendations
        )
    
    def _analyze_table_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Analyze table-level statistics"""
        table_stats = {}
        
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get all tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            for (table_name,) in tables:
                try:
                    # Get row count
                    cursor.execute(f"SELECT COUNT(*) FROM {table_name}")
                    row_count = cursor.fetchone()[0]
                    
                    # Get table info
                    cursor.execute(f"PRAGMA table_info({table_name})")
                    columns = cursor.fetchall()
                    
                    table_stats[table_name] = {
                        'row_count': row_count,
                        'column_count': len(columns),
                        'columns': [col[1] for col in columns],
                        'access_frequency': sum(1 for m in self.query_metrics.values() if table_name in m.tables_accessed)
                    }
                    
                except Exception as e:
                    self.logger.warning(f"Could not analyze table {table_name}: {e}")
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to analyze table statistics: {e}")
        
        return table_stats
    
    def _analyze_index_statistics(self) -> Dict[str, Dict[str, Any]]:
        """Analyze index-level statistics"""
        index_stats = {}
        
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get all indexes
            cursor.execute("SELECT name, tbl_name FROM sqlite_master WHERE type='index'")
            indexes = cursor.fetchall()
            
            for index_name, table_name in indexes:
                if index_name.startswith('sqlite_'):  # Skip system indexes
                    continue
                
                try:
                    # Get index info
                    cursor.execute(f"PRAGMA index_info({index_name})")
                    index_info = cursor.fetchall()
                    
                    index_stats[index_name] = {
                        'table_name': table_name,
                        'columns': [info[2] for info in index_info],
                        'usage_frequency': sum(1 for plan in self.execution_plans.values() if index_name in plan.index_usage)
                    }
                    
                except Exception as e:
                    self.logger.warning(f"Could not analyze index {index_name}: {e}")
            
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Failed to analyze index statistics: {e}")
        
        return index_stats
    
    def _generate_recommendations(self) -> List[str]:
        """Generate performance optimization recommendations"""
        recommendations = []
        
        # Analyze performance issues for recommendations
        issue_counts = {}
        for issue in self.performance_issues:
            issue_type = issue.issue_type
            if issue_type not in issue_counts:
                issue_counts[issue_type] = 0
            issue_counts[issue_type] += 1
        
        # Generate recommendations based on common issues
        if issue_counts.get(PerformanceIssueType.SLOW_QUERY, 0) > 0:
            recommendations.append("Consider optimizing slow queries by adding appropriate indexes")
        
        if issue_counts.get(PerformanceIssueType.FULL_TABLE_SCAN, 0) > 0:
            recommendations.append("Add indexes to eliminate full table scans")
        
        if issue_counts.get(PerformanceIssueType.MISSING_INDEX, 0) > 0:
            recommendations.append("Create indexes on frequently queried columns")
        
        if issue_counts.get(PerformanceIssueType.EXCESSIVE_SORTING, 0) > 0:
            recommendations.append("Add indexes to support ORDER BY and GROUP BY operations")
        
        if issue_counts.get(PerformanceIssueType.FREQUENT_QUERY, 0) > 0:
            recommendations.append("Consider implementing query result caching for frequently executed queries")
        
        # Add general recommendations
        if len(self.query_metrics) > 100:
            recommendations.append("Consider implementing query monitoring and alerting for production systems")
        
        if not recommendations:
            recommendations.append("Database performance appears to be well-optimized")
        
        return recommendationsclas
s PerformanceReportGenerator:
    """
    Generates comprehensive performance analysis reports
    """
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def generate_text_report(self, profile: DatabaseProfile) -> str:
        """Generate a comprehensive text-based performance report"""
        report = []
        
        # Header
        report.append("=" * 80)
        report.append("DATABASE PERFORMANCE ANALYSIS REPORT")
        report.append("=" * 80)
        report.append(f"Profile ID: {profile.profile_id}")
        report.append(f"Database: {profile.database_path}")
        report.append(f"Analysis Period: {profile.profile_start.strftime('%Y-%m-%d %H:%M:%S')} to {profile.profile_end.strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Duration: {(profile.profile_end - profile.profile_start).total_seconds():.1f} seconds")
        report.append("")
        
        # Executive Summary
        report.append("EXECUTIVE SUMMARY")
        report.append("-" * 40)
        report.append(f"Total Queries Executed: {profile.total_queries:,}")
        report.append(f"Unique Query Patterns: {profile.unique_queries:,}")
        report.append(f"Total Execution Time: {profile.total_execution_time_ms:,.1f} ms")
        report.append(f"Average Query Time: {profile.average_query_time_ms:.2f} ms")
        report.append(f"Performance Issues Found: {len(profile.performance_issues)}")
        report.append("")
        
        # Performance Issues Summary
        if profile.performance_issues:
            report.append("PERFORMANCE ISSUES SUMMARY")
            report.append("-" * 40)
            
            # Group issues by type
            issue_summary = {}
            for issue in profile.performance_issues:
                issue_type = issue.issue_type.value
                if issue_type not in issue_summary:
                    issue_summary[issue_type] = {'count': 0, 'high': 0, 'medium': 0, 'low': 0}
                issue_summary[issue_type]['count'] += 1
                issue_summary[issue_type][issue.severity.lower()] += 1
            
            for issue_type, summary in issue_summary.items():
                report.append(f"{issue_type.replace('_', ' ').title()}: {summary['count']} issues "
                             f"(High: {summary['high']}, Medium: {summary['medium']}, Low: {summary['low']})")
            report.append("")
        
        # Slowest Queries
        if profile.slowest_queries:
            report.append("TOP 10 SLOWEST QUERIES")
            report.append("-" * 40)
            for i, query in enumerate(profile.slowest_queries, 1):
                report.append(f"{i}. Average Time: {query.average_execution_time_ms:.2f}ms, "
                             f"Executions: {query.execution_count}, "
                             f"Type: {query.query_type.value}")
                report.append(f"   Query: {query.query_text[:100]}{'...' if len(query.query_text) > 100 else ''}")
                report.append("")
        
        # Most Frequent Queries
        if profile.most_frequent_queries:
            report.append("TOP 10 MOST FREQUENT QUERIES")
            report.append("-" * 40)
            for i, query in enumerate(profile.most_frequent_queries, 1):
                report.append(f"{i}. Executions: {query.execution_count}, "
                             f"Average Time: {query.average_execution_time_ms:.2f}ms, "
                             f"Total Time: {query.total_execution_time_ms:.1f}ms")
                report.append(f"   Query: {query.query_text[:100]}{'...' if len(query.query_text) > 100 else ''}")
                report.append("")
        
        # Table Statistics
        if profile.table_statistics:
            report.append("TABLE STATISTICS")
            report.append("-" * 40)
            for table_name, stats in profile.table_statistics.items():
                report.append(f"Table: {table_name}")
                report.append(f"  Rows: {stats['row_count']:,}")
                report.append(f"  Columns: {stats['column_count']}")
                report.append(f"  Access Frequency: {stats['access_frequency']}")
                report.append("")
        
        # Index Statistics
        if profile.index_statistics:
            report.append("INDEX STATISTICS")
            report.append("-" * 40)
            for index_name, stats in profile.index_statistics.items():
                report.append(f"Index: {index_name}")
                report.append(f"  Table: {stats['table_name']}")
                report.append(f"  Columns: {', '.join(stats['columns'])}")
                report.append(f"  Usage Frequency: {stats['usage_frequency']}")
                report.append("")
        
        # Detailed Performance Issues
        if profile.performance_issues:
            report.append("DETAILED PERFORMANCE ISSUES")
            report.append("-" * 40)
            
            # Sort by severity and impact
            sorted_issues = sorted(profile.performance_issues, 
                                 key=lambda x: (x.severity == 'HIGH', x.impact_score), 
                                 reverse=True)
            
            for i, issue in enumerate(sorted_issues, 1):
                report.append(f"{i}. {issue.issue_type.value.replace('_', ' ').title()} [{issue.severity}]")
                report.append(f"   Description: {issue.description}")
                report.append(f"   Impact Score: {issue.impact_score:.2f}")
                report.append(f"   Recommendation: {issue.recommendation}")
                report.append(f"   Estimated Improvement: {issue.estimated_improvement}")
                if issue.affected_tables:
                    report.append(f"   Affected Tables: {', '.join(issue.affected_tables)}")
                report.append("")
        
        # Recommendations
        if profile.recommendations:
            report.append("OPTIMIZATION RECOMMENDATIONS")
            report.append("-" * 40)
            for i, recommendation in enumerate(profile.recommendations, 1):
                report.append(f"{i}. {recommendation}")
            report.append("")
        
        # Footer
        report.append("=" * 80)
        report.append(f"Report generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("=" * 80)
        
        return "\n".join(report)
    
    def generate_json_report(self, profile: DatabaseProfile) -> str:
        """Generate a JSON-formatted performance report"""
        # Convert profile to serializable format
        profile_dict = asdict(profile)
        
        # Convert datetime objects to ISO format
        profile_dict['profile_start'] = profile.profile_start.isoformat()
        profile_dict['profile_end'] = profile.profile_end.isoformat()
        
        # Convert query metrics
        for query in profile_dict['slowest_queries']:
            query['first_seen'] = datetime.fromisoformat(query['first_seen']).isoformat() if isinstance(query['first_seen'], str) else query['first_seen'].isoformat()
            query['last_seen'] = datetime.fromisoformat(query['last_seen']).isoformat() if isinstance(query['last_seen'], str) else query['last_seen'].isoformat()
            query['query_type'] = query['query_type'].value if hasattr(query['query_type'], 'value') else query['query_type']
        
        for query in profile_dict['most_frequent_queries']:
            query['first_seen'] = datetime.fromisoformat(query['first_seen']).isoformat() if isinstance(query['first_seen'], str) else query['first_seen'].isoformat()
            query['last_seen'] = datetime.fromisoformat(query['last_seen']).isoformat() if isinstance(query['last_seen'], str) else query['last_seen'].isoformat()
            query['query_type'] = query['query_type'].value if hasattr(query['query_type'], 'value') else query['query_type']
        
        # Convert performance issues
        for issue in profile_dict['performance_issues']:
            issue['issue_type'] = issue['issue_type'].value if hasattr(issue['issue_type'], 'value') else issue['issue_type']
            issue['detected_at'] = datetime.fromisoformat(issue['detected_at']).isoformat() if isinstance(issue['detected_at'], str) else issue['detected_at'].isoformat()
        
        return json.dumps(profile_dict, indent=2)
    
    def save_report(self, profile: DatabaseProfile, output_path: str, format: str = 'text'):
        """Save performance report to file"""
        try:
            if format.lower() == 'json':
                content = self.generate_json_report(profile)
                filename = f"{profile.profile_id}_report.json"
            else:
                content = self.generate_text_report(profile)
                filename = f"{profile.profile_id}_report.txt"
            
            filepath = Path(output_path) / filename
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            with open(filepath, 'w') as f:
                f.write(content)
            
            self.logger.info(f"Performance report saved to: {filepath}")
            return str(filepath)
            
        except Exception as e:
            self.logger.error(f"Failed to save performance report: {e}")
            return None

class PerformanceAnalysisTools:
    """
    Main interface for database performance analysis tools
    """
    
    def __init__(self, database_path: str, results_directory: str = "performance_analysis"):
        self.database_path = database_path
        self.results_directory = Path(results_directory)
        self.results_directory.mkdir(exist_ok=True)
        
        self.profiler = DatabaseProfiler(database_path)
        self.report_generator = PerformanceReportGenerator()
        self.logger = logging.getLogger(__name__)
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze a single query's performance"""
        metrics, execution_plan, issues = self.profiler.analyze_query_performance(query)
        
        return {
            'query_metrics': asdict(metrics),
            'execution_plan': asdict(execution_plan) if execution_plan else None,
            'performance_issues': [asdict(issue) for issue in issues],
            'analysis_timestamp': datetime.now().isoformat()
        }
    
    def start_profiling_session(self) -> str:
        """Start a new profiling session"""
        return self.profiler.start_profiling()
    
    def record_query(self, query: str, execution_time_ms: float, rows_returned: int = 0):
        """Record a query execution for profiling"""
        self.profiler.record_query_execution(query, execution_time_ms, rows_returned)
    
    def generate_performance_report(self, save_to_file: bool = True, format: str = 'text') -> str:
        """Generate comprehensive performance report"""
        profile = self.profiler.generate_database_profile()
        
        if save_to_file:
            self.report_generator.save_report(profile, str(self.results_directory), format)
        
        if format.lower() == 'json':
            return self.report_generator.generate_json_report(profile)
        else:
            return self.report_generator.generate_text_report(profile)
    
    def get_optimization_recommendations(self) -> List[str]:
        """Get optimization recommendations based on current analysis"""
        profile = self.profiler.generate_database_profile()
        return profile.recommendations
    
    def get_performance_summary(self) -> Dict[str, Any]:
        """Get a summary of performance metrics"""
        profile = self.profiler.generate_database_profile()
        
        return {
            'total_queries': profile.total_queries,
            'unique_queries': profile.unique_queries,
            'average_query_time_ms': profile.average_query_time_ms,
            'total_issues': len(profile.performance_issues),
            'high_severity_issues': len([i for i in profile.performance_issues if i.severity == 'HIGH']),
            'medium_severity_issues': len([i for i in profile.performance_issues if i.severity == 'MEDIUM']),
            'low_severity_issues': len([i for i in profile.performance_issues if i.severity == 'LOW']),
            'slowest_query_time_ms': profile.slowest_queries[0].average_execution_time_ms if profile.slowest_queries else 0,
            'most_frequent_query_count': profile.most_frequent_queries[0].execution_count if profile.most_frequent_queries else 0
        }

# Utility functions for integration
def analyze_database_performance(database_path: str, output_dir: str = "performance_analysis") -> str:
    """Convenience function to analyze database performance"""
    tools = PerformanceAnalysisTools(database_path, output_dir)
    return tools.generate_performance_report()

def get_query_recommendations(database_path: str, query: str) -> List[str]:
    """Get optimization recommendations for a specific query"""
    tools = PerformanceAnalysisTools(database_path)
    analysis = tools.analyze_query(query)
    
    recommendations = []
    for issue in analysis['performance_issues']:
        recommendations.append(issue['recommendation'])
    
    return recommendations if recommendations else ["Query appears to be well-optimized"]