"""
Trading Engine System Health Monitoring
Provides comprehensive system health checks, metrics, and automated recovery
"""
import asyncio
import psutil
import sqlite3
import logging
import time
import json
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, asdict
from enum import Enum
from collections import defaultdict, deque
import subprocess
import socket
import requests
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """System health status levels"""
    HEALTHY = "HEALTHY"
    WARNING = "WARNING"
    CRITICAL = "CRITICAL"
    DOWN = "DOWN"

class ComponentType(Enum):
    """System component types"""
    DATABASE = "DATABASE"
    API_SERVER = "API_SERVER"
    MARKET_DATA = "MARKET_DATA"
    ORDER_EXECUTION = "ORDER_EXECUTION"
    RISK_ENGINE = "RISK_ENGINE"
    STRATEGY_MANAGER = "STRATEGY_MANAGER"
    ALERTING_SYSTEM = "ALERTING_SYSTEM"
    EVENT_BUS = "EVENT_BUS"
    EXTERNAL_API = "EXTERNAL_API"
    SYSTEM_RESOURCES = "SYSTEM_RESOURCES"

@dataclass
class HealthMetric:
    """Individual health metric"""
    name: str
    value: float
    unit: str
    status: HealthStatus
    threshold_warning: float
    threshold_critical: float
    timestamp: datetime
    details: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.details is None:
            self.details = {}

@dataclass
class ComponentHealth:
    """Health status of a system component"""
    component_id: str
    component_type: ComponentType
    status: HealthStatus
    metrics: List[HealthMetric]
    last_check: datetime
    uptime_seconds: float
    error_count: int = 0
    last_error: str = ""
    recovery_attempts: int = 0
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'component_id': self.component_id,
            'component_type': self.component_type.value,
            'status': self.status.value,
            'metrics': [asdict(m) for m in self.metrics],
            'last_check': self.last_check.isoformat(),
            'uptime_seconds': self.uptime_seconds,
            'error_count': self.error_count,
            'last_error': self.last_error,
            'recovery_attempts': self.recovery_attempts
        }

@dataclass
class SystemHealth:
    """Overall system health status"""
    overall_status: HealthStatus
    components: List[ComponentHealth]
    timestamp: datetime
    total_components: int
    healthy_components: int
    warning_components: int
    critical_components: int
    down_components: int
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'overall_status': self.overall_status.value,
            'components': [c.to_dict() for c in self.components],
            'timestamp': self.timestamp.isoformat(),
            'total_components': self.total_components,
            'healthy_components': self.healthy_components,
            'warning_components': self.warning_components,
            'critical_components': self.critical_components,
            'down_components': self.down_components
        }

class HealthChecker:
    """Base class for health checkers"""
    
    def __init__(self, component_id: str, component_type: ComponentType):
        self.component_id = component_id
        self.component_type = component_type
        self.start_time = datetime.now()
        self.error_count = 0
        self.last_error = ""
    
    async def check_health(self) -> ComponentHealth:
        """Check component health - to be implemented by subclasses"""
        raise NotImplementedError
    
    def _create_metric(self, name: str, value: float, unit: str, 
                      warning_threshold: float, critical_threshold: float) -> HealthMetric:
        """Create a health metric with status determination"""
        if value >= critical_threshold:
            status = HealthStatus.CRITICAL
        elif value >= warning_threshold:
            status = HealthStatus.WARNING
        else:
            status = HealthStatus.HEALTHY
        
        return HealthMetric(
            name=name,
            value=value,
            unit=unit,
            status=status,
            threshold_warning=warning_threshold,
            threshold_critical=critical_threshold,
            timestamp=datetime.now()
        )

class DatabaseHealthChecker(HealthChecker):
    """Database health checker"""
    
    def __init__(self, db_path: str):
        super().__init__("database", ComponentType.DATABASE)
        self.db_path = db_path
    
    async def check_health(self) -> ComponentHealth:
        """Check database health"""
        metrics = []
        status = HealthStatus.HEALTHY
        
        try:
            # Connection test
            start_time = time.time()
            with sqlite3.connect(self.db_path, timeout=5) as conn:
                cursor = conn.execute("SELECT 1")
                cursor.fetchone()
            connection_time = (time.time() - start_time) * 1000
            
            metrics.append(self._create_metric(
                "connection_time", connection_time, "ms", 100, 500
            ))
            
            # Database size
            db_size = Path(self.db_path).stat().st_size / (1024 * 1024)  # MB
            metrics.append(self._create_metric(
                "database_size", db_size, "MB", 500, 1000
            ))
            
            # Table count and row counts
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                )
                tables = cursor.fetchall()
                
                total_rows = 0
                for table in tables:
                    cursor = conn.execute(f"SELECT COUNT(*) FROM {table[0]}")
                    count = cursor.fetchone()[0]
                    total_rows += count
                
                metrics.append(self._create_metric(
                    "total_rows", total_rows, "rows", 100000, 500000
                ))
                
                metrics.append(self._create_metric(
                    "table_count", len(tables), "tables", 20, 50
                ))
            
            # Determine overall status
            for metric in metrics:
                if metric.status == HealthStatus.CRITICAL:
                    status = HealthStatus.CRITICAL
                    break
                elif metric.status == HealthStatus.WARNING and status == HealthStatus.HEALTHY:
                    status = HealthStatus.WARNING
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            status = HealthStatus.DOWN
            logger.error(f"Database health check failed: {e}")
        
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return ComponentHealth(
            component_id=self.component_id,
            component_type=self.component_type,
            status=status,
            metrics=metrics,
            last_check=datetime.now(),
            uptime_seconds=uptime,
            error_count=self.error_count,
            last_error=self.last_error
        )

class APIServerHealthChecker(HealthChecker):
    """API server health checker"""
    
    def __init__(self, base_url: str, endpoints: List[str] = None):
        super().__init__("api_server", ComponentType.API_SERVER)
        self.base_url = base_url
        self.endpoints = endpoints or ["/health", "/api/health"]
    
    async def check_health(self) -> ComponentHealth:
        """Check API server health"""
        metrics = []
        status = HealthStatus.HEALTHY
        
        try:
            # Test each endpoint
            response_times = []
            successful_endpoints = 0
            
            for endpoint in self.endpoints:
                try:
                    start_time = time.time()
                    response = requests.get(
                        f"{self.base_url}{endpoint}",
                        timeout=10
                    )
                    response_time = (time.time() - start_time) * 1000
                    response_times.append(response_time)
                    
                    if response.status_code == 200:
                        successful_endpoints += 1
                    
                except requests.RequestException:
                    response_times.append(10000)  # Timeout value
            
            # Average response time
            avg_response_time = sum(response_times) / len(response_times)
            metrics.append(self._create_metric(
                "avg_response_time", avg_response_time, "ms", 1000, 5000
            ))
            
            # Endpoint availability
            availability = (successful_endpoints / len(self.endpoints)) * 100
            metrics.append(self._create_metric(
                "endpoint_availability", availability, "%", 90, 50
            ))
            
            # Port connectivity test
            try:
                from urllib.parse import urlparse
                parsed_url = urlparse(self.base_url)
                host = parsed_url.hostname or 'localhost'
                port = parsed_url.port or (443 if parsed_url.scheme == 'https' else 80)
                
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(5)
                result = sock.connect_ex((host, port))
                sock.close()
                
                port_open = result == 0
                metrics.append(self._create_metric(
                    "port_connectivity", 1 if port_open else 0, "boolean", 0.5, 0.5
                ))
                
            except Exception:
                metrics.append(self._create_metric(
                    "port_connectivity", 0, "boolean", 0.5, 0.5
                ))
            
            # Determine overall status
            for metric in metrics:
                if metric.status == HealthStatus.CRITICAL:
                    status = HealthStatus.CRITICAL
                    break
                elif metric.status == HealthStatus.WARNING and status == HealthStatus.HEALTHY:
                    status = HealthStatus.WARNING
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            status = HealthStatus.DOWN
            logger.error(f"API server health check failed: {e}")
        
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return ComponentHealth(
            component_id=self.component_id,
            component_type=self.component_type,
            status=status,
            metrics=metrics,
            last_check=datetime.now(),
            uptime_seconds=uptime,
            error_count=self.error_count,
            last_error=self.last_error
        )

class SystemResourcesHealthChecker(HealthChecker):
    """System resources health checker"""
    
    def __init__(self):
        super().__init__("system_resources", ComponentType.SYSTEM_RESOURCES)
    
    async def check_health(self) -> ComponentHealth:
        """Check system resources health"""
        metrics = []
        status = HealthStatus.HEALTHY
        
        try:
            # CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            metrics.append(self._create_metric(
                "cpu_usage", cpu_percent, "%", 70, 90
            ))
            
            # Memory usage
            memory = psutil.virtual_memory()
            metrics.append(self._create_metric(
                "memory_usage", memory.percent, "%", 80, 95
            ))
            
            # Disk usage
            disk = psutil.disk_usage('/')
            disk_percent = (disk.used / disk.total) * 100
            metrics.append(self._create_metric(
                "disk_usage", disk_percent, "%", 80, 95
            ))
            
            # Network connections
            connections = len(psutil.net_connections())
            metrics.append(self._create_metric(
                "network_connections", connections, "connections", 1000, 2000
            ))
            
            # Process count
            process_count = len(psutil.pids())
            metrics.append(self._create_metric(
                "process_count", process_count, "processes", 300, 500
            ))
            
            # Load average (Unix-like systems)
            try:
                load_avg = psutil.getloadavg()[0]  # 1-minute load average
                cpu_count = psutil.cpu_count()
                load_percent = (load_avg / cpu_count) * 100
                metrics.append(self._create_metric(
                    "load_average", load_percent, "%", 70, 90
                ))
            except (AttributeError, OSError):
                # getloadavg not available on Windows
                pass
            
            # Determine overall status
            for metric in metrics:
                if metric.status == HealthStatus.CRITICAL:
                    status = HealthStatus.CRITICAL
                    break
                elif metric.status == HealthStatus.WARNING and status == HealthStatus.HEALTHY:
                    status = HealthStatus.WARNING
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            status = HealthStatus.DOWN
            logger.error(f"System resources health check failed: {e}")
        
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return ComponentHealth(
            component_id=self.component_id,
            component_type=self.component_type,
            status=status,
            metrics=metrics,
            last_check=datetime.now(),
            uptime_seconds=uptime,
            error_count=self.error_count,
            last_error=self.last_error
        )

class ExternalAPIHealthChecker(HealthChecker):
    """External API health checker"""
    
    def __init__(self, api_name: str, api_url: str, api_key: str = None):
        super().__init__(f"external_api_{api_name}", ComponentType.EXTERNAL_API)
        self.api_name = api_name
        self.api_url = api_url
        self.api_key = api_key
    
    async def check_health(self) -> ComponentHealth:
        """Check external API health"""
        metrics = []
        status = HealthStatus.HEALTHY
        
        try:
            headers = {}
            if self.api_key:
                headers['Authorization'] = f'Bearer {self.api_key}'
            
            start_time = time.time()
            response = requests.get(
                self.api_url,
                headers=headers,
                timeout=10
            )
            response_time = (time.time() - start_time) * 1000
            
            metrics.append(self._create_metric(
                "response_time", response_time, "ms", 2000, 10000
            ))
            
            # Status code check
            status_code_ok = 1 if response.status_code == 200 else 0
            metrics.append(self._create_metric(
                "status_code_ok", status_code_ok, "boolean", 0.5, 0.5
            ))
            
            # Rate limit check (if headers available)
            if 'X-RateLimit-Remaining' in response.headers:
                remaining = int(response.headers['X-RateLimit-Remaining'])
                limit = int(response.headers.get('X-RateLimit-Limit', 1000))
                usage_percent = ((limit - remaining) / limit) * 100
                
                metrics.append(self._create_metric(
                    "rate_limit_usage", usage_percent, "%", 80, 95
                ))
            
            # Determine overall status
            for metric in metrics:
                if metric.status == HealthStatus.CRITICAL:
                    status = HealthStatus.CRITICAL
                    break
                elif metric.status == HealthStatus.WARNING and status == HealthStatus.HEALTHY:
                    status = HealthStatus.WARNING
            
        except Exception as e:
            self.error_count += 1
            self.last_error = str(e)
            status = HealthStatus.DOWN
            logger.error(f"External API {self.api_name} health check failed: {e}")
        
        uptime = (datetime.now() - self.start_time).total_seconds()
        
        return ComponentHealth(
            component_id=self.component_id,
            component_type=self.component_type,
            status=status,
            metrics=metrics,
            last_check=datetime.now(),
            uptime_seconds=uptime,
            error_count=self.error_count,
            last_error=self.last_error
        )

class SystemHealthMonitor:
    """Main system health monitoring class"""
    
    def __init__(self, db_path: str = "system_health.db"):
        self.db_path = db_path
        self.health_checkers: Dict[str, HealthChecker] = {}
        self.health_history: deque = deque(maxlen=1000)  # Keep last 1000 checks
        self.monitoring_active = False
        self.monitoring_task = None
        self.check_interval = 30  # seconds
        self.recovery_handlers: Dict[ComponentType, Callable] = {}
        self.alert_callbacks: List[Callable] = []
        
        self._init_database()
        self._setup_default_checkers()
    
    def _init_database(self):
        """Initialize health monitoring database"""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS health_checks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    component_id TEXT NOT NULL,
                    component_type TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metrics TEXT NOT NULL,
                    uptime_seconds REAL,
                    error_count INTEGER DEFAULT 0,
                    last_error TEXT
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    component_id TEXT,
                    severity TEXT NOT NULL,
                    message TEXT NOT NULL,
                    details TEXT
                )
            """)
            
            # Create indexes for better performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_health_checks_timestamp 
                ON health_checks(timestamp)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_health_checks_component 
                ON health_checks(component_id, timestamp)
            """)
    
    def _setup_default_checkers(self):
        """Setup default health checkers"""
        # Database checker
        self.add_health_checker(DatabaseHealthChecker("trading_engine.db"))
        
        # API server checker
        self.add_health_checker(APIServerHealthChecker("http://localhost:8000"))
        
        # System resources checker
        self.add_health_checker(SystemResourcesHealthChecker())
        
        # External API checkers (examples)
        self.add_health_checker(ExternalAPIHealthChecker(
            "market_data", "https://api.example.com/health"
        ))
    
    def add_health_checker(self, checker: HealthChecker):
        """Add a health checker"""
        self.health_checkers[checker.component_id] = checker
        logger.info(f"Added health checker for {checker.component_id}")
    
    def remove_health_checker(self, component_id: str):
        """Remove a health checker"""
        if component_id in self.health_checkers:
            del self.health_checkers[component_id]
            logger.info(f"Removed health checker for {component_id}")
    
    def add_recovery_handler(self, component_type: ComponentType, handler: Callable):
        """Add recovery handler for component type"""
        self.recovery_handlers[component_type] = handler
        logger.info(f"Added recovery handler for {component_type.value}")
    
    def add_alert_callback(self, callback: Callable):
        """Add alert callback for health issues"""
        self.alert_callbacks.append(callback)
    
    async def check_all_components(self) -> SystemHealth:
        """Check health of all components"""
        component_healths = []
        
        # Run all health checks concurrently
        tasks = []
        for checker in self.health_checkers.values():
            tasks.append(checker.check_health())
        
        if tasks:
            component_healths = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Filter out exceptions and log them
            valid_healths = []
            for i, health in enumerate(component_healths):
                if isinstance(health, Exception):
                    checker_id = list(self.health_checkers.keys())[i]
                    logger.error(f"Health check failed for {checker_id}: {health}")
                else:
                    valid_healths.append(health)
            
            component_healths = valid_healths
        
        # Calculate overall system health
        total_components = len(component_healths)
        healthy_count = sum(1 for h in component_healths if h.status == HealthStatus.HEALTHY)
        warning_count = sum(1 for h in component_healths if h.status == HealthStatus.WARNING)
        critical_count = sum(1 for h in component_healths if h.status == HealthStatus.CRITICAL)
        down_count = sum(1 for h in component_healths if h.status == HealthStatus.DOWN)
        
        # Determine overall status
        if down_count > 0 or critical_count > total_components * 0.3:
            overall_status = HealthStatus.CRITICAL
        elif critical_count > 0 or warning_count > total_components * 0.5:
            overall_status = HealthStatus.WARNING
        else:
            overall_status = HealthStatus.HEALTHY
        
        system_health = SystemHealth(
            overall_status=overall_status,
            components=component_healths,
            timestamp=datetime.now(),
            total_components=total_components,
            healthy_components=healthy_count,
            warning_components=warning_count,
            critical_components=critical_count,
            down_components=down_count
        )
        
        # Store in history
        self.health_history.append(system_health)
        
        # Save to database
        self._save_health_check(system_health)
        
        # Trigger recovery if needed
        await self._handle_unhealthy_components(component_healths)
        
        # Send alerts if needed
        await self._send_health_alerts(system_health)
        
        return system_health
    
    def _save_health_check(self, system_health: SystemHealth):
        """Save health check results to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for component in system_health.components:
                    conn.execute("""
                        INSERT INTO health_checks 
                        (component_id, component_type, status, metrics, uptime_seconds, 
                         error_count, last_error)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (
                        component.component_id,
                        component.component_type.value,
                        component.status.value,
                        json.dumps([asdict(m) for m in component.metrics]),
                        component.uptime_seconds,
                        component.error_count,
                        component.last_error
                    ))
        except Exception as e:
            logger.error(f"Failed to save health check: {e}")
    
    async def _handle_unhealthy_components(self, components: List[ComponentHealth]):
        """Handle unhealthy components with recovery attempts"""
        for component in components:
            if component.status in [HealthStatus.CRITICAL, HealthStatus.DOWN]:
                # Log the issue
                self._log_system_event(
                    "COMPONENT_UNHEALTHY",
                    component.component_id,
                    component.status.value,
                    f"Component {component.component_id} is {component.status.value}",
                    {"error_count": component.error_count, "last_error": component.last_error}
                )
                
                # Attempt recovery
                recovery_handler = self.recovery_handlers.get(component.component_type)
                if recovery_handler and component.recovery_attempts < 3:
                    try:
                        logger.info(f"Attempting recovery for {component.component_id}")
                        await recovery_handler(component)
                        component.recovery_attempts += 1
                        
                        self._log_system_event(
                            "RECOVERY_ATTEMPTED",
                            component.component_id,
                            "INFO",
                            f"Recovery attempted for {component.component_id}",
                            {"attempt": component.recovery_attempts}
                        )
                    except Exception as e:
                        logger.error(f"Recovery failed for {component.component_id}: {e}")
    
    async def _send_health_alerts(self, system_health: SystemHealth):
        """Send health alerts to registered callbacks"""
        if system_health.overall_status in [HealthStatus.WARNING, HealthStatus.CRITICAL]:
            for callback in self.alert_callbacks:
                try:
                    await callback(system_health)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")
    
    def _log_system_event(self, event_type: str, component_id: str, severity: str, 
                         message: str, details: Dict[str, Any] = None):
        """Log system event to database"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO system_events 
                    (event_type, component_id, severity, message, details)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    event_type,
                    component_id,
                    severity,
                    message,
                    json.dumps(details) if details else None
                ))
        except Exception as e:
            logger.error(f"Failed to log system event: {e}")
    
    async def start_monitoring(self):
        """Start continuous health monitoring"""
        if self.monitoring_active:
            logger.warning("Health monitoring is already active")
            return
        
        self.monitoring_active = True
        self.monitoring_task = asyncio.create_task(self._monitoring_loop())
        logger.info("Started system health monitoring")
    
    async def stop_monitoring(self):
        """Stop health monitoring"""
        self.monitoring_active = False
        if self.monitoring_task:
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
        logger.info("Stopped system health monitoring")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while self.monitoring_active:
            try:
                await self.check_all_components()
                await asyncio.sleep(self.check_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.check_interval)
    
    def get_current_health(self) -> Optional[SystemHealth]:
        """Get current system health"""
        if self.health_history:
            return self.health_history[-1]
        return None
    
    def get_health_history(self, hours: int = 24) -> List[SystemHealth]:
        """Get health history for specified hours"""
        cutoff_time = datetime.now() - timedelta(hours=hours)
        return [h for h in self.health_history if h.timestamp >= cutoff_time]
    
    def get_component_metrics(self, component_id: str, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics for specific component"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    SELECT timestamp, status, metrics, uptime_seconds, error_count
                    FROM health_checks
                    WHERE component_id = ? AND timestamp >= ?
                    ORDER BY timestamp DESC
                """, (component_id, cutoff_time.isoformat()))
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'timestamp': row[0],
                        'status': row[1],
                        'metrics': json.loads(row[2]),
                        'uptime_seconds': row[3],
                        'error_count': row[4]
                    })
                
                return results
        except Exception as e:
            logger.error(f"Failed to get component metrics: {e}")
            return []
    
    def get_system_events(self, hours: int = 24, severity: str = None) -> List[Dict[str, Any]]:
        """Get system events"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            query = """
                SELECT timestamp, event_type, component_id, severity, message, details
                FROM system_events
                WHERE timestamp >= ?
            """
            params = [cutoff_time.isoformat()]
            
            if severity:
                query += " AND severity = ?"
                params.append(severity)
            
            query += " ORDER BY timestamp DESC"
            
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                
                results = []
                for row in cursor.fetchall():
                    results.append({
                        'timestamp': row[0],
                        'event_type': row[1],
                        'component_id': row[2],
                        'severity': row[3],
                        'message': row[4],
                        'details': json.loads(row[5]) if row[5] else None
                    })
                
                return results
        except Exception as e:
            logger.error(f"Failed to get system events: {e}")
            return []
    
    def get_health_statistics(self) -> Dict[str, Any]:
        """Get health statistics"""
        try:
            current_health = self.get_current_health()
            if not current_health:
                return {}
            
            # Calculate uptime percentage
            history_24h = self.get_health_history(24)
            if history_24h:
                healthy_checks = sum(1 for h in history_24h if h.overall_status == HealthStatus.HEALTHY)
                uptime_percentage = (healthy_checks / len(history_24h)) * 100
            else:
                uptime_percentage = 0
            
            # Get recent events
            recent_events = self.get_system_events(1)  # Last hour
            critical_events = [e for e in recent_events if e['severity'] == 'CRITICAL']
            
            return {
                'overall_status': current_health.overall_status.value,
                'total_components': current_health.total_components,
                'healthy_components': current_health.healthy_components,
                'warning_components': current_health.warning_components,
                'critical_components': current_health.critical_components,
                'down_components': current_health.down_components,
                'uptime_percentage_24h': round(uptime_percentage, 2),
                'recent_critical_events': len(critical_events),
                'monitoring_active': self.monitoring_active,
                'last_check': current_health.timestamp.isoformat()
            }
        except Exception as e:
            logger.error(f"Failed to get health statistics: {e}")
            return {}

# Global health monitor instance
system_health_monitor = SystemHealthMonitor()

# Recovery handlers
async def database_recovery_handler(component: ComponentHealth):
    """Recovery handler for database issues"""
    logger.info("Attempting database recovery...")
    # Add database-specific recovery logic here
    # For example: restart connection pool, repair database, etc.

async def api_server_recovery_handler(component: ComponentHealth):
    """Recovery handler for API server issues"""
    logger.info("Attempting API server recovery...")
    # Add API server recovery logic here
    # For example: restart server, clear cache, etc.

# Setup default recovery handlers
system_health_monitor.add_recovery_handler(
    ComponentType.DATABASE, database_recovery_handler
)
system_health_monitor.add_recovery_handler(
    ComponentType.API_SERVER, api_server_recovery_handler
)

# Health alert callback
async def health_alert_callback(system_health: SystemHealth):
    """Send health alerts"""
    try:
        # Import alerting system if available
        from .alerting_system import send_system_alert, AlertSeverity
        
        severity_map = {
            HealthStatus.WARNING: AlertSeverity.MEDIUM,
            HealthStatus.CRITICAL: AlertSeverity.HIGH,
            HealthStatus.DOWN: AlertSeverity.CRITICAL
        }
        
        severity = severity_map.get(system_health.overall_status, AlertSeverity.INFO)
        
        await send_system_alert(
            severity=severity,
            component="system_health_monitor",
            message=f"System health status: {system_health.overall_status.value}",
            additional_data={
                'total_components': system_health.total_components,
                'healthy_components': system_health.healthy_components,
                'critical_components': system_health.critical_components,
                'down_components': system_health.down_components
            }
        )
    except ImportError:
        logger.warning("Alerting system not available for health alerts")
    except Exception as e:
        logger.error(f"Failed to send health alert: {e}")

# Register health alert callback
system_health_monitor.add_alert_callback(health_alert_callback)