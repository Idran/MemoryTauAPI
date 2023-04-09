from datetime import timedelta
from typing import Union, Optional


class Config(object):
    """
    Contains global configuration
    """

    DEFAULT_TIMEOUT = 3.0
    DEFAULT_USER_AGENT = "mediawikiapi (https://github.com/Idran/MemoryTauAPI)"
    API_URL = "https://www.mysidia.org/trek/api.php"

    def __init__(
        self,
        user_agent: Optional[str] = None,
        timeout: Optional[float] = None,
        rate_limit: Optional[Union[int, timedelta]] = None,
    ):
        self.mediawiki_url: str = self.API_URL
        if isinstance(rate_limit, int):
            rate_limit = timedelta(milliseconds=rate_limit)
        self.__rate_limit: Optional[timedelta] = rate_limit
        self.timeout: float = timeout or self.DEFAULT_TIMEOUT
        self.user_agent: str = user_agent or self.DEFAULT_USER_AGENT

    def get_api_url(self) -> str:
        """Return api for specified language
        """
        return self.mediawiki_url

    @property
    def rate_limit(self) -> Optional[timedelta]:
        return self.__rate_limit

    @rate_limit.setter
    def rate_limit(self, rate_limit: Optional[Union[int, timedelta]] = None) -> None:
        """
        Enable or disable rate limiting on requests to the Mediawiki servers.
        If rate limiting is not enabled, under some circumstances (depending on
        load on Wikipedia, the number of requests you and other `wikipedia` users
        are making, and other factors), Wikipedia may return an HTTP timeout error.

        Enabling rate limiting generally prevents that issue, but please note that
        HTTPTimeoutError still might be raised.

        Arguments:
        * min_wait - (integer or timedelta) describes the minimum time to wait in milliseconds before requests.
               Example timedelta(milliseconds=50). If None, rate_limit won't be used.

        """
        if rate_limit is None:
            self.__rate_limit = None
        elif isinstance(rate_limit, timedelta):
            self.__rate_limit = rate_limit
        else:
            self.__rate_limit = timedelta(milliseconds=rate_limit)
