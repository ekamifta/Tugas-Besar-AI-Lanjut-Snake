import datetime

# Modul sederhana untuk mencetak ringkasan game & menyimpannya ke file results_Metrics.txt

def cetak_metrics_game(config, engine, metrics_history=None):
    if not engine:
        return

    # Ambil tanggal dan waktu saat match berakhir
    waktu_selesai = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    # Susun isi laporan teks
    laporan = []
    laporan.append("\n--- LAPORAN METRICS GAME ---")
    laporan.append(f"Waktu Selesai : {waktu_selesai}")
    
    # 1. Konfigurasi Game (Sesuai Tampilan UI)
    laporan.append(f"Mode Game     : {config.mode.value}")
    laporan.append(f"Ukuran Grid   : {config.rows} x {config.columns}")
    laporan.append(f"Jumlah Apel   : {config.apple_count}")
    laporan.append(f"Move Limit    : {config.move_limit}")
    laporan.append(f"Kecepatan     : {config.ai_speed} moves/s")
    laporan.append(f"Strategi      : {config.strategy_name}")
    if config.mode.value == "AI vs AI":
        laporan.append(f"Strategi 2    : {config.secondary_strategy_name}")
    
    # 2. Hasil Pertandingan
    laporan.append("\n--- HASIL MATCH ---")
    laporan.append(f"Alasan Selesai: {engine.finish_reason or 'Finished'}")
    total_langkah_ai = len(metrics_history) if metrics_history else engine.rounds_completed
    for snake_id, snake in engine.snakes.items():
        nama_ular = engine.display_name(snake_id)
        laporan.append(f"Skor {nama_ular}   : {snake.score} (Langkah: {total_langkah_ai})")

    # 3. Statistik Performa Algoritma AI
    laporan.append("\n--- PERFORMA ALGORITMA AI ---")
    if metrics_history:

        if config.mode.value != "AI vs AI":
            # ── SINGLE PLAYER METRICS ──────────────────────────────────────────
            total_expanded  = sum(m.get("expanded",  0) for m in metrics_history)
            total_generated = sum(m.get("generated", 0) for m in metrics_history)
            total_waktu     = sum(m.get("waktu_ms",  0) for m in metrics_history)
            total_path_len  = sum(m.get("path_len",  0) for m in metrics_history)
            total_cost      = sum(m.get("cost",      0) for m in metrics_history)

            # Food collected = score snake AI (setiap apel dimakan menambah score)
            ai_snake = next((s for sid, s in engine.snakes.items() if sid != "human"), None)
            food_collected = ai_snake.score if ai_snake else 0

            # Success rate = food collected / apple_count * 100%
            success_rate = (food_collected / config.apple_count * 100) if config.apple_count > 0 else 0.0

            laporan.append(f"Number of Food Items Collected : {food_collected}")
            laporan.append(f"Success Rate                   : {success_rate:.1f}%")
            laporan.append(f"Number of States Expanded      : {total_expanded}")
            laporan.append(f"Number of States Generated     : {total_generated}")
            laporan.append(f"Total Path Length              : {total_path_len}")
            laporan.append(f"Total Path Cost                : {total_cost:.2f}")
            laporan.append(f"Total Execution Time           : {total_waktu:.2f} ms")

        else:
            # ── MULTIPLAYER AI vs AI METRICS ──────────────────────────────────
            # Pisahkan metrics per ular berdasarkan tag "snake_id"
            ai1_metrics = [m for m in metrics_history if m.get("snake_id") == "human"]
            ai2_metrics = [m for m in metrics_history if m.get("snake_id") == "ai"]

            # Fallback: jika snake_id tidak di-tag, semua data dianggap AI 1
            if not ai1_metrics and not ai2_metrics:
                ai1_metrics = metrics_history
                ai2_metrics = []

            def _sum(lst, key):
                return sum(m.get(key, 0) for m in lst)

            for label, mlist, snake_id, engine_id, strategy_name in [
                ("AI 1", ai1_metrics, "A1", "human", config.strategy_name),
                ("AI 2", ai2_metrics, "A2", "ai", config.secondary_strategy_name),
            ]:
                snake  = engine.snakes.get(engine_id)
                score  = snake.score if snake else 0
                winner = engine.winner_id

                if winner == engine_id:
                    win_result = "Win"
                elif engine.is_draw:
                    win_result = "Draw"
                else:
                    win_result = "Lose"

                generated = _sum(mlist, "generated")
                evaluated = _sum(mlist, "evaluated")
                pruned    = _sum(mlist, "pruned")
                waktu     = _sum(mlist, "waktu_ms")
                depth     = _sum(mlist, "search_depth") 

                laporan.append(f"\n  [{label}]")
                laporan.append(f"  Snake ID                   : {snake_id}")
                laporan.append(f"  Algorithm                  : {strategy_name}")
                laporan.append(f"  Win/Lose/Draw              : {win_result}")
                laporan.append(f"  Final Score                : {snake.score}")
                laporan.append(f"  Number of States Generated : {generated}")
                laporan.append(f"  Number of States Evaluated : {evaluated}")
                laporan.append(f"  Number of Pruned Branches  : {pruned}")
                laporan.append(f"  Execution Time             : {waktu:.2f} ms")
    laporan.append("-----------------------------\n")

    isi_teks = "\n".join(laporan)

    # 1. Cetak ke terminal/layar
    print(isi_teks)

    # 2. Simpan & tambahkan ke file results_Metrics.txt (mode 'a' agar history tidak terhapus)
    with open("results_Metrics.txt", "a", encoding="utf-8") as f:
        f.write(isi_teks + "\n")
