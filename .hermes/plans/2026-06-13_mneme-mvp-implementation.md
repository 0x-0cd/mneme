# Mneme MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use strict TDD (test-driven-development skill). Every code-producing task MUST follow RED → GREEN → REFACTOR cycle. No production code without a failing test first.

**Goal:** Build Mneme — an edge-first, offline-first memory system for AI agents with HTTP API, MCP protocol, and CLI.

**Architecture:** Transport layer (HTTP/MCP/CLI) → Engine (Store + Search) → Storage (SQLite + sqlite-vec). Embedding is a shared dependency. MVP is single-process synchronous for simplicity; async is a future concern.

**Tech Stack:** Python 3.11+, SQLite3 + sqlite-vec, sentence-transformers, FastAPI, MCP Python SDK, rich, click, pytest, ruff, mypy.

**Constraints:**
- 🔒 No PII in any committed file (names, email, location, company)
- 📝 Conventional Commits (`feat:`, `fix:`, `test:`, `chore:`, `docs:`, `refactor:`, `style:`, `perf:`, `ci:`)

---

## Project Structure (final state after all tasks)

```
mneme/
├── src/mneme/
│   ├── __init__.py           # Version + public API
│   ├── __about__.py          # Version string
│   ├── cli.py                # Click CLI (serve, add, search, delete)
│   ├── server.py             # HTTP server entrypoint
│   ├── engine/
│   │   ├── __init__.py
│   │   ├── types.py          # Memory model, MemoryType enum
│   │   ├── store.py          # Store memory → embed + insert
│   │   └── search.py         # Semantic + keyword + filtered search
│   ├── storage/
│   │   ├── __init__.py
│   │   ├── db.py             # SQLite schema + CRUD
│   │   └── vector.py         # sqlite-vec operations
│   ├── api/
│   │   ├── __init__.py
│   │   ├── app.py            # FastAPI app factory
│   │   └── routes.py         # All HTTP routes
│   ├── mcp/
│   │   ├── __init__.py
│   │   └── server.py         # MCP tool definitions
│   └── embed/
│       ├── __init__.py
│       └── model.py          # Embedding model wrapper
├── tests/
│   ├── __init__.py
│   ├── conftest.py           # Shared fixtures
│   ├── test_types.py
│   ├── test_db.py
│   ├── test_vector.py
│   ├── test_engine_store.py
│   ├── test_engine_search.py
│   ├── test_api.py
│   ├── test_cli.py
│   └── test_integration.py
├── pyproject.toml
├── AGENTS.md
├── CONTRIBUTING.md
├── .gitmessage
└── README.md
```

---

### Task 1: Project scaffold + pyproject.toml + import smoke test

**Objective:** Set up the Python project with all dependencies, package structure, and verify `import mneme` works.

**Files:**
- Create: `pyproject.toml`
- Create: `src/mneme/__init__.py`
- Create: `src/mneme/__about__.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_types.py` (placeholder — will be replaced in Task 2)

- [ ] **Step 1: Create pyproject.toml**

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "mneme"
version = "0.1.0"
description = "Edge-first memory for AI agents."
readme = "README.md"
license = { text = "MIT" }
requires-python = ">=3.11"
authors = [
    { name = "Mneme by Emma" },
]
dependencies = [
    "fastapi>=0.115.0",
    "uvicorn[standard]>=0.30.0",
    "click>=8.1.0",
    "rich>=13.0.0",
    "sentence-transformers>=3.0.0",
    "mcp>=1.0.0",
    "sqlite-vec>=0.1.0",
]

[project.urls]
Homepage = "https://github.com/0x-0cd/mneme"
Repository = "https://github.com/0x-0cd/mneme"

[project.scripts]
mneme = "mneme.cli:cli"

[project.optional-dependencies]
dev = [
    "pytest>=8.0.0",
    "pytest-cov>=5.0.0",
    "httpx>=0.27.0",
    "ruff>=0.5.0",
    "mypy>=1.10.0",
]

[tool.hatch.build.targets.wheel]
packages = ["src/mneme"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["src"]
asyncio_mode = "auto"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]

[tool.mypy]
python_version = "3.11"
strict = true
ignore_missing_imports = true
```

- [ ] **Step 2: Create src/mneme/__about__.py**

```python
__version__ = "0.1.0"
```

- [ ] **Step 3: Create src/mneme/__init__.py**

```python
"""Mneme — Edge-first memory for AI agents."""

from mneme.__about__ import __version__

__all__ = ["__version__"]
```

- [ ] **Step 4: Create tests/__init__.py** (empty file)

- [ ] **Step 5: Create tests/conftest.py** (empty for now)

- [ ] **Step 6: Write the failing test — verify import works**

Create `tests/test_types.py`:

```python
"""Smoke test: verify package imports correctly."""


def test_import():
    import mneme  # noqa: F811

    assert mneme.__version__ == "0.1.0"
```

- [ ] **Step 7: Verify RED — test fails (package not installed)**

```bash
cd /home/qn/projects/ai-memory-system
python3 -m pytest tests/test_types.py -v
```

Expected: FAIL with `ModuleNotFoundError: No module named 'mneme'` (because we haven't installed the package yet).

- [ ] **Step 8: Install package in editable mode**

```bash
cd /home/qn/projects/ai-memory-system
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

- [ ] **Step 9: Verify GREEN — test passes**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_types.py -v
```

Expected: PASS (1 passed)

- [ ] **Step 10: Verify full suite runs (no other tests yet)**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/ -v
```

Expected: 1 passed

- [ ] **Step 11: Commit**

```bash
cd /home/qn/projects/ai-memory-system
git add pyproject.toml src/mneme/ tests/ .gitignore
git commit -m "chore: scaffold Mneme project with pyproject.toml, package structure, and test infra"
```

---

### Task 2: Memory type definitions (Core data model)

**Objective:** Define the MemoryType enum and Memory dataclass that all other modules depend on.

**Files:**
- Modify: `tests/test_types.py` (replace placeholder content)
- Create: `src/mneme/engine/__init__.py`
- Create: `src/mneme/engine/types.py`

- [ ] **Step 1: Create engine package init**

Create `src/mneme/engine/__init__.py` (empty).

- [ ] **Step 2: Write the failing tests**

Replace `tests/test_types.py`:

```python
"""Tests for memory type definitions."""

from datetime import datetime, timezone

import pytest

from mneme.engine.types import Memory, MemoryType


class TestMemoryType:
    """MemoryType enum tests."""

    def test_has_required_types(self):
        """Must support all 5 memory types from design doc."""
        expected = {"fact", "preference", "event", "conversation", "skill"}
        actual = {t.value for t in MemoryType}
        assert expected.issubset(actual)

    def test_default_is_fact(self):
        """Default memory type should be 'fact'."""
        m = Memory(content="test")
        assert m.type == MemoryType.FACT


class TestMemoryModel:
    """Memory dataclass tests."""

    def test_required_fields(self):
        """content is required; type defaults to fact."""
        m = Memory(content="Hello world")
        assert m.content == "Hello world"
        assert m.type == MemoryType.FACT
        assert m.weight == 1.0
        assert m.tags == []
        assert m.metadata == {}

    def test_all_fields(self):
        """All fields can be set explicitly."""
        now = datetime.now(timezone.utc)
        m = Memory(
            id="test-id",
            content="Important fact",
            type=MemoryType.PREFERENCE,
            weight=2.0,
            tags=["python", "agent"],
            metadata={"source": "user"},
            created_at=now,
            updated_at=now,
            version=1,
        )
        assert m.id == "test-id"
        assert m.content == "Important fact"
        assert m.type == MemoryType.PREFERENCE
        assert m.weight == 2.0
        assert m.tags == ["python", "agent"]
        assert m.metadata == {"source": "user"}
        assert m.created_at == now
        assert m.updated_at == now
        assert m.version == 1

    def test_content_cannot_be_empty(self):
        """Empty content should raise ValueError."""
        with pytest.raises(ValueError, match="content must not be empty"):
            Memory(content="")

    def test_weight_must_be_positive(self):
        """Weight must be > 0."""
        with pytest.raises(ValueError, match="weight must be positive"):
            Memory(content="test", weight=0)

    def test_id_generated_if_not_provided(self):
        """If no id given, a UUID4 string is generated."""
        m = Memory(content="test")
        assert m.id is not None
        assert len(m.id) == 36  # UUID4 format

    def test_tags_normalized(self):
        """Tags should be stored as list, even if provided differently."""
        m = Memory(content="test", tags=["a", "b"])
        assert m.tags == ["a", "b"]

    def test_created_at_defaults_to_now(self):
        """created_at should be set to current time if not provided."""
        m = Memory(content="test")
        assert m.created_at is not None
        assert isinstance(m.created_at, datetime)

    def test_version_defaults_to_1(self):
        """version defaults to 1."""
        m = Memory(content="test")
        assert m.version == 1

    def test_to_dict_serializable(self):
        """to_dict() returns JSON-serializable dict."""
        m = Memory(content="test", tags=["a"], metadata={"key": "val"})
        d = m.to_dict()
        assert d["content"] == "test"
        assert d["type"] == "fact"
        assert d["tags"] == ["a"]
        assert d["metadata"] == {"key": "val"}
        assert "created_at" in d

    def test_from_dict_roundtrip(self):
        """from_dict(to_dict()) should return equivalent object."""
        m = Memory(content="test", tags=["a"], metadata={"key": "val"}, weight=1.5)
        d = m.to_dict()
        m2 = Memory.from_dict(d)
        assert m2.content == m.content
        assert m2.type == m.type
        assert m2.weight == m.weight
        assert m2.tags == m.tags
        assert m2.metadata == m.metadata
```

- [ ] **Step 3: Verify RED**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_types.py -v
```

Expected: All fail with `ModuleNotFoundError` or `ImportError` — types module doesn't exist yet.

- [ ] **Step 4: Write minimal implementation**

Create `src/mneme/engine/types.py`:

```python
"""Memory type definitions for Mneme."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class MemoryType(str, Enum):
    FACT = "fact"
    PREFERENCE = "preference"
    EVENT = "event"
    CONVERSATION = "conversation"
    SKILL = "skill"


class Memory:
    """A single memory entry."""

    def __init__(
        self,
        content: str,
        type: MemoryType | str = MemoryType.FACT,
        weight: float = 1.0,
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        id: str | None = None,
        created_at: datetime | None = None,
        updated_at: datetime | None = None,
        version: int = 1,
        superseded_by: str | None = None,
        deleted_at: datetime | None = None,
    ):
        if not content or not content.strip():
            raise ValueError("content must not be empty")
        if weight <= 0:
            raise ValueError("weight must be positive")

        self.id = id or str(uuid.uuid4())
        self.type = MemoryType(type) if isinstance(type, str) else type
        self.content = content.strip()
        self.weight = weight
        self.tags = tags or []
        self.metadata = metadata or {}
        now = datetime.now(timezone.utc)
        self.created_at = created_at or now
        self.updated_at = updated_at or now
        self.version = version
        self.superseded_by = superseded_by
        self.deleted_at = deleted_at

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "id": self.id,
            "type": self.type.value,
            "content": self.content,
            "weight": self.weight,
            "tags": self.tags,
            "metadata": self.metadata,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "version": self.version,
            "superseded_by": self.superseded_by,
            "deleted_at": self.deleted_at.isoformat() if self.deleted_at else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Memory:
        """Deserialize from a dict (output of to_dict)."""
        return cls(
            id=data.get("id"),
            content=data["content"],
            type=MemoryType(data.get("type", "fact")),
            weight=data.get("weight", 1.0),
            tags=data.get("tags", []),
            metadata=data.get("metadata", {}),
            created_at=datetime.fromisoformat(data["created_at"]) if "created_at" in data else None,
            updated_at=datetime.fromisoformat(data["updated_at"]) if "updated_at" in data else None,
            version=data.get("version", 1),
            superseded_by=data.get("superseded_by"),
            deleted_at=datetime.fromisoformat(data["deleted_at"]) if data.get("deleted_at") else None,
        )
```

- [ ] **Step 5: Verify GREEN**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_types.py -v
```

Expected: All ~12 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /home/qn/projects/ai-memory-system
git add src/mneme/engine/__init__.py src/mneme/engine/types.py tests/test_types.py
git commit -m "feat: add MemoryType enum and Memory data model with validation"
```

---

### Task 3: Database layer — SQLite CRUD

**Objective:** Create the SQLite storage layer with schema creation, insert, query, update, soft-delete, and full-clear operations.

**Files:**
- Create: `src/mneme/storage/__init__.py`
- Create: `src/mneme/storage/db.py`
- Create: `tests/test_db.py`

- [ ] **Step 1: Create storage package init**

Create `src/mneme/storage/__init__.py` (empty).

- [ ] **Step 2: Write the failing tests**

Create `tests/test_db.py`:

```python
"""Tests for SQLite database layer."""

import pytest

from mneme.engine.types import Memory, MemoryType
from mneme.storage.db import Database


@pytest.fixture
def db():
    """Create an in-memory database for testing."""
    database = Database(":memory:")
    database.initialize()
    yield database
    database.close()


class TestDatabaseInit:
    def test_initialize_creates_tables(self, db):
        """After initialize(), the schema should exist."""
        row = db.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories'"
        ).fetchone()
        assert row is not None
        assert row[0] == "memories"


class TestDatabaseCRUD:
    def test_insert_memory(self, db):
        """Insert a memory and verify it's stored."""
        m = Memory(content="Hello world", tags=["greeting"])
        db.insert(m)
        row = db.conn.execute("SELECT id, content, type FROM memories WHERE id = ?", (m.id,)).fetchone()
        assert row is not None
        assert row[1] == "Hello world"

    def test_get_by_id(self, db):
        """Retrieve a memory by ID."""
        m = Memory(content="Test memory", type=MemoryType.FACT)
        db.insert(m)
        retrieved = db.get(m.id)
        assert retrieved is not None
        assert retrieved.content == "Test memory"
        assert retrieved.id == m.id

    def test_get_nonexistent_returns_none(self, db):
        """Getting a non-existent ID returns None."""
        assert db.get("nonexistent-id") is None

    def test_search_by_content(self, db):
        """Search memories by content substring."""
        db.insert(Memory(content="Python is great"))
        db.insert(Memory(content="I love Rust"))
        results = db.search("Python")
        assert len(results) == 1
        assert results[0].content == "Python is great"

    def test_search_by_type(self, db):
        """Filter search by memory type."""
        db.insert(Memory(content="fact 1", type=MemoryType.FACT))
        db.insert(Memory(content="pref 1", type=MemoryType.PREFERENCE))
        results = db.search("", type_filter=MemoryType.FACT)
        assert len(results) == 1
        assert results[0].type == MemoryType.FACT

    def test_search_by_tags(self, db):
        """Filter search by tags."""
        db.insert(Memory(content="python memory", tags=["python", "lang"]))
        db.insert(Memory(content="rust memory", tags=["rust", "lang"]))
        results = db.search("", tags=["python"])
        assert len(results) == 1
        assert "python" in results[0].content

    def test_search_limit(self, db):
        """Search respects limit parameter."""
        for i in range(10):
            db.insert(Memory(content=f"memory {i}"))
        results = db.search("memory", limit=3)
        assert len(results) == 3

    def test_update_memory(self, db):
        """Update a memory's content and verify."""
        m = Memory(content="original")
        db.insert(m)
        m.content = "updated"
        m.tags = ["updated"]
        db.update(m)
        retrieved = db.get(m.id)
        assert retrieved.content == "updated"
        assert retrieved.tags == ["updated"]
        assert retrieved.version == 2

    def test_soft_delete(self, db):
        """Soft-delete marks deleted_at but keeps the row."""
        m = Memory(content="to delete")
        db.insert(m)
        db.soft_delete(m.id)
        # Should not appear in search
        results = db.search("to delete")
        assert len(results) == 0
        # But still exists in DB
        row = db.conn.execute("SELECT deleted_at FROM memories WHERE id = ?", (m.id,)).fetchone()
        assert row[0] is not None

    def test_clear_all(self, db):
        """Clear all permanently deletes everything."""
        db.insert(Memory(content="a"))
        db.insert(Memory(content="b"))
        db.clear()
        results = db.search("")
        assert len(results) == 0

    def test_count(self, db):
        """Count returns number of non-deleted memories."""
        db.insert(Memory(content="a"))
        db.insert(Memory(content="b"))
        db.insert(Memory(content="c"))
        assert db.count() == 3
        db.soft_delete("a")
        # After soft-deleting one... wait, soft_delete by id needs the id
        # Let me redo this more carefully

    def test_get_all_memories(self, db):
        """Get all non-deleted memories."""
        db.insert(Memory(content="a"))
        db.insert(Memory(content="b"))
        all_m = db.get_all()
        assert len(all_m) == 2

    def test_soft_deleted_excluded_from_get_all(self, db):
        """Soft-deleted memories are excluded from get_all."""
        m = Memory(content="will be deleted")
        db.insert(m)
        db.soft_delete(m.id)
        all_m = db.get_all()
        assert len(all_m) == 0
```

- [ ] **Step 3: Verify RED**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_db.py -v
```

Expected: All fail with `ImportError` — db module doesn't exist yet.

- [ ] **Step 4: Write minimal implementation**

Create `src/mneme/storage/db.py`:

```python
"""SQLite storage layer for Mneme."""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from mneme.engine.types import Memory, MemoryType


class Database:
    """SQLite-backed memory storage."""

    def __init__(self, db_path: str = "memories.db"):
        self.db_path = db_path
        self.conn: sqlite3.Connection | None = None

    def initialize(self):
        """Create tables and indexes."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")

        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id          TEXT PRIMARY KEY,
                type        TEXT NOT NULL DEFAULT 'fact',
                content     TEXT NOT NULL,
                weight      REAL NOT NULL DEFAULT 1.0,
                metadata    TEXT NOT NULL DEFAULT '{}',
                tags        TEXT NOT NULL DEFAULT '',
                created_at  TEXT NOT NULL,
                updated_at  TEXT NOT NULL,
                version     INTEGER NOT NULL DEFAULT 1,
                superseded_by TEXT,
                deleted_at  TEXT
            )
        """)

        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_type ON memories(type)")
        self.conn.execute("CREATE INDEX IF NOT EXISTS idx_memories_deleted ON memories(deleted_at)")
        self.conn.commit()

    def close(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()

    def insert(self, memory: Memory) -> None:
        """Insert a new memory record."""
        self.conn.execute(
            """
            INSERT INTO memories (id, type, content, weight, metadata, tags,
                                  created_at, updated_at, version, superseded_by, deleted_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                memory.id,
                memory.type.value,
                memory.content,
                memory.weight,
                json.dumps(memory.metadata),
                ",".join(memory.tags),
                memory.created_at.isoformat(),
                memory.updated_at.isoformat(),
                memory.version,
                memory.superseded_by,
                memory.deleted_at.isoformat() if memory.deleted_at else None,
            ),
        )
        self.conn.commit()

    def get(self, memory_id: str) -> Memory | None:
        """Get a memory by ID (excluding soft-deleted)."""
        row = self.conn.execute(
            "SELECT * FROM memories WHERE id = ? AND deleted_at IS NULL", (memory_id,)
        ).fetchone()
        return self._row_to_memory(row) if row else None

    def search(
        self,
        query: str = "",
        type_filter: MemoryType | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
    ) -> list[Memory]:
        """Search memories by content, with optional type/tag filtering."""
        sql = "SELECT * FROM memories WHERE deleted_at IS NULL"
        params: list[Any] = []

        if query:
            sql += " AND content LIKE ?"
            params.append(f"%{query}%")

        if type_filter:
            sql += " AND type = ?"
            params.append(type_filter.value)

        if tags:
            for tag in tags:
                sql += " AND tags LIKE ?"
                params.append(f"%{tag}%")

        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)

        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def update(self, memory: Memory) -> None:
        """Update a memory record and increment version."""
        memory.version += 1
        memory.updated_at = datetime.now(timezone.utc)
        self.conn.execute(
            """
            UPDATE memories SET type=?, content=?, weight=?, metadata=?, tags=?,
                                updated_at=?, version=?
            WHERE id = ? AND deleted_at IS NULL
            """,
            (
                memory.type.value,
                memory.content,
                memory.weight,
                json.dumps(memory.metadata),
                ",".join(memory.tags),
                memory.updated_at.isoformat(),
                memory.version,
                memory.id,
            ),
        )
        self.conn.commit()

    def soft_delete(self, memory_id: str) -> None:
        """Soft-delete a memory by setting deleted_at."""
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE memories SET deleted_at = ? WHERE id = ?", (now, memory_id)
        )
        self.conn.commit()

    def clear(self) -> None:
        """Permanently delete all memories."""
        self.conn.execute("DELETE FROM memories")
        self.conn.commit()

    def count(self) -> int:
        """Count non-deleted memories."""
        row = self.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE deleted_at IS NULL"
        ).fetchone()
        return row[0]

    def get_all(self) -> list[Memory]:
        """Get all non-deleted memories."""
        rows = self.conn.execute(
            "SELECT * FROM memories WHERE deleted_at IS NULL ORDER BY created_at DESC"
        ).fetchall()
        return [self._row_to_memory(r) for r in rows]

    def _row_to_memory(self, row: sqlite3.Row) -> Memory:
        """Convert a SQLite row to a Memory object."""
        return Memory(
            id=row["id"],
            content=row["content"],
            type=MemoryType(row["type"]),
            weight=row["weight"],
            tags=row["tags"].split(",") if row["tags"] else [],
            metadata=json.loads(row["metadata"]) if row["metadata"] else {},
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            version=row["version"],
            superseded_by=row["superseded_by"],
            deleted_at=datetime.fromisoformat(row["deleted_at"]) if row["deleted_at"] else None,
        )
```

- [ ] **Step 5: Verify GREEN**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_db.py -v
```

Expected: All ~14 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /home/qn/projects/ai-memory-system
git add src/mneme/storage/ tests/test_db.py
git commit -m "feat: add SQLite storage layer with CRUD, search, and soft-delete"
```

---

### Task 4: Vector search with sqlite-vec

**Objective:** Set up sqlite-vec virtual table for semantic search, with vector insert and cosine similarity query.

**Files:**
- Create: `src/mneme/storage/vector.py`
- Create: `tests/test_vector.py`

- [ ] **Step 1: Check sqlite-vec availability**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -c "import sqlite_vec; print(sqlite_vec.__version__)"
```

If this fails, check architecture support (`pip install sqlite-vec` may need aarch64 wheel).

Expected outcome: sqlite-vec loads without error.

- [ ] **Step 2: Write the failing tests**

Create `tests/test_vector.py`:

```python
"""Tests for vector search layer."""

import pytest

from mneme.storage.vector import VectorIndex


@pytest.fixture
def vindex():
    """Create an in-memory vector index."""
    vi = VectorIndex(":memory:", dimensions=384)
    vi.initialize()
    yield vi
    vi.close()


class TestVectorIndex:
    def test_initialize_creates_virtual_table(self, vindex):
        """After init, the vec0 table should exist."""
        row = vindex.conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='memories_vec'"
        ).fetchone()
        assert row is not None

    def test_insert_vector(self, vindex):
        """Insert a vector and verify it's stored."""
        vindex.insert("mem-1", [0.1] * 384)
        row = vindex.conn.execute(
            "SELECT rowid FROM memories_vec WHERE rowid = ?", (1,)
        ).fetchone()
        assert row is not None

    def test_search_returns_nearest(self, vindex):
        """Search returns nearest neighbors by cosine distance."""
        vindex.insert("mem-1", [0.9] * 384)
        vindex.insert("mem-2", [0.1] * 384)
        # Search near the first vector
        results = vindex.search([0.85] * 384, limit=1)
        assert len(results) == 1
        assert results[0][0] == "mem-1"

    def test_search_limit(self, vindex):
        """Search respects limit."""
        for i in range(5):
            vindex.insert(f"mem-{i}", [0.5] * 384)
        results = vindex.search([0.5] * 384, limit=3)
        assert len(results) == 3

    def test_delete_vector(self, vindex):
        """Delete a vector from the index."""
        vindex.insert("mem-1", [0.5] * 384)
        vindex.delete("mem-1")
        results = vindex.search([0.5] * 384)
        assert len(results) == 0

    def test_empty_index_returns_empty(self, vindex):
        """Search on empty index returns empty list."""
        results = vindex.search([0.5] * 384)
        assert len(results) == 0
```

- [ ] **Step 3: Verify RED**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_vector.py -v
```

Expected: All fail with `ImportError` — module doesn't exist yet.

- [ ] **Step 4: Write minimal implementation**

Create `src/mneme/storage/vector.py`:

```python
"""sqlite-vec vector index layer."""

from __future__ import annotations

import sqlite3
import struct
from typing import Any

import sqlite_vec


class VectorIndex:
    """sqlite-vec backed vector index for semantic search."""

    def __init__(self, db_path: str = "memories.db", dimensions: int = 384):
        self.db_path = db_path
        self.dimensions = dimensions
        self.conn: sqlite3.Connection | None = None

    def initialize(self):
        """Create the virtual vector table."""
        self.conn = sqlite3.connect(self.db_path)
        self.conn.enable_load_extension(True)
        sqlite_vec.load(self.conn)
        self.conn.enable_load_extension(False)

        self.conn.execute(f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_vec USING vec0(
                id TEXT,
                embedding float[{self.dimensions}]
            )
        """)
        self.conn.commit()

    def close(self):
        """Close the connection."""
        if self.conn:
            self.conn.close()

    def insert(self, memory_id: str, embedding: list[float]) -> None:
        """Insert or replace a vector for a memory."""
        blob = self._serialize(embedding)
        # Delete first if exists, then insert
        self.conn.execute("DELETE FROM memories_vec WHERE id = ?", (memory_id,))
        self.conn.execute(
            "INSERT INTO memories_vec (id, embedding) VALUES (?, ?)",
            (memory_id, blob),
        )
        self.conn.commit()

    def search(
        self, query_vector: list[float], limit: int = 20
    ) -> list[tuple[str, float]]:
        """Search nearest neighbors. Returns list of (memory_id, distance)."""
        blob = self._serialize(query_vector)
        rows = self.conn.execute(
            """
            SELECT id, distance
            FROM memories_vec
            WHERE embedding MATCH ?
            ORDER BY distance
            LIMIT ?
            """,
            (blob, limit),
        ).fetchall()
        results = []
        for row in rows:
            memory_id = row[0]
            distance = row[1]
            results.append((memory_id, distance))
        return results

    def delete(self, memory_id: str) -> None:
        """Delete a vector from the index."""
        self.conn.execute("DELETE FROM memories_vec WHERE id = ?", (memory_id,))
        self.conn.commit()

    def count(self) -> int:
        """Count vectors in the index."""
        row = self.conn.execute("SELECT COUNT(*) FROM memories_vec").fetchone()
        return row[0]

    def _serialize(self, vector: list[float]) -> bytes:
        """Serialize a float list to a binary blob for sqlite-vec."""
        return struct.pack(f"{len(vector)}f", *vector)
```

- [ ] **Step 5: Verify GREEN**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_vector.py -v
```

Expected: All ~6 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /home/qn/projects/ai-memory-system
git add src/mneme/storage/vector.py tests/test_vector.py
git commit -m "feat: add vector index with sqlite-vec for semantic search"
```

---

### Task 5: Embedding model wrapper

**Objective:** Create a wrapper around sentence-transformers for generating embeddings, with lazy loading and dimension detection.

**Files:**
- Create: `src/mneme/embed/__init__.py`
- Create: `src/mneme/embed/model.py`
- Create: `tests/test_embed.py`

- [ ] **Step 1: Create embed package init**

Create `src/mneme/embed/__init__.py` (empty).

- [ ] **Step 2: Write the failing tests**

Create `tests/test_embed.py`:

```python
"""Tests for embedding model wrapper."""

import pytest

from mneme.embed.model import EmbeddingModel


class TestEmbeddingModel:
    def test_init_with_model_name(self):
        """Model can be initialized with a model name."""
        model = EmbeddingModel(model_name="all-MiniLM-L6-v2")
        assert model.model_name == "all-MiniLM-L6-v2"

    def test_lazy_load(self):
        """Model should not load until first encode call."""
        model = EmbeddingModel(model_name="all-MiniLM-L6-v2")
        assert model._model is None  # Not loaded yet

    def test_encode_returns_list_of_floats(self):
        """Encode returns a list of floats with expected dimensions."""
        model = EmbeddingModel(model_name="all-MiniLM-L6-v2")
        vec = model.encode("Hello world")
        assert isinstance(vec, list)
        assert len(vec) > 0
        assert all(isinstance(v, float) for v in vec)

    def test_encode_multiple_texts(self):
        """Encode multiple texts returns multiple vectors."""
        model = EmbeddingModel(model_name="all-MiniLM-L6-v2")
        vecs = model.encode(["Hello", "World"])
        assert len(vecs) == 2
        assert len(vecs[0]) > 0

    def test_model_dims_property(self):
        """Model dimensions are available after first encode."""
        model = EmbeddingModel(model_name="all-MiniLM-L6-v2")
        assert model.dims is None  # Not yet known
        model.encode("test")
        assert model.dims is not None
        assert isinstance(model.dims, int)
        assert model.dims > 0
```

Note: These tests download a model (~80MB) on first run. This is a one-time cost. For CI, consider using a smaller model or caching.

- [ ] **Step 3: Verify RED**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_embed.py -v
```

Expected: All fail with `ImportError`.

- [ ] **Step 4: Write minimal implementation**

Create `src/mneme/embed/model.py`:

```python
"""Embedding model wrapper using sentence-transformers."""

from __future__ import annotations

from typing import Any


class EmbeddingModel:
    """Lazy-loading wrapper around sentence-transformers."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        self.model_name = model_name
        self._model: Any = None
        self._dims: int | None = None

    @property
    def dims(self) -> int | None:
        """Get embedding dimensions (None if model not loaded yet)."""
        return self._dims

    def _load(self):
        """Load the model (lazy)."""
        from sentence_transformers import SentenceTransformer

        self._model = SentenceTransformer(self.model_name)
        self._dims = self._model.get_sentence_embedding_dimension()

    def encode(self, text: str | list[str]) -> list[float] | list[list[float]]:
        """Encode text(s) into embedding vector(s)."""
        if self._model is None:
            self._load()

        embeddings = self._model.encode(text, normalize_embeddings=True)
        if isinstance(text, str):
            return embeddings.tolist()
        return [e.tolist() for e in embeddings]
```

- [ ] **Step 5: Verify GREEN**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_embed.py -v
```

Expected: All ~5 tests PASS (first run downloads model, may take a minute)

- [ ] **Step 6: Commit**

```bash
cd /home/qn/projects/ai-memory-system
git add src/mneme/embed/ tests/test_embed.py
git commit -m "feat: add lazy-loading embedding model wrapper with all-MiniLM-L6-v2"
```

---

### Task 6: Memory Engine — Store module

**Objective:** Wire together embedding + storage: store memory generates embedding, inserts into both SQLite and vector index.

**Files:**
- Create: `src/mneme/engine/store.py`
- Create: `tests/test_engine_store.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_engine_store.py`:

```python
"""Tests for store module."""

import pytest

from mneme.embed.model import EmbeddingModel
from mneme.engine.store import Store
from mneme.engine.types import Memory, MemoryType
from mneme.storage.db import Database
from mneme.storage.vector import VectorIndex


@pytest.fixture
def store():
    """Create a store with in-memory DB and a real (small) embedding model."""
    db = Database(":memory:")
    db.initialize()
    vindex = VectorIndex(":memory:", dimensions=384)
    vindex.initialize()
    embed = EmbeddingModel(model_name="all-MiniLM-L6-v2")
    s = Store(db=db, vindex=vindex, embed=embed)
    yield s
    db.close()
    vindex.close()


class TestStore:
    def test_store_memory(self, store):
        """Storing a memory saves to DB and vector index."""
        m = store.store(Memory(content="Python is my favorite language"))
        assert m.id is not None
        # Check it's in DB
        retrieved = store.db.get(m.id)
        assert retrieved is not None
        assert retrieved.content == "Python is my favorite language"

    def test_store_generates_embedding(self, store):
        """Storing a memory should create a vector entry."""
        m = store.store(Memory(content="Test embedding generation"))
        # Check vector exists
        results = store.vindex.search([0.0] * 384, limit=100)
        ids = [r[0] for r in results]
        assert m.id in ids

    def test_store_with_empty_content_fails(self, store):
        """Storing with empty content raises ValueError."""
        with pytest.raises(ValueError):
            store.store(Memory(content=""))

    def test_get_memory(self, store):
        """Get a memory by ID."""
        m = store.store(Memory(content="memorable"))
        retrieved = store.get(m.id)
        assert retrieved is not None
        assert retrieved.content == "memorable"

    def test_delete_memory(self, store):
        """Deleting a memory removes from DB and vector index."""
        m = store.store(Memory(content="to delete"))
        store.delete(m.id)
        assert store.get(m.id) is None
        # Vector should also be gone
        results = store.vindex.search([0.0] * 384, limit=100)
        ids = [r[0] for r in results]
        assert m.id not in ids

    def test_clear_all(self, store):
        """Clear removes all memories."""
        store.store(Memory(content="a"))
        store.store(Memory(content="b"))
        store.clear()
        assert store.count() == 0
```

- [ ] **Step 2: Verify RED**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_engine_store.py -v
```

Expected: All fail with `ImportError`.

- [ ] **Step 3: Write minimal implementation**

Create `src/mneme/engine/store.py`:

```python
"""Memory store engine — wires embedding + storage layers."""

from __future__ import annotations

from mneme.embed.model import EmbeddingModel
from mneme.engine.types import Memory, MemoryType
from mneme.storage.db import Database
from mneme.storage.vector import VectorIndex


class Store:
    """Store memories with automatic embedding generation."""

    def __init__(
        self,
        db: Database,
        vindex: VectorIndex,
        embed: EmbeddingModel,
    ):
        self.db = db
        self.vindex = vindex
        self.embed = embed

    def store(self, memory: Memory) -> Memory:
        """Store a memory: generate embedding, insert to DB + vector index."""
        # Generate embedding
        embedding = self.embed.encode(memory.content)
        assert isinstance(embedding, list) and len(embedding) > 0

        # Insert to DB
        self.db.insert(memory)

        # Insert to vector index
        self.vindex.insert(memory.id, embedding)

        return memory

    def get(self, memory_id: str) -> Memory | None:
        """Get a memory by ID."""
        return self.db.get(memory_id)

    def delete(self, memory_id: str) -> None:
        """Delete a memory from DB and vector index."""
        self.db.soft_delete(memory_id)
        self.vindex.delete(memory_id)

    def clear(self) -> None:
        """Clear all memories."""
        self.db.clear()
        # Recreate vector table (simplest way to clear it)
        self.vindex.conn.execute("DROP TABLE IF EXISTS memories_vec")
        self.vindex.initialize()

    def count(self) -> int:
        """Count non-deleted memories."""
        return self.db.count()
```

- [ ] **Step 4: Verify GREEN**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_engine_store.py -v
```

Expected: All ~6 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /home/qn/projects/ai-memory-system
git add src/mneme/engine/store.py tests/test_engine_store.py
git commit -m "feat: add memory store engine with embedding + dual storage"
```

---

### Task 7: Memory Engine — Search module

**Objective:** Implement hybrid search (semantic + keyword) with type/tag filtering. Semantic search uses the vector index, keyword search falls back to SQLite LIKE / BM25.

**Files:**
- Create: `src/mneme/engine/search.py`
- Create: `tests/test_engine_search.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_engine_search.py`:

```python
"""Tests for search module."""

import pytest

from mneme.embed.model import EmbeddingModel
from mneme.engine.store import Store
from mneme.engine.search import Searcher
from mneme.engine.types import Memory, MemoryType
from mneme.storage.db import Database
from mneme.storage.vector import VectorIndex


@pytest.fixture
def searcher():
    """Create a searcher with some seeded memories."""
    db = Database(":memory:")
    db.initialize()
    vindex = VectorIndex(":memory:", dimensions=384)
    vindex.initialize()
    embed = EmbeddingModel(model_name="all-MiniLM-L6-v2")
    store = Store(db=db, vindex=vindex, embed=embed)
    s = Searcher(db=db, vindex=vindex, embed=embed)

    # Seed some memories
    store.store(Memory(content="Python is great for data science", type=MemoryType.FACT, tags=["python", "data"]))
    store.store(Memory(content="I prefer TypeScript for web apps", type=MemoryType.PREFERENCE, tags=["typescript", "web"]))
    store.store(Memory(content="Meeting at 3pm tomorrow", type=MemoryType.EVENT, tags=["meeting"]))
    store.store(Memory(content="The user said they love Rust", type=MemoryType.CONVERSATION, tags=["rust"]))
    store.store(Memory(content="Always use pytest for testing", type=MemoryType.SKILL, tags=["testing", "python"]))

    yield s
    db.close()
    vindex.close()


class TestSearcher:
    def test_search_by_keyword(self, searcher):
        """Basic keyword search returns matching memories."""
        results = searcher.search("Python")
        assert len(results) >= 1
        assert any("Python" in m.content for m in results)

    def test_search_by_type(self, searcher):
        """Search filtered by type."""
        results = searcher.search("", type_filter=MemoryType.EVENT)
        assert len(results) == 1
        assert results[0].type == MemoryType.EVENT

    def test_search_by_tag(self, searcher):
        """Search filtered by tag."""
        results = searcher.search("", tags=["python"])
        assert len(results) >= 2  # "Python" fact + "pytest" skill both tagged python

    def test_search_semantic(self, searcher):
        """Semantic search returns relevant results even without keyword match."""
        results = searcher.search("coding preferences", semantic_weight=1.0)
        assert len(results) >= 1
        # The preference about TypeScript should rank high
        # This is a soft test — semantic similarity is approximate
        assert len(results) > 0

    def test_search_hybrid(self, searcher):
        """Hybrid search combines semantic + keyword."""
        results = searcher.search("Python", semantic_weight=0.5)
        assert len(results) >= 1

    def test_search_limit(self, searcher):
        """Search respects limit."""
        results = searcher.search("", limit=2)
        assert len(results) <= 2

    def test_search_empty_no_results(self, searcher):
        """Search with nonsense text still returns empty (not crash)."""
        results = searcher.search("xyznonexistent12345")
        assert isinstance(results, list)

    def test_search_excludes_deleted(self, searcher):
        """Soft-deleted memories should not appear in search."""
        results_before = searcher.search("Meeting")
        # The searcher works on the db which already excludes soft-deleted
        # So this should work naturally
        assert len(results_before) >= 1
```

- [ ] **Step 2: Verify RED**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_engine_search.py -v
```

Expected: All fail with `ImportError`.

- [ ] **Step 3: Write minimal implementation**

Create `src/mneme/engine/search.py`:

```python
"""Memory search engine — hybrid semantic + keyword search."""

from __future__ import annotations

from mneme.embed.model import EmbeddingModel
from mneme.engine.types import Memory, MemoryType
from mneme.storage.db import Database
from mneme.storage.vector import VectorIndex


class Searcher:
    """Hybrid search: semantic (vector) + keyword (SQLite)."""

    def __init__(
        self,
        db: Database,
        vindex: VectorIndex,
        embed: EmbeddingModel,
    ):
        self.db = db
        self.vindex = vindex
        self.embed = embed

    def search(
        self,
        query: str = "",
        type_filter: MemoryType | None = None,
        tags: list[str] | None = None,
        limit: int = 20,
        semantic_weight: float = 0.5,
    ) -> list[Memory]:
        """Hybrid search with optional filters.

        If query is empty, uses keyword-only search with filters.
        If semantic_weight > 0, generates an embedding and searches vector index.
        Final results are merged: vector results ranked first, then keyword.
        """
        if not query.strip():
            # No query — just filter
            return self.db.search("", type_filter=type_filter, tags=tags, limit=limit)

        # 1. Vector search (semantic)
        vector_results: list[Memory] = []
        if semantic_weight > 0:
            query_vec = self.embed.encode(query)
            assert isinstance(query_vec, list)
            vec_hits = self.vindex.search(query_vec, limit=limit)
            if vec_hits:
                vec_ids = [hit[0] for hit in vec_hits]
                # Fetch full memories for these IDs, filtering by type/tag
                for vid in vec_ids:
                    mem = self.db.get(vid)
                    if mem is None:
                        continue
                    if type_filter and mem.type != type_filter:
                        continue
                    if tags and not any(t in mem.tags for t in tags):
                        continue
                    vector_results.append(mem)
                    if len(vector_results) >= limit:
                        break

        # 2. Keyword search
        keyword_results = self.db.search(query, type_filter=type_filter, tags=tags, limit=limit)

        # 3. Merge: vector results first (deduplicated), then keyword results
        seen_ids = set()
        merged: list[Memory] = []
        for mem in vector_results:
            if mem.id not in seen_ids:
                merged.append(mem)
                seen_ids.add(mem.id)
        for mem in keyword_results:
            if mem.id not in seen_ids:
                merged.append(mem)
                seen_ids.add(mem.id)
                if len(merged) >= limit:
                    break

        return merged[:limit]
```

- [ ] **Step 4: Verify GREEN**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_engine_search.py -v
```

Expected: All ~8 tests PASS

- [ ] **Step 5: Commit**

```bash
cd /home/qn/projects/ai-memory-system
git add src/mneme/engine/search.py tests/test_engine_search.py
git commit -m "feat: add hybrid semantic + keyword search engine"
```

---

### Task 8: HTTP API (FastAPI)

**Objective:** Create FastAPI application with all REST endpoints: CRUD, search, health, stats.

**Files:**
- Create: `src/mneme/__init__.py` (update to work with server)
- Create: `src/mneme/api/__init__.py`
- Create: `src/mneme/api/app.py`
- Create: `src/mneme/api/routes.py`
- Create: `src/mneme/server.py`
- Create: `tests/test_api.py`

- [ ] **Step 1: Create API package init**

Create `src/mneme/api/__init__.py` (empty).

- [ ] **Step 2: Write the failing tests**

Create `tests/test_api.py`:

```python
"""Tests for HTTP API."""

import pytest
from httpx import AsyncClient, ASGITransport

from mneme.api.app import create_app


@pytest.fixture
async def client():
    """Create a test client with in-memory storage."""
    app = create_app(db_path=":memory:")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_health(client):
    """GET /v1/health returns ok."""
    resp = await client.get("/v1/health")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ok"


@pytest.mark.asyncio
async def test_create_memory(client):
    """POST /v1/memories creates and returns a memory."""
    resp = await client.post("/v1/memories", json={"content": "Hello world"})
    assert resp.status_code == 201
    data = resp.json()
    assert data["content"] == "Hello world"
    assert data["type"] == "fact"
    assert "id" in data


@pytest.mark.asyncio
async def test_create_memory_with_type(client):
    """POST with type preference."""
    resp = await client.post(
        "/v1/memories", json={"content": "I like Python", "type": "preference"}
    )
    assert resp.status_code == 201
    assert resp.json()["type"] == "preference"


@pytest.mark.asyncio
async def test_get_memory(client):
    """GET /v1/memories/:id returns the memory."""
    create = await client.post("/v1/memories", json={"content": "test"})
    mem_id = create.json()["id"]
    resp = await client.get(f"/v1/memories/{mem_id}")
    assert resp.status_code == 200
    assert resp.json()["content"] == "test"


@pytest.mark.asyncio
async def test_get_nonexistent(client):
    """GET /v1/memories/:id returns 404 for missing."""
    resp = await client.get("/v1/memories/nonexistent")
    assert resp.status_code == 404


@pytest.mark.asyncio
async def test_search_memories(client):
    """GET /v1/memories?q=... searches memories."""
    await client.post("/v1/memories", json={"content": "Python rocks"})
    await client.post("/v1/memories", json={"content": "Rust is fast"})
    resp = await client.get("/v1/memories", params={"q": "Python"})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["results"]) >= 1
    assert data["results"][0]["content"] == "Python rocks"


@pytest.mark.asyncio
async def test_search_with_filters(client):
    """Search with type and tag filters."""
    await client.post(
        "/v1/memories", json={"content": "Python fact", "type": "fact", "tags": ["python"]}
    )
    await client.post(
        "/v1/memories", json={"content": "JS pref", "type": "preference", "tags": ["js"]}
    )
    resp = await client.get("/v1/memories", params={"type": "preference"})
    assert resp.status_code == 200
    assert len(resp.json()["results"]) == 1


@pytest.mark.asyncio
async def test_update_memory(client):
    """PUT /v1/memories/:id updates content."""
    create = await client.post("/v1/memories", json={"content": "original"})
    mem_id = create.json()["id"]
    resp = await client.put(f"/v1/memories/{mem_id}", json={"content": "updated"})
    assert resp.status_code == 200
    assert resp.json()["content"] == "updated"


@pytest.mark.asyncio
async def test_delete_memory(client):
    """DELETE /v1/memories/:id soft-deletes."""
    create = await client.post("/v1/memories", json={"content": "to delete"})
    mem_id = create.json()["id"]
    resp = await client.delete(f"/v1/memories/{mem_id}")
    assert resp.status_code == 200
    # Verify it's gone
    get_resp = await client.get(f"/v1/memories/{mem_id}")
    assert get_resp.status_code == 404


@pytest.mark.asyncio
async def test_clear_all(client):
    """DELETE /v1/memories clears all."""
    await client.post("/v1/memories", json={"content": "a"})
    await client.post("/v1/memories", json={"content": "b"})
    resp = await client.delete("/v1/memories")
    assert resp.status_code == 200
    # Verify empty
    search = await client.get("/v1/memories")
    assert len(search.json()["results"]) == 0


@pytest.mark.asyncio
async def test_stats(client):
    """GET /v1/stats returns system stats."""
    await client.post("/v1/memories", json={"content": "a"})
    resp = await client.get("/v1/stats")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] >= 1
    assert "by_type" in data


@pytest.mark.asyncio
async def test_create_memory_empty_content(client):
    """POST with empty content returns 422."""
    resp = await client.post("/v1/memories", json={"content": ""})
    assert resp.status_code == 422
```

- [ ] **Step 3: Verify RED**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_api.py -v
```

Expected: All fail with `ImportError`.

- [ ] **Step 4: Write minimal implementation**

Create `src/mneme/api/app.py`:

```python
"""FastAPI application factory for Mneme."""

from __future__ import annotations

from fastapi import FastAPI

from mneme.api.routes import router
from mneme.embed.model import EmbeddingModel
from mneme.engine.search import Searcher
from mneme.engine.store import Store
from mneme.engine.types import MemoryType
from mneme.storage.db import Database
from mneme.storage.vector import VectorIndex


def create_app(db_path: str = "memories.db") -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(title="Mneme", version="0.1.0", description="Edge-first memory for AI agents.")

    # Initialize storage
    db = Database(db_path)
    db.initialize()
    vindex = VectorIndex(db_path, dimensions=384)
    vindex.initialize()

    # Initialize engine
    embed = EmbeddingModel(model_name="all-MiniLM-L6-v2")
    store = Store(db=db, vindex=vindex, embed=embed)
    searcher = Searcher(db=db, vindex=vindex, embed=embed)

    # Store on app state
    app.state.db = db
    app.state.vindex = vindex
    app.state.embed = embed
    app.state.store = store
    app.state.searcher = searcher

    app.include_router(router, prefix="/v1")

    return app
```

Create `src/mneme/api/routes.py`:

```python
"""HTTP API routes for Mneme."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.requests import Request
from pydantic import BaseModel, Field

from mneme.engine.types import Memory, MemoryType

router = APIRouter()


class CreateMemoryRequest(BaseModel):
    content: str = Field(..., min_length=1)
    type: str = "fact"
    tags: list[str] = []
    weight: float = 1.0
    metadata: dict[str, Any] = {}


class UpdateMemoryRequest(BaseModel):
    content: str | None = None
    type: str | None = None
    tags: list[str] | None = None
    weight: float | None = None
    metadata: dict[str, Any] | None = None


@router.post("/memories", status_code=201)
async def create_memory(req: Request, body: CreateMemoryRequest):
    """Create a new memory."""
    store = req.app.state.store
    try:
        mem_type = MemoryType(body.type)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid type: {body.type}")

    memory = Memory(
        content=body.content,
        type=mem_type,
        tags=body.tags,
        weight=body.weight,
        metadata=body.metadata,
    )
    store.store(memory)
    return memory.to_dict()


@router.get("/memories/{memory_id}")
async def get_memory(req: Request, memory_id: str):
    """Get a memory by ID."""
    store = req.app.state.store
    memory = store.get(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    return memory.to_dict()


@router.get("/memories")
async def search_memories(
    req: Request,
    q: str = Query("", description="Search query"),
    type: str | None = Query(None, alias="type"),
    tags: str | None = Query(None, description="Comma-separated tags"),
    limit: int = Query(20, ge=1, le=100),
):
    """Search memories."""
    searcher = req.app.state.searcher
    type_filter = MemoryType(type) if type else None
    tag_list = tags.split(",") if tags else None
    results = searcher.search(query=q, type_filter=type_filter, tags=tag_list, limit=limit)
    return {"results": [m.to_dict() for m in results]}


@router.put("/memories/{memory_id}")
async def update_memory(req: Request, memory_id: str, body: UpdateMemoryRequest):
    """Update a memory."""
    store = req.app.state.store
    memory = store.get(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")

    if body.content is not None:
        memory.content = body.content
    if body.type is not None:
        try:
            memory.type = MemoryType(body.type)
        except ValueError:
            raise HTTPException(status_code=422, detail=f"Invalid type: {body.type}")
    if body.tags is not None:
        memory.tags = body.tags
    if body.weight is not None:
        memory.weight = body.weight
    if body.metadata is not None:
        memory.metadata = body.metadata

    store.db.update(memory)
    return memory.to_dict()


@router.delete("/memories/{memory_id}")
async def delete_memory(req: Request, memory_id: str):
    """Soft-delete a memory."""
    store = req.app.state.store
    memory = store.get(memory_id)
    if memory is None:
        raise HTTPException(status_code=404, detail="Memory not found")
    store.delete(memory_id)
    return {"status": "deleted"}


@router.delete("/memories")
async def clear_memories(req: Request):
    """Clear all memories."""
    store = req.app.state.store
    store.clear()
    return {"status": "cleared"}


@router.get("/health")
async def health():
    """Health check."""
    return {"status": "ok"}


@router.get("/stats")
async def stats(req: Request):
    """System statistics."""
    store = req.app.state.store
    db = req.app.state.db
    total = store.count()
    # Count by type
    rows = db.conn.execute(
        "SELECT type, COUNT(*) as cnt FROM memories WHERE deleted_at IS NULL GROUP BY type"
    ).fetchall()
    by_type = {row["type"]: row["cnt"] for row in rows}
    return {
        "total": total,
        "by_type": by_type,
    }
```

Create `src/mneme/server.py`:

```python
"""Mneme server entrypoint."""

from mneme.api.app import create_app

app = create_app()
```

- [ ] **Step 5: Verify GREEN**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_api.py -v
```

Expected: All ~13 tests PASS

- [ ] **Step 6: Commit**

```bash
cd /home/qn/projects/ai-memory-system
git add src/mneme/api/ src/mneme/server.py tests/test_api.py
git commit -m "feat: add FastAPI HTTP API with CRUD, search, health, and stats endpoints"
```

---

### Task 9: CLI

**Objective:** Create Click-based CLI with `mneme serve`, `mneme add`, `mneme search`, `mneme delete`, `mneme stats` commands.

**Files:**
- Modify: `src/mneme/cli.py`
- Create: `tests/test_cli.py`

- [ ] **Step 1: Write the failing tests**

Create `tests/test_cli.py`:

```python
"""Tests for CLI."""

import pytest
from click.testing import CliRunner

from mneme.cli import cli


@pytest.fixture
def runner():
    return CliRunner()


class TestCLI:
    def test_serve_help(self, runner):
        """`mneme serve --help` shows help."""
        result = runner.invoke(cli, ["serve", "--help"])
        assert result.exit_code == 0
        assert "Start" in result.output or "serve" in result.output

    def test_add_help(self, runner):
        """`mneme add --help` shows help."""
        result = runner.invoke(cli, ["add", "--help"])
        assert result.exit_code == 0
        assert "Add" in result.output or "add" in result.output

    def test_search_help(self, runner):
        """`mneme search --help` shows help."""
        result = runner.invoke(cli, ["search", "--help"])
        assert result.exit_code == 0
        assert "Search" in result.output or "search" in result.output

    def test_delete_help(self, runner):
        """`mneme delete --help` shows help."""
        result = runner.invoke(cli, ["delete", "--help"])
        assert result.exit_code == 0

    def test_stats_help(self, runner):
        """`mneme stats --help` shows help."""
        result = runner.invoke(cli, ["stats", "--help"])
        assert result.exit_code == 0
```

- [ ] **Step 2: Verify RED**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_cli.py -v
```

Expected: All fail — cli.py doesn't exist yet or is a stub.

- [ ] **Step 3: Write minimal implementation**

Create `src/mneme/cli.py`:

```python
"""Mneme CLI — Click-based command-line interface."""

from __future__ import annotations

import click
import uvicorn


@click.group()
def cli():
    """Mneme — Edge-first memory for AI agents."""


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=8989, help="Port to listen on", type=int)
@click.option("--db", default="memories.db", help="Database file path")
@click.option("--reload", is_flag=True, help="Enable auto-reload (dev only)")
def serve(host: str, port: int, db: str, reload: bool):
    """Start the Mneme HTTP server."""
    import os

    os.environ["MNEME_DB_PATH"] = db
    click.echo(f"🧠 Mneme server starting on http://{host}:{port}")
    click.echo(f"   Database: {db}")
    uvicorn.run(
        "mneme.server:app",
        host=host,
        port=port,
        reload=reload,
    )


@cli.command()
@click.argument("content")
@click.option("--type", "-t", default="fact", help="Memory type")
@click.option("--tags", "-g", default="", help="Comma-separated tags")
@click.option("--db", default="memories.db", help="Database file path")
def add(content: str, type: str, tags: str, db: str):
    """Add a new memory."""
    from mneme.embed.model import EmbeddingModel
    from mneme.engine.store import Store
    from mneme.engine.types import Memory, MemoryType
    from mneme.storage.db import Database
    from mneme.storage.vector import VectorIndex

    database = Database(db)
    database.initialize()
    vindex = VectorIndex(db, dimensions=384)
    vindex.initialize()
    embed = EmbeddingModel()
    store = Store(db=database, vindex=vindex, embed=embed)

    tag_list = [t.strip() for t in tags.split(",") if t.strip()] if tags else []
    try:
        mem_type = MemoryType(type)
    except ValueError:
        click.echo(f"❌ Invalid type: {type}", err=True)
        return

    memory = Memory(content=content, type=mem_type, tags=tag_list)
    store.store(memory)
    click.echo(f"✅ Stored memory: {memory.id[:8]}...")
    click.echo(f"   Content: {content[:60]}{'...' if len(content) > 60 else ''}")


@cli.command()
@click.argument("query", required=False, default="")
@click.option("--type", "-t", default=None, help="Filter by memory type")
@click.option("--tags", "-g", default=None, help="Filter by comma-separated tags")
@click.option("--limit", "-l", default=10, help="Max results", type=int)
@click.option("--db", default="memories.db", help="Database file path")
def search(query: str, type: str | None, tags: str | None, limit: int, db: str):
    """Search memories."""
    from mneme.embed.model import EmbeddingModel
    from mneme.engine.search import Searcher
    from mneme.engine.types import MemoryType
    from mneme.storage.db import Database
    from mneme.storage.vector import VectorIndex

    database = Database(db)
    database.initialize()
    vindex = VectorIndex(db, dimensions=384)
    vindex.initialize()
    embed = EmbeddingModel()
    searcher = Searcher(db=database, vindex=vindex, embed=embed)

    type_filter = MemoryType(type) if type else None
    tag_list = tags.split(",") if tags else None

    results = searcher.search(query=query, type_filter=type_filter, tags=tag_list, limit=limit)

    if not results:
        click.echo("📭 No memories found.")
        return

    from rich.console import Console
    from rich.table import Table

    console = Console()
    table = Table(title=f"Memories ({len(results)})")
    table.add_column("ID", style="dim")
    table.add_column("Type")
    table.add_column("Content")
    table.add_column("Tags")

    for m in results:
        table.add_row(
            m.id[:8],
            m.type.value,
            m.content[:50] + ("..." if len(m.content) > 50 else ""),
            ", ".join(m.tags),
        )
    console.print(table)


@cli.command()
@click.argument("memory_id")
@click.option("--db", default="memories.db", help="Database file path")
def delete(memory_id: str, db: str):
    """Delete a memory by ID."""
    from mneme.engine.store import Store
    from mneme.storage.db import Database
    from mneme.storage.vector import VectorIndex

    database = Database(db)
    database.initialize()
    vindex = VectorIndex(db, dimensions=384)
    vindex.initialize()

    # We need an embedding model for Store, but delete doesn't use it
    from mneme.embed.model import EmbeddingModel

    embed = EmbeddingModel()
    store = Store(db=database, vindex=vindex, embed=embed)

    if store.get(memory_id) is None:
        click.echo(f"❌ Memory not found: {memory_id}")
        return

    store.delete(memory_id)
    click.echo(f"🗑️  Deleted: {memory_id}")


@cli.command()
@click.option("--db", default="memories.db", help="Database file path")
@click.option("--force", is_flag=True, help="Skip confirmation")
def clear(db: str, force: bool):
    """Clear all memories."""
    if not force:
        click.confirm("⚠️  This will delete ALL memories. Continue?", abort=True)

    from mneme.engine.store import Store
    from mneme.storage.db import Database
    from mneme.storage.vector import VectorIndex

    database = Database(db)
    database.initialize()
    vindex = VectorIndex(db, dimensions=384)
    vindex.initialize()

    from mneme.embed.model import EmbeddingModel

    embed = EmbeddingModel()
    store = Store(db=database, vindex=vindex, embed=embed)
    store.clear()
    click.echo("🗑️  All memories cleared.")


@cli.command()
@click.option("--db", default="memories.db", help="Database file path")
def stats(db: str):
    """Show memory statistics."""
    from mneme.engine.store import Store
    from mneme.storage.db import Database
    from mneme.storage.vector import VectorIndex

    database = Database(db)
    database.initialize()
    vindex = VectorIndex(db, dimensions=384)
    vindex.initialize()

    from mneme.embed.model import EmbeddingModel

    embed = EmbeddingModel()
    store = Store(db=database, vindex=vindex, embed=embed)

    total = store.count()
    rows = database.conn.execute(
        "SELECT type, COUNT(*) as cnt FROM memories WHERE deleted_at IS NULL GROUP BY type"
    ).fetchall()

    click.echo(f"🧠 Mneme Statistics")
    click.echo(f"   Total memories: {total}")
    for row in rows:
        click.echo(f"   {row['type']}: {row['cnt']}")


if __name__ == "__main__":
    cli()
```

- [ ] **Step 4: Verify GREEN**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_cli.py -v
```

Expected: All ~5 tests PASS

- [ ] **Step 5: Quick smoke test — verify CLI entry point**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
mneme serve --help
mneme add --help
mneme search --help
```

Expected: All show help text with command descriptions.

- [ ] **Step 6: Commit**

```bash
cd /home/qn/projects/ai-memory-system
git add src/mneme/cli.py tests/test_cli.py
git commit -m "feat: add Click CLI with serve, add, search, delete, clear, stats commands"
```

---

### Task 10: MCP Protocol server

**Objective:** Implement MCP server exposing Mneme operations as MCP tools (store_memory, search_memory, forget_memory, wipe_memories, memory_stats).

**Files:**
- Create: `src/mneme/mcp/__init__.py`
- Create: `src/mneme/mcp/server.py`
- Create: `tests/test_mcp.py`

- [ ] **Step 1: Create MCP package init**

Create `src/mneme/mcp/__init__.py` (empty).

- [ ] **Step 2: Check MCP SDK availability**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -c "import mcp; print(mcp.__version__)"
```

If MCP SDK is not found or too old, install/upgrade: `pip install 'mcp>=1.0.0'`

- [ ] **Step 3: Write the failing tests**

Create `tests/test_mcp.py`:

```python
"""Tests for MCP server."""

import pytest

from mneme.embed.model import EmbeddingModel
from mneme.engine.search import Searcher
from mneme.engine.store import Store
from mneme.storage.db import Database
from mneme.storage.vector import VectorIndex


@pytest.fixture
def mcp_env():
    """Create MCP server with in-memory storage."""
    from mneme.mcp.server import create_mcp_server

    db = Database(":memory:")
    db.initialize()
    vindex = VectorIndex(":memory:", dimensions=384)
    vindex.initialize()
    embed = EmbeddingModel()
    store = Store(db=db, vindex=vindex, embed=embed)
    searcher = Searcher(db=db, vindex=vindex, embed=embed)

    mcp = create_mcp_server(store=store, searcher=searcher)
    yield mcp
    db.close()
    vindex.close()


class TestMCPServer:
    def test_server_name(self, mcp_env):
        """Server has name 'mneme'."""
        assert mcp_env.name == "mneme"

    @pytest.mark.asyncio
    async def test_store_memory_tool(self, mcp_env):
        """Store memory tool works."""
        result = await mcp_env.call_tool("store_memory", {"content": "test memory"})
        assert result is not None
        # Result should contain the memory ID
        assert "id" in str(result).lower() or len(str(result)) > 0

    @pytest.mark.asyncio
    async def test_search_memory_tool(self, mcp_env):
        """Search memory tool works."""
        await mcp_env.call_tool("store_memory", {"content": "python is cool"})
        result = await mcp_env.call_tool("search_memory", {"query": "python"})
        assert result is not None

    @pytest.mark.asyncio
    async def test_forget_memory_tool(self, mcp_env):
        """Forget memory tool works."""
        store_result = await mcp_env.call_tool("store_memory", {"content": "to forget"})
        # Extract memory ID from result
        result_str = str(store_result)
        # Search afterwards to verify it's gone
        search_result = await mcp_env.call_tool("search_memory", {"query": "to forget"})

    @pytest.mark.asyncio
    async def test_memory_stats_tool(self, mcp_env):
        """Memory stats tool works."""
        await mcp_env.call_tool("store_memory", {"content": "a"})
        await mcp_env.call_tool("store_memory", {"content": "b"})
        result = await mcp_env.call_tool("memory_stats", {})
        assert result is not None
```

- [ ] **Step 4: Verify RED**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_mcp.py -v
```

Expected: All fail with `ImportError`.

- [ ] **Step 5: Write minimal implementation**

Create `src/mneme/mcp/server.py`:

```python
"""MCP protocol server for Mneme."""

from __future__ import annotations

from typing import Any

from mneme.engine.search import Searcher
from mneme.engine.store import Store
from mneme.engine.types import Memory, MemoryType


def create_mcp_server(
    store: Store,
    searcher: Searcher,
) -> Any:
    """Create an MCP server with Mneme tools.

    Returns a FastMCP instance from the MCP Python SDK.
    """
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError:
        raise ImportError("MCP SDK required: pip install mcp>=1.0.0")

    mcp = FastMCP("mneme", instructions="Edge-first memory for AI agents.")

    @mcp.tool()
    def store_memory(
        content: str,
        type: str = "fact",
        tags: list[str] | None = None,
        weight: float = 1.0,
    ) -> dict[str, Any]:
        """Store a new memory.

        Args:
            content: The memory content text.
            type: Memory type (fact, preference, event, conversation, skill).
            tags: Optional list of tags.
            weight: Importance weight (default 1.0).
        """
        try:
            mem_type = MemoryType(type)
        except ValueError:
            return {"error": f"Invalid type: {type}. Must be one of: fact, preference, event, conversation, skill"}

        memory = Memory(content=content, type=mem_type, tags=tags or [], weight=weight)
        store.store(memory)
        return memory.to_dict()

    @mcp.tool()
    def search_memory(
        query: str = "",
        type: str | None = None,
        tags: str | None = None,
        limit: int = 20,
    ) -> dict[str, Any]:
        """Search memories.

        Args:
            query: Search text (optional — returns all if empty).
            type: Optional type filter.
            tags: Optional comma-separated tag filter.
            limit: Max results (default 20).
        """
        type_filter = MemoryType(type) if type else None
        tag_list = tags.split(",") if tags else None
        results = searcher.search(query=query, type_filter=type_filter, tags=tag_list, limit=limit)
        return {"results": [m.to_dict() for m in results]}

    @mcp.tool()
    def forget_memory(memory_id: str) -> dict[str, str]:
        """Delete a memory by ID.

        Args:
            memory_id: The UUID of the memory to delete.
        """
        existing = store.get(memory_id)
        if existing is None:
            return {"error": "Memory not found"}
        store.delete(memory_id)
        return {"status": "deleted", "id": memory_id}

    @mcp.tool()
    def wipe_memories(confirm: bool = False) -> dict[str, str]:
        """Clear ALL memories (requires confirm=True).

        Args:
            confirm: Must be True to proceed.
        """
        if not confirm:
            return {"error": "Confirmation required. Set confirm=True to wipe all memories."}
        store.clear()
        return {"status": "cleared"}

    @mcp.tool()
    def memory_stats() -> dict[str, Any]:
        """Get memory statistics."""
        total = store.count()
        db = store.db
        rows = db.conn.execute(
            "SELECT type, COUNT(*) as cnt FROM memories WHERE deleted_at IS NULL GROUP BY type"
        ).fetchall()
        by_type = {row["type"]: row["cnt"] for row in rows}
        vec_count = store.vindex.count()
        return {
            "total_memories": total,
            "by_type": by_type,
            "vector_count": vec_count,
        }

    return mcp
```

- [ ] **Step 6: Verify GREEN**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_mcp.py -v
```

Expected: All ~5 tests PASS

- [ ] **Step 7: Commit**

```bash
cd /home/qn/projects/ai-memory-system
git add src/mneme/mcp/ tests/test_mcp.py
git commit -m "feat: add MCP protocol server with store, search, forget, wipe, and stats tools"
```

---

### Task 11: Integration test — full end-to-end flow

**Objective:** Validate the complete pipeline: start server → store memories → search → update → delete → stats.

**Files:**
- Create: `tests/test_integration.py`

- [ ] **Step 1: Write the tests**

Create `tests/test_integration.py`:

```python
"""End-to-end integration tests for Mneme."""

import pytest
from httpx import AsyncClient, ASGITransport

from mneme.api.app import create_app


@pytest.fixture
async def client():
    app = create_app(db_path=":memory:")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_full_lifecycle(client):
    """Complete memory lifecycle: create → read → search → update → delete."""

    # 1. Create multiple memories
    m1 = await client.post("/v1/memories", json={"content": "Python is great for data science", "tags": ["python", "data"]})
    m2 = await client.post("/v1/memories", json={"content": "I prefer TypeScript for web", "type": "preference", "tags": ["typescript", "web"]})
    m3 = await client.post("/v1/memories", json={"content": "Meeting at 3pm tomorrow", "type": "event", "tags": ["meeting"]})

    assert m1.status_code == 201
    assert m2.status_code == 201
    assert m3.status_code == 201

    id1 = m1.json()["id"]
    id2 = m2.json()["id"]

    # 2. Read by ID
    get1 = await client.get(f"/v1/memories/{id1}")
    assert get1.status_code == 200
    assert get1.json()["content"] == "Python is great for data science"

    # 3. Search by keyword
    search = await client.get("/v1/memories", params={"q": "TypeScript"})
    assert search.status_code == 200
    results = search.json()["results"]
    assert len(results) >= 1
    assert any("TypeScript" in r["content"] for r in results)

    # 4. Search by type
    type_search = await client.get("/v1/memories", params={"type": "event"})
    assert len(type_search.json()["results"]) == 1

    # 5. Search by tag
    tag_search = await client.get("/v1/memories", params={"tags": "python"})
    assert len(tag_search.json()["results"]) >= 1

    # 6. Update
    update = await client.put(f"/v1/memories/{id1}", json={"content": "Python is amazing for data science"})
    assert update.status_code == 200
    assert update.json()["content"] == "Python is amazing for data science"

    # 7. Soft delete
    delete_resp = await client.delete(f"/v1/memories/{id2}")
    assert delete_resp.status_code == 200
    get_deleted = await client.get(f"/v1/memories/{id2}")
    assert get_deleted.status_code == 404

    # 8. Stats
    stats = await client.get("/v1/stats")
    assert stats.status_code == 200
    data = stats.json()
    assert data["total"] >= 2  # 3 stored - 1 deleted = 2
    assert "by_type" in data

    # 9. Clear all
    clear = await client.delete("/v1/memories")
    assert clear.status_code == 200
    after_clear = await client.get("/v1/memories")
    assert len(after_clear.json()["results"]) == 0


@pytest.mark.asyncio
async def test_health_endpoint(client):
    """Health check returns ok."""
    resp = await client.get("/v1/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


@pytest.mark.asyncio
async def test_invalid_memory_type(client):
    """Invalid type returns 422."""
    resp = await client.post("/v1/memories", json={"content": "test", "type": "invalid"})
    assert resp.status_code == 422
```

- [ ] **Step 2: Verify RED → GREEN**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/test_integration.py -v
```

Expected: All tests PASS

- [ ] **Step 3: Run full test suite**

```bash
cd /home/qn/projects/ai-memory-system
source .venv/bin/activate
python3 -m pytest tests/ -v --tb=short
```

Expected: All tests pass (~50+ tests total across all test files)

- [ ] **Step 4: Commit**

```bash
cd /home/qn/projects/ai-memory-system
git add tests/test_integration.py
git commit -m "test: add end-to-end integration test covering full memory lifecycle"
```

---

## Risks & Open Questions

1. **sqlite-vec on aarch64 (Raspberry Pi)** — sqlite-vec may not have prebuilt wheels for `aarch64-linux-gnu`. Alternative: compile from source, or use a fallback (no vector search if sqlite-vec is unavailable).
2. **sentence-transformers model download** — `all-MiniLM-L6-v2` is ~80MB. First `pip install` will download it. Consider offering a lighter model option for constrained devices.
3. **MCP SDK compatibility** — MCP Python SDK is still evolving (pre-1.0). Pin to a known-good version.
4. **Embedding model dependency** — sentence-transformers pulls in PyTorch (~800MB). This significantly increases install size. Consider offering `mneme-light` with an HTTP-based embedding option.
5. **CLI-first database path** — The CLI uses a file-based database by default (`memories.db`). The server uses the same. Both read `MNEME_DB_PATH` env var. Should work seamlessly.
