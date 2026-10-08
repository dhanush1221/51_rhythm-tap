import pygame
import random
import io
import math
import struct
import wave
from game.beat import Note, LANES, LANE_KEYS, LANE_LABELS, LANE_COLORS

WIDTH, HEIGHT = 480, 640
FPS = 60
HIT_Y = HEIGHT - 80
HIT_WINDOW = 30
BG = (15, 10, 25)
LANE_W = WIDTH // LANES

# Task 3: BPM-based note spawning
BPM = 120
BEAT_INTERVAL = 60.0 / BPM


class GameEngine:
    def __init__(self):
        pygame.init()
        pygame.mixer.init()
        self.hit_sound = self._create_hit_sound()
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        pygame.display.set_caption("Rhythm Tap")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("monospace", 26, bold=True)
        self.big_font = pygame.font.SysFont("monospace", 44, bold=True)
        self.reset()

    def _create_hit_sound(self):
        # Generate a short local beep in memory so no external sound asset is required.
        sample_rate = 44100
        duration = 0.08
        frequency = 880
        samples = int(sample_rate * duration)
        audio = bytearray()

        for i in range(samples):
            envelope = 1.0 - (i / samples)
            sample = int(
                32767
                * 0.25
                * envelope
                * math.sin(2 * math.pi * frequency * i / sample_rate)
            )
            audio.extend(struct.pack("<h", sample))

        wav_data = io.BytesIO()

        with wave.open(wav_data, "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(sample_rate)
            wav_file.writeframes(audio)

        wav_data.seek(0)
        return pygame.mixer.Sound(file=wav_data)

    def reset(self):
        self.notes = []
        self.score = 0
        self.combo = 0
        self.max_combo = 0
        self.misses = 0

        # Task 3: schedule the next note using real elapsed time.
        self.next_beat_time = pygame.time.get_ticks() + int(BEAT_INTERVAL * 1000)

        self.speed = 5
        self.frame = 0
        self.feedback = []  # (text, color, ttl, x, y)

        # Task 2: lanes currently being held by the player.
        self.held_lanes = set()

        self.game_over = False

    def spawn_note(self):
        lane = random.randint(0, LANES - 1)

        # Task 2: approximately 20% of notes are hold notes.
        is_hold = random.random() < 0.20

        self.notes.append(
            Note(
                lane,
                y=-30,
                speed=self.speed,
                is_hold=is_hold
            )
        )

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    self.reset()

                elif not self.game_over:
                    for i, key in enumerate(LANE_KEYS):
                        if event.key == key:
                            # Task 2: remember that this lane is being held.
                            self.held_lanes.add(i)
                            self.process_tap(i)

            elif event.type == pygame.KEYUP:
                for i, key in enumerate(LANE_KEYS):
                    if event.key == key:
                        self.held_lanes.discard(i)
                        self.release_hold(i)

        return True

    def process_tap(self, lane):
        # Find closest unhandled note in this lane near the hit zone.
        best = None
        best_dist = 9999

        for note in self.notes:
            if note.lane == lane and not note.hit and not note.missed:
                dist = abs(note.y + Note.HEIGHT // 2 - HIT_Y)

                if dist < best_dist:
                    best_dist = dist
                    best = note

        lane_x = lane * LANE_W + LANE_W // 2

        if best and best_dist <= HIT_WINDOW:

            # Task 2: hold notes are not scored immediately.
            if best.is_hold:
                best.holding = True
                best.hold_started_at = pygame.time.get_ticks()

                self.feedback.append(
                    ["HOLD", (180, 220, 255), 20, lane_x, HIT_Y - 30]
                )
                return

            # Normal note scoring from Task 1.
            best.hit = True

            if best_dist < 8:
                grade, pts = "PERFECT", 300
                col = (255, 220, 0)

            elif best_dist < 18:
                grade, pts = "GREAT", 200
                col = (100, 220, 100)

            else:
                grade, pts = "OK", 100
                col = (180, 180, 255)

            self.combo += 1
            self.max_combo = max(self.max_combo, self.combo)
            self.score += pts * max(1, self.combo // 5)

            self.feedback.append(
                [grade, col, 40, lane_x, HIT_Y - 30]
            )

            # Task 1: sound only for successful normal hits.
            self.hit_sound.play()

        else:
            self.combo = 0

            self.feedback.append(
                ["MISS", (220, 60, 60), 40, lane_x, HIT_Y - 30]
            )

    def release_hold(self, lane):
        # Releasing before one second cancels the hold.
        for note in self.notes:
            if (
                note.lane == lane
                and note.is_hold
                and note.holding
                and not note.hit
                and not note.missed
            ):
                note.holding = False
                note.missed = True
                note.hold_started_at = None

                self.misses += 1
                self.combo = 0

                lane_x = lane * LANE_W + LANE_W // 2

                self.feedback.append(
                    ["MISS", (220, 60, 60), 40, lane_x, HIT_Y - 30]
                )

                break

    def update(self):
        if self.game_over:
            return

        self.frame += 1

        # ---------------------------------------------------------
        # Task 3: BPM-synchronized spawning
        # ---------------------------------------------------------
        now = pygame.time.get_ticks()

        while now >= self.next_beat_time:
            self.spawn_note()

            # Keep the schedule based on the original beat timing
            # rather than the current frame time.
            self.next_beat_time += int(BEAT_INTERVAL * 1000)

        # Gradually increase note speed over time.
        if self.frame % 600 == 0:
            self.speed = min(10, self.speed + 0.5)

        # ---------------------------------------------------------
        # Update existing notes
        # ---------------------------------------------------------
        for note in self.notes:
            note.update()

            # Task 2: check active hold notes every frame.
            if (
                note.is_hold
                and note.holding
                and not note.hit
                and not note.missed
            ):
                # The key must remain physically pressed.
                if (
                    note.lane not in self.held_lanes
                    or not pygame.key.get_pressed()[LANE_KEYS[note.lane]]
                ):
                    self.release_hold(note.lane)

                # Successfully held for 1 second.
                elif (
                    now - note.hold_started_at
                    >= Note.HOLD_DURATION_MS
                ):
                    note.hit = True
                    note.holding = False
                    note.hold_started_at = None

                    self.combo += 1
                    self.max_combo = max(
                        self.max_combo,
                        self.combo
                    )

                    self.score += 300 * max(
                        1,
                        self.combo // 5
                    )

                    lane_x = (
                        note.lane * LANE_W
                        + LANE_W // 2
                    )

                    self.feedback.append(
                        [
                            "HOLD OK",
                            (120, 240, 255),
                            40,
                            lane_x,
                            HIT_Y - 30
                        ]
                    )

            # Normal notes and unstarted hold notes can be missed.
            if (
                not note.hit
                and not note.missed
                and not note.holding
                and note.y
                > HIT_Y + HIT_WINDOW + Note.HEIGHT
            ):
                note.missed = True
                self.misses += 1
                self.combo = 0

        # Remove completed/missed notes after they leave the screen.
        self.notes = [
            n
            for n in self.notes
            if not (
                n.hit
                or n.missed
                and n.y > HEIGHT + 10
            )
        ]

        # Update feedback messages.
        self.feedback = [
            [t, c, ttl - 1, x, y]
            for t, c, ttl, x, y in self.feedback
            if ttl > 1
        ]

        if self.misses >= 15:
            self.game_over = True

    def draw(self):
        self.screen.fill(BG)

        # Lane dividers.
        for i in range(LANES + 1):
            pygame.draw.line(
                self.screen,
                (40, 40, 60),
                (i * LANE_W, 0),
                (i * LANE_W, HEIGHT),
                1
            )

        # Hit line.
        pygame.draw.line(
            self.screen,
            (80, 80, 100),
            (0, HIT_Y),
            (WIDTH, HIT_Y),
            2
        )

        for i in range(LANES):
            lx = i * LANE_W + LANE_W // 2

            pygame.draw.rect(
                self.screen,
                LANE_COLORS[i],
                pygame.Rect(
                    lx - Note.WIDTH // 2,
                    HIT_Y - 12,
                    Note.WIDTH,
                    24
                ),
                border_radius=6
            )

            lbl = self.font.render(
                LANE_LABELS[i],
                True,
                (20, 20, 20)
            )

            self.screen.blit(
                lbl,
                (
                    lx - lbl.get_width() // 2,
                    HIT_Y - 10
                )
            )

        # ---------------------------------------------------------
        # Notes
        # ---------------------------------------------------------
        for note in self.notes:
            if note.hit:
                continue

            lx = note.lane * LANE_W + LANE_W // 2

            if note.is_hold:
                # Long visual body for hold notes.
                rect = note.get_rect(lx)

                pygame.draw.rect(
                    self.screen,
                    LANE_COLORS[note.lane],
                    rect,
                    border_radius=7
                )

                pygame.draw.rect(
                    self.screen,
                    (245, 245, 245),
                    rect,
                    width=3,
                    border_radius=7
                )

                pygame.draw.rect(
                    self.screen,
                    (255, 255, 255),
                    pygame.Rect(
                        lx - Note.WIDTH // 2 + 6,
                        int(note.y),
                        Note.WIDTH - 12,
                        Note.HEIGHT
                    ),
                    border_radius=4
                )

                # Show hold progress while the key is being held.
                if note.holding:
                    elapsed = (
                        pygame.time.get_ticks()
                        - note.hold_started_at
                    )

                    progress = min(
                        1.0,
                        elapsed / Note.HOLD_DURATION_MS
                    )

                    progress_h = max(
                        2,
                        int(note.hold_length * progress)
                    )

                    pygame.draw.rect(
                        self.screen,
                        (255, 255, 255),
                        pygame.Rect(
                            lx - 4,
                            int(note.y),
                            8,
                            progress_h
                        ),
                        border_radius=3
                    )

            else:
                # Normal tap note.
                rect = note.get_rect(lx)

                pygame.draw.rect(
                    self.screen,
                    LANE_COLORS[note.lane],
                    rect,
                    border_radius=5
                )

        # ---------------------------------------------------------
        # Feedback
        # ---------------------------------------------------------
        for text, color, ttl, x, y in self.feedback:
            surf = self.font.render(
                text,
                True,
                color
            )

            alpha = min(255, ttl * 7)
            surf.set_alpha(alpha)

            self.screen.blit(
                surf,
                (
                    x - surf.get_width() // 2,
                    y
                )
            )

        # ---------------------------------------------------------
        # HUD
        # ---------------------------------------------------------
        sc = self.font.render(
            f"Score: {self.score}",
            True,
            (220, 220, 220)
        )

        co = self.font.render(
            f"Combo: {self.combo}x",
            True,
            (255, 220, 80)
        )

        mi = self.font.render(
            f"Misses: {self.misses}/15",
            True,
            (220, 100, 100)
        )

        self.screen.blit(sc, (10, 10))
        self.screen.blit(co, (10, 40))
        self.screen.blit(
            mi,
            (WIDTH - 170, 10)
        )

        # ---------------------------------------------------------
        # Game Over
        # ---------------------------------------------------------
        if self.game_over:
            ov = pygame.Surface(
                (WIDTH, HEIGHT),
                pygame.SRCALPHA
            )

            ov.fill((0, 0, 0, 160))
            self.screen.blit(ov, (0, 0))

            msg = self.big_font.render(
                "GAME OVER",
                True,
                (220, 60, 60)
            )

            sc_msg = self.font.render(
                f"Final Score: {self.score}  "
                f"Max Combo: {self.max_combo}x",
                True,
                (200, 200, 200)
            )

            restart = self.font.render(
                "Press R to Restart",
                True,
                (160, 160, 160)
            )

            self.screen.blit(
                msg,
                (
                    WIDTH // 2 - msg.get_width() // 2,
                    HEIGHT // 2 - 70
                )
            )

            self.screen.blit(
                sc_msg,
                (
                    WIDTH // 2 - sc_msg.get_width() // 2,
                    HEIGHT // 2
                )
            )

            self.screen.blit(
                restart,
                (
                    WIDTH // 2 - restart.get_width() // 2,
                    HEIGHT // 2 + 50
                )
            )

        pygame.display.flip()

    def run(self):
        running = True

        while running:
            running = self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)

        pygame.quit()