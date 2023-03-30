@echo off
:: asynchronous version
cd %~dp0
call env\Scripts\activate
python asource.py
