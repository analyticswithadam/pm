@echo off
cd %~dp0..
docker compose up -d --build
