import pygame
import random
import sys
import sqlite3
from datetime import datetime

pygame.init()

WINDOW_SIZE = 400
GRID_SIZE = 4
CELL_SIZE = WINDOW_SIZE // GRID_SIZE
PADDING = 10

COLORS = {
    0: (205, 193, 180),  
    2: (238, 228, 218),
    4: (237, 224, 200),
    8: (242, 177, 121),
    16: (245, 149, 99),
    32: (246, 124, 95),
    64: (246, 94, 59),
    128: (237, 207, 114),
    256: (237, 204, 97),
    512: (237, 200, 80),
    1024: (237, 197, 63),
    2048: (237, 194, 46)
}

BACKGROUND_COLOR = (187, 173, 160)
TEXT_COLOR = (119, 110, 101)
LIGHT_TEXT = (249, 246, 242)

class Database:
    def __init__(self):
        self.conn = sqlite3.connect('game.db')
        self.cursor = self.conn.cursor()
        self.setup_database()

    def setup_database(self):
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS games
            if INTEGER PRIMARY KEY AUTOINCREMENT,
            score INTEGER,
            max_tile INTEGER,
            duration INTEGER,
            timestamp DATETIME,
            moves INTEGER)
        ''')

        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS high_scores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            score INTEGER,
            timestamp DATETIME)
            )
        ''')
        self.conn.commit()

    def save_game(self, score, max_tile, duration, moves):
        self.cursor.execute('''
            INSERT INTO games (score, max_tile, duration, timestamp, moves)
            VALUES (?, ?, ?, ?, ?)
            ''', (score, max_tile, duration, datetime.now(), moves))
        self.cursor.execute('SELECT MIN(score) FROM high_scores')
        min_high_score = self.cursor.fetchone()[0]

        if min_high_score is None or score > min_high_score:
            self.cursor.execute('''
                INSERT INTO high_scores (score, timestamp)
                VALUES (?, ?)
            ''', (score, datetime.now()))

            self.cursor.execute('''
                DELETE FROM high_scores
                WHERE id NOT IN (
                    SELECT id FROM high_scores
                    ORDER BY score DESC
                    LIMIT 5
                )
            ''')
            self.conn.commit()

    def get_high_scores(self):
        self.conn.execute('''
            SELECT score, timestamp
            FROM high_scores
            ORDER BY score DESC
            LIMIT 5
        ''')

        return self.cursor.fetchall()
    def close(self):
        self.conn.close()

class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((WINDOW_SIZE, WINDOW_SIZE))
        pygame.display.set_caption('2048')
        self.grid = [[0] * GRID_SIZE for _ in range(GRID_SIZE)]
        self.font = pygame.font.SysFont('Poppins', 36, bold = True)
        self.small_font = pygame.font.SysFont('Arial', 20, bold = True)

        self.score = 0
        self.moves = 0
        self.start_time = datetime.now()
        self.db = Database()
        self.add_new_tile()
        self.add_new_tile()

    def add_new_tile(self):
        empty_cells = [(i, j) for i in range(GRID_SIZE)
                    for j in range(GRID_SIZE) if self.grid[i][j] == 0]
        if empty_cells:
            i, j = random.choice(empty_cells)
            self.grid[i][j] = 2 if random.random() < 0.9 else 4

    def draw(self):
        self.screen.fill(BACKGROUND_COLOR)
        score_text = self.small_font.render(f'Score: {self.score}', True, LIGHT_TEXT)
        self.screen.blit(score_text, (10, 10))

        moves_text = self.small_font.render(f'Moves: {self.moves}', True, LIGHT_TEXT)
        self.screen.blit(moves_text, (WINDOW_SIZE - 120, 10))

        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                value = self.grid[i][j]
                rect = pygame.Rect(j * CELL_SIZE + PADDING,
                                i * CELL_SIZE + PADDING + 40,
                                CELL_SIZE - 2 * PADDING,
                                CELL_SIZE - 2 * PADDING)
                pygame.draw.rect(self.screen, COLORS.get(value, COLORS[0]), rect, border_radius = 8)
                if value != 0:
                    text_color = TEXT_COLOR if value <= 4 else LIGHT_TEXT
                    text = self.font.render(str(value), True, text_color)
                    text_rect = text.get_rect(center = rect.center)
                    self.screen.blit(text, text_rect)
        pygame.display.flip()

            

