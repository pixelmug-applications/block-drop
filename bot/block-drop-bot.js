import { createReadStream } from "node:fs";
import { stat } from "node:fs/promises";
import { createServer } from "node:http";
import { extname, join, normalize, relative } from "node:path";
import { fileURLToPath } from "node:url";
import { BubbleBot, InlineKeyboard } from "../../jeejio-bubble/sdk/BubbleSDK.js";
import PixelMugS1 from "../../jeejio-bubble/devices/ext/PixelMugS1_1.0.ext.js";
import { apiBaseUrl, token, mpsID, mpsVersion } from "./config.dev.js";

const port = Number(process.env.WEBAPP_PORT || 8810);
const host = process.env.WEBAPP_HOST || process.env.HOST || "127.0.0.1";
const baseUrl = process.env.WEBAPP_URL || `http://${host}:${port}/index.html`;
const webAppUrl = launchUrl(baseUrl);
const shouldServeStatic = !process.env.WEBAPP_URL;

const messages = {
  "zh-CN": {
    bindContent: "绑定 PixelMug 后即可运行方块掉落。",
    bindButton: "绑定 PixelMug",
    openButton: "打开方块掉落",
    intro: "**方块掉落**\n\n在 PixelMug 上玩复古彩色方块掉落游戏，使用手机手柄移动、旋转和掉落方块。\n\n点击下方按钮开始游戏。",
    commands: "命令：/bindDevice，/blockDrop",
    commandBind: "绑定 PixelMug",
    commandBlockDrop: "打开方块掉落",
  },
  "en-US": {
    bindContent: "Bind a PixelMug before running Block Drop.",
    bindButton: "Bind PixelMug",
    openButton: "Open Block Drop",
    intro: "**Block Drop**\n\nPlay colorful retro Block Drop on PixelMug. Move, rotate, and drop blocks with the phone controller.\n\nTap the button below to start.",
    commands: "Commands: /bindDevice, /blockDrop",
    commandBind: "Bind PixelMug",
    commandBlockDrop: "Open Block Drop",
  },
};

const pixelMug = new PixelMugS1();
const bot = new BubbleBot(token, {
  apiBaseUrl,
  debug: process.env.DEBUG !== "false",
  observeWebAppDeviceCalls: true,
  webAppDeviceAccess: "any",
});

bot.registerDevices([pixelMug]);
bot.on("error", async (ctx) => console.error("[block-drop-bot]", ctx.error || ctx));

bot.on("message", async (ctx) => {
  const language = localeFromContext(ctx);
  const command = extractCommand(ctx.message?.content || ctx.message?.text || "");
  if (command === "/bindDevice") {
    await ctx.sendBindDevice({
      content: text(language, "bindContent"),
      actionButtonTitle: text(language, "bindButton"),
    });
    return;
  }
  if (command === "/blockDrop" || command === "/webapp" || command === "/start") {
    const keyboard = new InlineKeyboard().url(text(language, "openButton"), withLocale(webAppUrl, language));
    await ctx.sendKeyboard(text(language, "intro"), keyboard, {
      mentionOnly: ctx.chat?.type === "group" ? true : undefined,
    });
    return;
  }
  await ctx.sendText(text(language, "commands"));
});

if (shouldServeStatic) await startStaticServer();

await bot.setCommands([
  {
    command: "bindDevice",
    description: messages["en-US"].commandBind,
    descTranslations: {
      "zh-CN": messages["zh-CN"].commandBind,
      en: messages["en-US"].commandBind,
    },
  },
  {
    command: "blockDrop",
    description: messages["en-US"].commandBlockDrop,
    descTranslations: {
      "zh-CN": messages["zh-CN"].commandBlockDrop,
      en: messages["en-US"].commandBlockDrop,
    },
  },
]);
await bot.start();
console.log("mps-block-drop bot is running.");
console.log(`WebApp URL: ${webAppUrl}`);

function extractCommand(value) {
  const match = String(value || "").trim().match(/\/[a-zA-Z0-9_-]+(?:@[a-zA-Z0-9_-]+)?/);
  return match ? match[0].split("@")[0] : "";
}

function localeFromContext(ctx) {
  const source = String(ctx.chat?.language || ctx.from?.language || process.env.APP_LOCALE || "").toLowerCase();
  return source.startsWith("zh") ? "zh-CN" : "en-US";
}

function text(language, key) {
  return messages[language]?.[key] || messages["en-US"][key] || key;
}

function launchUrl(value) {
  const url = new URL(value);
  url.searchParams.set("mps_id", mpsID);
  url.searchParams.set("mps_version", mpsVersion);
  return url.toString();
}

function withLocale(value, language) {
  const url = new URL(value);
  url.searchParams.set("lang", language);
  return url.toString();
}

function startStaticServer() {
  const root = fileURLToPath(new URL("../webapp/dist", import.meta.url));
  const server = createServer(async (req, res) => {
    try {
      const url = new URL(req.url || "/", `http://${req.headers.host || "localhost"}`);
      const path = normalize(join(root, decodeURIComponent(url.pathname === "/" ? "/index.html" : url.pathname)));
      if (relative(root, path).startsWith("..")) return reply(res, 403, "Forbidden");
      if (!(await stat(path)).isFile()) return reply(res, 404, "Not found");
      res.writeHead(200, { "content-type": contentType(path), "cache-control": "no-store" });
      createReadStream(path).pipe(res);
    } catch (error) {
      reply(res, 404, String(error?.code || "Not found").includes("ENOENT") ? "Build not found. Run npm run build first." : "Not found");
    }
  });
  return new Promise((resolve, reject) => {
    server.once("error", reject);
    server.listen(port, "0.0.0.0", () => { server.off("error", reject); resolve(server); });
  });
}

function reply(res, status, body) {
  res.writeHead(status, { "content-type": "text/plain; charset=utf-8" });
  res.end(body);
}

function contentType(path) {
  return ({ ".html": "text/html; charset=utf-8", ".js": "text/javascript; charset=utf-8", ".css": "text/css; charset=utf-8", ".png": "image/png", ".svg": "image/svg+xml" })[extname(path)] || "application/octet-stream";
}
