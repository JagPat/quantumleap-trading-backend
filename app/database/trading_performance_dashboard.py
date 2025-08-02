"""
Trading Performance Dashboard
Real-time performance monitoring dashboard for optimized trading database
"""
import asyncio
import logging
from typing import Dict, List, Any, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict
import json

from .trading_engine_integration import trading_db_integration

logger = logging.getLogger(__name__)

@dataclass
class PerformanceMetric:
    """Performance metric data structure"""
    name: str
    value: float
    unit: str
    timestamp: datetime
    category: str
    threshold_warning: Optional[float] = None
    threshold_critical: Optional[float] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'name': self.name,
            'value': self.value,
            'unit': self.unit,
            'timestamp': self.timestamp.isoformat(),
            'category': self.category,
            'threshold_warning': self.threshold_warning,
            'threshold_critical': self.threshold_critical,
            'status': self._get_status()
        }
    
    def _get_status(self) -> str:
        """Get metric status based on thresholds"""
        if self.threshold_critical and self.value >= self.threshold_critical:
            return 'critical'
        elif self.threshold_warning and self.value >= self.threshold_warning:
            return 'warning'
        else:
            return 'normal'

class TradingPerformanceDashboard:
    """
    Real-time performance dashboard for trading database operations
    """
    
    def __init__(self):
        self.integration = trading_db_integration
        self.metrics_history = []
        self.max_history_size = 1000
        self.update_interval = 30  # seconds
        self.monitoring_task = None
        
        # Performance thresholds
        self.thresholds = {
            'query_latency_ms': {'warning': 500, 'critical': 1000},
            'transaction_latency_ms': {'warning': 1000, 'critical': 2000},
            'error_rate_percent': {'warning': 1.0, 'critical': 5.0},
            'connection_pool_usage_percent': {'warning': 80.0, 'critical': 95.0},
            'database_size_mb': {'warning': 1000, 'critical': 2000},
            'active_connections': {'warning': 50, 'critical': 80}
        }
        
        logger.info("TradingPerformanceDashboard initialized")
    
    async def start_monitoring(self):
        """Start real-time performance monitoring"""
        if self.monitoring_task is None or self.monitoring_task.done():
            self.monitoring_task = asyncio.create_task(self._monitoring_loop())
            logger.info("Performance monitoring started")
    
    async def stop_monitoring(self):
        """Stop performance monitoring"""
        if self.monitoring_task and not self.monitoring_task.done():
            self.monitoring_task.cancel()
            try:
                await self.monitoring_task
            except asyncio.CancelledError:
                pass
            logger.info("Performance monitoring stopped")
    
    async def _monitoring_loop(self):
        """Main monitoring loop"""
        while True:
            try:
                await self._collect_metrics()
                await asyncio.sleep(self.update_interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in monitoring loop: {e}")
                await asyncio.sleep(self.update_interval)
    
    async def _collect_metrics(self):
        """Collect performance metrics"""
        try:
            timestamp = datetime.now()
            
            # Get database performance metrics
            db_metrics = await self.integration.get_performance_dashboard_data()
            
            # Convert to PerformanceMetric objects
            metrics = []
            
            # Database performance metrics
            if 'database_performance' in db_metrics:
                perf_data = db_metrics['database_performance']
                
                if 'average_query_time_ms' in perf_data:
                    metrics.append(PerformanceMetric(
                        name='Query Latency',
                        value=perf_data['average_query_time_ms'],
                        unit='ms',
                        timestamp=timestamp,
                        category='database',
                        threshold_warning=self.thresholds['query_latency_ms']['warning'],
                        threshold_critical=self.thresholds['query_latency_ms']['critical']
                    ))
                
                if 'transaction_count' in perf_data:
                    metrics.append(PerformanceMetric(
                        name='Transaction Count',
                        value=perf_data['transaction_count'],
                        unit='count',
                        timestamp=timestamp,
                        category='database'
                    ))
                
                if 'error_rate_percent' in perf_data:
                    metrics.append(PerformanceMetric(
                        name='Error Rate',
                        value=perf_data['error_rate_percent'],
                        unit='%',
                        timestamp=timestamp,
                        category='database',
                        threshold_warning=self.thresholds['error_rate_percent']['warning'],
                        threshold_critical=self.thresholds['error_rate_percent']['critical']
                    ))
            
            # Database health metrics
            if 'database_health' in db_metrics:
                health_data = db_metrics['database_health']
                
                if 'connection_count' in health_data:
                    metrics.append(PerformanceMetric(
                        name='Active Connections',
                        value=health_data['connection_count'],
                        unit='count',
                        timestamp=timestamp,
                        category='connections',
                        threshold_warning=self.thresholds['active_connections']['warning'],
                        threshold_critical=self.thresholds['active_connections']['critical']
                    ))
                
                if 'database_size_mb' in health_data:
                    metrics.append(PerformanceMetric(
                        name='Database Size',
                        value=health_data['database_size_mb'],
                        unit='MB',
                        timestamp=timestamp,
                        category='storage',
                        threshold_warning=self.thresholds['database_size_mb']['warning'],
                        threshold_critical=self.thresholds['database_size_mb']['critical']
                    ))
            
            # Query optimization metrics
            if 'query_optimization' in db_metrics:
                opt_data = db_metrics['query_optimization']
                
                if 'optimization_rate_percent' in opt_data:
                    metrics.append(PerformanceMetric(
                        name='Query Optimization Rate',
                        value=opt_data['optimization_rate_percent'],
                        unit='%',
                        timestamp=timestamp,
                        category='optimization'
                    ))
                
                if 'cache_hit_rate_percent' in opt_data:
                    metrics.append(PerformanceMetric(
                        name='Cache Hit Rate',
                        value=opt_data['cache_hit_rate_percent'],
                        unit='%',
                        timestamp=timestamp,
                        category='optimization'
                    ))
            
            # Transaction statistics
            if 'transaction_statistics' in db_metrics:
                trans_data = db_metrics['transaction_statistics']
                
                if 'average_transaction_time_ms' in trans_data:
                    metrics.append(PerformanceMetric(
                        name='Transaction Latency',
                        value=trans_data['average_transaction_time_ms'],
                        unit='ms',
                        timestamp=timestamp,
                        category='transactions',
                        threshold_warning=self.thresholds['transaction_latency_ms']['warning'],
                        threshold_critical=self.thresholds['transaction_latency_ms']['critical']
                    ))
                
                if 'rollback_rate_percent' in trans_data:
                    metrics.append(PerformanceMetric(
                        name='Transaction Rollback Rate',
                        value=trans_data['rollback_rate_percent'],
                        unit='%',
                        timestamp=timestamp,
                        category='transactions'
                    ))
            
            # Add metrics to history
            self.metrics_history.extend(metrics)
            
            # Trim history if too large
            if len(self.metrics_history) > self.max_history_size:
                self.metrics_history = self.metrics_history[-self.max_history_size:]
            
            # Log critical metrics
            critical_metrics = [m for m in metrics if m._get_status() == 'critical']
            if critical_metrics:
                logger.warning(f"Critical performance metrics detected: {[m.name for m in critical_metrics]}")
            
        except Exception as e:
            logger.error(f"Error collecting metrics: {e}")
    
    async def get_current_metrics(self) -> List[Dict[str, Any]]:
        """Get current performance metrics"""
        try:
            # Get latest metrics for each category
            latest_metrics = {}
            
            for metric in reversed(self.metrics_history):
                key = f"{metric.category}_{metric.name}"
                if key not in latest_metrics:
                    latest_metrics[key] = metric
            
            return [metric.to_dict() for metric in latest_metrics.values()]
            
        except Exception as e:
            logger.error(f"Error getting current metrics: {e}")
            return []
    
    async def get_metrics_history(self, hours: int = 24) -> List[Dict[str, Any]]:
        """Get metrics history for specified time period"""
        try:
            cutoff_time = datetime.now() - timedelta(hours=hours)
            
            filtered_metrics = [
                metric for metric in self.metrics_history
                if metric.timestamp >= cutoff_time
            ]
            
            return [metric.to_dict() for metric in filtered_metrics]
            
        except Exception as e:
            logger.error(f"Error getting metrics history: {e}")
            return []
    
    async def get_performance_summary(self) -> Dict[str, Any]:
        """Get performance summary with key statistics"""
        try:
            current_metrics = await self.get_current_metrics()
            
            # Calculate summary statistics
            summary = {
                'timestamp': datetime.now().isoformat(),
                'total_metrics': len(current_metrics),
                'status_breakdown': {
                    'normal': 0,
                    'warning': 0,
                    'critical': 0
                },
                'categories': {},
                'alerts': []
            }
            
            # Process current metrics
            for metric in current_metrics:
                status = metric['status']
                summary['status_breakdown'][status] += 1
                
                category = metric['category']
                if category not in summary['categories']:
                    summary['categories'][category] = {
                        'count': 0,
                        'normal': 0,
                        'warning': 0,
                        'critical': 0
                    }
                
                summary['categories'][category]['count'] += 1
                summary['categories'][category][status] += 1
                
                # Add alerts for warning/critical metrics
                if status in ['warning', 'critical']:
                    summary['alerts'].append({
                        'metric': metric['name'],
                        'value': metric['value'],
                        'unit': metric['unit'],
                        'status': status,
                        'category': category
                    })
            
            # Calculate overall health score (0-100)
            total_metrics = summary['total_metrics']
            if total_metrics > 0:
                normal_count = summary['status_breakdown']['normal']
                warning_count = summary['status_breakdown']['warning']
                critical_count = summary['status_breakdown']['critical']
                
                # Health score: normal=100%, warning=50%, critical=0%
                health_score = (normal_count * 100 + warning_count * 50) / total_metrics
                summary['health_score'] = round(health_score, 1)
            else:
                summary['health_score'] = 100.0
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting performance summary: {e}")
            return {}
    
    async def get_trading_specific_metrics(self) -> Dict[str, Any]:
        """Get trading-specific performance metrics"""
        try:
            # Get recent trading activity metrics
            trading_metrics = {
                'timestamp': datetime.now().isoformat(),
                'order_processing': {},
                'position_management': {},
                'execution_tracking': {},
                'signal_processing': {}
            }
            
            # Get database performance data
            db_metrics = await self.integration.get_performance_dashboard_data()
            
            # Extract trading-specific metrics
            if 'database_performance' in db_metrics:
                perf_data = db_metrics['database_performance']
                
                # Order processing metrics
                trading_metrics['order_processing'] = {
                    'orders_per_second': perf_data.get('orders_per_second', 0),
                    'average_order_latency_ms': perf_data.get('average_order_latency_ms', 0),
                    'order_success_rate_percent': perf_data.get('order_success_rate_percent', 100)
                }
                
                # Position management metrics
                trading_metrics['position_management'] = {
                    'positions_updated_per_second': perf_data.get('positions_updated_per_second', 0),
                    'position_calculation_latency_ms': perf_data.get('position_calculation_latency_ms', 0),
                    'position_accuracy_percent': perf_data.get('position_accuracy_percent', 100)
                }
                
                # Execution tracking metrics
                trading_metrics['execution_tracking'] = {
                    'executions_per_second': perf_data.get('executions_per_second', 0),
                    'execution_recording_latency_ms': perf_data.get('execution_recording_latency_ms', 0),
                    'execution_data_integrity_percent': perf_data.get('execution_data_integrity_percent', 100)
                }
                
                # Signal processing metrics
                trading_metrics['signal_processing'] = {
                    'signals_processed_per_second': perf_data.get('signals_processed_per_second', 0),
                    'signal_to_order_latency_ms': perf_data.get('signal_to_order_latency_ms', 0),
                    'signal_conversion_rate_percent': perf_data.get('signal_conversion_rate_percent', 0)
                }
            
            return trading_metrics
            
        except Exception as e:
            logger.error(f"Error getting trading-specific metrics: {e}")
            return {}
    
    async def export_metrics(self, format: str = 'json', hours: int = 24) -> str:
        """Export metrics data in specified format"""
        try:
            metrics_data = await self.get_metrics_history(hours)
            summary = await self.get_performance_summary()
            trading_metrics = await self.get_trading_specific_metrics()
            
            export_data = {
                'export_timestamp': datetime.now().isoformat(),
                'time_period_hours': hours,
                'summary': summary,
                'trading_metrics': trading_metrics,
                'detailed_metrics': metrics_data
            }
            
            if format.lower() == 'json':
                return json.dumps(export_data, indent=2)
            else:
                # Could add CSV, XML, or other formats here
                return json.dumps(export_data, indent=2)
                
        except Exception as e:
            logger.error(f"Error exporting metrics: {e}")
            return "{}"
    
    async def get_dashboard_data(self) -> Dict[str, Any]:
        """Get comprehensive dashboard data for frontend"""
        try:
            current_metrics = await self.get_current_metrics()
            summary = await self.get_performance_summary()
            trading_metrics = await self.get_trading_specific_metrics()
            
            # Get recent history for charts (last 2 hours)
            recent_history = await self.get_metrics_history(hours=2)
            
            # Organize data for dashboard
            dashboard_data = {
                'timestamp': datetime.now().isoformat(),
                'health_score': summary.get('health_score', 100),
                'status': 'healthy' if summary.get('health_score', 100) > 80 else 'warning' if summary.get('health_score', 100) > 60 else 'critical',
                'current_metrics': current_metrics,
                'summary': summary,
                'trading_metrics': trading_metrics,
                'charts_data': self._prepare_charts_data(recent_history),
                'alerts': summary.get('alerts', []),
                'system_info': {
                    'monitoring_active': self.monitoring_task and not self.monitoring_task.done(),
                    'update_interval_seconds': self.update_interval,
                    'metrics_history_size': len(self.metrics_history)
                }
            }
            
            return dashboard_data
            
        except Exception as e:
            logger.error(f"Error getting dashboard data: {e}")
            return {}
    
    def _prepare_charts_data(self, metrics_history: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Prepare data for dashboard charts"""
        try:
            charts_data = {
                'query_latency': [],
                'transaction_latency': [],
                'error_rate': [],
                'connection_count': [],
                'throughput': []
            }
            
            # Group metrics by name for chart data
            for metric in metrics_history:
                timestamp = metric['timestamp']
                value = metric['value']
                
                if metric['name'] == 'Query Latency':
                    charts_data['query_latency'].append({
                        'timestamp': timestamp,
                        'value': value
                    })
                elif metric['name'] == 'Transaction Latency':
                    charts_data['transaction_latency'].append({
                        'timestamp': timestamp,
                        'value': value
                    })
                elif metric['name'] == 'Error Rate':
                    charts_data['error_rate'].append({
                        'timestamp': timestamp,
                        'value': value
                    })
                elif metric['name'] == 'Active Connections':
                    charts_data['connection_count'].append({
                        'timestamp': timestamp,
                        'value': value
                    })
            
            return charts_data
            
        except Exception as e:
            logger.error(f"Error preparing charts data: {e}")
            return {}

# Global dashboard instance
trading_performance_dashboard = TradingPerformanceDashboard()