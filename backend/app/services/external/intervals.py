"""
Intervals.icu Service - Integration with Intervals.icu platform.

This is a placeholder implementation. The actual integration
will be implemented in a future version.
"""
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

from app.core.logging import get_logger

logger = get_logger(__name__)


class IntervalsServiceInterface(ABC):
    """Abstract interface for Intervals.icu integration."""
    
    @abstractmethod
    async def sync_activities(self, athlete_id: str) -> List[Dict[str, Any]]:
        """Sync activities from Intervals.icu."""
        pass
    
    @abstractmethod
    async def push_workout(self, athlete_id: str, workout: Dict[str, Any]) -> str:
        """Push a planned workout to Intervals.icu."""
        pass
    
    @abstractmethod
    async def get_athlete_profile(self, athlete_id: str) -> Dict[str, Any]:
        """Get athlete profile from Intervals.icu."""
        pass
    
    @abstractmethod
    async def get_wellness_data(
        self,
        athlete_id: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """Get wellness data for date range."""
        pass


class IntervalsService(IntervalsServiceInterface):
    """
    Placeholder implementation for Intervals.icu integration.
    
    All methods raise NotImplementedError until the actual
    integration is implemented.
    """
    
    def __init__(self, api_key: Optional[str] = None, athlete_id: Optional[str] = None):
        """
        Initialize the Intervals.icu service.
        
        Args:
            api_key: Intervals.icu API key
            athlete_id: Default athlete ID
        """
        self.api_key = api_key
        self.athlete_id = athlete_id
        self.base_url = "https://intervals.icu/api/v1"
        
        logger.info("IntervalsService initialized (placeholder)")
    
    async def sync_activities(self, athlete_id: str) -> List[Dict[str, Any]]:
        """
        Sync activities from Intervals.icu.
        
        Args:
            athlete_id: Athlete ID to sync activities for
            
        Returns:
            List of activity data
            
        Raises:
            NotImplementedError: Integration not yet implemented
        """
        raise NotImplementedError(
            "Intervals.icu activity sync is not yet implemented. "
            "This feature will be available in a future version."
        )
    
    async def push_workout(self, athlete_id: str, workout: Dict[str, Any]) -> str:
        """
        Push a planned workout to Intervals.icu.
        
        Args:
            athlete_id: Athlete ID
            workout: Workout data to push
            
        Returns:
            Workout ID from Intervals.icu
            
        Raises:
            NotImplementedError: Integration not yet implemented
        """
        raise NotImplementedError(
            "Intervals.icu workout push is not yet implemented. "
            "This feature will be available in a future version."
        )
    
    async def get_athlete_profile(self, athlete_id: str) -> Dict[str, Any]:
        """
        Get athlete profile from Intervals.icu.
        
        Args:
            athlete_id: Athlete ID
            
        Returns:
            Athlete profile data
            
        Raises:
            NotImplementedError: Integration not yet implemented
        """
        raise NotImplementedError(
            "Intervals.icu athlete profile fetch is not yet implemented. "
            "This feature will be available in a future version."
        )
    
    async def get_wellness_data(
        self,
        athlete_id: str,
        start_date: str,
        end_date: str
    ) -> List[Dict[str, Any]]:
        """
        Get wellness data for date range.
        
        Args:
            athlete_id: Athlete ID
            start_date: Start date (YYYY-MM-DD)
            end_date: End date (YYYY-MM-DD)
            
        Returns:
            List of wellness data entries
            
        Raises:
            NotImplementedError: Integration not yet implemented
        """
        raise NotImplementedError(
            "Intervals.icu wellness data fetch is not yet implemented. "
            "This feature will be available in a future version."
        )
    
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return bool(self.api_key and self.athlete_id)

