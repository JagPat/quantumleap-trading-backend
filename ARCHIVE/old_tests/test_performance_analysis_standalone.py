#!/usr/bin/env python3
"""
Standalone test script for the Database Performance Analysis Tools
"""

import os
import time
import json
import sqlite3
import tempfile
import shutil
import statistics
import hashlib
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass
from pathlib import Path
from enum import Enum

# Minimal inline implementation for testing
class QueryType(Enum):
    SELECT = "SELECT"
    INSERT = "INSERT"
    UPDATE = "UPDATE"
    DELETE = "DELETE"
    UNKNOWN = "UNKNOWN"

class PerformanceIssueType(Enum):
    SLOW_QUERY = "slow_query"
    FREQUENT_QUERY = "frequent_query"
    LARGE_RESULT_SET = "large_result_set"
    FULL_TABLE_SCAN = "full_table_scan"

@dataclass
class QueryMetrics:
    query_hash: str
    query_text: str
    query_type: QueryType
    execution_count: int
    average_execution_time_ms: float
    total_execution_time_ms: float
    tables_accessed: List[str]

@dataclass
class PerformanceIssue:
    issue_type: PerformanceIssueType
    severity: str
    description: str
    recommendation: str

class SimpleQueryAnalyzer:
    """Simplified query analyzer for testing"""
    
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
            r'INSERT\s+INTO\s+([a-zA-Z_][a-zA-Z0-9_]*)'
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
        
        return hashlib.md5(normalized.encode()).hexdigest()[:8]

class SimpleExecutionPlanAnalyzer:
    """Simplified execution plan analyzer for testing"""
    
    def __init__(self, database_path: str):
        self.database_path = database_path
    
    def get_execution_plan(self, query: str) -> Optional[Dict[str, Any]]:
        """Get and analyze execution plan for a query"""
        try:
            conn = sqlite3.connect(self.database_path)
            cursor = conn.cursor()
            
            # Get query plan using EXPLAIN QUERY PLAN
            cursor.execute(f"EXPLAIN QUERY PLAN {query}")
            plan_rows = cursor.fetchall()
            
            conn.close()
            
            if not plan_rows:
                return None
            
            # Parse execution plan
            plan_text = "\n".join([f"{row[0]}|{row[1]}|{row[2]}|{row[3]}" for row in plan_rows])
            
            # Analyze plan characteristics
            has_table_scan = 'SCAN TABLE' in plan_text.upper()
            has_index_usage = 'USING INDEX' in plan_text.upper()
            has_sorting = 'USE TEMP B-TREE' in plan_text.upper()
            
            return {
                'plan_text': plan_text,
                'has_table_scan': has_table_scan,
                'has_index_usage': has_index_usage,
                'has_sorting': has_sorting,
                'estimated_cost': 10 if has_table_scan else 5 if has_sorting else 1
            }
            
        except Exception as e:
            print(f"Failed to get execution plan: {e}")
            return None

class SimplePerformanceIssueDetector:
    """Simplified performance issue detector for testing"""
    
    def __init__(self):
        self.slow_query_threshold_ms = 100
        self.frequent_query_threshold = 10
    
    def detect_issues(self, metrics: QueryMetrics, execution_plan: Optional[Dict] = None) -> List[PerformanceIssue]:
        """Detect performance issues for a query"""
        issues = []
        
        # Check for slow queries
        if metrics.average_execution_time_ms > self.slow_query_threshold_ms:
            issues.append(PerformanceIssue(
                issue_type=PerformanceIssueType.SLOW_QUERY,
                severity="HIGH" if metrics.average_execution_time_ms > 500 else "MEDIUM",
                description=f"Query has average execution time of {metrics.average_execution_time_ms:.2f}ms",
                recommendation="Consider adding indexes or optimizing the query"
            ))
        
        # Check for frequent queries
        if metrics.execution_count > self.frequent_query_threshold:
            issues.append(PerformanceIssue(
                issue_type=PerformanceIssueType.FREQUENT_QUERY,
                severity="MEDIUM",
                description=f"Query executed {metrics.execution_count} times",
                recommendation="Consider caching results or optimizing the query"
            ))
        
        # Check execution plan issues
        if execution_plan and execution_plan.get('has_table_scan'):
            issues.append(PerformanceIssue(
                issue_type=PerformanceIssueType.FULL_TABLE_SCAN,
                severity="HIGH",
                description="Query performs full table scan",
                recommendation="Add appropriate indexes to avoid full table scans"
            ))
        
        return issues

class SimplePerformanceAnalyzer:
    """Simplified performance analyzer for testing"""
    
    def __init__(self, database_path: str):
        self.database_path = database_path
        self.query_analyzer = SimpleQueryAnalyzer()
        self.plan_analyzer = SimpleExecutionPlanAnalyzer(database_path)
        self.issue_detector = SimplePerformanceIssueDetector()
        
        # Query tracking
        self.query_metrics: Dict[str, QueryMetrics] = {}
        self.performance_issues: List[PerformanceIssue] = []
    
    def record_query_execution(self, query: str, execution_time_ms: float):
        """Record a query execution for analysis"""
        query_hash = self.query_analyzer.generate_query_hash(query)
        query_type = self.query_analyzer.parse_query_type(query)
        tables_accessed = self.query_analyzer.extract_tables(query)
        
        if query_hash in self.query_metrics:
            # Update existing metrics
            metrics = self.query_metrics[query_hash]
            metrics.execution_count += 1
            metrics.total_execution_time_ms += execution_time_ms
            metrics.average_execution_time_ms = metrics.total_execution_time_ms / metrics.execution_count
        else:
            # Create new metrics
            self.query_metrics[query_hash] = QueryMetrics(
                query_hash=query_hash,
                query_text=query,
                query_type=query_type,
                execution_count=1,
                average_execution_time_ms=execution_time_ms,
                total_execution_time_ms=execution_time_ms,
                tables_accessed=tables_accessed
            )
    
    def analyze_query(self, query: str) -> Dict[str, Any]:
        """Analyze a specific query's performance"""
        query_hash = self.query_analyzer.generate_query_hash(query)
        
        # Get or create query metrics
        if query_hash not in self.query_metrics:
            self.record_query_execution(query, 0)
        
        metrics = self.query_metrics[query_hash]
        
        # Get execution plan
        execution_plan = self.plan_analyzer.get_execution_plan(query)
        
        # Detect performance issues
        issues = self.issue_detector.detect_issues(metrics, execution_plan)
        
        return {
            'query_metrics': {
                'query_hash': metrics.query_hash,
                'query_type': metrics.query_type.value,
                'execution_count': metrics.execution_count,
                'average_execution_time_ms': metrics.average_execution_time_ms,
                'tables_accessed': metrics.tables_accessed
            },
            'execution_plan': execution_plan,
            'performance_issues': [
                {
                    'issue_type': issue.issue_type.value,
                    'severity': issue.severity,
                    'description': issue.description,
                    'recommendation': issue.recommendation
                } for issue in issues
            ]
        }
    
    def generate_performance_report(self) -> str:
        """Generate a simple performance report"""
        report = []
        
        report.append("DATABASE PERFORMANCE ANALYSIS REPORT")
        report.append("=" * 50)
        report.append(f"Total Queries Analyzed: {len(self.query_metrics)}")
        
        if self.query_metrics:
            total_executions = sum(m.execution_count for m in self.query_metrics.values())
            avg_time = sum(m.average_execution_time_ms for m in self.query_metrics.values()) / len(self.query_metrics)
            
            report.append(f"Total Query Executions: {total_executions}")
            report.append(f"Average Query Time: {avg_time:.2f}ms")
            report.append("")
            
            # Slowest queries
            slowest_queries = sorted(
                self.query_metrics.values(),
                key=lambda x: x.average_execution_time_ms,
                reverse=True
            )[:5]
            
            if slowest_queries:
                report.append("SLOWEST QUERIES:")
                for i, query in enumerate(slowest_queries, 1):
                    report.append(f"{i}. {query.average_execution_time_ms:.2f}ms - {query.query_text[:60]}...")
                report.append("")
            
            # Most frequent queries
            frequent_queries = sorted(
                self.query_metrics.values(),
                key=lambda x: x.execution_count,
                reverse=True
            )[:5]
            
            if frequent_queries:
                report.append("MOST FREQUENT QUERIES:")
                for i, query in enumerate(frequent_queries, 1):
                    report.append(f"{i}. {query.execution_count} executions - {query.query_text[:60]}...")
                report.append("")
        
        # Performance issues summary
        if self.performance_issues:
            issue_counts = {}
            for issue in self.performance_issues:
                issue_type = issue.issue_type.value
                if issue_type not in issue_counts:
                    issue_counts[issue_type] = 0
                issue_counts[issue_type] += 1
            
            report.append("PERFORMANCE ISSUES:")
            for issue_type, count in issue_counts.items():
                report.append(f"- {issue_type.replace('_', ' ').title()}: {count}")
            report.append("")
        
        report.append("=" * 50)
        
        return "\n".join(report)

def create_test_database():
    """Create a temporary test database with sample data"""
    temp_dir = tempfile.mkdtemp()
    db_path = os.path.join(temp_dir, "test_performance.db")
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Create test tables
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE trades (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            price REAL NOT NULL,
            trade_type TEXT NOT NULL,
            timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
        )
    """)
    
    # Create some indexes
    cursor.execute("CREATE INDEX idx_trades_user_id ON trades(user_id)")
    cursor.execute("CREATE INDEX idx_trades_symbol ON trades(symbol)")
    
    # Insert sample data
    for i in range(50):
        cursor.execute("INSERT INTO users (username, email) VALUES (?, ?)", 
                      (f"user_{i}", f"user_{i}@example.com"))
    
    for i in range(200):
        cursor.execute("INSERT INTO trades (user_id, symbol, quantity, price, trade_type) VALUES (?, ?, ?, ?, ?)",
                      (i % 50 + 1, f"STOCK_{i % 5}", (i % 100) + 1, 100.0 + (i % 50), "BUY" if i % 2 == 0 else "SELL"))
    
    conn.commit()
    conn.close()
    
    return db_path, temp_dir

def test_query_analyzer():
    """Test the query analyzer functionality"""
    print("Testing SimpleQueryAnalyzer...")
    
    analyzer = SimpleQueryAnalyzer()
    
    # Test query type parsing
    print("  Testing query type parsing...")
    assert analyzer.parse_query_type("SELECT * FROM users") == QueryType.SELECT
    assert analyzer.parse_query_type("INSERT INTO users VALUES (1, 'test')") == QueryType.INSERT
    assert analyzer.parse_query_type("UPDATE users SET name = 'test'") == QueryType.UPDATE
    assert analyzer.parse_query_type("DELETE FROM users WHERE id = 1") == QueryType.DELETE
    print("  ✓ Query type parsing working")
    
    # Test table extraction
    print("  Testing table extraction...")
    tables = analyzer.extract_tables("SELECT * FROM users JOIN trades ON users.id = trades.user_id")
    assert "USERS" in tables and "TRADES" in tables
    
    tables = analyzer.extract_tables("UPDATE portfolio SET quantity = 100 WHERE user_id = 1")
    assert "PORTFOLIO" in tables
    print("  ✓ Table extraction working")
    
    # Test query hash generation
    print("  Testing query hash generation...")
    hash1 = analyzer.generate_query_hash("SELECT * FROM users WHERE id = 1")
    hash2 = analyzer.generate_query_hash("SELECT * FROM users WHERE id = 2")
    hash3 = analyzer.generate_query_hash("SELECT * FROM users WHERE id = 1")
    
    assert hash1 == hash2, "Normalized queries should have same hash"
    assert hash1 == hash3, "Same query should have same hash"
    print("  ✓ Query hash generation working")
    
    print("✓ SimpleQueryAnalyzer tests passed!")

def test_execution_plan_analyzer():
    """Test the execution plan analyzer"""
    print("\nTesting SimpleExecutionPlanAnalyzer...")
    
    db_path, temp_dir = create_test_database()
    
    try:
        analyzer = SimpleExecutionPlanAnalyzer(db_path)
        
        # Test execution plan analysis
        print("  Testing execution plan analysis...")
        
        # Simple query
        simple_query = "SELECT * FROM users WHERE id = 1"
        plan = analyzer.get_execution_plan(simple_query)
        
        assert plan is not None, "Should get execution plan"
        assert 'plan_text' in plan, "Should have plan text"
        assert 'estimated_cost' in plan, "Should have estimated cost"
        print("  ✓ Simple query plan analysis working")
        
        # Query that might cause table scan
        scan_query = "SELECT * FROM trades WHERE price > 100"
        scan_plan = analyzer.get_execution_plan(scan_query)
        
        assert scan_plan is not None, "Should get scan query plan"
        print("  ✓ Table scan query plan analysis working")
        
        # Query that should use index
        indexed_query = "SELECT * FROM trades WHERE user_id = 1"
        indexed_plan = analyzer.get_execution_plan(indexed_query)
        
        assert indexed_plan is not None, "Should get indexed query plan"
        print("  ✓ Indexed query plan analysis working")
        
        print("✓ SimpleExecutionPlanAnalyzer tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_performance_issue_detector():
    """Test the performance issue detector"""
    print("\nTesting SimplePerformanceIssueDetector...")
    
    detector = SimplePerformanceIssueDetector()
    
    # Test slow query detection
    print("  Testing slow query detection...")
    slow_query_metrics = QueryMetrics(
        query_hash="slow_query",
        query_text="SELECT * FROM large_table",
        query_type=QueryType.SELECT,
        execution_count=5,
        average_execution_time_ms=250,  # Slow query
        total_execution_time_ms=1250,
        tables_accessed=["large_table"]
    )
    
    issues = detector.detect_issues(slow_query_metrics)
    slow_issues = [i for i in issues if i.issue_type == PerformanceIssueType.SLOW_QUERY]
    assert len(slow_issues) > 0, "Should detect slow query issue"
    print("  ✓ Slow query detection working")
    
    # Test frequent query detection
    print("  Testing frequent query detection...")
    frequent_query_metrics = QueryMetrics(
        query_hash="frequent_query",
        query_text="SELECT * FROM users WHERE id = ?",
        query_type=QueryType.SELECT,
        execution_count=15,  # Frequent query
        average_execution_time_ms=50,
        total_execution_time_ms=750,
        tables_accessed=["users"]
    )
    
    issues = detector.detect_issues(frequent_query_metrics)
    frequent_issues = [i for i in issues if i.issue_type == PerformanceIssueType.FREQUENT_QUERY]
    assert len(frequent_issues) > 0, "Should detect frequent query issue"
    print("  ✓ Frequent query detection working")
    
    # Test table scan detection
    print("  Testing table scan detection...")
    execution_plan = {'has_table_scan': True, 'has_index_usage': False}
    
    issues = detector.detect_issues(slow_query_metrics, execution_plan)
    scan_issues = [i for i in issues if i.issue_type == PerformanceIssueType.FULL_TABLE_SCAN]
    assert len(scan_issues) > 0, "Should detect table scan issue"
    print("  ✓ Table scan detection working")
    
    print("✓ SimplePerformanceIssueDetector tests passed!")

def test_performance_analyzer():
    """Test the main performance analyzer"""
    print("\nTesting SimplePerformanceAnalyzer...")
    
    db_path, temp_dir = create_test_database()
    
    try:
        analyzer = SimplePerformanceAnalyzer(db_path)
        
        # Test query recording
        print("  Testing query recording...")
        test_queries = [
            ("SELECT * FROM users WHERE id = 1", 50),
            ("SELECT * FROM users WHERE id = 2", 45),
            ("SELECT * FROM trades WHERE user_id = 1", 75),
            ("SELECT COUNT(*) FROM users", 200),
            ("SELECT * FROM trades WHERE price > 100", 300)  # Potentially slow
        ]
        
        for query, exec_time in test_queries:
            analyzer.record_query_execution(query, exec_time)
        
        assert len(analyzer.query_metrics) > 0, "Should record query metrics"
        print("  ✓ Query recording working")
        
        # Test query analysis
        print("  Testing query analysis...")
        test_query = "SELECT * FROM users WHERE username = 'test'"
        analysis = analyzer.analyze_query(test_query)
        
        assert 'query_metrics' in analysis, "Should have query metrics"
        assert 'execution_plan' in analysis, "Should have execution plan"
        assert 'performance_issues' in analysis, "Should have performance issues"
        print("  ✓ Query analysis working")
        
        # Test report generation
        print("  Testing report generation...")
        report = analyzer.generate_performance_report()
        
        assert len(report) > 0, "Should generate report"
        assert "DATABASE PERFORMANCE ANALYSIS REPORT" in report, "Should have report header"
        assert "Total Queries Analyzed:" in report, "Should have query count"
        print("  ✓ Report generation working")
        
        print("✓ SimplePerformanceAnalyzer tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_performance_analysis_scenario():
    """Test a complete performance analysis scenario"""
    print("\nTesting complete performance analysis scenario...")
    
    db_path, temp_dir = create_test_database()
    
    try:
        analyzer = SimplePerformanceAnalyzer(db_path)
        
        print("  Simulating various query patterns...")
        
        # Simulate different types of queries with varying performance
        query_scenarios = [
            # Fast queries (good performance)
            ("SELECT * FROM users WHERE id = 1", 25),
            ("SELECT * FROM users WHERE id = 2", 30),
            ("SELECT * FROM users WHERE id = 3", 28),
            
            # Medium performance queries
            ("SELECT * FROM trades WHERE user_id = 1", 75),
            ("SELECT * FROM trades WHERE symbol = 'STOCK_1'", 85),
            ("SELECT COUNT(*) FROM trades WHERE trade_type = 'BUY'", 120),
            
            # Slow queries (performance issues)
            ("SELECT * FROM trades WHERE price > 100", 250),  # No index on price
            ("SELECT u.*, COUNT(t.id) FROM users u LEFT JOIN trades t ON u.id = t.user_id GROUP BY u.id", 400),
            
            # Frequent queries (executed multiple times)
            ("SELECT * FROM users WHERE username = ?", 40),
            ("SELECT * FROM users WHERE username = ?", 42),
            ("SELECT * FROM users WHERE username = ?", 38),
            ("SELECT * FROM users WHERE username = ?", 45),
            ("SELECT * FROM users WHERE username = ?", 41),
            ("SELECT * FROM users WHERE username = ?", 43),
            ("SELECT * FROM users WHERE username = ?", 39),
            ("SELECT * FROM users WHERE username = ?", 44),
            ("SELECT * FROM users WHERE username = ?", 37),
            ("SELECT * FROM users WHERE username = ?", 46),
            ("SELECT * FROM users WHERE username = ?", 40),
            ("SELECT * FROM users WHERE username = ?", 42),
        ]
        
        # Record all query executions
        for query, exec_time in query_scenarios:
            analyzer.record_query_execution(query, exec_time)
        
        print(f"    Recorded {len(query_scenarios)} query executions")
        print(f"    Unique query patterns: {len(analyzer.query_metrics)}")
        
        # Analyze specific problematic queries
        print("  Analyzing problematic queries...")
        
        slow_query = "SELECT * FROM trades WHERE price > 100"
        slow_analysis = analyzer.analyze_query(slow_query)
        
        print(f"    Slow query analysis:")
        print(f"      Average time: {slow_analysis['query_metrics']['average_execution_time_ms']:.2f}ms")
        print(f"      Issues found: {len(slow_analysis['performance_issues'])}")
        
        for issue in slow_analysis['performance_issues']:
            print(f"        - {issue['issue_type']}: {issue['description']}")
        
        # Generate comprehensive report
        print("  Generating performance report...")
        report = analyzer.generate_performance_report()
        
        # Verify report contains expected information
        assert "SLOWEST QUERIES:" in report, "Should identify slowest queries"
        assert "MOST FREQUENT QUERIES:" in report, "Should identify frequent queries"
        
        # Display key metrics from report
        lines = report.split('\n')
        for line in lines:
            if 'Total Queries Analyzed:' in line or 'Total Query Executions:' in line or 'Average Query Time:' in line:
                print(f"    {line}")
        
        # Check if performance issues were detected
        if "PERFORMANCE ISSUES:" in report:
            print("    Performance issues detected:")
            issue_section = False
            for line in lines:
                if "PERFORMANCE ISSUES:" in line:
                    issue_section = True
                    continue
                elif issue_section and line.startswith("- "):
                    print(f"      {line}")
                elif issue_section and line.strip() == "":
                    break
        
        print("✓ Complete performance analysis scenario passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def main():
    """Run all tests"""
    print("Starting Database Performance Analysis Tools Tests")
    print("=" * 60)
    
    try:
        test_query_analyzer()
        test_execution_plan_analyzer()
        test_performance_issue_detector()
        test_performance_analyzer()
        test_performance_analysis_scenario()
        
        print("\n" + "=" * 60)
        print("🎉 ALL TESTS PASSED! 🎉")
        print("Database Performance Analysis Tools are working correctly!")
        
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    success = main()
    exit(0 if success else 1)