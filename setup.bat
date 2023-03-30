@echo off
cd %~dp0
python -m venv env
call env\Scripts\activate
pip install -r requirements.txt
