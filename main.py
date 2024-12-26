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

    def move(self, direction):
        moved = False
        if direction in ['UP', 'DOWN']:
            for j in range(GRID_SIZE):
                column = [self.grid[i][j] for i in range(GRID_SIZE)]
                if direction == 'UP':
                    new_column = self.merge(column)
                else:
                    new_column = self.merge(column[::-1])[::-1]
        else:
            for i in range(GRID_SIZE):
                row = self.grid[i][:]
                if direction == 'LEFT':
                    new_row = self.merge(row)
                else:
                    new_row = self.merge(row[::-1])[::-1]
                if self.grid[i] != new_row:
                    moved = True
                self.grid[i] = new_row
        if moved:
            self.moves += 1
            self.add_new_tile()
        return moved
    
    def merge(self, line):
        new_line = [x for x in line if x != 0]
        for i in range(len(new_line) - 1):
            if new_line[i] == new_line[i + 1]:
                new_line[i] *= 2
                self.score += new_line[i]
                new_line[i + 1] = 0
        
        new_line = [x for x in new_tile if x != 0]
        new_line.extend([0] * (GRID_SIZE - len(new_line)))
        return new_line
    
    def get_max_tile(self):
        return max(max(row) for row in self.grid)

    def game_over(self):
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                if self.grid[i][j] == 0:
                    return False
                if i < GRID_SIZE - 1 and self.grid[i][j] == self.grid[i + 1][j]:
                    return False
                if j < GRID_SIZE - 1 and self.grid[i][j] == self.grid[i][j + 1]:
                    return False
        return True
    
    def display_game_over(self):
        duration = int((datetime.now() - self.start_time).total_seconds())
        max_tile = self.get_max_tile()

        self.db.save_game(self.score, max_tile, duration, self.moves)
        self.screen.fill(BACKGROUND_COLOR)
        game_over_text = self.font.render('Game Over', True, LIGHT_TEXT)
        score_text = self.font.render(f'Final Score: {self.score}', True, LIGHT_TEXT)
        max_tile_text = self.font.render(f'Max Tile: {max_tile}', True, LIGHT_TEXT)
        moves_text = self.font.render(f'Moves: {self.moves}', True, LIGHT_TEXT)
        time_text = self.font.render(f'Duration: {duration} seconds', True, LIGHT_TEXT)

        texts = [game_over_text, score_text, max_tile_text, moves_text, time_text]
        spacing = 50

        for i, text in enumerate(texts):
            text_rect = text.get_rect(center = (WINDOW_SIZE // 2, WINDOW_SIZE // 2 - 100 + i * spacing))
            self.screen.blit(text, text_rect)
        pygame.display.flip()
        pygame.time.wait(3000)

    def display_high_scores(self):
        self.screen.fill(BACKGROUND_COLOR)
        high_scores = self.db.get_high_scores()
        title_text = self.font.render('High Scores', True, LIGHT_TEXT)
        title_rect = title_text.get_rect(center = (WINDOW_SIZE // 2, 50))
        self.screen.blit(title_text, title_rect)

        for i, (score, timestamp) in enumerate(high_scores):
            score_text = self.small_font.render(
                f'{i + 1}. {score} ({timestamp.split(".")[0]})',
                True,
                LIGHT_TEXT
            )
            text_rect = score_text.get_rect(center = (WINDOW_SIZE // 2, 120 + i * 40))
            self.screen.blit(score_text, text_rect)

        pygame.display.flip()
        pygame.time.wait(3000)

    def run(self):
        running = True
        while running:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                if event.type == pygame.KEYDOWN:
                    moved = False
                    if event.key == pygame.K_UP:
                        moved = self.move('UP')
                    elif event.key == pygame.K_DOWN:
                        moved = self.move('DOWN')
                    elif event.key == pygame.K_LEFT:
                        moved = self.move('LEFT')
                    elif event.key == pygame.K_RIGHT:
                        moved = self.move('RIGHT')
                    
                    if self.game_over():
                        self.display_game_over()
                        self.display_high_scores()
                        running = False
            self.draw()
        self.db.close()
        pygame.quit()
        sys.exit()

if __name__ == "__main__":
    game = Game()
    game.run()



            

