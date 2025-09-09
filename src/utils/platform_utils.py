"""
Platform-specific utilities for zkSNARK Benchmark Framework.

Handles platform differences in tool execution and path resolution.
"""

import platform
import shutil
from pathlib import Path
from typing import Optional


def get_tool_executable(tool_name: str) -> str:
    """Get the correct executable name for a tool on current platform.
    
    Args:
        tool_name: Base tool name (e.g., 'snarkjs', 'circom')
        
    Returns:
        Platform-appropriate executable name
    """
    if platform.system() == "Windows":
        # For npm packages on Windows, try .cmd first
        if tool_name in ("snarkjs", "node"):
            cmd_version = f"{tool_name}.cmd"
            if shutil.which(cmd_version):
                return cmd_version
            # If .cmd not found, check for PowerShell version
            ps1_version = f"{tool_name}.ps1"
            if shutil.which(ps1_version):
                return cmd_version  # Still return .cmd as it's more compatible with subprocess
        
        # For other Windows executables, try .exe
        exe_version = f"{tool_name}.exe"
        if shutil.which(exe_version):
            return exe_version
    
    # Default: return as-is for Unix-like systems or if specific version not found
    return tool_name


def find_npm_global_path() -> Optional[Path]:
    """Find npm global installation directory."""
    try:
        import subprocess
        result = subprocess.run(
            ["npm", "config", "get", "prefix"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0:
            npm_prefix = Path(result.stdout.strip())
            if platform.system() == "Windows":
                return npm_prefix
            else:
                return npm_prefix / "bin"
    except Exception:
        pass
    
    return None


def ensure_tool_available(tool_name: str) -> str:
    """Ensure a tool is available and return its executable path.
    
    Args:
        tool_name: Tool name to check
        
    Returns:
        Executable path/name
        
    Raises:
        RuntimeError: If tool is not found
    """
    # First try platform-specific version
    executable = get_tool_executable(tool_name)
    
    if shutil.which(executable):
        return executable
    
    # If not found in PATH, try npm global directory
    if tool_name in ("snarkjs",):
        npm_path = find_npm_global_path()
        if npm_path:
            if platform.system() == "Windows":
                npm_tool = npm_path / f"{tool_name}.cmd"
            else:
                npm_tool = npm_path / tool_name
            
            if npm_tool.exists():
                return str(npm_tool)
    
    # Tool not found
    available_tools = []
    for variant in [tool_name, f"{tool_name}.cmd", f"{tool_name}.exe"]:
        if shutil.which(variant):
            available_tools.append(variant)
    
    if available_tools:
        error_msg = f"Tool '{tool_name}' not found, but found: {available_tools}"
    else:
        error_msg = f"Tool '{tool_name}' not found. Please install it."
    
    raise RuntimeError(error_msg)


def get_default_compiler_tools():
    """Get default tool paths for the compiler.
    
    Returns:
        Dictionary with circom_bin and snarkjs_bin paths
    """
    try:
        return {
            "circom_bin": ensure_tool_available("circom"),
            "snarkjs_bin": ensure_tool_available("snarkjs"),
        }
    except RuntimeError as e:
        # Return defaults and let the compiler handle the error
        return {
            "circom_bin": "circom",
            "snarkjs_bin": get_tool_executable("snarkjs"),
        }