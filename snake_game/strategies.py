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
@register_strategy("A*")
class AStarStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random) -> Direction:
        start_time=time.time()
        legal_moves = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal_moves or not snapshot.apples:
            self.last_metrics = {                    
                "expanded": 0, "generated": 0, "evaluated": 0,
                "path_len": 0, "cost": 0,
                "waktu_ms": (time.time() - start_time) * 1000,
        }
        return legal_moves[0] if legal_moves else snake.direction

        def manhattan(a, b):
            return abs(a[0] - b[0]) + abs(a[1] - b[1])

        def simulate(body, direction):
            dx, dy = direction.vector
            new_head = (body[0][0] + dx, body[0][1] + dy)
            return new_head, (new_head,) + body[:-1]

        def legal_from(body, last_direction):
            options = []
            for direction in Direction:
                if len(body) > 1 and direction is last_direction.opposite:
                    continue  # ga boleh membalik badan
                new_head, _ = simulate(body, direction)
                x, y = new_head
                if not (0 <= x < snapshot.columns and 0 <= y < snapshot.rows):
                    continue  # nabrak dinding
                if new_head in body[:-1]:
                    continue  # nabrak badan sendiri (ekor akan bergerak menjauh)
                if new_head in obstacles:
                    continue  # nabrak lawan
                options.append(direction)
            return options

        obstacles = frozenset(
            part
            for other in snapshot.snakes
            if other.snake_id != snake_id
            for part in other.body
        )
        target = min(snapshot.apples, key=lambda apple: manhattan(snake.body[0], apple))

        counter = 0
        start_head = snake.body[0]
        h_start = manhattan(start_head, target)
        frontier = [(h_start, h_start, counter, start_head, snake.body, ())]
        visited = set()
        expanded = 0            
        generated = 1
        first_step = None
        path_length = 0
        final_cost = 0.0


        while frontier:
            best_index = 0
            for index in range(1, len(frontier)):
                if frontier[index] < frontier[best_index]:
                    best_index = index
            f, h, _, head, body, path = frontier.pop(best_index)

            state = (head, body)
            expanded += 1
            if state in visited:
                continue
            visited.add(state) 
            if len(visited) > 5000:
                break  

            if head == target:
                final_cost = f - h             
                path_length = len(path)
                first_step = path[0] if path else None
                break

            current_direction = path[-1] if path else snake.direction
            g = f - h 
            for direction in legal_from(body, current_direction):
                new_head, new_body = simulate(body, direction)
                if (new_head, new_body) in visited:
                    continue
                counter += 1
                generated +=1
                g_new = g + 1                         
                h_new = manhattan(new_head, target)     
                f_new = g_new + h_new                
                frontier.append(
                    (f_new, h_new, counter, new_head, new_body, path + (direction,))
                )
        waktu_ms = (time.time() - start_time) * 1000
        self.last_metrics = {
            "expanded": expanded,
            "generated": generated,
            "evaluated": expanded,
            "path_len": path_length if first_step else 1,
            "cost": final_cost,
            "waktu_ms": waktu_ms,
            }
        if first_step:
            return first_step
        return rng.choice(legal_moves)
       # return legal_moves[0]
        
@register_strategy("Alpha-Beta")
class AlphaBetaStrategy(MoveStrategy):
    DEPTH = 6 
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        legal_moves = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal_moves:
            return snake.direction

        opponent = None
        for other in snapshot.snakes:
            if other.snake_id != snake_id:
                opponent = other
                break

        # Tanpa lawan (mode Single Player): Alpha-Beta tidak berlaku (tidak
        # ada pihak yang meminimalkan), jatuh ke langkah paling dekat apel.
        if opponent is None:
            if not snapshot.apples:
                return legal_moves[0]
            head = snake.body[0]

            def apple_distance(direction):
                dx, dy = direction.vector
                nx, ny = head[0] + dx, head[1] + dy
                return min(abs(nx - ax) + abs(ny - ay) for ax, ay in snapshot.apples)

            best = min(apple_distance(direction) for direction in legal_moves)
            return rng.choice([d for d in legal_moves if apple_distance(d) == best])

     
        def simulate(body, direction, apples):
            dx, dy = direction.vector
            new_head = (body[0][0] + dx, body[0][1] + dy)
            if new_head in apples:
                new_body = (new_head,) + body
                new_apples = tuple(apple for apple in apples if apple != new_head)
            else:
                new_body = (new_head,) + body[:-1]
                new_apples = apples
            return new_body, new_apples

        def legal_from(body, last_direction, other_body):
            options = []
            for direction in Direction:
                if len(body) > 1 and direction is last_direction.opposite:
                    continue  # tidak boleh membalik badan
                dx, dy = direction.vector
                new_head = (body[0][0] + dx, body[0][1] + dy)
                x, y = new_head
                if not (0 <= x < snapshot.columns and 0 <= y < snapshot.rows):
                    continue  # menabrak dinding
                if new_head in body[:-1]:
                    continue  # menabrak badan sendiri (ekor akan bergerak menjauh)
                if new_head in other_body:
                    continue  # menabrak ular lawan
                options.append(direction)
            return options

        def evaluate(my_body, opp_body, apples):
            score = (len(my_body) - len(opp_body)) * 100
            if apples:
                head = my_body[0]
                score -= min(abs(head[0] - ax) + abs(head[1] - ay) for ax, ay in apples)
            return score

        def alphabeta(my_body, my_dir, opp_body, opp_dir, apples, depth, my_turn, alpha, beta):
            if my_turn:
                options = legal_from(my_body, my_dir, opp_body)
                if not options:
                    return -10_000  # kita terjebak -> kalah, seburuk mungkin
                if depth == 0:
                    return evaluate(my_body, opp_body, apples)
                value = float("-inf")
                for direction in options:
                    new_body, new_apples = simulate(my_body, direction, apples)
                    child = alphabeta(
                        new_body, direction, opp_body, opp_dir, new_apples,
                        depth - 1, False, alpha, beta,
                    )
                    if child > value:
                        value = child
                    if value > alpha:
                        alpha = value
                    if alpha >= beta:
                        break  # pemangkasan beta: lawan di atas tak akan pernah memilih cabang ini
                return value
            else:
                options = legal_from(opp_body, opp_dir, my_body)
                if not options:
                    return 10_000  # lawan terjebak -> kita menang, sebaik mungkin
                if depth == 0:
                    return evaluate(my_body, opp_body, apples)
                value = float("inf")
                for direction in options:
                    new_body, new_apples = simulate(opp_body, direction, apples)
                    child = alphabeta(
                        my_body, my_dir, new_body, direction, new_apples,
                        depth - 1, True, alpha, beta,
                    )
                    if child < value:
                        value = child
                    if value < beta:
                        beta = value
                    if alpha >= beta:
                        break  # pemangkasan alpha: kita di atas tak akan pernah memilih cabang ini
                return value

        best_score = float("-inf")
        best_moves = []
        alpha = float("-inf")
        beta = float("inf")
        for direction in legal_moves:
            new_body, new_apples = simulate(snake.body, direction, snapshot.apples)
            value = alphabeta(
                new_body, direction, opponent.body, opponent.direction,
                new_apples, self.DEPTH - 1, False, alpha, beta,
            )
            if value > best_score:
                best_score = value
                best_moves = [direction]
            elif value == best_score:
                best_moves.append(direction)
            if best_score > alpha:
                alpha = best_score

        return rng.choice(best_moves)
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
