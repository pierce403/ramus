from __future__ import annotations

from ramus_bot.protocol import parse_command, help_text


def test_parse_settings_command() -> None:
    command = parse_command("settings")
    assert command.action == "settings"


def test_parse_bounty_reward_wei() -> None:
    command = parse_command("set bounty_reward_wei 123")
    assert command.action == "admin.set_bounty_reward_wei"
    assert command.payload["reward"] == "123"


def test_parse_bounty_reward_eth_natural() -> None:
    command = parse_command("set bounty reward 0.01 eth")
    assert command.action == "admin.set_bounty_reward_eth"
    assert command.payload["reward"] == "0.01"


def test_parse_auto_run_off() -> None:
    command = parse_command("set auto_run off")
    assert command.action == "admin.set_auto_run"
    assert command.payload["enabled"] == "off"


def test_parse_auto_run_off_natural() -> None:
    command = parse_command("auto run off")
    assert command.action == "admin.set_auto_run"
    assert command.payload["enabled"] is False


def test_help_text_does_not_include_examples() -> None:
    text = help_text()
    assert "admin text" not in text
    assert "how many claims" not in text
    assert "Operator only:" in text


def test_parse_bounties_command() -> None:
    command = parse_command("bounties")
    assert command.action == "bounties.list"
