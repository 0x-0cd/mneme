"""Tests for CLI commands using Click CliRunner."""

from __future__ import annotations

import ast
import os
import tempfile

import pytest
from click.testing import CliRunner

from mneme.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    os.unlink(path)
    yield path
    if os.path.exists(path):
        os.unlink(path)


class TestAdd:
    def test_add_memory(self, runner, db_path):
        result = runner.invoke(cli, ["add", "hello world", "--db", db_path])
        assert result.exit_code == 0
        assert "hello world" in result.output

    def test_add_memory_with_type_and_tags(self, runner, db_path):
        result = runner.invoke(cli, [
            "add", "important event",
            "--type", "event",
            "--tags", "urgent,work",
            "--db", db_path,
        ])
        assert result.exit_code == 0
        assert "important event" in result.output
        assert "event" in result.output
        assert "urgent" in result.output


class TestSearch:
    def test_search_finds_memory(self, runner, db_path):
        runner.invoke(cli, ["add", "hello world", "--db", db_path])
        result = runner.invoke(cli, ["search", "hello", "--db", db_path])
        assert result.exit_code == 0
        assert "hello world" in result.output

    def test_search_no_results(self, runner, db_path):
        result = runner.invoke(cli, ["search", "nonexistent", "--db", db_path])
        assert result.exit_code == 0
        assert "No memories found" in result.output

    def test_search_by_type(self, runner, db_path):
        runner.invoke(cli, ["add", "fact one", "--type", "fact", "--db", db_path])
        runner.invoke(cli, ["add", "pref one", "--type", "preference", "--db", db_path])
        result = runner.invoke(cli, ["search", "--type", "preference", "--db", db_path])
        assert result.exit_code == 0
        assert "pref one" in result.output
        assert "fact one" not in result.output

    def test_search_by_tags(self, runner, db_path):
        runner.invoke(cli, ["add", "urgent task", "--tags", "urgent,work", "--db", db_path])
        runner.invoke(cli, ["add", "fun task", "--tags", "fun", "--db", db_path])
        result = runner.invoke(cli, ["search", "--tags", "work", "--db", db_path])
        assert result.exit_code == 0
        assert "urgent task" in result.output
        assert "fun task" not in result.output


class TestDelete:
    @staticmethod
    def _add_and_get_id(runner, db_path, content="to delete"):
        r = runner.invoke(cli, ["add", content, "--db", db_path])
        data = ast.literal_eval(r.output.strip())
        return data["id"]

    def test_delete_memory(self, runner, db_path):
        mem_id = self._add_and_get_id(runner, db_path)
        result = runner.invoke(cli, ["delete", mem_id, "--db", db_path])
        assert result.exit_code == 0
        assert f"Deleted memory {mem_id}" in result.output

    def test_delete_nonexistent(self, runner, db_path):
        result = runner.invoke(cli, ["delete", "nonexistent-id", "--db", db_path])
        assert result.exit_code == 1
        assert "not found" in result.output


class TestClear:
    def test_clear_with_force(self, runner, db_path):
        runner.invoke(cli, ["add", "hello", "--db", db_path])
        result = runner.invoke(cli, ["clear", "--db", db_path, "--force"])
        assert result.exit_code == 0
        assert "All memories cleared" in result.output

    def test_clear_removes_all_memories(self, runner, db_path):
        runner.invoke(cli, ["add", "hello", "--db", db_path])
        runner.invoke(cli, ["clear", "--db", db_path, "--force"])
        result = runner.invoke(cli, ["search", "", "--db", db_path])
        assert "No memories found" in result.output


class TestStats:
    def test_stats_empty(self, runner, db_path):
        result = runner.invoke(cli, ["stats", "--db", db_path])
        assert result.exit_code == 0
        assert "Total memories: 0" in result.output

    def test_stats_with_data(self, runner, db_path):
        runner.invoke(cli, ["add", "fact one", "--type", "fact", "--db", db_path])
        runner.invoke(cli, ["add", "pref one", "--type", "preference", "--db", db_path])
        runner.invoke(cli, ["add", "fact two", "--type", "fact", "--db", db_path])
        result = runner.invoke(cli, ["stats", "--db", db_path])
        assert result.exit_code == 0
        assert "Total memories: 3" in result.output
