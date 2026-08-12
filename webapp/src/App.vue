<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue';
import { useTetrisDevice, type TetrisCommand } from './device';
import { t } from './i18n';

const game = useTetrisDevice();
const entered = ref(false);
const prepared = ref(false);
const busy = ref(false);
const error = ref('');
const pressed = ref<TetrisCommand | ''>('');
let repeatTimer: number | undefined;
let bleCountdownTimer: number | undefined;
const bleSeconds = ref(20);

const bleLabel = computed(() => {
  if (game.ready.value) return t('ble.connected');
  if (game.connecting.value) return t('ble.connecting', { seconds: bleSeconds.value });
  if (game.state.connection === 'failed') return t('ble.timeout');
  return t('ble.disconnected');
});

const canReconnect = computed(() => !game.ready.value && !game.connecting.value);

async function openGame() {
  if (prepared.value) {
    entered.value = true;
    return;
  }
  busy.value = true;
  error.value = '';
  try {
    await game.openOnDevice();
    prepared.value = true;
    void game.connectDevice();
  } catch (reason) {
    error.value = reason instanceof Error ? reason.message : String(reason);
  } finally {
    busy.value = false;
  }
}

function tap(command: TetrisCommand) {
  pressed.value = command;
  void game.send(command);
  window.setTimeout(() => { if (pressed.value === command) pressed.value = ''; }, 100);
}

function startOrPause() {
  tap(game.state.gameState === 'ready' ? 'START' : 'PAUSE');
}

function hold(command: 'LEFT' | 'RIGHT' | 'DOWN', event: PointerEvent) {
  (event.currentTarget as HTMLElement).setPointerCapture(event.pointerId);
  stopHold();
  pressed.value = command;
  void game.send(command);
  repeatTimer = window.setInterval(() => void game.send(command), command === 'DOWN' ? 75 : 105);
}

function stopHold() {
  window.clearInterval(repeatTimer);
  repeatTimer = undefined;
  pressed.value = '';
}

watch(
  () => game.connecting.value,
  (connecting) => {
    window.clearInterval(bleCountdownTimer);
    bleSeconds.value = 20;
    if (!connecting) return;
    bleCountdownTimer = window.setInterval(() => {
      bleSeconds.value = Math.max(0, bleSeconds.value - 1);
    }, 1000);
  },
  { immediate: true },
);

onBeforeUnmount(() => {
  stopHold();
  window.clearInterval(bleCountdownTimer);
});
</script>

<template>
  <main v-if="!entered" class="landing" :class="{ ready: prepared }">
    <section class="landing-content">
      <div class="tetromino" aria-hidden="true"><i /><i /><i /><i /></div>
      <h1>TETRIS</h1>
      <p>{{ t('landing.subtitle') }}</p>
    </section>
    <section class="landing-actions">
      <button :disabled="busy" @click="openGame">
        {{ busy ? t('landing.opening') : prepared ? t('landing.enter') : error ? t('landing.retry') : t('landing.install') }}
      </button>
      <p
        v-if="busy || prepared || error || game.state.message"
        class="install-status"
        :class="{
          error: Boolean(error) && !prepared,
          success: prepared,
        }"
      >
        {{ prepared ? t('status.launchReady') : error || game.state.message }}
      </p>
    </section>
  </main>

  <main v-else class="controller" :class="{ offline: !game.ready.value }">
    <section class="utility-row">
      <button
        class="small green"
        :class="{ pressed: pressed === 'PAUSE' || pressed === 'START' }"
        :disabled="!game.ready.value"
        @click="startOrPause"
      >
        <i />{{ game.state.gameState === 'ready' ? t('game.start') : game.state.gameState === 'paused' ? t('game.resume') : t('game.pause') }}
      </button>
      <button
        class="small green"
        :class="{ pressed: pressed === 'SOUND', muted: !game.state.soundEnabled }"
        :title="game.state.soundEnabled ? t('game.soundDisable') : t('game.soundEnable')"
        :disabled="!game.ready.value"
        @click="tap('SOUND')"
      ><i />{{ game.state.soundEnabled ? t('game.soundOn') : t('game.soundOff') }}</button>
      <button class="small red" :class="{ pressed: pressed === 'RESTART' }" :disabled="!game.ready.value" @click="tap('RESTART')"><i />{{ t('game.restart') }}</button>
      <button
        class="small blue ble-control"
        :class="{ connecting: game.connecting.value }"
        :disabled="!canReconnect"
        @click="game.reconnect"
      ><i />{{ bleLabel }}</button>
    </section>

    <button class="drop blue" :class="{ pressed: pressed === 'DROP' }" :disabled="!game.ready.value" @pointerdown.prevent="tap('DROP')">
      <i />{{ t('game.drop') }}
    </button>

    <section class="dpad">
      <button class="round blue up" :class="{ pressed: pressed === 'ROTATE' }" :disabled="!game.ready.value" @pointerdown.prevent="tap('ROTATE')"><i />{{ t('game.rotate') }}</button>
      <button class="round blue left" :class="{ pressed: pressed === 'LEFT' }" :disabled="!game.ready.value" @pointerdown.prevent="hold('LEFT', $event)" @pointerup.prevent="stopHold" @pointercancel.prevent="stopHold"><i />{{ t('game.left') }}</button>
      <button class="round blue right" :class="{ pressed: pressed === 'RIGHT' }" :disabled="!game.ready.value" @pointerdown.prevent="hold('RIGHT', $event)" @pointerup.prevent="stopHold" @pointercancel.prevent="stopHold"><i />{{ t('game.right') }}</button>
      <button class="round blue down" :class="{ pressed: pressed === 'DOWN' }" :disabled="!game.ready.value" @pointerdown.prevent="hold('DOWN', $event)" @pointerup.prevent="stopHold" @pointercancel.prevent="stopHold"><i />{{ t('game.down') }}</button>
    </section>
  </main>
</template>
