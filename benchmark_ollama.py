"""Benchmark Ollama performance. Implementation: scripts/benchmark_ollama.py"""
import os
import runpy

runpy.run_path(os.path.join(os.path.dirname(__file__), "scripts", "benchmark_ollama.py"), run_name="__main__")
