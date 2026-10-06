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

        laporan.append(f"Total Langkah AI    : {n}")
        laporan.append(f"Rata-rata Expanded  : {round(total_expanded / n, 2)}")
        laporan.append(f"Rata-rata Generated : {round(total_generated / n, 2)}")
        laporan.append(f"Rata-rata Waktu/Move: {round(total_waktu / n, 3)} ms")
    else:
        laporan.append("Belum ada data langkah AI.")

    laporan.append("-----------------------------\n")

    isi_teks = "\n".join(laporan)

    # 1. Cetak ke terminal/layar
    print(isi_teks)

    # 2. Simpan & tambahkan ke file results_Metrics.txt (mode 'a' agar history tidak terhapus)
    with open("results_Metrics.txt", "a", encoding="utf-8") as f:
        f.write(isi_teks + "\n")
