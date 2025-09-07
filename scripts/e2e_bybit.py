#!/usr/bin/env python3
"""
scripts/e2e_bybit.py

Wrapper runner with a correct environment banner (demo/testnet/main/custom).
It prints the detected environment and then delegates to the existing
`scripts.e2e_bybit_testnet` module, preserving its functionality
(create/cancel order via BYBIT_* env vars, etc.).
"""

import os
import sys
import subprocess


def detect_env_label() -> str:
    url = os.getenv("BYBIT_PRIVATE_URL") or os.getenv("BYBIT_PUBLIC_URL") or ""
    url_l = url.lower()

    if "api-demo.bybit.com" in url_l:
        return "demo"
    if "api-testnet.bybit.com" in url_l:
        return "testnet"
    if "api.bybit.com" in url_l:
        return "main"
    if url:
        return f"custom({url})"
    return "unknown"


def main() -> int:
    label = detect_env_label()
    pub = os.getenv("BYBIT_PUBLIC_URL", "<unset>")
    prv = os.getenv("BYBIT_PRIVATE_URL", "<unset>")

    print(f"== E2E ({label}) : env check ==")
    print(f"PUBLIC_URL  : {pub}")
    print(f"PRIVATE_URL : {prv}")

    # If WS endpoints are explicitly set, show them too (useful for demo)
    ws_spot = os.getenv("WS_PUBLIC_URL_SPOT")
    ws_lin  = os.getenv("WS_PUBLIC_URL_LINEAR")
    if ws_spot or ws_lin:
        print("WS endpoints:")
        if ws_spot:
            print(f"  WS_PUBLIC_URL_SPOT  : {ws_spot}")
        if ws_lin:
            print(f"  WS_PUBLIC_URL_LINEAR: {ws_lin}")

    print("\n-- Delegating to legacy runner: scripts.e2e_bybit_testnet --\n")
    # Delegate to existing test script so behavior stays identical
    try:
        result = subprocess.run([sys.executable, "-m", "scripts.e2e_bybit_testnet"], check=False)
        return result.returncode
    except FileNotFoundError as e:
        print("ERROR: Could not locate the legacy module 'scripts.e2e_bybit_testnet'.")
        print("Make sure it exists in your repository. Original error:", e)
        return 1


if __name__ == "__main__":
    sys.exit(main())
