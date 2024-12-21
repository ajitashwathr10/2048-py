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
        super().__init__()
        self.initialize_features()

    def initialize_features(self):
        self.game_mode = GameMode.CLASSIC
        self.time_attack_duration = 180 
        self.time_remaining = self.time_attack_duration
        self.last_time = time.time()
        self.animations = []
        self.animation_speed = 0.3
        #self.load_sound_effects()
        self.setup_achievements()
    
        self.available_power_ups = self.initialize_power_ups()
        self.active_power_ups = []
        
        self.stats = self.load_statistics()
        self.move_history = []
        self.max_undos = 3
        self.undo_count = 0

    #def load_sound_effects(self):
    #    self.sounds = {
    #        'merge': pygame.mixer.Sound('assets/merge.wav'),
    #        'move': pygame.mixer.Sound('assets/move.wav'),
    #        'game_over': pygame.mixer.Sound('assets/game_over.wav'),
    #        'achievement': pygame.mixer.Sound('assets/achievement.wav'),
    #        'power_up': pygame.mixer.Sound('assets/power_up.wav')
    #    }
        
        # Create assets directory if it doesn't exist
    #    if not os.path.exists('assets'):
    #        os.makedirs('assets')
    #        print("Please add sound files to the assets directory")
    

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
                'key': 'u'
            },
            'clear_tile': {
                'name': 'Clear Tile',
                'description': 'Remove any tile from the board',
                'count': 1,
                'key': 'c'
            },
            'double_points': {
                'name': 'Double Points',
                'description': 'Double points for 5 moves',
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

    def move_tiles(self, direction: str) -> bool:
        self.move_history.append([row[:] for row in self.grid])
        if len(self.move_history) > self.max_undos + 1:
            self.move_history.pop(0)
        moved = super().move_tiles(direction)
        if moved:
            self.stats['moves_made'] += 1
            self.play_sound('move')
            self.check_achievements()
            self.update_power_ups()
        
        return moved

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
                self.play_sound('power_up')
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
        super().update()
        
        if self.game_mode == GameMode.TIME_ATTACK and not self.game_over:
            current_time = time.time()
            self.time_remaining -= current_time - self.last_time
            self.last_time = current_time
            
            if self.time_remaining <= 0:
                self.game_over = True
                self.save_score()

    #def play_sound(self, sound_id: str):
    #    if sound_id in self.sounds and self.config['sound_volume'] > 0:
    #        self.sounds[sound_id].play()

    def check_achievements(self):
        for achievement in self.achievements:
            if not achievement.unlocked:
                condition_met = eval(achievement.condition)
                if condition_met:
                    self.unlock_achievement(achievement)

    def unlock_achievement(self, achievement: Achievement):
        achievement.unlocked = True
        self.play_sound('achievement')
        self.notifications.append({
            'text': f'Achievement Unlocked: {achievement.name}',
            'start_time': pygame.time.get_ticks(),
            'duration': 3000
        })
        self.conn.execute('''INSERT INTO achievements (id, unlock_date)
                           VALUES (?, CURRENT_TIMESTAMP)''',
                        (achievement.id,))
        self.conn.commit()

    def load_achievements(self):
        self.conn.execute('''CREATE TABLE IF NOT EXISTS achievements
                           (id TEXT PRIMARY KEY,
                            unlock_date DATETIME)''')
        
        unlocked = {row[0] for row in 
                   self.conn.execute('SELECT id FROM achievements')}
        
        for achievement in self.achievements:
            achievement.unlocked = achievement.id in unlocked

    def render(self):
        super().render()
        
        if self.game_mode == GameMode.TIME_ATTACK:
            self.render_timer()
        
        self.render_power_ups()
        self.render_achievements()

    def render_timer(self):
        minutes = int(self.time_remaining // 60)
        seconds = int(self.time_remaining % 60)
        timer_text = self.fonts['medium'].render(
            f'Time: {minutes:02d}:{seconds:02d}',
            True, self.color_scheme['text']
        )
        self.screen.blit(timer_text, (10, 10))

    def render_power_ups(self):
        x = 10
        y = self.config['screen_height'] - 60
        
        for power_up_id, power_up in self.available_power_ups.items():
            if power_up['count'] > 0:
                text = self.fonts['small'].render(
                    f"{power_up['name']} ({power_up['key']}): {power_up['count']}",
                    True, self.color_scheme['text']
                )
                self.screen.blit(text, (x, y))
                y += 25

    def render_achievements(self):
        current_time = pygame.time.get_ticks()
        for achievement in self.achievements:
            if (achievement.unlocked and 
                current_time - achievement.unlock_time < 3000):
                self.render_achievement_notification(achievement)

    def cleanup(self):
        self.save_statistics()
        super().cleanup()

if __name__ == "__main__":
    game = Game()
    game.run()

    