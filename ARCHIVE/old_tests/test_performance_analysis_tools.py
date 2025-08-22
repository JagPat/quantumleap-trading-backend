#!/usr/bin/env python3
"""
Comprehensive tests for the Database Performance Analysis Tools
"""

import os
import time
import tempfile
import shutil
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

# Import the system under test
from app.database.performance_analysis_tools import (
    PerformanceAnalysisTools,
    DatabaseProfiler,
    QueryAnalyzer,
    ExecutionPlanAnalyzer,
    PerformanceIssueDetector,
    PerformanceReportGenerator,
    QueryType,
    PerformanceIssueType,
    analyze_database_performance,
    get_query_recommendations
)

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
    
    cursor.execute("""
        CREATE TABLE portfolio (
            id INTEGER PRIMARY KEY,
            user_id INTEGER,
            symbol TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            avg_price REAL NOT NULL,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            UNIQUE(user_id, symbol)
        )
    """)
    
    # Create some indexes
    cursor.execute("CREATE INDEX idx_trades_user_id ON trades(user_id)")
    cursor.execute("CREATE INDEX idx_trades_symbol ON trades(symbol)")
    cursor.execute("CREATE INDEX idx_portfolio_user_symbol ON portfolio(user_id, symbol)")
    
    # Insert sample data
    for i in range(100):
        cursor.execute("INSERT INTO users (username, email) VALUES (?, ?)", 
                      (f"user_{i}", f"user_{i}@example.com"))
    
    for i in range(500):
        cursor.execute("INSERT INTO trades (user_id, symbol, quantity, price, trade_type) VALUES (?, ?, ?, ?, ?)",
                      (i % 100 + 1, f"STOCK_{i % 10}", (i % 100) + 1, 100.0 + (i % 50), "BUY" if i % 2 == 0 else "SELL"))
    
    for i in range(200):
        cursor.execute("INSERT INTO portfolio (user_id, symbol, quantity, avg_price) VALUES (?, ?, ?, ?)",
                      (i % 100 + 1, f"STOCK_{i % 10}", (i % 50) + 1, 100.0 + (i % 30)))
    
    conn.commit()
    conn.close()
    
    return db_path, temp_dir

def test_query_analyzer():
    """Test the QueryAnalyzer class"""
    print("Testing QueryAnalyzer...")
    
    analyzer = QueryAnalyzer()
    
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
    
    # Test complexity analysis
    print("  Testing complexity analysis...")
    simple_query = "SELECT * FROM users WHERE id = 1"
    complex_query = "SELECT u.*, COUNT(t.id) FROM users u JOIN trades t ON u.id = t.user_id GROUP BY u.id ORDER BY COUNT(t.id) DESC"
    
    simple_complexity = analyzer.analyze_query_complexity(simple_query)
    complex_complexity = analyzer.analyze_query_complexity(complex_query)
    
    assert simple_complexity['estimated_complexity'] in ['LOW', 'MEDIUM']
    assert complex_complexity['estimated_complexity'] in ['MEDIUM', 'HIGH']
    assert complex_complexity['complexity_score'] > simple_complexity['complexity_score']
    print("  ✓ Complexity analysis working")
    
    print("✓ QueryAnalyzer tests passed!")

def test_execution_plan_analyzer():
    """Test the ExecutionPlanAnalyzer class"""
    print("\nTesting ExecutionPlanAnalyzer...")
    
    db_path, temp_dir = create_test_database()
    
    try:
        analyzer = ExecutionPlanAnalyzer(db_path)
        
        # Test execution plan analysis
        print("  Testing execution plan analysis...")
        
        # Simple query
        simple_query = "SELECT * FROM users WHERE id = 1"
        plan = analyzer.get_execution_plan(simple_query)
        
        assert plan is not None, "Should get execution plan"
        assert plan.query_hash, "Should have query hash"
        assert plan.plan_text, "Should have plan text"
        assert plan.estimated_cost > 0, "Should have estimated cost"
        print("  ✓ Simple query plan analysis working")
        
        # Complex query with join
        complex_query = "SELECT u.username, COUNT(t.id) FROM users u JOIN trades t ON u.id = t.user_id GROUP BY u.username"
        complex_plan = analyzer.get_execution_plan(complex_query)
        
        assert complex_plan is not None, "Should get complex execution plan"
        assert complex_plan.estimated_cost >= plan.estimated_cost, "Complex query should have higher cost"
        print("  ✓ Complex query plan analysis working")
        
        # Query that should use index
        indexed_query = "SELECT * FROM trades WHERE user_id = 1"
        indexed_plan = analyzer.get_execution_plan(indexed_query)
        
        assert indexed_plan is not None, "Should get indexed query plan"
        print("  ✓ Indexed query plan analysis working")
        
        print("✓ ExecutionPlanAnalyzer tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_performance_issue_detector():
    """Test the PerformanceIssueDetector class"""
    print("\nTesting PerformanceIssueDetector...")
    
    detector = PerformanceIssueDetector()
    
    # Create mock query metrics for testing
    from app.database.performance_analysis_tools import QueryMetrics, ExecutionPlan
    
    # Test slow query detection
    print("  Testing slow query detection...")
    slow_query_metrics = QueryMetrics(
        query_hash="slow_query_hash",
        query_text="SELECT * FROM large_table",
        query_type=QueryType.SELECT,
        execution_count=10,
        total_execution_time_ms=15000,
        average_execution_time_ms=1500,  # Slow query
        min_execution_time_ms=1000,
        max_execution_time_ms=2000,
        median_execution_time_ms=1500,
        p95_execution_time_ms=1800,
        rows_examined=10000,
        rows_returned=1000,
        first_seen=datetime.now(),
        last_seen=datetime.now(),
        tables_accessed=["large_table"],
        indexes_used=[]
    )
    
    issues = detector.detect_issues(slow_query_metrics)
    slow_issues = [i for i in issues if i.issue_type == PerformanceIssueType.SLOW_QUERY]
    assert len(slow_issues) > 0, "Should detect slow query issue"
    print("  ✓ Slow query detection working")
    
    # Test frequent query detection
    print("  Testing frequent query detection...")
    frequent_query_metrics = QueryMetrics(
        query_hash="frequent_query_hash",
        query_text="SELECT * FROM users WHERE id = ?",
        query_type=QueryType.SELECT,
        execution_count=150,  # Frequent query
        total_execution_time_ms=7500,
        average_execution_time_ms=50,
        min_execution_time_ms=30,
        max_execution_time_ms=100,
        median_execution_time_ms=50,
        p95_execution_time_ms=80,
        rows_examined=1,
        rows_returned=1,
        first_seen=datetime.now(),
        last_seen=datetime.now(),
        tables_accessed=["users"],
        indexes_used=["PRIMARY"]
    )
    
    issues = detector.detect_issues(frequent_query_metrics)
    frequent_issues = [i for i in issues if i.issue_type == PerformanceIssueType.FREQUENT_QUERY]
    assert len(frequent_issues) > 0, "Should detect frequent query issue"
    print("  ✓ Frequent query detection working")
    
    print("✓ PerformanceIssueDetector tests passed!")

def test_database_profiler():
    """Test the DatabaseProfiler class"""
    print("\nTesting DatabaseProfiler...")
    
    db_path, temp_dir = create_test_database()
    
    try:
        profiler = DatabaseProfiler(db_path)
        
        # Test profiling session
        print("  Testing profiling session...")
        profile_id = profiler.start_profiling()
        assert profile_id.startswith("profile_"), "Should generate profile ID"
        print("  ✓ Profiling session started")
        
        # Test query recording
        print("  Testing query recording...")
        test_queries = [
            ("SELECT * FROM users WHERE id = 1", 50, 1),
            ("SELECT * FROM users WHERE id = 2", 45, 1),
            ("SELECT * FROM trades WHERE user_id = 1", 75, 5),
            ("SELECT COUNT(*) FROM users", 200, 1),
            ("SELECT u.*, t.* FROM users u JOIN trades t ON u.id = t.user_id", 300, 50)
        ]
        
        for query, exec_time, rows in test_queries:
            profiler.record_query_execution(query, exec_time, rows)
        
        assert len(profiler.query_metrics) > 0, "Should record query metrics"
        print("  ✓ Query recording working")
        
        # Test query analysis
        print("  Testing query analysis...")
        test_query = "SELECT * FROM users WHERE username = 'test'"
        metrics, plan, issues = profiler.analyze_query_performance(test_query)
        
        assert metrics is not None, "Should get query metrics"
        # plan might be None if query hasn't been executed
        assert isinstance(issues, list), "Should get list of issues"
        print("  ✓ Query analysis working")
        
        # Test profile generation
        print("  Testing profile generation...")
        profile = profiler.generate_database_profile()
        
        assert profile.total_queries > 0, "Should have total queries"
        assert profile.unique_queries > 0, "Should have unique queries"
        assert profile.average_query_time_ms > 0, "Should have average query time"
        assert len(profile.table_statistics) > 0, "Should have table statistics"
        print("  ✓ Profile generation working")
        
        print("✓ DatabaseProfiler tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_performance_report_generator():
    """Test the PerformanceReportGenerator class"""
    print("\nTesting PerformanceReportGenerator...")
    
    db_path, temp_dir = create_test_database()
    
    try:
        # Generate a profile to test with
        profiler = DatabaseProfiler(db_path)
        profiler.start_profiling()
        
        # Record some test queries
        test_queries = [
            ("SELECT * FROM users WHERE id = 1", 50, 1),
            ("SELECT COUNT(*) FROM trades", 200, 1),
            ("SELECT * FROM trades WHERE user_id = 1", 75, 5)
        ]
        
        for query, exec_time, rows in test_queries:
            profiler.record_query_execution(query, exec_time, rows)
        
        profile = profiler.generate_database_profile()
        
        # Test report generation
        generator = PerformanceReportGenerator()
        
        print("  Testing text report generation...")
        text_report = generator.generate_text_report(profile)
        
        assert len(text_report) > 0, "Should generate text report"
        assert "DATABASE PERFORMANCE ANALYSIS REPORT" in text_report, "Should have report header"
        assert "EXECUTIVE SUMMARY" in text_report, "Should have executive summary"
        assert str(profile.total_queries) in text_report, "Should include query count"
        print("  ✓ Text report generation working")
        
        print("  Testing JSON report generation...")
        json_report = generator.generate_json_report(profile)
        
        assert len(json_report) > 0, "Should generate JSON report"
        assert '"profile_id"' in json_report, "Should have profile ID in JSON"
        assert '"total_queries"' in json_report, "Should have total queries in JSON"
        print("  ✓ JSON report generation working")
        
        # Test report saving
        print("  Testing report saving...")
        results_dir = os.path.join(temp_dir, "reports")
        
        text_file = generator.save_report(profile, results_dir, 'text')
        json_file = generator.save_report(profile, results_dir, 'json')
        
        assert text_file and os.path.exists(text_file), "Should save text report file"
        assert json_file and os.path.exists(json_file), "Should save JSON report file"
        print("  ✓ Report saving working")
        
        print("✓ PerformanceReportGenerator tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_performance_analysis_tools():
    """Test the main PerformanceAnalysisTools class"""
    print("\nTesting PerformanceAnalysisTools...")
    
    db_path, temp_dir = create_test_database()
    results_dir = os.path.join(temp_dir, "analysis_results")
    
    try:
        tools = PerformanceAnalysisTools(db_path, results_dir)
        
        # Test single query analysis
        print("  Testing single query analysis...")
        test_query = "SELECT * FROM users WHERE username = 'test_user'"
        analysis = tools.analyze_query(test_query)
        
        assert 'query_metrics' in analysis, "Should have query metrics"
        assert 'performance_issues' in analysis, "Should have performance issues"
        assert 'analysis_timestamp' in analysis, "Should have analysis timestamp"
        print("  ✓ Single query analysis working")
        
        # Test profiling session
        print("  Testing profiling session...")
        session_id = tools.start_profiling_session()
        assert session_id.startswith("profile_"), "Should start profiling session"
        
        # Record some queries
        tools.record_query("SELECT * FROM users WHERE id = 1", 50, 1)
        tools.record_query("SELECT COUNT(*) FROM trades", 150, 1)
        tools.record_query("SELECT * FROM trades WHERE symbol = 'AAPL'", 75, 10)
        print("  ✓ Profiling session working")
        
        # Test performance report generation
        print("  Testing performance report generation...")
        report = tools.generate_performance_report(save_to_file=True, format='text')
        
        assert len(report) > 0, "Should generate performance report"
        assert "DATABASE PERFORMANCE ANALYSIS REPORT" in report, "Should have report header"
        
        # Check if file was saved
        report_files = list(Path(results_dir).glob("*.txt"))
        assert len(report_files) > 0, "Should save report file"
        print("  ✓ Performance report generation working")
        
        # Test optimization recommendations
        print("  Testing optimization recommendations...")
        recommendations = tools.get_optimization_recommendations()
        
        assert isinstance(recommendations, list), "Should return list of recommendations"
        assert len(recommendations) > 0, "Should have recommendations"
        print("  ✓ Optimization recommendations working")
        
        # Test performance summary
        print("  Testing performance summary...")
        summary = tools.get_performance_summary()
        
        assert 'total_queries' in summary, "Should have total queries"
        assert 'average_query_time_ms' in summary, "Should have average query time"
        assert 'total_issues' in summary, "Should have total issues"
        print("  ✓ Performance summary working")
        
        print("✓ PerformanceAnalysisTools tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_utility_functions():
    """Test utility functions"""
    print("\nTesting utility functions...")
    
    db_path, temp_dir = create_test_database()
    
    try:
        # Test analyze_database_performance
        print("  Testing analyze_database_performance...")
        output_dir = os.path.join(temp_dir, "analysis_output")
        
        report = analyze_database_performance(db_path, output_dir)
        
        assert len(report) > 0, "Should generate performance analysis report"
        assert "DATABASE PERFORMANCE ANALYSIS REPORT" in report, "Should have report header"
        
        # Check if output directory was created
        assert os.path.exists(output_dir), "Should create output directory"
        print("  ✓ analyze_database_performance working")
        
        # Test get_query_recommendations
        print("  Testing get_query_recommendations...")
        test_query = "SELECT * FROM users WHERE email = 'test@example.com'"
        recommendations = get_query_recommendations(db_path, test_query)
        
        assert isinstance(recommendations, list), "Should return list of recommendations"
        assert len(recommendations) > 0, "Should have recommendations"
        print("  ✓ get_query_recommendations working")
        
        print("✓ Utility functions tests passed!")
        
    finally:
        shutil.rmtree(temp_dir)

def test_integration_scenario():
    """Test a complete integration scenario"""
    print("\nTesting integration scenario...")
    
    db_path, temp_dir = create_test_database()
    
    try:
        # Simulate a realistic performance analysis scenario
        tools = PerformanceAnalysisTools(db_path)
        
        # Start profiling
        session_id = tools.start_profiling_session()
        print(f"  Started profiling session: {session_id}")
        
        # Simulate various queries with different performance characteristics
        queries_and_times = [
            # Fast queries
            ("SELECT * FROM users WHERE id = 1", 25, 1),
            ("SELECT * FROM users WHERE id = 2", 30, 1),
            ("SELECT * FROM users WHERE id = 3", 28, 1),
            
            # Medium queries
            ("SELECT * FROM trades WHERE user_id = 1", 75, 5),
            ("SELECT * FROM trades WHERE symbol = 'STOCK_1'", 85, 12),
            ("SELECT COUNT(*) FROM trades WHERE trade_type = 'BUY'", 120, 1),
            
            # Slow queries
            ("SELECT * FROM trades WHERE price > 100", 450, 200),  # No index on price
            ("SELECT u.*, COUNT(t.id) FROM users u LEFT JOIN trades t ON u.id = t.user_id GROUP BY u.id", 650, 100),
            
            # Frequent queries
            ("SELECT * FROM portfolio WHERE user_id = ?", 40, 3),  # Executed multiple times
            ("SELECT * FROM portfolio WHERE user_id = ?", 42, 3),
            ("SELECT * FROM portfolio WHERE user_id = ?", 38, 3),
            ("SELECT * FROM portfolio WHERE user_id = ?", 45, 3),
            ("SELECT * FROM portfolio WHERE user_id = ?", 41, 3),
        ]
        
        print("  Recording query executions...")
        for query, exec_time, rows in queries_and_times:
            tools.record_query(query, exec_time, rows)
        
        # Generate comprehensive analysis
        print("  Generating performance analysis...")
        report = tools.generate_performance_report(save_to_file=False)
        
        # Verify report contains expected sections
        assert "EXECUTIVE SUMMARY" in report, "Should have executive summary"
        assert "SLOWEST QUERIES" in report, "Should have slowest queries section"
        assert "MOST FREQUENT QUERIES" in report, "Should have frequent queries section"
        assert "OPTIMIZATION RECOMMENDATIONS" in report, "Should have recommendations"
        
        # Get performance summary
        summary = tools.get_performance_summary()
        
        print(f"    Total queries analyzed: {summary['total_queries']}")
        print(f"    Unique query patterns: {summary['unique_queries']}")
        print(f"    Average query time: {summary['average_query_time_ms']:.2f}ms")
        print(f"    Performance issues found: {summary['total_issues']}")
        print(f"    High severity issues: {summary['high_severity_issues']}")
        
        # Verify we detected some issues
        assert summary['total_queries'] > 0, "Should have analyzed queries"
        assert summary['unique_queries'] > 0, "Should have unique patterns"
        assert summary['average_query_time_ms'] > 0, "Should have average time"
        
        # Get recommendations
        recommendations = tools.get_optimization_recommendations()
        print(f"    Optimization recommendations: {len(recommendations)}")
        for i, rec in enumerate(recommendations[:3], 1):
            print(f"      {i}. {rec}")
        
        print("✓ Integration scenario test passed!")
        
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
        test_database_profiler()
        test_performance_report_generator()
        test_performance_analysis_tools()
        test_utility_functions()
        test_integration_scenario()
        
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