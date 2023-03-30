@echo off
:: synchronous version
cd %~dp0
call env\Scripts\activate
python source.py
