"""
Strava Service - Integration with Strava platform.

This is a placeholder implementation. The actual integration
will be implemented in a future version.
"""
from typing import Any, Dict, List, Optional
from abc import ABC, abstractmethod

from app.core.logging import get_logger

logger = get_logger(__name__)


class StravaServiceInterface(ABC):
    """Abstract interface for Strava integration."""
    
    @abstractmethod
    async def get_authorization_url(self, redirect_uri: str) -> str:
        """Get OAuth authorization URL."""
        pass
    
    @abstractmethod
    async def exchange_token(self, code: str) -> Dict[str, Any]:
        """Exchange authorization code for access token."""
        pass
    
    @abstractmethod
    async def get_athlete(self, access_token: str) -> Dict[str, Any]:
        """Get authenticated athlete profile."""
        pass
    
    @abstractmethod
    async def get_activities(
        self,
        access_token: str,
        after: Optional[int] = None,
        before: Optional[int] = None,
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """Get athlete activities."""
        pass
    
    @abstractmethod
    async def get_activity_details(
        self,
        access_token: str,
        activity_id: int
    ) -> Dict[str, Any]:
        """Get detailed activity data."""
        pass


class StravaService(StravaServiceInterface):
    """
    Placeholder implementation for Strava integration.
    
    All methods raise NotImplementedError until the actual
    integration is implemented.
    """
    
    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None
    ):
        """
        Initialize the Strava service.
        
        Args:
            client_id: Strava API client ID
            client_secret: Strava API client secret
        """
        self.client_id = client_id
        self.client_secret = client_secret
        self.base_url = "https://www.strava.com/api/v3"
        self.auth_url = "https://www.strava.com/oauth"
        
        logger.info("StravaService initialized (placeholder)")
    
    async def get_authorization_url(self, redirect_uri: str) -> str:
        """
        Get OAuth authorization URL.
        
        Args:
            redirect_uri: OAuth redirect URI
            
        Returns:
            Authorization URL
            
        Raises:
            NotImplementedError: Integration not yet implemented
        """
        raise NotImplementedError(
            "Strava OAuth is not yet implemented. "
            "This feature will be available in a future version."
        )
    
    async def exchange_token(self, code: str) -> Dict[str, Any]:
        """
        Exchange authorization code for access token.
        
        Args:
            code: Authorization code from OAuth flow
            
        Returns:
            Token response with access_token, refresh_token, etc.
            
        Raises:
            NotImplementedError: Integration not yet implemented
        """
        raise NotImplementedError(
            "Strava token exchange is not yet implemented. "
            "This feature will be available in a future version."
        )
    
    async def get_athlete(self, access_token: str) -> Dict[str, Any]:
        """
        Get authenticated athlete profile.
        
        Args:
            access_token: Strava access token
            
        Returns:
            Athlete profile data
            
        Raises:
            NotImplementedError: Integration not yet implemented
        """
        raise NotImplementedError(
            "Strava athlete fetch is not yet implemented. "
            "This feature will be available in a future version."
        )
    
    async def get_activities(
        self,
        access_token: str,
        after: Optional[int] = None,
        before: Optional[int] = None,
        per_page: int = 30
    ) -> List[Dict[str, Any]]:
        """
        Get athlete activities.
        
        Args:
            access_token: Strava access token
            after: Epoch timestamp for activities after
            before: Epoch timestamp for activities before
            per_page: Number of activities per page
            
        Returns:
            List of activity summaries
            
        Raises:
            NotImplementedError: Integration not yet implemented
        """
        raise NotImplementedError(
            "Strava activities fetch is not yet implemented. "
            "This feature will be available in a future version."
        )
    
    async def get_activity_details(
        self,
        access_token: str,
        activity_id: int
    ) -> Dict[str, Any]:
        """
        Get detailed activity data.
        
        Args:
            access_token: Strava access token
            activity_id: Strava activity ID
            
        Returns:
            Detailed activity data
            
        Raises:
            NotImplementedError: Integration not yet implemented
        """
        raise NotImplementedError(
            "Strava activity details fetch is not yet implemented. "
            "This feature will be available in a future version."
        )
    
    def is_configured(self) -> bool:
        """Check if the service is properly configured."""
        return bool(self.client_id and self.client_secret)

