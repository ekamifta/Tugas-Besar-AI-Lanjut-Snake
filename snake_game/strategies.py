from __future__ import annotations

import time
from abc import ABC, abstractmethod
from collections.abc import Callable
from random import Random

from .models import Direction, GameSnapshot


class MoveStrategy(ABC):
    """Base class for every automated snake movement method."""

    def __init__(self) -> None:
        self.last_metrics: dict = {}

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
        start_time = time.time()
        legal = snapshot.legal_moves_for(snake_id)
        move = rng.choice(legal) if legal else snapshot.snake(snake_id).direction
        waktu_ms = (time.time() - start_time) * 1000

        self.last_metrics = {
            "expanded": 1,
            "generated": len(legal),
            "evaluated": len(legal),
            "path_len": 1,
            "cost": 1,
            "waktu_ms": waktu_ms
        }
        return move


@register_strategy("Greedy")
class GreedyStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        start_time = time.time()
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal or not snapshot.apples:
            self.last_metrics = {"expanded": 0, "generated": 0, "evaluated": 0, "path_len": 0, "cost": 0, "waktu_ms": (time.time() - start_time) * 1000}
            return snake.direction

        head_x, head_y = snake.body[0]
        expanded = 1
        generated = len(legal)
        evaluated = 0

        def distance(direction: Direction) -> int:
            nonlocal evaluated
            evaluated += 1
            dx, dy = direction.vector
            new_x, new_y = head_x + dx, head_y + dy
            return min(
                abs(new_x - apple_x) + abs(new_y - apple_y)
                for apple_x, apple_y in snapshot.apples
            )

        best_distance = min(distance(direction) for direction in legal)
        best_moves = [direction for direction in legal if distance(direction) == best_distance]
        chosen_move = rng.choice(best_moves)

        waktu_ms = (time.time() - start_time) * 1000
        self.last_metrics = {
            "expanded": expanded,
            "generated": generated,
            "evaluated": evaluated,
            "path_len": 1,
            "cost": float(best_distance),
            "waktu_ms": waktu_ms
        }
        return chosen_move


@register_strategy("UCS")
class UCSStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        start_time = time.time()
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal or not snapshot.apples:
            self.last_metrics = {"expanded": 0, "generated": 0, "evaluated": 0, "path_len": 0, "cost": 0, "waktu_ms": (time.time() - start_time) * 1000}
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

        expanded = 0
        generated = 1

        while pq:
            # Cari elemen dengan cost terkecil di dalam list pq 
            min_index = 0
            for i in range(1, len(pq)):
                if pq[i][0] < pq[min_index][0]:
                    min_index = i
            # Pop elemen dengan cost terkecil tersebut
            curr_cost, curr_pos = pq.pop(min_index)
            expanded += 1

            if curr_pos in apples:
                target_found = curr_pos
                break

            if curr_cost > visited_cost.get(curr_pos, float('inf')):
                continue

            curr_x, curr_y = curr_pos
            for direction in Direction:
                dx, dy = direction.vector
                next_pos = (curr_x + dx, curr_y + dy)
                
                if (0 <= next_pos[0] < snapshot.columns and
                    0 <= next_pos[1] < snapshot.rows and
                    next_pos not in obstacles):
                    
                    generated += 1
                    step_cost = 1
                    new_cost = curr_cost + step_cost
                    
                    if next_pos not in visited_cost or new_cost < visited_cost[next_pos]:
                        visited_cost[next_pos] = new_cost
                        parent[next_pos] = (curr_pos, direction)
                        pq.append((new_cost, next_pos))

        first_step = None
        path_length = 0
        final_cost = 0.0

        if target_found:
            curr = target_found
            final_cost = visited_cost[target_found]
            while curr in parent:
                prev_pos, move_direction = parent[curr]
                first_step = move_direction
                curr = prev_pos
                path_length += 1

        waktu_ms = (time.time() - start_time) * 1000
        self.last_metrics = {
            "expanded": expanded,
            "generated": generated,
            "evaluated": expanded,
            "path_len": path_length if first_step else 1,
            "cost": final_cost,
            "waktu_ms": waktu_ms
        }

        if first_step:
            return first_step

        return rng.choice(legal)

@register_strategy("Breadth-First Search")
class BFSStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        start_time = time.time()
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal or not snapshot.apples:
            self.last_metrics = {"expanded": 0, "generated": 0, "evaluated": 0, "path_len": 0, "cost": 0, "waktu_ms": (time.time() - start_time) * 1000}
            return snake.direction

        #inisialisasi variabel
        head_x, head_y = snake.body[0]
        movement = []
        queue = []
        queue.append((head_x, head_y, movement))
        visited = []
        visited.append((head_x, head_y))

        expanded = 0
        generated = 0
        found_movement = None

        #hanya bisa jalan bila ada yang di queue
        while len(queue)>0:
            #cek queue[0]
            head_x, head_y, movement = queue.pop(0)
            if len(movement) > 0:
                expanded += 1

            #kalau kepala = apel
            if (head_x, head_y) in snapshot.apples:
                found_movement = movement
                break

            #jalan. +posisi baru --> queue
            for direction in Direction:
                if len(movement) == 0 and direction not in legal:
                    continue
                dx, dy = direction.vector
                new_x = head_x + dx
                new_y = head_y + dy

                if 0 <= new_x < snapshot.columns and 0 <= new_y < snapshot.rows:
                    generated += 1
                if (new_x, new_y) not in visited:
                    visited.append((new_x, new_y))
                    new_movement = movement + [direction]
                    queue.append((new_x, new_y, new_movement))

        path_length = len(found_movement) if found_movement is not None else 0
        final_cost = float(path_length)

        waktu_ms = (time.time() - start_time) * 1000
        self.last_metrics = {
            "expanded": expanded,
            "generated": generated,
            "evaluated": expanded,
            "path_len": path_length,
            "cost": final_cost,
            "waktu_ms": waktu_ms
        }

        if found_movement:
            return found_movement[0]
        return snake.direction

@register_strategy("Depth-First Search")
class DFSStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        start_time = time.time()
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal or not snapshot.apples:
            self.last_metrics = {"expanded": 0, "generated": 0, "evaluated": 0, "path_len": 0, "cost": 0, "waktu_ms": (time.time() - start_time) * 1000}
            return snake.direction

        #inisialisasi variabel
        head_x, head_y = snake.body[0]
        movement = []
        stack = []
        stack.append((head_x, head_y, movement))
        visited = []
        visited.append((head_x, head_y))

        expanded = 0
        generated = 0
        found_movement = None

        #hanya bisa jalan bila ada yang di stack
        while len(stack)>0:
            #cek stack terakhir
            head_x, head_y, movement = stack.pop()
            if len(movement) > 0:
                expanded += 1

            #kalau kepala = apel
            if (head_x, head_y) in snapshot.apples:
                found_movement = movement
                break

            #jalan. +posisi baru --> stack
            for direction in Direction:
                if len(movement) == 0 and direction not in legal:
                    continue
                dx, dy = direction.vector
                new_x = head_x + dx
                new_y = head_y + dy
                if 0 <= new_x < snapshot.columns and 0 <= new_y < snapshot.rows:
                    generated += 1
                    if (new_x, new_y) not in visited:
                        visited.append((new_x, new_y))
                        new_movement = movement + [direction]
                        stack.append((new_x, new_y, new_movement))

        path_length = len(found_movement) if found_movement is not None else 0
        final_cost = float(path_length)

        waktu_ms = (time.time() - start_time) * 1000
        self.last_metrics = {
            "expanded": expanded,
            "generated": generated,
            "evaluated": expanded,
            "path_len": path_length,
            "cost": final_cost,
            "waktu_ms": waktu_ms
        }

        if found_movement:
            return found_movement[0]
        return snake.direction


@register_strategy("Bidirectional Search")
class BidirectionalStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        start_time = time.time()
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal or not snapshot.apples:
            self.last_metrics = {"expanded": 0, "generated": 0, "evaluated": 0, "path_len": 0, "cost": 0, "waktu_ms": (time.time() - start_time) * 1000}
            return snake.direction

        head_x, head_y = snake.body[0]
        apple_x, apple_y = snapshot.apples[0]
        movement = []
        queue_snake = []
        queue_snake.append((head_x, head_y, movement))
        queue_apple = []
        queue_apple.append((apple_x, apple_y))
        visited_snake = []
        visited_snake.append((head_x, head_y))
        visited_apple = []
        visited_apple.append((apple_x, apple_y))
        apple_depth = {(apple_x, apple_y): 0}  # jarak tiap node ke apel

        expanded = 0
        generated = 0
        target_found = False
        first_step = None
        path_length = 0

        #harus ada posisi snake dan apple di queue
        while len(queue_snake)>0 and len(queue_apple)>0:
            #cek queue snake[0]
            head_x, head_y, movement = queue_snake.pop(0)
            if len(movement) > 0:
                expanded += 1

            #kalau kepala = apple
            if (head_x, head_y) in visited_apple:
                target_found = True
                path_length = len(movement) + apple_depth[(head_x, head_y)]
                if len(movement) > 0:
                    first_step = movement[0]
                break

            #jalan. +posisi baru snake --> queue snake
            for direction in Direction:
                if len(movement) == 0 and direction not in legal:
                    continue
                dx, dy = direction.vector
                new_x = head_x + dx
                new_y = head_y + dy
                if (0 <= new_x < snapshot.columns and 0 <= new_y < snapshot.rows):
                    generated += 1
                    if (new_x, new_y) not in visited_snake:
                        visited_snake.append((new_x, new_y))
                        new_movement = movement + [direction]
                        queue_snake.append((new_x, new_y, new_movement))

            #cek queue apple[0]
            apple_x, apple_y = queue_apple.pop(0)
            if apple_depth[(apple_x, apple_y)] > 0:
                expanded += 1

            #kalau apel = kepala
            if (apple_x, apple_y) in visited_snake:
                for snake_x, snake_y, snake_movement in queue_snake:
                    if (snake_x, snake_y) == (apple_x, apple_y):
                        if len(snake_movement) > 0:
                            target_found = True
                            first_step = snake_movement[0]
                            path_length = len(snake_movement) + apple_depth[(apple_x, apple_y)]
                            break
                if target_found:
                    break
                if (apple_x, apple_y) == (head_x, head_y):
                    target_found = True
                    path_length = apple_depth[(apple_x, apple_y)]
                    break

            #+posisi baru pencarian apple --> queue apple
            for direction in Direction:
                dx, dy = direction.vector
                new_x = apple_x + dx
                new_y = apple_y + dy
                if 0 <= new_x < snapshot.columns and 0 <= new_y < snapshot.rows:
                    generated += 1
                    if (new_x, new_y) not in visited_apple:
                        visited_apple.append((new_x, new_y))
                        apple_depth[(new_x, new_y)] = apple_depth[(apple_x, apple_y)] + 1
                        queue_apple.append((new_x, new_y))

        final_cost = float(path_length) if target_found else 0.0

        waktu_ms = (time.time() - start_time) * 1000
        self.last_metrics = {
            "expanded": expanded,
            "generated": generated,
            "evaluated": expanded,
            "path_len": path_length,
            "cost": final_cost,
            "waktu_ms": waktu_ms
        }

        if first_step:
            return first_step
        return snake.direction

print("aku mau coba push ke github")
print("mau coba lagi")
    
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
