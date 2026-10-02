@echo off
REM ==============================================================================
REM Script para Ejecutar la Tarea Programada de Tasa de Cambio USD a HNL
REM Programado para ejecutarse diariamente entre las 1:00 AM y 4:00 AM (ej: 02:30 AM)
REM ==============================================================================

cd /d "e:\GitHubProjects\recipe_app"
"C:\Users\pablo\miniconda3\envs\recipe\python.exe" manage.py update_daily_exchange_rate
