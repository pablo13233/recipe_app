@echo off
REM ==============================================================================
REM Registra la Tarea Programada en el Programador de Tareas de Windows (schtasks)
REM Se ejecutará todos los días a las 02:30 AM (entre 1:00 AM y 4:00 AM)
REM ==============================================================================

echo Registrando tarea programada 'RecipeApp_TasaCambioDiaria'...
schtasks /create /tn "RecipeApp_TasaCambioDiaria" /tr "e:\GitHubProjects\recipe_app\scripts\update_exchange_rate.bat" /sc daily /st 02:30 /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ==============================================================================
    echo [EXITO] Tarea 'RecipeApp_TasaCambioDiaria' registrada para las 02:30 AM todos los dias.
    echo ==============================================================================
) else (
    echo.
    echo [ERROR] No se pudo registrar la tarea. Ejecuta esta consola como Administrador si es necesario.
)
pause
