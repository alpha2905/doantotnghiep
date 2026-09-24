@echo off
REM Test nhanh API phần không cần AI (health, search, fallback, collect-request)
cd /d %~dp0..
cd backend
start /b "" ..\venv\Scripts\python.exe -m uvicorn main:app --host 127.0.0.1 --port 8000 > ..\logs\a2_test.log 2>&1
ping -n 16 127.0.0.1 > nul

set OUT=..\logs\a2_api_test.txt
echo === HEALTH === > %OUT%
curl -s -m 8 http://127.0.0.1:8000/health >> %OUT%
echo. >> %OUT%
echo === SEARCH_PHANTOM (fallback) === >> %OUT%
curl -s -m 15 "http://127.0.0.1:8000/api/search?name=dsadsadxyz" >> %OUT%
echo. >> %OUT%
echo === SEARCH_FALLBACK_RAG === >> %OUT%
curl -s -m 15 "http://127.0.0.1:8000/api/search/fallback?name=iphone%2015&limit=3" >> %OUT%
echo. >> %OUT%
echo === SUGGEST === >> %OUT%
curl -s -m 10 "http://127.0.0.1:8000/api/suggest?name=iphone%2015&limit=3" >> %OUT%
echo. >> %OUT%
echo === COLLECT_REQUEST === >> %OUT%
curl -s -m 10 -X POST -H "Content-Type: application/json" -d "{\"name\":\"iPhone 99 Test\"}" http://127.0.0.1:8000/api/collect-request >> %OUT%
echo. >> %OUT%
echo === COMPARE_FAST === >> %OUT%
curl -s -m 20 "http://127.0.0.1:8000/api/compare?name=iphone%2015&fast=true" >> %OUT%
echo. >> %OUT%
echo DONE >> %OUT%

for /f "tokens=5" %%p in ('netstat -ano ^| findstr :8000 ^| findstr LISTENING') do taskkill /pid %%p /f > nul 2>&1
