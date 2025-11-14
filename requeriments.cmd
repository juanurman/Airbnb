@echo off
echo =========================================================
echo  INSTALADOR DE DEPENDENCIAS DEL PROYECTO (SCRAPER + WEB)
echo =========================================================
echo.
echo Este script instalara todas las librerias de Python necesarias.
echo (Esto puede tardar unos minutos)...
echo.

REM Usamos python -m pip para asegurar que use el Python correcto
py -m pip install selenium
py -m pip install beautifulsoup4
py -m pip install pandas
py -m pip install openpyxl
py -m pip install scikit-learn
py -m pip install flask
py -m pip install joblib

echo.
echo --- ¡Instalacion completa! ---
echo.
echo Presiona cualquier tecla para cerrar esta ventana.
pause