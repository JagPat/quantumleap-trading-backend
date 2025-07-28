"""
Component Loader
Loads routers with proper error isolation and fallback management
"""
import logging
import time
import traceback
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
from fastapi import APIRouter, HTTPException
from datetime import datetime

logger = logging.getLogger(__name__)

class ComponentStatus(Enum):
    """Status of a component during loading"""
    LOADED = "loaded"
    FALLBACK = "fallback"
    FAILED = "failed"

@dataclass
class RouterLoadResult:
    """Result of router loading attempt"""
    success: bool
    router: Optional[APIRouter]
    error: Optional[Exception]
    fallback_used: bool
    load_duration: float
    component_name: str
    error_details: Optional[str] = None

@dataclass
class ComponentStatusInfo:
    """Information about a component's status"""
    name: str
    status: ComponentStatus
    error_message: Optional[str]
    load_time: datetime
    fallback_reason: Optional[str]
    load_duration: float

class ComponentLoader:
    """Loads routers with proper error isolation and fallback management"""
    
    def __init__(self):
        self.component_statuses: Dict[str, ComponentStatusInfo] = {}
        self.loaded_routers: Dict[str, APIRouter] = {}
        self.fallback_routers: Dict[str, APIRouter] = {}
    
    def load_router_with_fallback(self, router_name: str, router_path: str, 
                                 fallback_prefix: str = None, 
                                 validate_syntax: bool = True) -> RouterLoadResult:
        """
        Load a router with automatic fallback on failure
        
        Args:
            router_name: Name of the component (e.g., "portfolio", "trading")
            router_path: Import path for the router (e.g., "app.portfolio.router")
            fallback_prefix: API prefix for fallback router (e.g., "/api/portfolio")
        
        Returns:
            RouterLoadResult with loading outcome
        """
        start_time = time.time()
        
        logger.info(f"🔍 Attempting to load {router_name} router from {router_path}")
        
        try:
            # Validate syntax if requested
            if validate_syntax:
                try:
                    from .syntax_error_fixer import SyntaxErrorFixer
                    
                    # Convert module path to file path
                    module_parts = router_path.split('.')
                    file_path = '/'.join(module_parts) + '.py'
                    
                    # Try to find the actual file path
                    import os
                    possible_paths = [
                        file_path,
                        os.path.join(os.getcwd(), file_path),
                        file_path.replace('/', os.sep)
                    ]
                    
                    actual_file_path = None
                    for path in possible_paths:
                        if os.path.exists(path):
                            actual_file_path = path
                            break
                    
                    if actual_file_path:
                        syntax_fixer = SyntaxErrorFixer()
                        validation_result = syntax_fixer.validate_router_syntax(actual_file_path)
                        
                        if not validation_result.valid:
                            logger.warning(f"Syntax issues detected in {actual_file_path}, attempting to fix...")
                            fix_result = syntax_fixer.fix_common_syntax_errors(actual_file_path)
                            
                            if fix_result.success:
                                logger.info(f"Successfully fixed syntax errors in {actual_file_path}")
                            else:
                                logger.error(f"Failed to fix syntax errors in {actual_file_path}")
                    
                except Exception as syntax_e:
                    logger.warning(f"Syntax validation failed for {router_name}: {str(syntax_e)}")
            
            # Attempt to import and load the production router
            module_parts = router_path.split('.')
            module_name = '.'.join(module_parts[:-1])
            router_attr = module_parts[-1]
            
            # Dynamic import
            module = __import__(module_name, fromlist=[router_attr])
            router = getattr(module, router_attr)
            
            if not isinstance(router, APIRouter):
                raise TypeError(f"Expected APIRouter, got {type(router)}")
            
            load_duration = time.time() - start_time
            
            # Track successful loading
            self.track_component_status(
                router_name, 
                ComponentStatus.LOADED, 
                None, 
                load_duration
            )
            
            self.loaded_routers[router_name] = router
            
            logger.info(f"✅ {router_name} router loaded successfully in {load_duration:.2f}s")
            
            return RouterLoadResult(
                success=True,
                router=router,
                error=None,
                fallback_used=False,
                load_duration=load_duration,
                component_name=router_name
            )
            
        except Exception as e:
            load_duration = time.time() - start_time
            error_details = traceback.format_exc()
            
            logger.error(f"❌ Failed to load {router_name} router: {str(e)}")
            logger.debug(f"Error details for {router_name}: {error_details}")
            
            # Create fallback router
            fallback_router = self.create_fallback_router(router_name, fallback_prefix, str(e))
            
            if fallback_router:
                self.track_component_status(
                    router_name,
                    ComponentStatus.FALLBACK,
                    str(e),
                    load_duration,
                    f"Production router failed, using fallback"
                )
                
                self.fallback_routers[router_name] = fallback_router
                
                logger.warning(f"🔄 {router_name} fallback router created")
                
                return RouterLoadResult(
                    success=False,
                    router=fallback_router,
                    error=e,
                    fallback_used=True,
                    load_duration=load_duration,
                    component_name=router_name,
                    error_details=error_details
                )
            else:
                self.track_component_status(
                    router_name,
                    ComponentStatus.FAILED,
                    str(e),
                    load_duration,
                    "Both production and fallback router creation failed"
                )
                
                logger.error(f"❌ {router_name} completely failed - no fallback available")
                
                return RouterLoadResult(
                    success=False,
                    router=None,
                    error=e,
                    fallback_used=False,
                    load_duration=load_duration,
                    component_name=router_name,
                    error_details=error_details
                )
    
    def create_fallback_router(self, component_name: str, prefix: str = None, 
                              error_message: str = None) -> Optional[APIRouter]:
        """
        Create a minimal fallback router for a failed component
        
        Args:
            component_name: Name of the component
            prefix: API prefix for the router
            error_message: Original error message
        
        Returns:
            Fallback APIRouter or None if creation fails
        """
        try:
            if not prefix:
                prefix = f"/api/{component_name}"
            
            fallback_router = APIRouter(
                prefix=prefix, 
                tags=[f"{component_name.title()} - Fallback"]
            )
            
            # Create standard fallback endpoints
            @fallback_router.get("/status")
            async def fallback_status():
                return {
                    "status": "fallback",
                    "component": component_name,
                    "message": f"{component_name.title()} service in fallback mode",
                    "error": error_message,
                    "timestamp": datetime.now().isoformat(),
                    "fallback_active": True,
                    "real_data": False  # Clear indicator for frontend
                }
            
            @fallback_router.get("/health")
            async def fallback_health():
                return {
                    "status": "degraded",
                    "component": component_name,
                    "message": f"{component_name.title()} service operating in fallback mode",
                    "fallback_active": True,
                    "real_data": False
                }
            
            # Component-specific fallback endpoints
            if component_name == "portfolio":
                @fallback_router.get("/")
                async def fallback_portfolio_list():
                    return {
                        "status": "fallback",
                        "portfolios": [],
                        "message": "Portfolio service unavailable - showing fallback data",
                        "fallback_active": True,
                        "real_data": False
                    }
                
                @fallback_router.post("/analyze")
                async def fallback_portfolio_analysis(portfolio_data: dict):
                    return {
                        "status": "fallback",
                        "analysis": {
                            "health_score": 75.0,
                            "risk_level": "MODERATE",
                            "recommendations": [
                                {
                                    "type": "FALLBACK_WARNING",
                                    "title": "⚠️ Fallback Analysis Active",
                                    "description": "This is not real analysis data. Portfolio analysis service is temporarily unavailable.",
                                    "priority": "HIGH"
                                }
                            ]
                        },
                        "message": "Portfolio analysis service in fallback mode",
                        "fallback_active": True,
                        "real_data": False
                    }
            
            elif component_name == "trading":
                @fallback_router.get("/orders")
                async def fallback_orders():
                    return {
                        "status": "fallback",
                        "orders": [],
                        "message": "Trading service unavailable - no real orders available",
                        "fallback_active": True,
                        "real_data": False
                    }
                
                @fallback_router.post("/order")
                async def fallback_place_order():
                    raise HTTPException(
                        status_code=503, 
                        detail="Trading service unavailable - cannot place real orders"
                    )
            
            elif component_name == "broker":
                @fallback_router.get("/accounts")
                async def fallback_accounts():
                    return {
                        "status": "fallback",
                        "accounts": [],
                        "message": "Broker service unavailable - no real account data",
                        "fallback_active": True,
                        "real_data": False
                    }
            
            # Catch-all for any other endpoints
            @fallback_router.get("/{path:path}")
            async def fallback_catchall(path: str):
                raise HTTPException(
                    status_code=503, 
                    detail=f"{component_name.title()} service unavailable - fallback mode active"
                )
            
            return fallback_router
            
        except Exception as e:
            logger.error(f"Failed to create fallback router for {component_name}: {str(e)}")
            return None
    
    def track_component_status(self, component: str, status: ComponentStatus, 
                              error_message: str = None, load_duration: float = 0.0,
                              fallback_reason: str = None) -> None:
        """
        Track the status of a component during loading
        
        Args:
            component: Component name
            status: Current status
            error_message: Error message if failed
            load_duration: Time taken to load
            fallback_reason: Reason for fallback activation
        """
        self.component_statuses[component] = ComponentStatusInfo(
            name=component,
            status=status,
            error_message=error_message,
            load_time=datetime.now(),
            fallback_reason=fallback_reason,
            load_duration=load_duration
        )
        
        # Log status change
        status_emoji = {
            ComponentStatus.LOADED: "✅",
            ComponentStatus.FALLBACK: "🔄",
            ComponentStatus.FAILED: "❌"
        }
        
        emoji = status_emoji.get(status, "❓")
        logger.info(f"{emoji} Component {component}: {status.value}")
        
        if error_message:
            logger.debug(f"Error details for {component}: {error_message}")
    
    def get_component_status(self, component: str) -> Optional[ComponentStatusInfo]:
        """Get status information for a specific component"""
        return self.component_statuses.get(component)
    
    def get_all_component_statuses(self) -> Dict[str, ComponentStatusInfo]:
        """Get status information for all components"""
        return self.component_statuses.copy()
    
    def get_loaded_components(self) -> List[str]:
        """Get list of successfully loaded components"""
        return [
            name for name, status in self.component_statuses.items()
            if status.status == ComponentStatus.LOADED
        ]
    
    def get_fallback_components(self) -> List[str]:
        """Get list of components running in fallback mode"""
        return [
            name for name, status in self.component_statuses.items()
            if status.status == ComponentStatus.FALLBACK
        ]
    
    def get_failed_components(self) -> List[str]:
        """Get list of completely failed components"""
        return [
            name for name, status in self.component_statuses.items()
            if status.status == ComponentStatus.FAILED
        ]
    
    def is_component_healthy(self, component: str) -> bool:
        """Check if a component is healthy (loaded successfully)"""
        status = self.component_statuses.get(component)
        return status is not None and status.status == ComponentStatus.LOADED