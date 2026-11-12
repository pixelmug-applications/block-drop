# Block Drop

Block Drop is a PixelMug Studio application with a MicroPython game runtime and a Vue WebApp controller. The WebApp uses BLE to send movement, rotation, drop, pause, restart, and sound commands to the device.

## Project layout

```text
block-drop/
  bot/        Bot integration
  mpy/        MicroPython game and sound assets
  webapp/     Vue WebApp controller
```

## Development

Install both dependency sets from the project root:

```bash
npm install
npm --prefix webapp install
```

Build the WebApp:

```bash
npm run build
```

The Bot entry is `bot/index.js`. When opened in PixelMug Studio, Studio supplies `BOT_TOKEN`, `BOT_API_BASE_URL`, `STUDIO_WEBAPP_URL`, `STUDIO_MPS_ID`, and `STUDIO_MPS_VERSION`. Do not create a local `config.dev.js` or commit tokens.

After binding a PixelMug, open Block Drop from the Bot. Studio installs and runs the MPY application when the WebApp requests it.

The MPY manifest is `mpy/mps.json`. Device sound assets live under `mpy/assets/` and are uploaded with the MPY project using device-relative paths.
