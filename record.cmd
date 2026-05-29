@echo off
pushd "%~dp0"
echo Starting Meet-Recorder...
uv run python main.py record --chunk-size 15
popd
pause
