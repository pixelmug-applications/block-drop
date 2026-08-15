import random
import time

import audio_service
import micropyxel as pyxel
from maopaoBleApp import BleAppService
from pyxel_prompt_sound import PromptSoundPlayer


SCR_W = 32
SCR_H = 16
BOARD_W = 10
BOARD_H = 16
BOARD_X = (SCR_W - BOARD_W) // 2
LEFT_WALL_X = BOARD_X - 1
RIGHT_WALL_X = BOARD_X + BOARD_W
PREVIEW_X = RIGHT_WALL_X + 1
PREVIEW_CONTENT_X = PREVIEW_X + 1
PREVIEW_W = SCR_W - PREVIEW_X
FPS = 30
LINE_FLASH_INTERVAL_MS = 100
LINE_FLASH_PHASES = 4

SOUND_VOLUME = 100
SOUND_PACKETS_PER_UPDATE = 5
DROP_SOUND = "drop.opus"
MOVE_SOUND = "move.opus"
ROTATE_SOUND = "rotate.opus"

COL_BLACK = 0
COL_WHITE = 7
COL_RED = 8
COL_YELLOW = 10
COL_WALL_GRAY = 13

STATE_READY = "ready"
STATE_PLAYING = "playing"
STATE_PAUSED = "paused"
STATE_GAME_OVER = "gameover"

# I, J, L, O, S, T, Z: cyan, blue, orange, yellow, green, purple, red.
PIECE_COLORS = (12, 5, 9, 10, 11, 2, 8)

# Every rotation is described in a 4x4 local grid.  O intentionally keeps one state.
SHAPES = (
    (((0, 1), (1, 1), (2, 1), (3, 1)), ((2, 0), (2, 1), (2, 2), (2, 3))),
    (((0, 0), (0, 1), (1, 1), (2, 1)), ((1, 0), (2, 0), (1, 1), (1, 2)),
     ((0, 1), (1, 1), (2, 1), (2, 2)), ((1, 0), (1, 1), (0, 2), (1, 2))),
    (((2, 0), (0, 1), (1, 1), (2, 1)), ((1, 0), (1, 1), (1, 2), (2, 2)),
     ((0, 1), (1, 1), (2, 1), (0, 2)), ((0, 0), (1, 0), (1, 1), (1, 2))),
    (((1, 0), (2, 0), (1, 1), (2, 1)),),
    (((1, 0), (2, 0), (0, 1), (1, 1)), ((1, 0), (1, 1), (2, 1), (2, 2))),
    (((1, 0), (0, 1), (1, 1), (2, 1)), ((1, 0), (1, 1), (2, 1), (1, 2)),
     ((0, 1), (1, 1), (2, 1), (1, 2)), ((1, 0), (0, 1), (1, 1), (1, 2))),
    (((0, 0), (1, 0), (1, 1), (2, 1)), ((2, 0), (1, 1), (2, 1), (1, 2))),
)

START_BLOCK_MS = 1000

# Minimal 3x5 glyphs used for the cleared-line counter.
DIGIT_3X5 = (
    (0b111, 0b101, 0b101, 0b101, 0b111),
    (0b010, 0b110, 0b010, 0b010, 0b111),
    (0b111, 0b001, 0b111, 0b100, 0b111),
    (0b111, 0b001, 0b111, 0b001, 0b111),
    (0b101, 0b101, 0b111, 0b001, 0b001),
    (0b111, 0b100, 0b111, 0b001, 0b111),
    (0b111, 0b100, 0b111, 0b101, 0b111),
    (0b111, 0b001, 0b010, 0b010, 0b010),
    (0b111, 0b101, 0b111, 0b101, 0b111),
    (0b111, 0b101, 0b111, 0b001, 0b111),
)


def ticks_ms():
    return time.ticks_ms()


def ticks_diff(a, b):
    return time.ticks_diff(a, b)


class BlockDropApp:
    def __init__(self):
        self.ble = BleAppService("BlockDrop", app_version="1.0.0", max_message=384)
        self.sound_enabled = True
        self._register_ble_protocol()
        self.audio = audio_service.audio
        self.audio_initialized = False
        self.sound = PromptSoundPlayer(
            audio=self.audio,
            asset_root="assets",
            debug=False,
            log_prefix="[BlockDropSound]",
            packets_per_update=SOUND_PACKETS_PER_UPDATE,
            stop_handler=self.stop_sound,
        )
        pyxel.init(start_audio=False)
        self.prepare_sound()
        self.reset_game(start=False)

    def start(self):
        self.ble.start()
        pyxel.run(self.update, self.draw, fps=FPS, on_exit=self.on_exit)

    def on_exit(self, rt, reason, exc):
        try:
            self.sound.deinit()
        except Exception:
            pass
        if self.audio_initialized:
            try:
                self.audio.deinit()
            except Exception:
                pass
            self.audio_initialized = False
        try:
            pyxel.destroy()
        except Exception:
            pass
        self.ble.deinit()

    def _register_ble_protocol(self):
        for command in ("START", "LEFT", "RIGHT", "DOWN", "ROTATE", "DROP", "PAUSE", "RESTART"):
            self.ble.realtime(command, self._realtime_handler(command))
            self.ble.command(command, self._command_handler(command), priority=0, mutates=False)
        self.ble.command("SOUND", self._command_handler("SOUND"), priority=0, mutates=False)
        self.ble.realtime("control", self._handle_realtime_control)
        self.ble.command("blockDropControl", self._cmd_control, priority=0, mutates=False)
        self.ble.command("blockDropGetState", self._cmd_get_state, priority=1, mutates=False)
        self.ble.command("getState", self._cmd_get_state, priority=1, mutates=False)
        self.ble.set_state_provider(self.state_payload)

    def _realtime_handler(self, command):
        def handler(data, message=None):
            self.control(command)
        return handler

    def _command_handler(self, command):
        def handler(params, message=None):
            self.control(command)
            return self.state_payload()
        return handler

    def _handle_realtime_control(self, data, message=None):
        self.control(data.get("command", "") if isinstance(data, dict) else data)

    def _cmd_control(self, params, message=None):
        self.control(params.get("command", "") if isinstance(params, dict) else params)
        return self.state_payload()

    def _cmd_get_state(self, params, message=None):
        return self.state_payload()

    def reset_game(self, start=True):
        self.board = [[0 for _ in range(BOARD_W)] for _ in range(BOARD_H)]
        self.lines = 0
        self.state = STATE_PLAYING if start else STATE_READY
        self.piece = None
        self.clearing_rows = []
        self.line_flash_started_ms = 0
        self.next_kind = random.randrange(len(SHAPES))
        self.last_drop_ms = ticks_ms()
        self.start_page_started_ms = self.last_drop_ms
        if start:
            self.spawn_piece()
        self.publish_state("blockDropRestarted" if start else "blockDropReady")

    def start_game(self):
        if self.state != STATE_READY:
            return
        self.state = STATE_PLAYING
        self.last_drop_ms = ticks_ms()
        self.spawn_piece()
        self.publish_state("blockDropStarted")

    def spawn_piece(self):
        kind = self.next_kind
        self.next_kind = random.randrange(len(SHAPES))
        self.piece = {"kind": kind, "rotation": 0, "x": 3, "y": -1}
        if self.collides(self.piece["x"], self.piece["y"], 0):
            self.state = STATE_GAME_OVER
            self.piece = None
            self.publish_state("blockDropGameOver")

    def cells(self, rotation=None):
        rotations = SHAPES[self.piece["kind"]]
        return rotations[(self.piece["rotation"] if rotation is None else rotation) % len(rotations)]

    def collides(self, x, y, rotation=None):
        for dx, dy in self.cells(rotation):
            bx = x + dx
            by = y + dy
            if bx < 0 or bx >= BOARD_W or by >= BOARD_H:
                return True
            if by >= 0 and self.board[by][bx]:
                return True
        return False

    def move(self, dx, dy):
        if self.piece is None or self.collides(self.piece["x"] + dx, self.piece["y"] + dy):
            return False
        self.piece["x"] += dx
        self.piece["y"] += dy
        return True

    def rotate(self):
        if self.piece is None:
            return
        rotations = SHAPES[self.piece["kind"]]
        target = (self.piece["rotation"] + 1) % len(rotations)
        for kick in (0, -1, 1, -2, 2):
            if not self.collides(self.piece["x"] + kick, self.piece["y"], target):
                self.piece["x"] += kick
                self.piece["rotation"] = target
                return

    def lock_piece(self):
        color = PIECE_COLORS[self.piece["kind"]]
        above_top = False
        for dx, dy in self.cells():
            x = self.piece["x"] + dx
            y = self.piece["y"] + dy
            if y < 0:
                above_top = True
            else:
                self.board[y][x] = color
        if above_top:
            self.state = STATE_GAME_OVER
            self.piece = None
            self.publish_state("blockDropGameOver")
            return
        self.clearing_rows = [y for y in range(BOARD_H) if all(self.board[y])]
        if self.clearing_rows:
            self.piece = None
            self.line_flash_started_ms = ticks_ms()
            return
        self.spawn_piece()

    def finish_line_clear(self):
        cleared = len(self.clearing_rows)
        if not cleared:
            return
        kept = [row for y, row in enumerate(self.board) if y not in self.clearing_rows]
        self.board = [[0 for _ in range(BOARD_W)] for _ in range(cleared)] + kept
        self.clearing_rows = []
        self.lines += cleared
        self.last_drop_ms = ticks_ms()
        self.publish_state("blockDropLineClear")
        self.spawn_piece()

    def hard_drop(self):
        while self.move(0, 1):
            pass
        self.lock_piece()

    def control(self, value):
        command = str(value or "").strip().upper()
        if command == "SOUND":
            self.sound_enabled = not self.sound_enabled
            if not self.sound_enabled:
                self.stop_sound()
            self.publish_state("blockDropSoundChanged")
            return
        if command == "START":
            self.start_game()
            return
        if command == "RESTART":
            self.reset_game()
            return
        if command == "PAUSE" and self.state != STATE_GAME_OVER:
            self.state = STATE_PLAYING if self.state == STATE_PAUSED else STATE_PAUSED
            self.last_drop_ms = ticks_ms()
            if self.state == STATE_PLAYING and self.clearing_rows:
                self.line_flash_started_ms = self.last_drop_ms
            self.publish_state("blockDropResumed" if self.state == STATE_PLAYING else "blockDropPaused")
            return
        if self.state != STATE_PLAYING:
            return
        if self.clearing_rows:
            return
        if command == "LEFT":
            self.play_sound(MOVE_SOUND, interrupt=True)
            self.move(-1, 0)
        elif command == "RIGHT":
            self.play_sound(MOVE_SOUND, interrupt=True)
            self.move(1, 0)
        elif command == "DOWN":
            self.play_sound(MOVE_SOUND, interrupt=True)
            if not self.move(0, 1):
                self.lock_piece()
            self.last_drop_ms = ticks_ms()
        elif command == "ROTATE":
            self.play_sound(ROTATE_SOUND, interrupt=True)
            self.rotate()
        elif command == "DROP":
            self.play_sound(DROP_SOUND, interrupt=True)
            self.hard_drop()
            self.last_drop_ms = ticks_ms()

    def drop_interval(self):
        return max(120, 650 - (self.lines // 5) * 55)

    def update(self, rt):
        self.ble.poll(budget_ms=1, max_messages=3)
        self.sound.update(budget_packets=SOUND_PACKETS_PER_UPDATE)
        if self.state == STATE_PLAYING:
            now = ticks_ms()
            if self.clearing_rows:
                flash_duration = LINE_FLASH_INTERVAL_MS * LINE_FLASH_PHASES
                if ticks_diff(now, self.line_flash_started_ms) >= flash_duration:
                    self.finish_line_clear()
            elif ticks_diff(now, self.last_drop_ms) >= self.drop_interval():
                if not self.move(0, 1):
                    self.lock_piece()
                self.last_drop_ms = now
        self.ble.poll(budget_ms=1, max_messages=3)

    def draw(self, rt):
        pyxel.cls(COL_BLACK)
        if self.state == STATE_READY:
            self.draw_start_page()
            return
        if self.state == STATE_GAME_OVER:
            self.draw_centered_text(2, "OVER", COL_RED)
            self.draw_centered_text(9, str(min(999, self.lines)), COL_WHITE)
            return
        self.draw_walls()
        for y in range(BOARD_H):
            for x in range(BOARD_W):
                color = self.board[y][x]
                if color:
                    pyxel.pset(BOARD_X + x, y, color)
        if self.clearing_rows:
            phase = max(0, ticks_diff(ticks_ms(), self.line_flash_started_ms)) // LINE_FLASH_INTERVAL_MS
            flash_color = COL_WHITE if phase % 2 == 0 else COL_WALL_GRAY
            for y in self.clearing_rows:
                for x in range(BOARD_W):
                    pyxel.pset(BOARD_X + x, y, flash_color)
        if self.piece is not None:
            color = PIECE_COLORS[self.piece["kind"]]
            for dx, dy in self.cells():
                x = self.piece["x"] + dx
                y = self.piece["y"] + dy
                if y >= 0:
                    pyxel.pset(BOARD_X + x, y, color)
        self.draw_next_piece()
        self.draw_line_count()
        if self.state == STATE_PAUSED:
            self.draw_pause_overlay()

    def draw_start_page(self):
        self.draw_centered_text(0, "BLOCK", COL_YELLOW)
        self.draw_centered_text(6, "DROP", COL_YELLOW)
        phase = max(0, ticks_diff(ticks_ms(), self.start_page_started_ms)) // START_BLOCK_MS
        kind = phase % len(SHAPES)
        cells = SHAPES[kind][0]
        min_x, max_x, min_y, max_y = self.cell_bounds(cells)
        width = max_x - min_x + 1
        height = max_y - min_y + 1
        origin_x = (SCR_W - width) // 2 - min_x
        origin_y = 12 + (4 - height) // 2 - min_y
        self.draw_shape(cells, origin_x, origin_y, PIECE_COLORS[kind])

    def draw_walls(self):
        for y in range(BOARD_H):
            color = COL_WHITE if y % 2 == 0 else COL_WALL_GRAY
            pyxel.pset(LEFT_WALL_X, y, color)
            pyxel.pset(RIGHT_WALL_X, y, color)

    def draw_next_piece(self):
        # Preview the exact spawn orientation.  Choosing a narrower rotated
        # variant here makes the preview look like a different upcoming block.
        cells = SHAPES[self.next_kind][0]
        min_x, max_x, min_y, max_y = self.cell_bounds(cells)
        width = max_x - min_x + 1
        origin_x = PREVIEW_X + (PREVIEW_W - width) // 2 - min_x
        origin_y = -min_y
        self.draw_shape(cells, origin_x, origin_y, PIECE_COLORS[self.next_kind])

    def cell_bounds(self, cells):
        min_x = min(cell[0] for cell in cells)
        max_x = max(cell[0] for cell in cells)
        min_y = min(cell[1] for cell in cells)
        max_y = max(cell[1] for cell in cells)
        return min_x, max_x, min_y, max_y

    def draw_shape(self, cells, origin_x, origin_y, color):
        for dx, dy in cells:
            pyxel.pset(origin_x + dx, origin_y + dy, color)

    def draw_line_count(self):
        value = str(min(999, max(0, self.lines)))
        x = PREVIEW_CONTENT_X
        y = SCR_H - 5
        for digit in value:
            self.draw_digit_3x5(x, y, int(digit), COL_YELLOW)
            x += 3

    def draw_pause_overlay(self):
        pyxel.rect(0, 0, SCR_W, SCR_H, COL_BLACK)
        self.draw_centered_text(5, "Pause", COL_YELLOW)

    def draw_digit_3x5(self, x, y, digit, color):
        rows = DIGIT_3X5[digit]
        for dy in range(5):
            bits = rows[dy]
            for dx in range(3):
                if bits & (1 << (2 - dx)):
                    pyxel.pset(x + dx, y + dy, color)

    def draw_centered_text(self, y, value, color):
        text = str(value)
        pyxel.text(max(0, (SCR_W - len(text) * 4) // 2), y, text, color)

    def prepare_sound(self):
        if not self.ensure_audio():
            return False
        ok = True
        for path in (DROP_SOUND, MOVE_SOUND, ROTATE_SOUND):
            if not self.sound.preload(path):
                print("[BlockDrop] preload sound failed:", path, self.sound.last_error)
                ok = False
        return ok

    def play_sound(self, path, interrupt=True):
        if not self.sound_enabled:
            return False
        if not self.ensure_audio():
            return False
        ok = self.sound.play(path, interrupt=interrupt)
        if not ok:
            print("[BlockDrop] sound failed:", path, self.sound.last_error)
        return ok

    def stop_sound(self, player=None):
        if player is None:
            player = self.sound
        return player.cancel()

    def ensure_audio(self):
        if self.audio_initialized:
            return True
        try:
            self.audio.init(
                enable_input=False,
                enable_output=True,
                with_opus_encoder=False,
                with_opus_decoder=True,
            )
            self.audio.configure(output_volume=SOUND_VOLUME, input_gain=1.0)
            self.audio_initialized = True
            return True
        except Exception as exc:
            print("[BlockDrop] audio init failed:", exc)
            return False

    def state_payload(self):
        return {
            "state": self.state,
            "lines": self.lines,
            "level": self.lines // 5 + 1,
            "nextKind": self.next_kind,
            "soundEnabled": self.sound_enabled,
        }

    def publish_state(self, event):
        if not self.ble.connected:
            return False
        return self.ble.send_event(event, self.state_payload(), priority=1)


def appMain():
    BlockDropApp().start()


if __name__ == "__main__":
    appMain()
