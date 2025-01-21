@echo off
echo Starting One Window in Docker...

:: Get host IP address using more reliable method
FOR /F "tokens=4 delims= " %%i IN ('route print ^| find "0.0.0.0" ^| find "0.0.0.0"') DO (
    set HOST_IP=%%i
    goto :next
)

:next
echo Using host IP: %HOST_IP%

:: Start docker-compose
docker-compose up --build

pause
