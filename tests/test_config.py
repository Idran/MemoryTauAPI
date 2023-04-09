# -*- coding: utf-8 -*-
import unittest
from datetime import timedelta
from memorytauapi.config import Config
from memorytauapi import Language


class TestConfig(unittest.TestCase):
    def test_default_language_config(self) -> None:
        self.assertEqual(Config().language, Language.DEFAULT_LANGUAGE)

    def test_default_user_agent_config(self) -> None:
        self.assertEqual(Config().user_agent, Config.DEFAULT_USER_AGENT)

    def test_default_rate_limit_is_None(self) -> None:
        self.assertEqual(Config().rate_limit, None)

    def test_custom_rate_limit_as_int(self) -> None:
        rate_limit: int = 10
        self.assertEqual(
            Config(rate_limit=rate_limit).rate_limit, timedelta(milliseconds=10)
        )

    def test_custom_rate_limit_as_timedelta(self) -> None:
        rate_limit: timedelta = timedelta(milliseconds=10)
        self.assertEqual(Config(rate_limit=rate_limit).rate_limit, rate_limit)

    def test_set_rate_limit(self) -> None:
        rate_limit_int = 10
        rate_limit: timedelta = timedelta(milliseconds=rate_limit_int)
        config = Config()
        config.rate_limit = None
        self.assertEqual(config.rate_limit, None)
        config.rate_limit = rate_limit_int  # type:ignore
        self.assertEqual(config.rate_limit, rate_limit)
        config.rate_limit = rate_limit
        self.assertEqual(config.rate_limit, rate_limit)
