import { BubbleBot, InlineKeyboard } from "@jeejio-bubble/bot/sdk";
import PixelMugS1 from "@jeejio-bubble/bot/devices/pixelmug-s1";

const mpsId = process.env.STUDIO_MPS_ID || "";
const mpsVersion = process.env.STUDIO_MPS_VERSION || "1.0.1";
const webAppUrl = launchUrl(requiredEnv("STUDIO_WEBAPP_URL"));

const messages = {
  "zh-CN": {
    bindContent: "绑定 PixelMug 后即可运行方块掉落。",
    bindButton: "绑定 PixelMug",
    addedIntro: "你好，我是方块掉落游戏智能体。你可以在 PixelMug 上玩彩色方块掉落游戏，并使用手机控制方块移动、旋转和快速下落。在使用之前，请先绑定你的 PixelMug。",
    openButton: "打开方块掉落",
    intro: "**方块掉落**\\n\\n在 PixelMug 上玩彩色方块掉落游戏，使用手机手柄移动、旋转和快速下落。\\n\\n点击下方按钮开始游戏。",
    commands: "命令：/bindDevice、/blockDrop",
    commandBind: "绑定 PixelMug",
    commandBlockDrop: "打开方块掉落",
  },
  "en-US": {
    bindContent: "Bind a PixelMug before running Block Drop.",
    bindButton: "Bind PixelMug",
    addedIntro: "Hello, I am the Block Drop game agent. I let you play a colorful retro block-dropping game on PixelMug and use your phone as a controller to move, rotate, and quickly drop blocks. Before you start, please bind your PixelMug.",
    openButton: "Open Block Drop",
    intro: "**Block Drop**\\n\\nPlay a colorful retro block-dropping game on PixelMug. Move, rotate, and drop blocks with the phone controller.\\n\\nTap the button below to start.",
    commands: "Commands: /bindDevice, /blockDrop",
    commandBind: "Bind PixelMug",
    commandBlockDrop: "Open Block Drop",
  },
};

const pixelMug = new PixelMugS1();
const bot = new BubbleBot(requiredEnv("BOT_TOKEN"), {
  apiBaseUrl: process.env.BOT_API_BASE_URL,
  webAppDeviceAccess: "any",
});

bot.registerDevices([pixelMug]);
bot.on("error", async (ctx) => console.error("[block-drop-bot]", ctx.error || ctx));
bot.on("contact_added", async (ctx) => sendAddedIntro(ctx));
bot.on("joined_group", async (ctx) => sendAddedIntro(ctx, { mentionOnly: false }));

bot.on("message", async (ctx) => {
  const locale = localeFromContext(ctx);
  const command = extractCommand(ctx.message?.content || ctx.message?.text || "");
  if (command === "/bindDevice") {
    await sendBindDevice(ctx, locale);
    return;
  }
  if (command === "/blockDrop" || command === "/webapp" || command === "/start") {
    const keyboard = new InlineKeyboard().url(text(locale, "openButton"), withLocale(webAppUrl, locale));
    await ctx.sendKeyboard(text(locale, "intro"), keyboard, {
      mentionOnly: ctx.chat?.type === "group" ? true : undefined,
    });
    return;
  }
  await ctx.sendText(text(locale, "commands"));
});

await bot.setCommands([
  {
    command: "bindDevice",
    description: messages["en-US"].commandBind,
    descTranslations: { "zh-CN": messages["zh-CN"].commandBind, en: messages["en-US"].commandBind },
  },
  {
    command: "blockDrop",
    description: messages["en-US"].commandBlockDrop,
    descTranslations: { "zh-CN": messages["zh-CN"].commandBlockDrop, en: messages["en-US"].commandBlockDrop },
  },
]);

await bot.start();
console.log("mps-block-drop bot is running.");
console.log(`WebApp URL: ${webAppUrl}`);

function requiredEnv(name) {
  const value = process.env[name];
  if (!value) throw new Error(`Missing required environment variable: ${name}`);
  return value;
}

function launchUrl(value) {
  const url = new URL(value);
  if (mpsId) url.searchParams.set("mps_id", mpsId);
  url.searchParams.set("mps_version", mpsVersion);
  return url.toString();
}

function withLocale(value, locale) {
  const url = new URL(value);
  url.searchParams.set("lang", locale);
  return url.toString();
}

function extractCommand(value) {
  const match = String(value || "").trim().match(/\/[a-zA-Z0-9_-]+(?:@[a-zA-Z0-9_-]+)?/);
  return match ? match[0].split("@")[0] : "";
}

function localeFromContext(ctx) {
  const source = ctx.chat?.language || ctx.from?.language || process.env.APP_LOCALE;
  return String(source || "").toLowerCase().startsWith("zh") ? "zh-CN" : "en-US";
}

function text(locale, key) {
  return messages[locale]?.[key] || messages["en-US"][key] || key;
}

function sendAddedIntro(ctx, options = {}) {
  const locale = localeFromContext(ctx);
  return ctx.sendBindDevice({ content: text(locale, "addedIntro"), actionButtonTitle: text(locale, "bindButton"), ...options });
}

function sendBindDevice(ctx, locale = localeFromContext(ctx)) {
  return ctx.sendBindDevice({ content: text(locale, "bindContent"), actionButtonTitle: text(locale, "bindButton") });
}
