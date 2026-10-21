# VPN OnOff

**自动根据 WiFi 连接状态切换 VPN 的 Android 应用。**

- **WiFi 断开 → 自动开启 VPN**
- **WiFi 连接 → 自动关闭 VPN**

支持亮屏、后台、锁屏等场景下的自动切换；sing-box 的锁屏启动限制见下文。

## 前置条件

**1. 安装并配置好以下任一 VPN 客户端**（至少一个，APP 内可切换）：

| 客户端 | 项目地址 |
|--------|----------|
| Clash Meta for Android (CMFA) | https://github.com/MetaCubeX/ClashMetaForAndroid |
| Bettbox | https://github.com/appshubcc/Bettbox |
| FlClash | https://github.com/chen08209/FlClash |
| Surfboard | https://github.com/getsurfboard/surfboard |
| ClashMi | https://github.com/KaringX/clashmi |
| sing-box for Android (SFA) | https://github.com/SagerNet/sing-box |

> 所选客户端必须已完成订阅配置，确保手动启动 VPN 可正常使用。
> ClashMi 无感切换需要 v1.0.25.1106 或更高版本。
> sing-box 支持官方 SFA（包名 `io.nekohasekai.sfa`），需先在 SFA 中选好配置、使用 VPN 模式并手动成功连接一次，完成系统 VPN 授权。

**2. 安装并启动 [Shizuku](https://github.com/RikkaApps/Shizuku)** — 用于在锁屏等受限场景下控制 VPN 切换。

> **缺少 Shizuku 或上述任一客户端，VPN OnOff 将无法正常工作。**

## 权限设置

安装后打开 APP，界面会显示各项权限状态。请确保以下权限均已授予：

| 权限 | 说明 | 授予方式 |
|------|------|----------|
| **Shizuku 授权** | 核心功能，用于后台/锁屏控制 VPN | 点击 APP 内状态文字，弹窗授权 |
| **后台弹出界面** | MIUI/HyperOS 设备专属 | 点击 APP 内状态文字跳转设置 |
| **通知权限** | 前台服务通知 | 首次启动时弹窗授权 |

## 使用方法

1. 确保所选 VPN 客户端已配置好并能正常使用
2. 确保 Shizuku 已启动且正在运行
3. 打开 VPN OnOff，从下拉框中选择要使用的 VPN 客户端
4. 确认所有权限状态为绿色
5. 点击「开始监听」
6. 完成！APP 会在后台自动根据 WiFi 状态切换 VPN

## sing-box 使用说明

- 在客户端下拉框中选择「sing-box (SFA)」，再开始监听。
- SFA 未提供可供外部应用调用的启动接口。本应用通过 Shizuku 调用系统的 sing-box 快捷开关，首次启动会自动把该开关加入快捷设置。**启动时会短暂展开并收起快捷设置面板**，使系统绑定该开关；断开时沿用 `force-stop`，不会删除配置。
- Android 12 及以上按当前手机用户的系统 VPN 状态检查 SFA 是否已连接，避免将空闲前台服务误判为 VPN 已开启；旧版 Android 使用前台服务检测。启动后等待连接，失败时通知会提示检查配置、VPN 授权和快捷开关。
- **安全锁屏时不能无感启动 SFA**：官方快捷开关要求解锁。本应用会显示「等待解锁」，解锁后若 WiFi 仍未连接则重试。锁屏时关闭 VPN 不受影响。
- 支持官方 SFA，不包含其他基于 sing-box 内核的第三方客户端。

## 构建与 ADB 验证

本地构建需要 JDK 17 和 Android SDK 34，先配置好 `JAVA_HOME`、`ANDROID_HOME`（若同时设置 `ANDROID_SDK_ROOT`，需与 `ANDROID_HOME` 一致）。

```sh
./gradlew :app:assembleDebug
adb -s <设备序列号> install -r app/build/outputs/apk/debug/app-debug.apk
adb -s <设备序列号> shell am start -n com.vpnonoff/.MainActivity
```

在设备中配置 SFA、授权 Shizuku，选择 sing-box 并开始监听后，可以运行真实设备集成检查：

```sh
python3 scripts/verify-sing-box.py --serial <设备序列号>
```

该主机检查脚本仅用于 USB 或模拟器连接，会临时切换 WiFi 两轮、重启 VPN OnOff，验证 SFA 的前台服务和系统 VPN 状态；结束时恢复原 WiFi 开关。设备需保持解锁，并能连接已保存的 WiFi。检查只使用现有 SFA 配置，不创建测试订阅。无线 ADB 会随 WiFi 断开，必须使用在手机端独立运行并自带 WiFi 恢复保护的检查，不能直接运行此主机脚本。

若调试包采用独立包名并行安装，可加 `--package com.vpnonoff.debug`，避免与手机上使用正式签名的版本冲突。

定位控制问题可使用：

```sh
adb -s <设备序列号> logcat -s VPNOnOff
adb -s <设备序列号> shell dumpsys activity services io.nekohasekai.sfa/.bg.VPNService
adb -s <设备序列号> shell dumpsys vpn_management
```

## 注意事项

- 首次通过本 APP 启动 VPN 时，系统会弹出 VPN 连接确认对话框，点击允许即可，后续不会再弹出
- 切换 VPN 客户端后服务会自动重启以应用新选择
- 服务开启后支持开机自启，无需每次手动启动
- 建议在系统设置中将本 APP 加入电池优化白名单，避免被系统杀后台
