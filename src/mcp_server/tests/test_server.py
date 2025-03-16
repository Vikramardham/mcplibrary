"""
Tests for the DocFetcherMCPServer implementation.
"""

import os
import pytest
import tempfile
from pathlib import Path
from mcp import Context, Entity
from ..server import DocFetcherMCPServer


@pytest.fixture
def temp_cache_dir():
    """Create a temporary directory for caching docs."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield tmpdir


@pytest.fixture
def server(temp_cache_dir):
    """Create a server instance with temporary cache directory."""
    return DocFetcherMCPServer(cache_dir=temp_cache_dir)


@pytest.mark.asyncio
async def test_handle_request_missing_url(server):
    """Test handling request with missing URL."""
    request = Context(entities=[])
    response = await server.handle_request(request)

    assert len(response.entities) == 1
    assert response.entities[0].type == "error"
    assert response.entities[0].name == "missing_url"


@pytest.mark.asyncio
async def test_handle_request_invalid_url(server):
    """Test handling request with invalid URL."""
    request = Context(entities=[Entity(type="url", name="test_url", data={})])
    response = await server.handle_request(request)

    assert len(response.entities) == 1
    assert response.entities[0].type == "error"
    assert response.entities[0].name == "invalid_url"


@pytest.mark.asyncio
async def test_handle_request_valid_url(server):
    """Test handling request with valid URL."""
    url = "https://ai.pydantic.dev"
    request = Context(entities=[Entity(type="url", name="test_url", data={"url": url})])
    response = await server.handle_request(request)

    assert len(response.entities) == 1
    assert response.entities[0].type == "document"
    assert response.entities[0].data["source_url"] == url
    assert response.entities[0].data["content"] is not None
    assert len(response.entities[0].data["content"]) > 0


@pytest.mark.asyncio
async def test_caching(server):
    """Test document caching functionality."""
    url = "https://ai.pydantic.dev"
    request = Context(entities=[Entity(type="url", name="test_url", data={"url": url})])

    # First request should fetch and cache
    response1 = await server.handle_request(request)
    assert response1.entities[0].type == "document"

    # Get cache file path
    domain = url.replace("https://", "").replace(".", "_")
    cache_file = Path(server.cache_dir) / domain / "fasthtml_doc.txt"

    # Verify cache file exists
    assert cache_file.exists()

    # Second request should use cache
    response2 = await server.handle_request(request)
    assert response2.entities[0].type == "document"

    # Content should be identical
    assert (
        response1.entities[0].data["content"] == response2.entities[0].data["content"]
    )


def test_server_initialization(temp_cache_dir):
    """Test server initialization."""
    server = DocFetcherMCPServer(cache_dir=temp_cache_dir)
    assert server.cache_dir == Path(temp_cache_dir)
    assert server.cache_dir.exists()


def test_get_domain_dir(server):
    """Test domain directory creation."""
    url = "https://ai.pydantic.dev"
    domain_dir = server._get_domain_dir(url)
    assert domain_dir.exists()
    assert domain_dir.name == "ai_pydantic_dev"


def test_echo_resource():
    """Test the echo resource."""
    result = mcp.get_resource("echo://hello")
    assert result == "Echo from resource: hello"


def test_echo_tool():
    """Test the echo tool."""
    result = mcp.call_tool("echo_tool", {"message": "hello"})
    assert result == "Echo from tool: hello"


def test_echo_prompt():
    """Test the echo prompt."""
    result = mcp.get_prompt("echo_prompt", {"message": "hello"})
    assert result == "Please process this message: hello"
