"""
Startup Monitor
Provides comprehensive visibility into startup process
"""
import logging
import time
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
from datetime import datetime
from fastapi import APIRouter

from .component_loader import ComponentStatusInfo, ComponentStatus

logger = logging.getLogger(__name__)

@dataclass
class StartupSummary:
    """Summary of startup process"""
    total_components: int
    loaded_successfully: int
    fallback_active: int
    failed_completely: int
    startup_duration: float
    startup_time: datetime
    components: List[ComponentStatusInfo]
    infrastructure_status: Dict[str, Any]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            "total_components": self.total_components,
            "loaded_successfully": self.loaded_successfully,
            "fallback_active": self.fallback_active,
            "failed_completely": self.failed_completely,
            "startup_duration": self.startup_duration,
            "startup_time": self.startup_time.isoformat(),
            "components": [
                {
                    "name": comp.name,
                    "status": comp.status.value,
                    "error_message": comp.error_message,
                    "load_time": comp.load_time.isoformat(),
                    "fallback_reason": comp.fallback_reason,
                    "load_duration": comp.load_duration
                }
                for comp in self.components
            ],
            "infrastructure_status": self.infrastructure_status
        }

class StartupMonitor:
    """Monitors and logs startup process with comprehensive visibility"""
    
    def __init__(self):
        self.startup_start_time = time.time()
        self.startup_events: List[Dict[str, Any]] = []
        self.component_statuses: Dict[str, ComponentStatusInfo] = {}
        self.infrastructure_results: Dict[str, Any] = {}
        
    def log_startup_progress(self, component: str, status: str, 
                           details: str = None, duration: float = None) -> None:
        """
        Log startup progress with clear status indicators
        
        Args:
            component: Component name
            status: Status (loading, success, fallback, failed)
            details: Additional details
            duration: Time taken for this step
        """
        timestamp = datetime.now()
        
        # Choose appropriate emoji and log level
        status_indicators = {
            "loading": ("🔍", logging.INFO),
            "success": ("✅", logging.INFO),
            "fallback": ("🔄", logging.WARNING),
            "failed": ("❌", logging.ERROR),
            "created": ("📁", logging.INFO),
            "validated": ("✔️", logging.INFO)
        }
        
        emoji, log_level = status_indicators.get(status, ("❓", logging.INFO))
        
        # Format message
        message = f"{emoji} {component}"
        if details:
            message += f": {details}"
        if duration:
            message += f" ({duration:.2f}s)"
        
        # Log the message
        logger.log(log_level, message)
        
        # Store event for summary
        event = {
            "timestamp": timestamp,
            "component": component,
            "status": status,
            "details": details,
            "duration": duration,
            "message": message
        }
        self.startup_events.append(event)
        
        # Print to console for immediate visibility
        print(message)
    
    def update_component_status(self, component_status: ComponentStatusInfo) -> None:
        """Update component status information"""
        self.component_statuses[component_status.name] = component_status
        
        # Log component status update
        status_messages = {
            ComponentStatus.LOADED: "loaded successfully",
            ComponentStatus.FALLBACK: "running in fallback mode",
            ComponentStatus.FAILED: "failed to load"
        }
        
        message = status_messages.get(component_status.status, "status unknown")
        self.log_startup_progress(
            component_status.name,
            component_status.status.value,
            message,
            component_status.load_duration
        )
    
    def set_infrastructure_results(self, results: Dict[str, Any]) -> None:
        """Set infrastructure validation results"""
        self.infrastructure_results = results
        
        # Log infrastructure results
        for category, result in results.items():
            if hasattr(result, 'success'):
                status = "success" if result.success else "failed"
                details = result.message
                self.log_startup_progress(f"Infrastructure {category}", status, details)
    
    def generate_startup_summary(self) -> StartupSummary:
        """Generate comprehensive startup summary"""
        startup_duration = time.time() - self.startup_start_time
        
        # Count component statuses
        loaded_count = sum(1 for status in self.component_statuses.values() 
                          if status.status == ComponentStatus.LOADED)
        fallback_count = sum(1 for status in self.component_statuses.values() 
                           if status.status == ComponentStatus.FALLBACK)
        failed_count = sum(1 for status in self.component_statuses.values() 
                         if status.status == ComponentStatus.FAILED)
        
        summary = StartupSummary(
            total_components=len(self.component_statuses),
            loaded_successfully=loaded_count,
            fallback_active=fallback_count,
            failed_completely=failed_count,
            startup_duration=startup_duration,
            startup_time=datetime.fromtimestamp(self.startup_start_time),
            components=list(self.component_statuses.values()),
            infrastructure_status=self.infrastructure_results
        )
        
        # Log summary
        self._log_startup_summary(summary)
        
        return summary
    
    def _log_startup_summary(self, summary: StartupSummary) -> None:
        """Log startup summary with clear formatting"""
        print("\n" + "="*60)
        print("🎯 STARTUP SUMMARY")
        print("="*60)
        
        print(f"⏱️  Total startup time: {summary.startup_duration:.2f}s")
        print(f"📊 Components: {summary.total_components} total")
        print(f"   ✅ Loaded successfully: {summary.loaded_successfully}")
        print(f"   🔄 Fallback active: {summary.fallback_active}")
        print(f"   ❌ Failed completely: {summary.failed_completely}")
        
        if summary.fallback_active > 0:
            print(f"\n⚠️  WARNING: {summary.fallback_active} components running in fallback mode")
            fallback_components = [comp for comp in summary.components 
                                 if comp.status == ComponentStatus.FALLBACK]
            for comp in fallback_components:
                print(f"   🔄 {comp.name}: {comp.fallback_reason}")
        
        if summary.failed_completely > 0:
            print(f"\n❌ ERROR: {summary.failed_completely} components failed completely")
            failed_components = [comp for comp in summary.components 
                               if comp.status == ComponentStatus.FAILED]
            for comp in failed_components:
                print(f"   ❌ {comp.name}: {comp.error_message}")
        
        # Infrastructure status
        if summary.infrastructure_status:
            print(f"\n🏗️  Infrastructure Status:")
            for category, result in summary.infrastructure_status.items():
                if hasattr(result, 'success'):
                    status_icon = "✅" if result.success else "❌"
                    print(f"   {status_icon} {category}: {result.message}")
        
        print("="*60)
        
        # Log to logger as well
        logger.info(f"Startup completed in {summary.startup_duration:.2f}s - "
                   f"{summary.loaded_successfully}/{summary.total_components} components loaded successfully")
        
        if summary.fallback_active > 0:
            logger.warning(f"{summary.fallback_active} components running in fallback mode")
        
        if summary.failed_completely > 0:
            logger.error(f"{summary.failed_completely} components failed completely")
    
    def create_health_endpoints(self) -> APIRouter:
        """Create health monitoring endpoints"""
        health_router = APIRouter(prefix="/health", tags=["Health Monitoring"])
        
        @health_router.get("/startup-summary")
        async def get_startup_summary():
            """Get comprehensive startup summary"""
            summary = self.generate_startup_summary()
            return summary.to_dict()
        
        @health_router.get("/component-status")
        async def get_component_status():
            """Get detailed component status information"""
            return {
                "components": {
                    name: {
                        "status": status.status.value,
                        "error_message": status.error_message,
                        "load_time": status.load_time.isoformat(),
                        "fallback_reason": status.fallback_reason,
                        "load_duration": status.load_duration,
                        "healthy": status.status == ComponentStatus.LOADED
                    }
                    for name, status in self.component_statuses.items()
                },
                "summary": {
                    "total": len(self.component_statuses),
                    "loaded": sum(1 for s in self.component_statuses.values() 
                                if s.status == ComponentStatus.LOADED),
                    "fallback": sum(1 for s in self.component_statuses.values() 
                                  if s.status == ComponentStatus.FALLBACK),
                    "failed": sum(1 for s in self.component_statuses.values() 
                                if s.status == ComponentStatus.FAILED)
                }
            }
        
        @health_router.get("/fallback-status")
        async def get_fallback_status():
            """Get information about components in fallback mode"""
            fallback_components = {
                name: {
                    "error_message": status.error_message,
                    "fallback_reason": status.fallback_reason,
                    "load_time": status.load_time.isoformat(),
                    "real_data": False,  # Clear indicator for frontend
                    "fallback_active": True
                }
                for name, status in self.component_statuses.items()
                if status.status == ComponentStatus.FALLBACK
            }
            
            return {
                "fallback_active": len(fallback_components) > 0,
                "fallback_count": len(fallback_components),
                "components": fallback_components,
                "message": "Some components are running in fallback mode with limited functionality" 
                          if fallback_components else "All components running normally"
            }
        
        @health_router.get("/startup-events")
        async def get_startup_events():
            """Get detailed startup events log"""
            return {
                "events": [
                    {
                        "timestamp": event["timestamp"].isoformat(),
                        "component": event["component"],
                        "status": event["status"],
                        "details": event["details"],
                        "duration": event["duration"],
                        "message": event["message"]
                    }
                    for event in self.startup_events
                ],
                "total_events": len(self.startup_events),
                "startup_duration": time.time() - self.startup_start_time
            }
        
        @health_router.get("/performance-metrics")
        async def get_performance_metrics():
            """Get startup performance metrics"""
            current_time = time.time()
            startup_duration = current_time - self.startup_start_time
            
            # Calculate component loading performance
            component_metrics = {}
            total_load_time = 0
            
            for name, status in self.component_statuses.items():
                component_metrics[name] = {
                    "load_duration": status.load_duration,
                    "status": status.status.value,
                    "load_time": status.load_time.isoformat(),
                    "performance_rating": self._get_performance_rating(status.load_duration)
                }
                total_load_time += status.load_duration
            
            # Calculate overall performance metrics
            avg_load_time = total_load_time / len(self.component_statuses) if self.component_statuses else 0
            
            return {
                "timestamp": datetime.now().isoformat(),
                "startup_duration": startup_duration,
                "total_component_load_time": total_load_time,
                "average_component_load_time": avg_load_time,
                "components": component_metrics,
                "performance_summary": {
                    "startup_speed": self._get_startup_speed_rating(startup_duration),
                    "component_efficiency": self._get_efficiency_rating(avg_load_time),
                    "total_components": len(self.component_statuses),
                    "fastest_component": self._get_fastest_component(),
                    "slowest_component": self._get_slowest_component()
                }
            }
        
        @health_router.get("/memory-usage")
        async def get_memory_usage():
            """Get memory usage information during startup"""
            try:
                import psutil
                process = psutil.Process()
                memory_info = process.memory_info()
                
                return {
                    "timestamp": datetime.now().isoformat(),
                    "memory_usage": {
                        "rss": memory_info.rss,  # Resident Set Size
                        "vms": memory_info.vms,  # Virtual Memory Size
                        "rss_mb": round(memory_info.rss / 1024 / 1024, 2),
                        "vms_mb": round(memory_info.vms / 1024 / 1024, 2)
                    },
                    "memory_percent": process.memory_percent(),
                    "startup_duration": time.time() - self.startup_start_time
                }
            except ImportError:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "error": "psutil not available for memory monitoring",
                    "startup_duration": time.time() - self.startup_start_time
                }
            except Exception as e:
                return {
                    "timestamp": datetime.now().isoformat(),
                    "error": f"Memory monitoring failed: {str(e)}",
                    "startup_duration": time.time() - self.startup_start_time
                }
        
        return health_router
    
    def get_startup_events(self) -> List[Dict[str, Any]]:
        """Get list of startup events"""
        return self.startup_events.copy()
    
    def get_component_statuses(self) -> Dict[str, ComponentStatusInfo]:
        """Get current component statuses"""
        return self.component_statuses.copy()
    
    def is_startup_healthy(self) -> bool:
        """Check if startup was generally healthy"""
        if not self.component_statuses:
            return False
        
        # Consider startup healthy if at least 50% of components loaded successfully
        loaded_count = sum(1 for status in self.component_statuses.values() 
                          if status.status == ComponentStatus.LOADED)
        total_count = len(self.component_statuses)
        
        return loaded_count >= (total_count * 0.5)
    
    def get_fallback_components_info(self) -> Dict[str, Dict[str, Any]]:
        """Get detailed information about fallback components for frontend transparency"""
        return {
            name: {
                "error_message": status.error_message,
                "fallback_reason": status.fallback_reason,
                "load_time": status.load_time.isoformat(),
                "real_data": False,
                "fallback_active": True,
                "warning": f"⚠️ {name.title()} service is in fallback mode - data may not be accurate"
            }
            for name, status in self.component_statuses.items()
            if status.status == ComponentStatus.FALLBACK
        }
    
    def _get_performance_rating(self, duration: float) -> str:
        """Get performance rating based on load duration"""
        if duration < 0.5:
            return "excellent"
        elif duration < 1.0:
            return "good"
        elif duration < 2.0:
            return "fair"
        else:
            return "slow"
    
    def _get_startup_speed_rating(self, duration: float) -> str:
        """Get overall startup speed rating"""
        if duration < 5.0:
            return "fast"
        elif duration < 10.0:
            return "moderate"
        elif duration < 20.0:
            return "slow"
        else:
            return "very_slow"
    
    def _get_efficiency_rating(self, avg_duration: float) -> str:
        """Get component loading efficiency rating"""
        if avg_duration < 0.3:
            return "highly_efficient"
        elif avg_duration < 0.7:
            return "efficient"
        elif avg_duration < 1.5:
            return "moderate"
        else:
            return "inefficient"
    
    def _get_fastest_component(self) -> Optional[Dict[str, Any]]:
        """Get the fastest loading component"""
        if not self.component_statuses:
            return None
        
        fastest = min(self.component_statuses.values(), key=lambda s: s.load_duration)
        return {
            "name": fastest.name,
            "duration": fastest.load_duration,
            "status": fastest.status.value
        }
    
    def _get_slowest_component(self) -> Optional[Dict[str, Any]]:
        """Get the slowest loading component"""
        if not self.component_statuses:
            return None
        
        slowest = max(self.component_statuses.values(), key=lambda s: s.load_duration)
        return {
            "name": slowest.name,
            "duration": slowest.load_duration,
            "status": slowest.status.value
        }