@echo off
pushd "%~dp0"
echo Meet-Recorder (AUTO MODE) is waiting for a meeting...
uv run python main.py auto
popd
pause
