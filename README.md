# Block Drop

PixelMug 上的 10×16 彩色方块掉落游戏，由横屏 WebApp 手柄通过 BLE 控制。

## 控制协议

WebApp 通过 BLE 实时通道发送：`LEFT`、`RIGHT`、`DOWN`、`ROTATE`、`DROP`、`PAUSE`、`RESTART`。声音按钮暂时禁用。

MPY 同时提供 `blockDropControl`、`blockDropGetState` 和 `getState` 命令用于调试。

## 运行

在 `bot/config.dev.js` 中配置 bot token、API 地址、MPS ID 和版本，然后运行：

    npm --prefix webapp install
    npm run build
    npm run bot
