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

        start_time = time.perf_counter()

        legal = snapshot.legal_moves_for(snake_id)
        snake = snapshot.snake(snake_id)

        # Tidak ada gerakan legal atau tidak ada apel
        if not legal or not snapshot.apples:
            self.last_metrics = {
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

        # Frontier Agenda): (biaya kumulatif, posisi)
        agenda = [(0, start)]

        # Biaya terbaik yang diketahui untuk setiap posisi
        best = {start: 0}

        # Parent untuk merekonstruksi jalur
        parent = {}

        target = None
        expanded = 0
        generated = 0  # Root tidak dihitung

        while agenda:
            # Ambil state dengan biaya terkecil
            min_index = 0
            for i in range(1, len(agenda)):
                if agenda[i][0] < agenda[min_index][0]:
                    min_index = i

            cost, pos = agenda.pop(min_index)

            # Abaikan entri yang sudah tidak optimal
            if cost > best[pos]:
                continue

            # Goal test: goal tidak dihitung sebagai expanded
            if pos in apples:
                target = pos
                break

            # Initial state tidak dihitung sebagai expanded
            if pos != start:
                expanded += 1

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

                # Periksa obstacle
                if nxt in obstacles:
                    continue

                # Semua successor legal dihitung, termasuk posisi yang sudah ditemukan
                generated += 1

                new_cost = cost + 1

                # Perbarui hanya jika biaya lebih baik
                if nxt not in best or new_cost < best[nxt]:
                    best[nxt] = new_cost
                    parent[nxt] = (pos, direction)
                    agenda.append((new_cost, nxt))

        # Rekonstruksi jalur solusi
        first_step = None
        path_len = 0
        final_cost = 0

        if target is not None:
            final_cost = best[target]
            cur = target

            while cur in parent:
                prev_pos, move_direction = parent[cur]
                first_step = move_direction
                cur = prev_pos
                path_len += 1

        # Simpan metrik
        self.last_metrics = {
            "expanded": expanded,
            "generated": generated,
            "evaluated": expanded,
            "path_len": path_len if target is not None else 0,
            "cost": final_cost,
            "waktu_ms": (time.perf_counter() - start_time) * 1000,
        }

        # Jalankan langkah pertama jika valid
        if first_step is not None and first_step in legal:
            return first_step

        # Fallback jika jalur tidak ditemukan
        return rng.choice(legal)

@register_strategy("Minimax")
class MinimaxStrategy(MoveStrategy):
    DEPTH_LIMIT = 3
    SCORE_W = 1000     # ASUMSI : harus > DIST_W * (rows + cols), supaya makan apel selalu menang
    DIST_W = 1
    WIN = 100000       # ASUMSI : harus > SCORE_W * jumlah apel

    def choose_move(self, snapshot, snake_id, rng):
        start_time = time.perf_counter()

        depth_limit = self.DEPTH_LIMIT

        # Metrik diinisialisasi lengkap agar struktur konsisten
        # pada setiap jalur keluar fungsi.
        expanded = 0
        generated = 0
        evaluated = 0

        def simpan_metrics(first_step=None, cost=0):
            self.last_metrics = {
                "algorithm": "Minimax",
                "snake_id": snake_id,
                "expanded": expanded,
                "generated": generated,
                "evaluated": evaluated,
                "pruned_branches": 0,
                "search_depth": depth_limit,
                "path_len": 1 if first_step is not None else 0,
                "cost": cost,
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
