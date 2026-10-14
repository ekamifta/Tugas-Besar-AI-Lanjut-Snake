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
        n = total_langkah_ai
        total_expanded = sum(m.get("expanded", 0) for m in metrics_history)
        total_generated = sum(m.get("generated", 0) for m in metrics_history)
        total_waktu = sum(m.get("waktu_ms", 0) for m in metrics_history)

        sukses = [m for m in metrics_history if m.get("success", 0) == 1]
        success_rate = len(sukses) / n * 100
        avg_path_len = sum(m["path_len"] for m in sukses) / len(sukses) if sukses else 0
        avg_cost = sum(m["cost"] for m in sukses) / len(sukses) if sukses else 0

        laporan.append(f"Total Langkah AI    : {n}")
        laporan.append(f"Rata-rata Expanded  : {round(total_expanded / n, 2)}")
        laporan.append(f"Rata-rata Generated : {round(total_generated / n, 2)}")
        laporan.append(f"Rata-rata Waktu/Move: {round(total_waktu / n, 3)} ms")

        ab = [m for m in metrics_history if m.get("algoritma") == "Alpha-Beta"]
        if ab:
            na = len(ab)
            ab_gen = sum(m.get("generated", 0) for m in ab)
            ab_eval = sum(m.get("evaluated", 0) for m in ab)
            ab_prun = sum(m.get("pruned", 0) for m in ab)
            ab_waktu = sum(m.get("waktu_ms", 0) for m in ab)
            laporan.append("\n--- METRICS ALPHA-BETA ---")
            laporan.append("Algoritma           : Alpha-Beta")
            laporan.append(f"Depth               : {ab[-1].get('depth', '-')}")
            laporan.append(f"Total Langkah       : {na}")
            laporan.append(f"States Generated    : {ab_gen} (rata-rata/move: {round(ab_gen / na, 2)})")
            laporan.append(f"States Evaluated    : {ab_eval} (rata-rata/move: {round(ab_eval / na, 2)})")
            laporan.append(f"Pruned Branches     : {ab_prun} (rata-rata/move: {round(ab_prun / na, 2)})")
            laporan.append(f"Exec Time / Move    : {round(ab_waktu / na, 3)} ms")

        laporan.append(f"Success Rate        : {round(success_rate, 2)} %")
        laporan.append(f"Rata-rata Path Length: {round(avg_path_len, 2)}")
        laporan.append(f"Rata-rata Path Cost  : {round(avg_cost, 2)}")

    else:
        laporan.append("Belum ada data langkah AI.")

    rekap = cetak_metrics_game.__dict__.setdefault("rekap", {})
    daftar_ular = list(engine.snakes.items())
    nama_strategi = [config.strategy_name, getattr(config, "secondary_strategy_name", None)]
    skor_semua = [s.score for _, s in daftar_ular]
    skor_max = max(skor_semua)
    for i, (_, s) in enumerate(daftar_ular):
        if i < len(nama_strategi) and nama_strategi[i]:
            menang = 1 if s.score == skor_max and skor_semua.count(skor_max) == 1 else 0
            r = rekap.setdefault(nama_strategi[i], {"match": 0, "menang": 0, "skor": 0})
            r["match"] += 1
            r["menang"] += menang
            r["skor"] += s.score
    if config.strategy_name in rekap:
        r = rekap[config.strategy_name]
        laporan.append(f"Win Rate ({config.strategy_name}) : {round(r['menang'] / r['match'] * 100, 2)} % dari {r['match']} match")
        laporan.append(f"Avg Score           : {round(r['skor'] / r['match'], 2)}")
    laporan.append("-----------------------------\n")

    isi_teks = "\n".join(laporan)

    # 1. Cetak ke terminal/layar
    print(isi_teks)

    # 2. Simpan & tambahkan ke file results_Metrics.txt (mode 'a' agar history tidak terhapus)
    with open("results_Metrics.txt", "a", encoding="utf-8") as f:
        f.write(isi_teks + "\n")
