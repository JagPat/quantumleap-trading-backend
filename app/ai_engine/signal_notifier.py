"""
Signal Notifier
Real-time trading signal notification system with email and webhook support
"""
import json
import logging
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from enum import Enum
from ..database.service import get_db_connection

logger = logging.getLogger(__name__)

class NotificationType(str, Enum):
    """Notification types for signals"""
    EMAIL = "email"
    WEBHOOK = "webhook"
    PUSH = "push"
    SMS = "sms"
    IN_APP = "in_app"

class NotificationPriority(str, Enum):
    """Notification priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    URGENT = "urgent"

class SignalNotifier:
    """
    Signal notification system for real-time alerts
    """
    
    def __init__(self):
        pass
    
    async def send_signal_notification(
        self, 
        user_id: str, 
        signal: Dict[str, Any],
        notification_types: Optional[List[NotificationType]] = None
    ) -> Dict[str, Any]:
        """Send signal notification through configured channels"""
        
        try:
            # Default to in-app notification if none specified
            if not notification_types:
                notification_types = [NotificationType.IN_APP]
            
            # Get user notification preferences
            user_preferences = await self.get_user_notification_preferences(user_id)
            
            # Prepare notification content
            notification_content = self.prepare_notification_content(signal)
            
            # Track notification results
            results = {}
            
            # Send notifications through each channel
            for notification_type in notification_types:
                # Check if user has enabled this notification type
                if self.is_notification_enabled(notification_type, signal, user_preferences):
                    # Send notification through appropriate channel
                    if notification_type == NotificationType.EMAIL:
                        result = await self.send_email_notification(user_id, notification_content)
                    elif notification_type == NotificationType.WEBHOOK:
                        result = await self.send_webhook_notification(user_id, notification_content)
                    elif notification_type == NotificationType.PUSH:
                        result = await self.send_push_notification(user_id, notification_content)
                    elif notification_type == NotificationType.SMS:
                        result = await self.send_sms_notification(user_id, notification_content)
                    else:  # In-app notification
                        result = await self.send_in_app_notification(user_id, notification_content)
                    
                    results[notification_type] = result
            
            # Store notification record
            notification_id = await self.store_notification_record(
                user_id, 
                signal["id"], 
                notification_types,
                results
            )
            
            return {
                "status": "success",
                "notification_id": notification_id,
                "channels": results,
                "timestamp": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send signal notification: {e}")
            return {
                "status": "error",
                "message": f"Notification failed: {str(e)}"
            }    

    def prepare_notification_content(self, signal: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare notification content from signal data"""
        
        # Get signal details
        symbol = signal.get("symbol", "Unknown")
        signal_type = signal.get("signal_type", "unknown")
        confidence = signal.get("confidence_score", 0)
        target_price = signal.get("target_price")
        
        # Format notification title based on signal type
        if signal_type == "buy":
            title = f"🟢 BUY Signal: {symbol}"
        elif signal_type == "sell":
            title = f"🔴 SELL Signal: {symbol}"
        else:
            title = f"⚪ HOLD Signal: {symbol}"
        
        # Format notification message
        message = f"{signal_type.upper()} signal for {symbol} with {confidence*100:.1f}% confidence"
        if target_price:
            message += f". Target price: ₹{target_price}"
        
        # Determine priority based on confidence
        if confidence >= 0.8:
            priority = NotificationPriority.HIGH
        elif confidence >= 0.6:
            priority = NotificationPriority.MEDIUM
        else:
            priority = NotificationPriority.LOW
        
        return {
            "title": title,
            "message": message,
            "signal_id": signal.get("id"),
            "symbol": symbol,
            "signal_type": signal_type,
            "confidence": confidence,
            "target_price": target_price,
            "priority": priority,
            "deep_link": f"/signals/details/{signal.get('id')}",
            "timestamp": datetime.now().isoformat()
        }
    
    def is_notification_enabled(
        self, 
        notification_type: NotificationType,
        signal: Dict[str, Any],
        user_preferences: Dict[str, Any]
    ) -> bool:
        """Check if notification type is enabled based on user preferences"""
        
        # Get notification preferences
        notification_prefs = user_preferences.get("notifications", {})
        
        # Check if this notification type is enabled
        if notification_type.value not in notification_prefs:
            # Default to enabled for in-app, disabled for others
            return notification_type == NotificationType.IN_APP
        
        type_prefs = notification_prefs[notification_type.value]
        
        # Check if enabled
        if not type_prefs.get("enabled", False):
            return False
        
        # Check confidence threshold
        confidence_threshold = type_prefs.get("confidence_threshold", 0)
        if signal.get("confidence_score", 0) < confidence_threshold:
            return False
        
        # Check signal type filter
        signal_types = type_prefs.get("signal_types", ["buy", "sell", "hold"])
        if signal.get("signal_type") not in signal_types:
            return False
        
        # Check symbol filter if specified
        symbols = type_prefs.get("symbols", [])
        if symbols and signal.get("symbol") not in symbols:
            return False
        
        return True  
  
    async def send_email_notification(
        self, 
        user_id: str, 
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send email notification"""
        
        try:
            # In production, this would use an email service like SendGrid
            logger.info(f"Sending email notification to user {user_id}: {content['title']}")
            
            # Mock email sending
            return {
                "status": "success",
                "channel": "email",
                "sent_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send email notification: {e}")
            return {
                "status": "error",
                "channel": "email",
                "error": str(e)
            }
    
    async def send_webhook_notification(
        self, 
        user_id: str, 
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send webhook notification"""
        
        try:
            # Get webhook URL from user preferences
            webhook_url = await self.get_user_webhook_url(user_id)
            
            if not webhook_url:
                return {
                    "status": "error",
                    "channel": "webhook",
                    "error": "No webhook URL configured"
                }
            
            # In production, this would make an HTTP request to the webhook URL
            logger.info(f"Sending webhook notification to {webhook_url}: {content['title']}")
            
            # Mock webhook sending
            return {
                "status": "success",
                "channel": "webhook",
                "webhook_url": webhook_url,
                "sent_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send webhook notification: {e}")
            return {
                "status": "error",
                "channel": "webhook",
                "error": str(e)
            }
    
    async def send_push_notification(
        self, 
        user_id: str, 
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send push notification"""
        
        try:
            # In production, this would use a push notification service
            logger.info(f"Sending push notification to user {user_id}: {content['title']}")
            
            # Mock push notification
            return {
                "status": "success",
                "channel": "push",
                "sent_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return {
                "status": "error",
                "channel": "push",
                "error": str(e)
            }
    
    async def send_sms_notification(
        self, 
        user_id: str, 
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send SMS notification"""
        
        try:
            # In production, this would use an SMS service like Twilio
            logger.info(f"Sending SMS notification to user {user_id}: {content['title']}")
            
            # Mock SMS sending
            return {
                "status": "success",
                "channel": "sms",
                "sent_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send SMS notification: {e}")
            return {
                "status": "error",
                "channel": "sms",
                "error": str(e)
            }
    
    async def send_in_app_notification(
        self, 
        user_id: str, 
        content: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Send in-app notification"""
        
        try:
            # In production, this would store in database and push to frontend
            logger.info(f"Sending in-app notification to user {user_id}: {content['title']}")
            
            # Store in-app notification
            notification_id = await self.store_in_app_notification(user_id, content)
            
            return {
                "status": "success",
                "channel": "in_app",
                "notification_id": notification_id,
                "sent_at": datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Failed to send in-app notification: {e}")
            return {
                "status": "error",
                "channel": "in_app",
                "error": str(e)
            } 
   
    async def get_user_notification_preferences(self, user_id: str) -> Dict[str, Any]:
        """Get user's notification preferences"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # In production, this would query a notification_preferences table
            # For now, return mock preferences
            
            # Mock notification preferences
            preferences = {
                "notifications": {
                    "email": {
                        "enabled": True,
                        "confidence_threshold": 0.7,
                        "signal_types": ["buy", "sell"]
                    },
                    "push": {
                        "enabled": True,
                        "confidence_threshold": 0.5,
                        "signal_types": ["buy", "sell", "hold"]
                    },
                    "in_app": {
                        "enabled": True,
                        "confidence_threshold": 0.0,
                        "signal_types": ["buy", "sell", "hold"]
                    },
                    "webhook": {
                        "enabled": False
                    },
                    "sms": {
                        "enabled": False
                    }
                }
            }
            
            return preferences
            
        except Exception as e:
            logger.warning(f"Failed to get notification preferences for user {user_id}: {e}")
            # Return default preferences
            return {
                "notifications": {
                    "in_app": {"enabled": True}
                }
            }
    
    async def get_user_webhook_url(self, user_id: str) -> Optional[str]:
        """Get user's webhook URL for notifications"""
        
        try:
            # In production, this would query the database
            # For now, return a mock URL
            return f"https://example.com/webhook/{user_id}"
            
        except Exception as e:
            logger.warning(f"Failed to get webhook URL for user {user_id}: {e}")
            return None
    
    async def store_in_app_notification(
        self, 
        user_id: str, 
        content: Dict[str, Any]
    ) -> str:
        """Store in-app notification in database"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Generate notification ID
            notification_id = f"notif_{int(datetime.now().timestamp())}"
            
            # In production, this would insert into a notifications table
            logger.info(f"Stored in-app notification {notification_id} for user {user_id}")
            
            return notification_id
            
        except Exception as e:
            logger.error(f"Failed to store in-app notification: {e}")
            return f"error_{int(datetime.now().timestamp())}"
    
    async def store_notification_record(
        self, 
        user_id: str, 
        signal_id: str,
        notification_types: List[NotificationType],
        results: Dict[NotificationType, Dict[str, Any]]
    ) -> str:
        """Store notification record in database"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # Generate record ID
            record_id = f"record_{int(datetime.now().timestamp())}"
            
            # In production, this would insert into a notification_records table
            logger.info(f"Stored notification record {record_id} for user {user_id}, signal {signal_id}")
            
            return record_id
            
        except Exception as e:
            logger.error(f"Failed to store notification record: {e}")
            return f"error_{int(datetime.now().timestamp())}"
    
    async def get_user_notifications(
        self, 
        user_id: str, 
        limit: int = 50,
        unread_only: bool = False
    ) -> List[Dict[str, Any]]:
        """Get user's in-app notifications"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # In production, this would query the notifications table
            # For now, return mock notifications
            
            # Generate mock notifications
            import random
            
            notifications = []
            for i in range(min(limit, 10)):
                notification = {
                    "id": f"notif_{i}",
                    "title": f"Signal Alert: {random.choice(['BUY', 'SELL', 'HOLD'])} {random.choice(['RELIANCE', 'TCS', 'HDFCBANK'])}",
                    "message": "Trading signal generated based on technical analysis",
                    "priority": random.choice(["low", "medium", "high"]),
                    "read": not unread_only and random.choice([True, False]),
                    "created_at": (datetime.now() - timedelta(hours=random.randint(1, 48))).isoformat()
                }
                notifications.append(notification)
            
            return sorted(notifications, key=lambda x: x["created_at"], reverse=True)
            
        except Exception as e:
            logger.error(f"Failed to get notifications for user {user_id}: {e}")
            return []
    
    async def mark_notification_read(
        self, 
        user_id: str, 
        notification_id: str
    ) -> bool:
        """Mark notification as read"""
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            # In production, this would update the notifications table
            logger.info(f"Marked notification {notification_id} as read for user {user_id}")
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to mark notification as read: {e}")
            return False