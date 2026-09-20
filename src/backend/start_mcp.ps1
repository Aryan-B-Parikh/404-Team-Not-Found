#!/usr/bin/env pwsh
# Wrapper so bob mcp add can invoke the MCP server without --directory confusion
Set-Location "$PSScriptRoot"
& "C:\Users\kukad\.local\bin\uv.exe" run python -m app.mcp_server
