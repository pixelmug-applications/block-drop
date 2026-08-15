import { computed, reactive } from 'vue';

export type AppLocale = 'zh-CN' | 'en-US';

const messages = {
  'zh-CN': {
    'landing.subtitle': '在 PixelMug 上玩复古彩色方块掉落',
    'landing.opening': '正在打开...',
    'landing.enter': '进入游戏手柄',
    'landing.retry': '重试安装',
    'landing.install': '安装并打开',
    'status.findingDevice': '正在查找 PixelMug...',
    'status.deviceMissing': '还没有绑定 PixelMug。',
    'status.launching': '正在启动方块掉落...',
    'status.preparing': '正在准备应用...',
    'status.switching': '正在切换应用...',
    'status.launchReady': '方块掉落已启动。',
    'status.connectingBle': '应用已启动，正在连接 BLE...',
    'status.bleConnected': '安装成功，BLE 已连接。',
    'status.mockConnected': '安装成功，浏览器模拟连接已就绪。',
    'status.bleConnectFailed': 'MPS 已启动，但 BLE 连接失败：{error}',
    'status.missingConfig': '缺少 MPS ID 或版本。',
    'status.openFailed': '无法打开应用（返回码 {code}）。',
    'status.launchTimeout': '无法确认应用已经启动。',
    'status.installFailed': '安装失败，错误码：{code}',
    'status.mpsInstallFailed': 'MPS 安装失败，错误码：{code}',
    'status.runningFailed': '安装成功，但应用内部启动失败。',
    'status.unknownError': '未知错误',
    'game.start': '开始',
    'game.resume': '继续',
    'game.pause': '暂停',
    'game.soundOn': '声音开',
    'game.soundOff': '声音关',
    'game.soundEnable': '开启声音',
    'game.soundDisable': '关闭声音',
    'game.restart': '重玩',
    'game.drop': '掉落',
    'game.rotate': '旋转',
    'game.left': '左移',
    'game.right': '右移',
    'game.down': '下移',
    'ble.connected': '蓝牙（已连接）',
    'ble.connecting': '蓝牙（连接中，{seconds}s...）',
    'ble.timeout': '蓝牙（连接超时）',
    'ble.disconnected': '蓝牙（未连接）',
  },
  'en-US': {
    'landing.subtitle': 'Play colorful retro Block Drop on PixelMug',
    'landing.opening': 'Opening...',
    'landing.enter': 'Enter controller',
    'landing.retry': 'Retry installation',
    'landing.install': 'Install and open',
    'status.findingDevice': 'Finding PixelMug...',
    'status.deviceMissing': 'No PixelMug is bound yet.',
    'status.launching': 'Launching Block Drop...',
    'status.preparing': 'Preparing app...',
    'status.switching': 'Switching app...',
    'status.launchReady': 'Block Drop is ready.',
    'status.connectingBle': 'App started. Connecting BLE...',
    'status.bleConnected': 'Installed. BLE connected.',
    'status.mockConnected': 'Installed. Browser mock connection is ready.',
    'status.bleConnectFailed': 'MPS started, but BLE connection failed: {error}',
    'status.missingConfig': 'MPS ID or version is missing.',
    'status.openFailed': 'Could not open app (code {code}).',
    'status.launchTimeout': 'Could not confirm the app opened.',
    'status.installFailed': 'Installation failed. Error code: {code}',
    'status.mpsInstallFailed': 'MPS installation failed. Error code: {code}',
    'status.runningFailed': 'Installation succeeded, but the app failed to start.',
    'status.unknownError': 'Unknown error',
    'game.start': 'Start',
    'game.resume': 'Resume',
    'game.pause': 'Pause',
    'game.soundOn': 'Sound on',
    'game.soundOff': 'Sound off',
    'game.soundEnable': 'Enable sound',
    'game.soundDisable': 'Disable sound',
    'game.restart': 'Restart',
    'game.drop': 'Drop',
    'game.rotate': 'Rotate',
    'game.left': 'Left',
    'game.right': 'Right',
    'game.down': 'Down',
    'ble.connected': 'Bluetooth (connected)',
    'ble.connecting': 'Bluetooth (connecting, {seconds}s...)',
    'ble.timeout': 'Bluetooth (connection timed out)',
    'ble.disconnected': 'Bluetooth (disconnected)',
  },
} as const;

export type MessageKey = keyof typeof messages['en-US'];

const state = reactive({ locale: detectLocale() });

export const currentLocale = computed(() => state.locale);

export function setLocale(locale: string | null | undefined) {
  state.locale = normalizeLocale(locale);
}

export function t(key: MessageKey, params: Record<string, string | number> = {}) {
  let text: string = messages[state.locale][key] || messages['en-US'][key] || key;
  for (const [name, value] of Object.entries(params)) {
    text = text.split(`{${name}}`).join(String(value));
  }
  return text;
}

function detectLocale(): AppLocale {
  const queryLocale = new URLSearchParams(globalThis.location?.search || '').get('lang');
  const bridgeLocale = (globalThis as { JeeWeb?: { Language?: string } }).JeeWeb?.Language;
  return normalizeLocale(queryLocale || bridgeLocale || globalThis.navigator?.language);
}

function normalizeLocale(value: string | null | undefined): AppLocale {
  return String(value || '').toLowerCase().startsWith('zh') ? 'zh-CN' : 'en-US';
}
