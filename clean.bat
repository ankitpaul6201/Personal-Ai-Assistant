@echo off
echo Cleaning build directories and temporary files...
if exist build rmdir /s /q build
if exist dist rmdir /s /q dist
if exist release rmdir /s /q release
if exist __pycache__ rmdir /s /q __pycache__
for /d /r . %%d in (__pycache__) do @if exist "%%d" rmdir /s /q "%%d"
echo Clean completed!
