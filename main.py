import pygame
import random
import sqlite3
import json
import os
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass
from enum import Enum
import time

class GameMode(Enum):
    CLASSIC = "classic"
    TIME_ATTACK = "time_attack"
    ZEN = "zen"
    CHALLENGE = "challenge"

@dataclass
class Achievement:
    id: str
    name: str
    description: str
    condition: str
    icon: str
    unlocked: bool = False

class Game():
    def __init__(self):
        pygame.init()
        self.config = {
            'screen_width': 800,
            'screen_height': 600,
            'board_size': 4,
            'max_undos': 3
        }
        self.screen = pygame.display.set_mode(
            (self.config['screen_width'], self.config['screen_height'])
        )
        pygame.display.set_caption('2048')
        
        self.fonts = {
            'small': pygame.font.Font(None, 24),
            'medium': pygame.font.Font(None, 36),
            'large': pygame.font.Font(None, 48)
        }
        
        self.color_scheme = {
            'background': (250, 248, 239),
            'text': (119, 110, 101),
            'grid': (187, 173, 160),
            'empty': (205, 193, 180)
        }
        
        self.board_size = self.config['board_size']
        self.max_undos = self.config['max_undos'] 
        self.grid = [[0] * self.board_size for _ in range(self.board_size)]
        self.score = 0
        self.game_over = False
        
        self.notifications = []
        self.conn = sqlite3.connect('game.db')
        self.initialize_features()
        self.add_new_tile()
        self.add_new_tile()   

    def initialize_features(self):
        self.game_mode = GameMode.CLASSIC
        self.time_attack_duration = 180 
        self.time_remaining = self.time_attack_duration
        self.last_time = time.time()
        self.animations = []
        self.animation_speed = 0.3
        self.setup_achievements()
        self.power_ups = self.initialize_power_ups()
        self.active_power_ups = []
        
        self.stats = self.load_statistics()
        self.move_history = []
        self.max_undos = 3
        self.undo_count = 0

    def setup_achievements(self):
        self.achievements = [
            Achievement(
                id = "first_2048",
                name = "First 2048!",
                description = "Get your first 2048 tile",
                condition = "max_tile >= 2048",
                icon = "🏆"
            ),
            Achievement(
                id = "speed_demon",
                name = "Speed Demon",
                description = "Win a game in under 3 minutes",
                condition = "win_time < 180",
                icon = "⚡"
            ),
            Achievement(
                id = "perfect_game",
                name = "Perfect Game",
                description = "Win without using undo",
                condition = "undo_count == 0",
                icon = "✨"
            )
        ]
        self.load_achievements()

    def initialize_power_ups(self) -> Dict:
        return {
            'undo': {
                'name': 'Undo',
                'description': 'Reverse your last move',
                'count': self.max_undos,
                'initial_count': self.max_undos,
                'key': 'u'
            },
            'clear_tile': {
                'name': 'Clear Tile',
                'description': 'Remove any tile from the board',
                'initial_count': 1,
                'key': 'c'
            },
            'double_points': {
                'name': 'Double Points',
                'initial_count': 1,
                'count': 1,
                'key': 'd',
                'duration': 5
            }
        }

    def load_statistics(self) -> Dict:
        try:
            with open('game_stats.json', 'r') as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {
                'games_played': 0,
                'total_score': 0,
                'highest_tile': 0,
                'time_played': 0,
                'moves_made': 0
            }

    def save_statistics(self):
        with open('game_stats.json', 'w') as f:
            json.dump(self.stats, f)

    def add_new_tile(self):
        empty_cells = [
            (i, j) for i in range(self.board_size) 
            for j in range(self.board_size) if self.grid[i][j] == 0
        ]
        if empty_cells:
            i, j = random.choice(empty_cells)
            self.grid[i][j] = 2 if random.random() < 0.9 else 4

    def move_tiles(self, direction: str) -> bool:
        self.move_history.append([row[:] for row in self.grid])
        if len(self.move_history) > self.max_undos + 1:
            self.move_history.pop(0)
            
        original_grid = [row[:] for row in self.grid]
        merged = [[False] * self.board_size for _ in range(self.board_size)]
        
        if direction in ['up', 'down']:
            for j in range(self.board_size):
                if direction == 'up':
                    for i in range(1, self.board_size):
                        self._move_tile(i, j, -1, 0, merged)
                else:
                    for i in range(self.board_size - 2, -1, -1):
                        self._move_tile(i, j, 1, 0, merged)
                        
        elif direction in ['left', 'right']:
            for i in range(self.board_size):
                if direction == 'left':
                    for j in range(1, self.board_size):
                        self._move_tile(i, j, 0, -1, merged)
                else:
                    for j in range(self.board_size - 2, -1, -1):
                        self._move_tile(i, j, 0, 1, merged)
        
        moved = original_grid != self.grid
        if moved:
            self.stats['moves_made'] += 1
            self.check_achievements()
            self.update_power_ups()
            self.add_new_tile()
            
        return moved

    def _move_tile(self, i: int, j: int, di: int, dj: int, merged: List[List[bool]]):
        if self.grid[i][j] == 0:
            return
            
        current = self.grid[i][j]
        ni, nj = i + di, j + dj
        
        while (0 <= ni < self.board_size and 
               0 <= nj < self.board_size):
            if self.grid[ni][nj] == 0:
                self.grid[ni][nj] = current
                self.grid[ni-di][nj-dj] = 0
                ni += di
                nj += dj
            elif (self.grid[ni][nj] == current and 
                  not merged[ni][nj] and 
                  not merged[ni-di][nj-dj]):
                self.grid[ni][nj] *= 2
                self.score += self.grid[ni][nj] * self.get_score_multiplier()
                self.grid[ni-di][nj-dj] = 0
                merged[ni][nj] = True
                break
            else:
                break
        
    def undo_move(self) -> bool:
        if (len(self.move_history) > 1 and 
            self.undo_count < self.max_undos and 
            not self.game_over):
            self.move_history.pop()  
            self.grid = [row[:] for row in self.move_history[-1]]
            self.undo_count += 1
            return True
        return False

    def update_power_ups(self):
        for power_up in self.active_power_ups[:]:
            if 'duration' in power_up:
                power_up['duration'] -= 1
                if power_up['duration'] <= 0:
                    self.active_power_ups.remove(power_up)

    def use_power_up(self, power_up_id: str, *args) -> bool:
        if (power_up_id in self.available_power_ups and 
            self.available_power_ups[power_up_id]['count'] > 0):
            if power_up_id == 'undo':
                success = self.undo_move()
            elif power_up_id == 'clear_tile':
                success = self.clear_tile(*args)
            elif power_up_id == 'double_points':
                success = self.activate_double_points()
            
            if success:
                self.available_power_ups[power_up_id]['count'] -= 1
                return True
        return False

    def clear_tile(self, row: int, col: int) -> bool:
        if 0 <= row < self.board_size and 0 <= col < self.board_size:
            if self.grid[row][col] != 0:
                self.grid[row][col] = 0
                return True
        return False

    def activate_double_points(self) -> bool:
        self.active_power_ups.append({
            'type': 'double_points',
            'duration': self.available_power_ups['double_points']['duration']
        })
        return True

    def get_score_multiplier(self) -> float:
        multiplier = 1.0
        for power_up in self.active_power_ups:
            if power_up['type'] == 'double_points':
                multiplier *= 2.0
        return multiplier

    def update(self):
        if self.game_mode == GameMode.TIME_ATTACK and not self.game_over:
            current_time = time.time()
            self.time_remaining -= current_time - self.last_time
            self.last_time = current_time
            
            if self.time_remaining <= 0:
                self.game_over = True
                self.save_statistics()
        if not self.game_over:
            empty_cells = any(
                self.grid[i][j] == 0 
                for i in range(self.board_size) 
                for j in range(self.board_size)
            )
            can_merge = self._check_can_merge()
            
            if not empty_cells and not can_merge:
                self.game_over = True
                self.save_statistics()

    def _check_can_merge(self) -> bool:
        for i in range(self.board_size):
            for j in range(self.board_size):
                current = self.grid[i][j]
                if current != 0:
                    if (j < self.board_size - 1 and 
                        self.grid[i][j+1] == current):
                        return True
                    if (i < self.board_size - 1 and 
                        self.grid[i+1][j] == current):
                        return True
        return False

    def check_achievements(self):
        max_tile = max(
            tile for row in self.grid for tile in row
        )
        for achievement in self.achievements:
            if not achievement.unlocked:
                condition_met = eval(
                    achievement.condition, 
                    {'max_tile': max_tile, 
                     'win_time': self.time_attack_duration - self.time_remaining,
                     'undo_count': self.undo_count}
                )
                if condition_met:
                    self.unlock_achievement(achievement)

    def unlock_achievement(self, achievement: Achievement):
        achievement.unlocked = True
        self.notifications.append({
            'text': f'Achievement Unlocked: {achievement.name}',
            'start_time': pygame.time.get_ticks(),
            'duration': 3000
        })
        self.conn.execute(
            'INSERT INTO achievements (id, unlock_date) VALUES (?, CURRENT_TIMESTAMP)',
            (achievement.id,)
        )
        self.conn.commit()

    def load_achievements(self):
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS achievements
            (id TEXT PRIMARY KEY, unlock_date DATETIME)
        ''')
        
        unlocked = {row[0] for row in 
                   self.conn.execute('SELECT id FROM achievements')}
        
        for achievement in self.achievements:
            achievement.unlocked = achievement.id in unlocked

    def render(self):
        self.screen.fill(self.color_scheme['background'])
        cell_size = min(
            (self.config['screen_width'] - 100) // self.board_size,
            (self.config['screen_height'] - 200) // self.board_size
        )
        grid_size = cell_size * self.board_size
        start_x = (self.config['screen_width'] - grid_size) // 2
        start_y = (self.config['screen_height'] - grid_size) // 2
        
        for i in range(self.board_size):
            for j in range(self.board_size):
                x = start_x + j * cell_size
                y = start_y + i * cell_size
                pygame.draw.rect(
                    self.screen,
                    self.color_scheme['empty'],
                    (x, y, cell_size - 2, cell_size - 2)
                )
                if self.grid[i][j] != 0:
                    value = self.grid[i][j]
                    text = self.fonts['medium'].render(
                        str(value), True, self.color_scheme['text']
                    )
                    text_rect = text.get_rect(
                        center = (x + cell_size//2, y + cell_size//2)
                    )
                    self.screen.blit(text, text_rect)
        score_text = self.fonts['large'].render(
            f'Score: {self.score}', True, self.color_scheme['text']
        )
        self.screen.blit(
            score_text,
            (10, 10)
        )
        
        if self.game_mode == GameMode.TIME_ATTACK:
            self.render_timer()
        
        self.render_power_ups()
        self.render_notifications()
        
        if self.game_over:
            self.render_game_over()
        pygame.display.flip()

    def render_timer(self):
        minutes = int(self.time_remaining // 60)
        seconds = int(self.time_remaining % 60)
        timer_text = self.fonts['medium'].render(
            f'Time: {minutes:02d}:{seconds:02d}',
            True, self.color_scheme['text']
        )
        self.screen.blit(timer_text, (10, 70))

    def render_power_ups(self):
        power_up_y = 120
        for power_up_id, power_up in self.available_power_ups.items():
            if power_up['count'] > 0:
                text = self.fonts['small'].render(
                    f"{power_up['name']} ({power_up['key']}): {power_up['count']}",
                    True, self.color_scheme['text']
                )
                self.screen.blit(text, (10, power_up_y))
                power_up_y += 30

    def render_notifications(self):
        current_time = pygame.time.get_ticks()
        y_offset = 150
        
        for notification in self.notifications[:]:
            elapsed = current_time - notification['start_time']
            if elapsed < notification['duration']:
                alpha = 255
                if elapsed > notification['duration'] - 500:  # Fade out
                    alpha = int(255 * (notification['duration'] - elapsed) / 500)
                
                text = self.fonts['medium'].render(
                    notification['text'], True, self.color_scheme['text']
                )
                text.set_alpha(alpha)
                self.screen.blit(text, (10, y_offset))
                y_offset += 40
            else:
                self.notifications.remove(notification)

    def render_game_over(self):
        overlay = pygame.Surface((self.config['screen_width'], self.config['screen_height']))
        overlay.fill((0, 0, 0))
        overlay.set_alpha(128)
        self.screen.blit(overlay, (0, 0))
        
        game_over_text = self.fonts['large'].render('Game Over!', True, (255, 255, 255))
        score_text = self.fonts['medium'].render(
            f'Final Score: {self.score}', True, (255, 255, 255)
        )
        restart_text = self.fonts['small'].render(
            'Press R to Restart', True, (255, 255, 255)
        )
        
        text_y = self.config['screen_height'] // 2 - 60
        for text in [game_over_text, score_text, restart_text]:
            text_rect = text.get_rect(
                center=(self.config['screen_width'] // 2, text_y)
            )
            self.screen.blit(text, text_rect)
            text_y += 50

    def reset_game(self):
        self.grid = [[0] * self.board_size for _ in range(self.board_size)]
        self.score = 0
        self.game_over = False
        self.move_history.clear()
        self.undo_count = 0
        self.time_remaining = self.time_attack_duration
        self.last_time = time.time()
        self.notifications.clear()
        self.active_power_ups.clear()
        
        for power_up in self.available_power_ups.values():
            if 'count' in power_up:
                power_up['count'] = power_up.get('initial_count', 1)
        
        self.add_new_tile()
        self.add_new_tile()
        
        self.stats['games_played'] += 1
        self.save_statistics()

    def handle_input(self) -> bool:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
                
            if event.type == pygame.KEYDOWN:
                if self.game_over:
                    if event.key == pygame.K_r:
                        self.reset_game()
                else:
                    if event.key in [pygame.K_UP, pygame.K_w]:
                        self.move_tiles('up')
                    elif event.key in [pygame.K_DOWN, pygame.K_s]:
                        self.move_tiles('down')
                    elif event.key in [pygame.K_LEFT, pygame.K_a]:
                        self.move_tiles('left')
                    elif event.key in [pygame.K_RIGHT, pygame.K_d]:
                        self.move_tiles('right')
                    
                    # Power-up handling
                    for power_up_id, power_up in self.available_power_ups.items():
                        if (event.key == ord(power_up['key']) and 
                            power_up['count'] > 0):
                            self.use_power_up(power_up_id)
        
        return True

    def run(self):
        running = True
        clock = pygame.time.Clock()
        
        while running:
            running = self.handle_input()
            self.update()
            self.render()
            clock.tick(60)
        
        pygame.quit()
        self.conn.close()

if __name__ == "__main__":
    game = Game()
    game.run()