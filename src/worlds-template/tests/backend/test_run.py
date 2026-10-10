"""[base] Optional end-to-end agent run. Skipped unless GEMINI_API_KEY is set."""

import os

import pytest


@pytest.mark.skipif(not os.environ.get("GEMINI_API_KEY"), reason="needs GEMINI_API_KEY")
class TestAgentRun:
    def test_agent_plays_one_episode(self):
        pytest.skip("placeholder: the agent harness is not part of the template yet")
