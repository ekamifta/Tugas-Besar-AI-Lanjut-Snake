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


# Validasi Strategi yang tersedia per mode
SINGLE_PLAYER_STRATEGIES: list[str] = [
    "Depth-First Search",
    "Breadth-First Search",
    "UCS",
    "Greedy",
    "A*",
    "Bidirectional Search",
]

MULTIPLAYER_STRATEGIES: list[str] = [
    "Minimax",
    "Alpha-Beta",
]


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

        start_time = time.perf_counter()

        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)

        # Tidak ada gerakan legal atau tidak ada apel
        if not legal or not snapshot.apples:
            self.last_metrics = {
                "snake_id": snake_id,
                "expanded": 0,
                "generated": 0,
                "evaluated": 0,
                "path_len": 0,
                "cost": 0,
                "waktu_ms": (time.perf_counter() - start_time) * 1000,
            }
            return snake.direction

        start = snake.body[0]
        apples = set(snapshot.apples)

        # Seluruh badan ular menjadi obstacle statis
        obstacles = {
            part
            for s in snapshot.snakes
            for part in s.body
        }

        # Frontier (Agenda): (biaya kumulatif, posisi)
        agenda = [(0, start)]

        # Biaya terbaik yang diketahui untuk setiap posisi
        best = {start: 0}

        # Parent untuk merekonstruksi jalur
        parent = {}

        # Set untuk melacak node yang sudah di-expand (opsional untuk rekam jejak)
        closed_set = set()

        target = None
        expanded = 0
        generated = 0  

        while agenda:
            # Ambil state dengan biaya terkecil dari list manual
            min_index = 0
            for i in range(1, len(agenda)):
                if agenda[i][0] < agenda[min_index][0]:
                    min_index = i

            cost, pos = agenda.pop(min_index)

            # Jika posisi sudah pernah diexpand dengan biaya lebih baik atau sama, lewati
            if pos in closed_set and cost > best.get(pos, float('inf')):
                continue

            # Goal test
            if pos in apples:
                target = pos
                break

            # Initial state tidak dihitung sebagai expanded
            if pos != start and pos not in closed_set:
                expanded += 1
                closed_set.add(pos)

            x, y = pos

            for direction in Direction:
                dx, dy = direction.vector
                nxt = (x + dx, y + dy)

                # Periksa batas papan
                if not (
                    0 <= nxt[0] < snapshot.columns
                    and 0 <= nxt[1] < snapshot.rows
                ):
                    continue

                # Periksa obstacle (tubuh ular)
                if nxt in obstacles:
                    continue
                
                generated += 1
                new_cost = cost + 1

                # Perbarui hanya jika belum ada atau ditemukan biaya yang lebih baik
                if nxt not in best or new_cost < best[nxt]:
                    best[nxt] = new_cost
                    parent[nxt] = (pos, direction)
                    agenda.append((new_cost, nxt))

        # Rekonstruksi jalur solusi
        first_step = None
        # path_len = 0
        # final_cost = 0

        if target is not None:
            # final_cost = best[target]
            cur = target

            while cur in parent:
                prev_pos, move_direction = parent[cur]
                first_step = move_direction
                cur = prev_pos
                # path_len += 1
        
        # Langkah dihitung hanya jika benar-benar dijalankan
        executed = first_step is not None and first_step in legal

        # Simpan metrik
        self.last_metrics = {
            "snake_id": snake_id,
            "expanded": expanded,
            "generated": generated,
            "evaluated": expanded,
            # "path_len": path_len if target is not None else 0,
            # "cost": final_cost,
            "path_len": 1 if executed else 0,
            "cost": 1 if executed else 0, 
            "waktu_ms": (time.perf_counter() - start_time) * 1000,
        }

        # Jalankan langkah pertama jika valid
        # if first_step is not None and first_step in legal:
        if executed:
            return first_step

        # Fallback jika jalur tidak ditemukan
        return rng.choice(legal)

@register_strategy("Minimax")
class MinimaxStrategy(MoveStrategy):
    DEPTH_LIMIT = 6
    SCORE_W = 1000     # ASUMSI : harus > DIST_W * (rows + cols), supaya makan apel selalu menang
    DIST_W = 1
    WIN = 100000       # ASUMSI : harus > SCORE_W * jumlah apel

    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        start_time = time.perf_counter()

        depth_limit = self.DEPTH_LIMIT

        # Metrik diinisialisasi lengkap agar struktur konsisten
        # pada setiap jalur keluar fungsi.
        expanded = 0
        generated = 0
        evaluated = 0

        def simpan_metrics(first_step=None, cost=0):
            executed = first_step is not None
            self.last_metrics = {
                "algorithm": "Minimax",
                "snake_id": snake_id,
                "expanded": expanded,
                "generated": generated,
                "evaluated": evaluated,
                "pruned_branches": 0,
                "search_depth": depth_limit,
                # "path_len": 1 if first_step is not None else 0,
                # "cost": cost,
                "path_len": 1 if executed else 0,
                "cost": 1 if executed else 0, 
                "waktu_ms": (
                    time.perf_counter() - start_time) * 1000,
            }

        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)

        if not legal:
            simpan_metrics()
            return snake.direction

        opponents = [
            s for s in snapshot.snakes
            if s.snake_id != snake_id
        ]

        # Implementasi ini hanya mendukung dua ular.
        if len(opponents) != 1:
            first_step = rng.choice(legal)
            simpan_metrics(first_step)
            return first_step

        max_id = snake_id
        min_id = opponents[0].snake_id

        initial_state = {
            "bodies": {
                s.snake_id: tuple(s.body)
                for s in snapshot.snakes
            },
            "directions": {
                s.snake_id: s.direction
                for s in snapshot.snakes
            },
            "scores": {
                s.snake_id: s.score
                for s in snapshot.snakes
            },
            "apples": frozenset(snapshot.apples),
            "terminal": False,
            "winner": None,
        }

        def terminal_value(state, depth):
            diff = state["scores"][max_id] - state["scores"][min_id]

            if state["winner"] == max_id:
                return self.WIN - depth + diff

            if state["winner"] == min_id:
                return -self.WIN + depth + diff

            return diff

        #Jarak Manhattan ke apel terdekat
        def nearest(head, apples):
            return min(
                abs(head[0] - ax) + abs(head[1] - ay)
                for ax, ay in apples
            )

        # Heuristik / Fungsi Evaluasi
        def evaluate(state):
            nonlocal evaluated
            evaluated += 1

            max_score = state["scores"][max_id]
            min_score = state["scores"][min_id]
            score_diff = max_score - min_score

            apples = state["apples"]

            if not apples:
                return self.SCORE_W * score_diff

            #Eval = SCORE_W*(skor_AI - skor_lawan) + DIST_W*(dLawan - dAI)
            d_max = nearest(state["bodies"][max_id][0], apples)
            d_min = nearest(state["bodies"][min_id][0], apples)

            return (
                self.SCORE_W * score_diff
                + self.DIST_W * (d_min - d_max)
            )

        def get_successors(state, mover_id):
            body = state["bodies"][mover_id]
            direction_now = state["directions"][mover_id]
            head = body[0]
            results = []

            other_id = (
                min_id if mover_id == max_id else max_id
            )

            for direction in Direction:
                if (
                    len(body) > 1
                    and direction is direction_now.opposite
                ):
                    continue

                dx, dy = direction.vector
                new_head = (head[0] + dx, head[1] + dy)
                x, y = new_head

                # Tabrakan dengan dinding.
                if not (
                    0 <= x < snapshot.columns
                    and 0 <= y < snapshot.rows
                ):
                    continue

                apples = state["apples"]
                growing = new_head in apples

                # Ekor lama boleh dimasuki jika ular tidak tumbuh.
                own_occupied = body if growing else body[:-1]

                if new_head in own_occupied:
                    continue

                # Tabrakan dengan ular lawan.
                if new_head in state["bodies"][other_id]:
                    continue

                new_state = {
                    "bodies": dict(state["bodies"]),
                    "directions": dict(state["directions"]),
                    "scores": dict(state["scores"]),
                    "apples": apples,
                    "terminal": False,
                    "winner": None,
                }

                new_body = (new_head,) + body

                if not growing:
                    new_body = new_body[:-1]

                new_state["bodies"][mover_id] = new_body
                new_state["directions"][mover_id] = direction

                if growing:
                    new_state["scores"][mover_id] += 1
                    new_state["apples"] = frozenset(
                        apple for apple in apples
                        if apple != new_head
                    )

                    # Engine mengakhiri permainan ketika semua
                    # apel habis. Tentukan pemenang dari skor.
                    if not new_state["apples"]:
                        new_state["terminal"] = True

                        max_score = new_state["scores"][max_id]
                        min_score = new_state["scores"][min_id]

                        if max_score > min_score:
                            new_state["winner"] = max_id
                        elif min_score > max_score:
                            new_state["winner"] = min_id

                results.append((direction, new_state))

            return results

        def minimax(state, depth, is_max):
            nonlocal expanded, generated, evaluated

            if state["terminal"]:
                evaluated += 1
                return terminal_value(state, depth)

            if depth >= depth_limit:
                return evaluate(state)

            mover_id = max_id if is_max else min_id
            children = get_successors(state, mover_id)

            expanded += 1
            generated += len(children)

            # Asumsi pencarian: tidak ada langkah legal berarti kalah.
            # Pastikan asumsi ini konsisten dengan aturan game runner.
            if not children:
                evaluated += 1
                return (
                    (-self.WIN + depth) if is_max
                    else (self.WIN - depth)
                )

            if is_max:
                best_value = float("-inf")

                for _, child_state in children:
                    value = minimax(
                        child_state,
                        depth + 1,
                        False,
                    )
                    best_value = max(best_value, value)

                return best_value

            best_value = float("inf")

            for _, child_state in children:
                value = minimax(
                    child_state,
                    depth + 1,
                    True,
                )
                best_value = min(best_value, value)

            return best_value

        # Root adalah giliran MAX.
        root_children = get_successors(initial_state, max_id)

        #expanded += 1
        generated += len(root_children)

        best_value = float("-inf")
        best_moves = []

        for direction, child_state in root_children:
            value = minimax(
                child_state,
                depth=1,
                is_max=False,
            )

            if value > best_value:
                best_value = value
                best_moves = [direction]
            elif value == best_value:
                best_moves.append(direction)

        first_step = rng.choice(best_moves) if best_moves else None

        # Jika simulasi tidak menghasilkan successor yang valid,
        # gunakan langkah legal dari snapshot sebagai fallback.
        if first_step is None or first_step not in legal:
            first_step = rng.choice(legal)

        simpan_metrics(first_step, best_value if best_moves else 0)
        return first_step


@register_strategy("A*")
class AStarStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random) -> Direction:
        start_time=time.time()
        legal_moves = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal_moves or not snapshot.apples:
            self.last_metrics = {                    
                "snake_id": snake_id,
                "expanded": 0, "generated": 0, "evaluated": 0,
                "path_len": 0, "cost": 0, "success":0,
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
        target = min(snapshot.apples, key=lambda apple: (manhattan(snake.body[0], apple),apple))

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

            state = head
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
                if new_head in visited:
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
            "snake_id": snake_id,
            "strategy": "A*",
            "expanded": expanded,
            "generated": generated,
            "evaluated": expanded,
            "path_len": path_length,
            "cost": final_cost,
            "success": 1 if first_step else 0,
            "waktu_ms": waktu_ms,
        }
        if first_step:
            return first_step

        blocked = obstacles | set(snake.body[:-1])

        def free_space(start):
            seen = {start}
            stack = [start]
            while stack:
                cx, cy = stack.pop()
                for ddx, ddy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    nxt = (cx + ddx, cy + ddy)
                    if nxt in seen or nxt in blocked:
                        continue
                    if not (0 <= nxt[0] < snapshot.columns and 0 <= nxt[1] < snapshot.rows):
                        continue
                    seen.add(nxt)
                    stack.append(nxt)
            return len(seen)

        def skor(d):
            nh = (snake.body[0][0] + d.vector[0], snake.body[0][1] + d.vector[1])
            return (-free_space(nh), manhattan(nh, target))

        return min(legal_moves, key=skor)
        
@register_strategy("Alpha-Beta")
class AlphaBetaStrategy(MoveStrategy):
    DEPTH = 6 
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        start_time = time.perf_counter()
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

        stat={"generated":0,"evaluated":0,"pruned":0}
        def simulate(body, direction, apples):
            stat["generated"]+=1
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
            stat["evaluated"]+=1
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
                        stat["pruned"]+=1
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
                        stat["pruned"]+=1
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
        
        self.last_metrics = {
            "snake_id": snake_id,
            "algorithm": "Alpha-Beta",
            "depth": self.DEPTH,
            "generated": stat["generated"],
            "evaluated": stat["evaluated"], 
            "pruned": stat["pruned"],
            "waktu_ms": (time.perf_counter() - start_time) * 1000,
        }
        return rng.choice(best_moves)


@register_strategy("Breadth-First Search")
class BFSStrategy(MoveStrategy):
    def choose_move(
        self, snapshot: GameSnapshot, snake_id: str, rng: Random
    ) -> Direction:
        start_time = time.perf_counter()
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal or not snapshot.apples:
            self.last_metrics = {"snake_id": snake_id, "expanded": 0, "generated": 0, "evaluated": 0, "path_len": 0, "cost": 0, "waktu_ms": (time.perf_counter() - start_time) * 1000}
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

        waktu_ms = (time.perf_counter() - start_time) * 1000
        self.last_metrics = {
            "snake_id": snake_id,
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
        start_time = time.perf_counter()
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal or not snapshot.apples:
            self.last_metrics = {"snake_id": snake_id, "expanded": 0, "generated": 0, "evaluated": 0, "path_len": 0, "cost": 0, "waktu_ms": (time.perf_counter() - start_time) * 1000}
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

        waktu_ms = (time.perf_counter() - start_time) * 1000
        self.last_metrics = {
            "snake_id": snake_id,
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
        start_time = time.perf_counter()
        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)
        if not legal or not snapshot.apples:
            self.last_metrics = {"snake_id": snake_id, "expanded": 0, "generated": 0, "evaluated": 0, "path_len": 0, "cost": 0, "waktu_ms": (time.perf_counter() - start_time) * 1000}
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

        waktu_ms = (time.perf_counter() - start_time) * 1000
        self.last_metrics = {
            "snake_id": snake_id,
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
