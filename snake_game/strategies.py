from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Callable
from random import Random

from .models import Direction, GameSnapshot


class MoveStrategy(ABC):
    """Base class for every automated snake movement method."""

    @abstractmethod
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        """Return the direction for ``snake_id`` for the current turn."""


STRATEGY_REGISTRY: dict[str, type[MoveStrategy]] = {}


def register_strategy(name: str) -> Callable[[type[MoveStrategy]], type[MoveStrategy]]:
    """Register a strategy class so it appears in the setup-screen dropdown."""

    def decorator(strategy_class: type[MoveStrategy]) -> type[MoveStrategy]:
        if not name.strip():
            raise ValueError("Strategy names cannot be empty.")
        STRATEGY_REGISTRY[name] = strategy_class
        return strategy_class

    return decorator


def create_strategy(name: str) -> MoveStrategy:
    try:
        return STRATEGY_REGISTRY[name]()
    except KeyError as exc:
        raise ValueError(f"Unknown strategy: {name}") from exc


@register_strategy("Safe Random")
class SafeRandomStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        legal = snapshot.legal_moves_for(snake_id)
        if legal:
            return rng.choice(legal)
        return snapshot.snake(snake_id).direction


@register_strategy("Greedy")
class GreedyStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal or not snapshot.apples:
            return snake.direction

        head_x, head_y = snake.body[0]

        def distance(direction: Direction) -> int:
            dx, dy = direction.vector
            new_x, new_y = head_x + dx, head_y + dy
            return min(
                abs(new_x - apple_x) + abs(new_y - apple_y)
                for apple_x, apple_y in snapshot.apples
            )

        best_distance = min(distance(direction) for direction in legal)
        best_moves = [direction for direction in legal if distance(direction) == best_distance]
        return rng.choice(best_moves)

@register_strategy("UCS")
class UCSStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal or not snapshot.apples:
            return snake.direction
        
        start = snake.body[0] # Posisi kepala ular (x, y)
        apples = set(snapshot.apples)
        # Mengumpulkan seluruh badan dari SEMUA ular (termasuk lawan/human) sebagai rintangan
        obstacles = {part for s in snapshot.snakes for part in s.body}
        # Priority Queue manual menggunakan List
        # Format elemen: (cost, posisi)
        pq = [(0, start)]
        
        # Dictionary untuk mencatat cost terkecil & parent node (asal langkah)
        visited_cost = {start: 0}
        parent = {}
        target_found = None
        while pq:
            # Cari elemen dengan cost terkecil di dalam list pq 
            min_index = 0
            for i in range(1, len(pq)):
                if pq[i][0] < pq[min_index][0]:
                    min_index = i
            # Pop elemen dengan cost terkecil tersebut
            curr_cost, curr_pos = pq.pop(min_index)
            # ------------------------------------------
            # Jika sudah sampai di salah satu apel, hentikan pencarian
            if curr_pos in apples:
                target_found = curr_pos
                break
            # Cek jika ada cost yang lebih murah yang sudah pernah dikunjungi sebelumnya
            if curr_cost > visited_cost.get(curr_pos, float('inf')):
                continue
            curr_x, curr_y = curr_pos
            # Cek 4 arah menggunakan enum Direction yang sudah ada
            for direction in Direction:
                dx, dy = direction.vector
                next_pos = (curr_x + dx, curr_y + dy)
                # Cek batas area permainan & rintangan (badan ular)
                if (0 <= next_pos[0] < snapshot.columns and
                    0 <= next_pos[1] < snapshot.rows and
                    next_pos not in obstacles):
                    # Bobot per langkah (dapat disesuaikan jika ingin ada penalti)
                    step_cost = 1
                    new_cost = curr_cost + step_cost
                    # Jika posisi baru belum pernah dikunjungi atau menemukan jalur yang lebih murah
                    if next_pos not in visited_cost or new_cost < visited_cost[next_pos]:
                        visited_cost[next_pos] = new_cost
                        parent[next_pos] = (curr_pos, direction) # Catat asal & arahnya
                        pq.append((new_cost, next_pos))
        # Backtrack dari apel untuk mendapatkan LANGKAH PERTAMA
        if target_found:
            curr = target_found
            first_step = None
            while curr in parent:
                prev_pos, move_direction = parent[curr]
                first_step = move_direction
                curr = prev_pos
            if first_step:
                return first_step
        # Jika tidak ada jalur ke apel via UCS, ambil langkah aman acak
        return rng.choice(legal)
    
# Assignment template -------------------------------------------------------
# 1. Copy this class and give it a unique name.
# 2. Implement choose_move using only the immutable snapshot.
# 3. Add @register_strategy("My Strategy") above the class. It will then appear
#    automatically in the setup screen.
#
# @register_strategy("My Strategy")
# class MyStrategy(MoveStrategy):
#     def choose_move(self, snapshot, snake_id, rng):
#         legal_moves = snapshot.legal_moves_for(snake_id)
#         return legal_moves[0] if legal_moves else snapshot.snake(snake_id).direction
