@echo off
echo EduBrain AI - PowerShell 执行策略设置工具
echo ============================================
echo.
echo 此工具将帮助您设置 PowerShell 执行策略以运行 build.ps1 脚本
echo.

:menu
echo 请选择操作:
echo 1. 设置执行策略为 RemoteSigned (推荐)
echo 2. 设置执行策略为 Unrestricted (不推荐)
echo 3. 查看当前执行策略
echo 4. 退出
echo.
set /p choice="请输入选择 (1-4): "

if "%choice%"=="1" goto set_remotesigned
if "%choice%"=="2" goto set_unrestricted
if "%choice%"=="3" goto check_policy
if "%choice%"=="4" goto exit

echo 无效选择，请重新输入
goto menu

:set_remotesigned
echo.
echo 设置执行策略为 RemoteSigned...
powershell -Command "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser"
if %errorlevel%==0 (
    echo.
    echo ✅ 执行策略设置成功！
    echo 现在您可以运行 .\build.ps1 脚本了
) else (
    echo.
    echo ❌ 执行策略设置失败！
    echo 请尝试以管理员身份运行此批处理文件
)
goto end

:set_unrestricted
echo.
echo 设置执行策略为 Unrestricted...
powershell -Command "Set-ExecutionPolicy -ExecutionPolicy Unrestricted -Scope CurrentUser"
if %errorlevel%==0 (
    echo.
    echo ✅ 执行策略设置成功！
    echo 现在您可以运行 .\build.ps1 脚本了
) else (
    echo.
    echo ❌ 执行策略设置失败！
    echo 请尝试以管理员身份运行此批处理文件
)
goto end

:check_policy
echo.
echo 查看当前执行策略...
powershell -Command "Get-ExecutionPolicy -List"
goto end

:exit
echo.
echo 再见！
goto end

:end
echo.
pause
