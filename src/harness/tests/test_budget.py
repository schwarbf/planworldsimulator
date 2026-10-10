from planworldsimulator_harness.budget import Budget
from pydantic_ai.usage import RunUsage


def test_status_is_numbers_only():
    budget = Budget(tokens=2_000_000, seconds=600)
    usage = RunUsage(tool_calls=88, input_tokens=1_000_000, output_tokens=200_000)
    assert budget.status(usage, elapsed=230) == (
        "Budget left: 0.8M/2.0M tokens, 6:10 min."
    )


def test_status_never_negative():
    usage = RunUsage(tool_calls=999, input_tokens=9_000_000)
    assert "0k/2.0M tokens" in Budget().status(usage, elapsed=9999)
    assert "0:00 min" in Budget().status(usage, elapsed=9999)


def test_agent_key_from_file(tmp_path, monkeypatch):
    from planworldsimulator_harness.agents import api_key

    keyfile = tmp_path / "key.txt"
    keyfile.write_text("file-key\n")
    monkeypatch.delenv("HARNESS_TEST_KEY", raising=False)
    monkeypatch.setenv("HARNESS_TEST_KEY_FILE", str(keyfile))
    assert api_key("HARNESS_TEST_KEY") == "file-key"
