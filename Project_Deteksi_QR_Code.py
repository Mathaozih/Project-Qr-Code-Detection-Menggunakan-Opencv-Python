import cv2
from pyzbar import pyzbar
import imutils
import webbrowser
import csv
import os
import winsound  # Untuk bunyi beep di Windows
import tkinter as tk
from tkinter import ttk, font
from PIL import Image, ImageTk

# === Variabel global ===
last_data = None
last_type = None
scanned_data = set()  # Menyimpan data unik yang sudah terbaca
scan_count = 0        # Jumlah total QR/Barcode unik

# === File output ===
TXT_FILE = "hasil_scan.txt"
CSV_FILE = "hasil_scan.csv"

# === Variabel Global GUI ===
root = None
camera_label = None
link_var = None
log_tree = None
camera = None
last_data_displayed = None # Untuk optimasi update link

# --- PALET WARNA BIRU ---
BLUE_BG = "#EAF2FF"      # Background umum
BLUE_LIGHT = "#D4E4FF"   # Untuk frame/panel
BLUE_MEDIUM = "#B4D2FF"  # Untuk header label
BLUE_DARK = "#4A7EE2"    # Untuk item terpilih
BLUE_TEXT = "#001B4D"    # Warna teks gelap
BLUE_ENTRY_BG = "#F5F9FF" # Warna background entry readonly
BLUE_LINK = "#0000AA"    # Warna teks link

# Buat file CSV jika belum ada
if not os.path.exists(CSV_FILE):
    with open(CSV_FILE, mode="w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["No", "Jenis", "Data"])


def save_scan_data(code_type, data):
    """Simpan hasil scan ke file .txt, .csv, dan update GUI log"""
    global scan_count, log_tree
    scan_count += 1

    # Simpan ke .txt
    with open(TXT_FILE, "a", encoding="utf-8") as txt_file:
        txt_file.write(f"{scan_count}. [{code_type}] {data}\n")

    # Simpan ke .csv
    with open(CSV_FILE, "a", newline="", encoding="utf-8") as csv_file:
        writer = csv.writer(csv_file)
        writer.writerow([scan_count, code_type, data])
    
    # --- MODIFIKASI: Update GUI Treeview ---
    if log_tree:
        log_tree.insert("", tk.END, values=(scan_count, code_type, data))
        log_tree.yview_moveto(1) # Auto-scroll ke bawah


def beep_sound():
    """Bunyi beep ketika ada kode baru"""
    try:
        duration = 200  # ms
        freq = 1000   # Hz
        winsound.Beep(freq, duration)
    except Exception as e:
        print(f"Gagal membunyikan beep: {e}")


def detect_codes(frame):
    """Mendeteksi barcode/QR di frame kamera"""
    global last_data, last_type
    codes = pyzbar.decode(frame)

    for code in codes:
        (x, y, w, h) = code.rect
        data = code.data.decode("utf-8")
        code_type = code.type

        # Gambar kotak hijau di sekitar kode
        cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
        text = f"{code_type}: {data}"
        cv2.putText(frame, text, (x, y - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 0, 0), 2)

        # Jika data baru (belum pernah discan)
        if data not in scanned_data:
            scanned_data.add(data)
            last_data = data
            last_type = code_type
            beep_sound()  # Bunyi beep
            save_scan_data(code_type, data)  # Simpan ke file & update GUI
            print(f"[INFO] Data baru terbaca: {data}")

    return frame, codes


def handle_enter_key(event=None):
    """Fungsi untuk menangani penekanan tombol ENTER."""
    global last_data, last_type
    
    if last_data and (last_data.startswith("http://") or last_data.startswith("https://")):
        print(f"[INFO] Membuka tautan: {last_data}")
        webbrowser.open(last_data, new=2)
    elif last_data:
        print(f"[INFO] Jenis: {last_type}")
        print(f"[INFO] Data: {last_data}")
        print("[INFO] Tidak ada URL yang valid untuk dibuka.")
    else:
        print("[INFO] Belum ada data yang terbaca.")


def update_frame():
    """Loop utama untuk mengambil frame kamera dan memperbarui GUI."""
    global camera, camera_label, last_data, last_data_displayed, link_var, root
    
    if not camera.isOpened():
        print("[ERROR] Kamera tidak terbuka, mencoba lagi...")
        root.after(1000, update_frame)
        return

    ret, frame = camera.read()
    if not ret:
        print("[ERROR] Gagal membaca frame dari kamera.")
        root.after(1000, update_frame) # Coba lagi setelah 1 detik
        return

    # Resize frame untuk ditampilkan di GUI (agar tidak terlalu besar)
    frame = imutils.resize(frame, width=800)
    
    # Deteksi kode
    frame_processed, codes = detect_codes(frame)

    # Update "LINK TERDETEKSI" jika ada data baru
    if last_data != last_data_displayed:
        link_var.set(last_data if last_data else "")
        last_data_displayed = last_data

    # Konversi frame OpenCV (BGR) ke format PIL (RGB)
    rgb_frame = cv2.cvtColor(frame_processed, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(rgb_frame)
    
    # Konversi gambar PIL ke format Tkinter
    img_tk = ImageTk.PhotoImage(image=img)

    # Tampilkan gambar di label
    camera_label.config(image=img_tk)
    camera_label.image = img_tk  # Simpan referensi agar tidak di-garbage collect

    # Jadwalkan update frame berikutnya
    root.after(10, update_frame)


def on_closing():
    """Fungsi saat menutup jendela GUI."""
    print("\n=== Program selesai ===")
    print(f"Total data unik terbaca: {len(scanned_data)}")
    print(f"Hasil tersimpan di: {TXT_FILE} dan {CSV_FILE}")
    
    if camera:
        camera.release()
    if root:
        root.destroy()


def main_gui():
    global root, camera_label, link_var, log_tree, camera

    # === Inisialisasi Kamera ===
    print("=== Sistem Pendeteksi Barcode & QR Code (GUI) ===")
    camera = cv2.VideoCapture(0)
    if not camera.isOpened():
        print("[FATAL] Tidak dapat membuka kamera. Pastikan kamera terhubung.")
        # Buat jendela peringatan sederhana
        alert_root = tk.Tk()
        alert_root.withdraw() # Sembunyikan jendela utama
        tk.messagebox.showerror("Kesalahan Kamera", "Tidak dapat membuka kamera. Pastikan kamera terhubung dan tidak digunakan oleh aplikasi lain.")
        alert_root.destroy()
        return
        
    camera.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    print("Kamera berhasil diinisialisasi.")

    # === Setup Jendela Utama ===
    root = tk.Tk()
    root.title("Sistem Pendeteksi Barcode & QR Code")
    root.configure(bg=BLUE_BG) # Warna background

    main_frame = tk.Frame(root, bg=BLUE_BG, padx=20, pady=20)
    main_frame.pack(fill=tk.BOTH, expand=True)

    # === Kolom Kiri (Kamera & Instruksi) ===
    left_frame = tk.Frame(main_frame, bg=BLUE_BG)
    left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 20))

    # Label untuk "KAMERA PENDETEKSI"
    tk.Label(left_frame, text="KAMERA PENDETEKSI", bg=BLUE_MEDIUM, fg=BLUE_TEXT,
              font=("Arial", 14, "bold"), anchor="center", relief="solid", borderwidth=1
              ).pack(fill=tk.X, pady=(0, 5))
    
    # Label untuk Video Feed
    camera_label = tk.Label(left_frame, bg=BLUE_LIGHT, relief="solid", borderwidth=1)
    camera_label.pack(fill=tk.BOTH, expand=True)

    # Instruksi
    font_instruksi = ("Arial", 10, "bold")
    tk.Label(left_frame, text="ENTER untuk membuka link", bg=BLUE_BG, fg=BLUE_TEXT, font=font_instruksi).pack(anchor="w", pady=(10, 0))
    tk.Label(left_frame, text="ESC untuk keluar", bg=BLUE_BG, fg=BLUE_TEXT, font=font_instruksi).pack(anchor="w")

    # === Kolom Kanan (Link & Log) ===
    right_frame = tk.Frame(main_frame, bg=BLUE_BG)
    right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)

    # --- Bagian "LINK TERDETEKSI" ---
    tk.Label(right_frame, text="LINK TERDETEKSI", bg=BLUE_MEDIUM, fg=BLUE_TEXT,
              font=("Arial", 14, "bold"), anchor="center", relief="solid", borderwidth=1
              ).pack(fill=tk.X, pady=(0, 5))

    link_var = tk.StringVar()
    link_entry = tk.Entry(right_frame, textvariable=link_var, state="readonly",
                          font=("Arial", 12), bg=BLUE_ENTRY_BG, relief="solid", borderwidth=1,
                          readonlybackground=BLUE_ENTRY_BG, fg=BLUE_LINK)
    link_entry.pack(fill=tk.X, ipady=8, pady=(0, 15))

    # --- Bagian "LOG QR" ---
    tk.Label(right_frame, text="LOG QR", bg=BLUE_MEDIUM, fg=BLUE_TEXT,
              font=("Arial", 14, "bold"), anchor="center", relief="solid", borderwidth=1
              ).pack(fill=tk.X, pady=(0, 5))

    log_frame = tk.Frame(right_frame, bg=BLUE_LIGHT, relief="solid", borderwidth=1)
    log_frame.pack(fill=tk.BOTH, expand=True)
    
    # Konfigurasi style Treeview
    style = ttk.Style()
    style.theme_use("clam") # 'clam' atau 'alt' lebih mudah dikustomisasi
    style.configure("Treeview.Heading", font=("Arial", 11, "bold"), background=BLUE_MEDIUM, foreground=BLUE_TEXT)
    style.configure("Treeview", font=("Arial", 10), rowheight=25, background=BLUE_ENTRY_BG, foreground=BLUE_TEXT, fieldbackground=BLUE_ENTRY_BG)
    style.map('Treeview', background=[('selected', BLUE_DARK)]) # Warna saat dipilih
    style.configure("Vertical.TScrollbar", background=BLUE_LIGHT, troughcolor=BLUE_BG)


    # Buat Treeview (Log)
    log_tree = ttk.Treeview(log_frame, columns=("No", "Jenis", "Data"), show="headings")
    log_tree.heading("No", text="No")
    log_tree.heading("Jenis", text="Jenis")
    log_tree.heading("Data", text="Data")

    log_tree.column("No", width=50, anchor="center")
    log_tree.column("Jenis", width=120)
    log_tree.column("Data", width=400)

    # Scrollbar untuk Treeview
    scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=log_tree.yview)
    log_tree.configure(yscrollcommand=scrollbar.set)
    
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    log_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

    # === Binding Keyboard & Penutupan Jendela ===
    root.bind('<Return>', handle_enter_key)
    root.bind('<Escape>', lambda e: on_closing())
    root.protocol("WM_DELETE_WINDOW", on_closing)

    # === Mulai Loop ===
    print("Tekan 'ENTER' untuk membuka link (jika URL)")
    print("Tekan 'ESC' untuk keluar")
    print("---------------------------------------------\n")
    
    update_frame()  # Mulai video loop
    root.mainloop()


if __name__ == "__main__":
    main_gui()