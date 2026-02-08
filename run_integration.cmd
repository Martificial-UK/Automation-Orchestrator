@echo off
cd /d "c:\AI Automation\Automation Orchestrator"

echo.
echo ============================================================
echo Automation Orchestrator - Audit Integration
echo ============================================================
echo.

echo [1/2] Integrating audit logging...
python integrate_audit.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Integration failed!
    pause
    exit /b 1
)

echo.
echo [2/2] Running tests...
python test_audit_integration.py
if %ERRORLEVEL% NEQ 0 (
    echo ERROR: Tests failed!
    pause
    exit /b 1
)

echo.
echo ============================================================
echo SUCCESS: Audit integration complete!
echo ============================================================
echo.
echo Audit logging is now active in all modules.
echo Check logs/audit.log for operation trail.
echo.
pause
