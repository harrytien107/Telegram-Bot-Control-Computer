import os
import re
import time
import pyautogui
import nest_asyncio
from pywinauto import Application
import psutil
import subprocess
nest_asyncio.apply()
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from telegram import Update, ReplyKeyboardMarkup, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, CallbackQueryHandler, filters

# Đường dẫn lưu file tải về
UPLOAD_FOLDER = "D:/"

# Tạo thư mục nếu chưa tồn tại
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# Thêm biến NIRCMD_PATH vào đầu file, sau các biến đường dẫn khác
NIRCMD_PATH = "<Enter the path to nircmd nircmdc.exe"

COMMANDS = {
    "/introduce": "Giới thiệu về tôi.",
    "/shutdown": "Lệnh tắt máy.",
    "/restart": "Lệnh khởi động máy.",
    "/cancel": "Lệnh hủy toàn bộ các lệnh.",
    "/screenshot": "Lệnh chụp ảnh màn hình và gửi về máy.",
    "/uploadfile": "Yêu cầu người dùng gửi file để tải lên.",
    "/downloadfile": "Yêu cầu người dùng gửi file để tải về.",
    "/tasklist": "Hiển thị danh sách các tiến trình đang chạy.",
    "/systeminfo": "Hiển thị thông tin hệ thống.",
    "/ipconfig": "Hiển thị thông tin cấu hình mạng.",
    "/release": "Giải phóng địa chỉ IP hiện tại.",
    "/renew": "Gia hạn địa chỉ IP mới.",
    "/netuser": "Hiển thị danh sách người dùng trên máy tính.",
    "/whoami": "Hiển thị tên tài khoản đang đăng nhập.",
    "/hostname": "Hiển thị tên máy tính.",
    "/menu": "Hiển thị danh sách các lệnh.",
    "/playvideo": "Phát video YouTube từ link.",
    "/customvolume": "Điều chỉnh âm lượng.",
    "/hibernate": "Lệnh chế độ ngủ đông.",
    "/sleep": "Lệnh chế độ ngủ.",
    "/spotify": "Điều khiển ứng dụng Spotify.",
    "/openspotify": "Mở ứng dụng Spotify.",
    "/kill": "Kết thúc một tiến trình đang chạy."
}

# Selenium setup
# Có thể đổi các chữ THORIUM_PATH thành CHROME_PATH nếu bạn muốn dùng Chrome
# Có thể đổi các chữ CHROME_DRIVER_PATH thành BRAVE_DRIVER_PATH nếu bạn muốn dùng Brave
CHROME_DRIVER_PATH = "<Enter the path to ChromeDriver (chromedriver.exe)"
THORIUM_PATH = "<Enter the path to Brave Browser (brave.exe) or Chrome (chrome.exe)>"

options = Options()
options.binary_location = THORIUM_PATH

# Thêm đường dẫn đến hồ sơ trình duyệt của bạn
USER_DATA_DIR = "<Enter the path to the Brave User Data folder>"
options.add_argument(f"--user-data-dir={USER_DATA_DIR}")

options.add_argument("--start-maximized")

# Biến toàn cục cho Selenium
driver = None

async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    basic_commands = "\n".join([
        f"🔻 {command} ➡️ {desc}" for command, desc in COMMANDS.items()
    ])
    await update.message.reply_text(f"Danh sách các lệnh:\n{basic_commands}")

async def set_command_suggestions(context: ContextTypes.DEFAULT_TYPE):
    commands = [BotCommand(command, desc) for command, desc in COMMANDS.items()]
    await context.bot.set_my_commands(commands)

# Tính năng phát video
async def play_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global driver

    # Kiểm tra trạng thái của Thorium
    thorium_running = "thorium.exe" in os.popen('tasklist').read()

    if (thorium_running):
        # Tạo nút chọn hành động (nằm ngang)
        keyboard = [
            [
                InlineKeyboardButton("✅ Có", callback_data="close_thorium_and_play"), # đổi tên thorium thành brave or chrome 
                InlineKeyboardButton("❌ Không", callback_data="cancel_playvideo")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Trình duyệt Thorium hiện đang mở. Bạn có muốn đóng trình duyệt để phát video không?",
            reply_markup=reply_markup
        )
        return

    # Lấy link từ tham số hoặc tin nhắn
    youtube_url = context.args[0] if context.args else update.message.text.strip()

    # Kiểm tra link YouTube hợp lệ
    youtube_pattern = r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+" 
    if not re.match(youtube_pattern, youtube_url):
        await update.message.reply_text("Hãy gửi một link YouTube kèm lệnh /playvideo [link].\nLưu ý trình duyệt phải đang đóng.")
        return

    # Khởi chạy Selenium nếu chưa khởi động
    if driver is None:
        service = Service(CHROME_DRIVER_PATH)
        driver = webdriver.Chrome(service=service, options=options)

    # Mở link YouTube
    driver.get(youtube_url)
    await update.message.reply_text("Đang phát video trên Thorium.")

    # Tạo các nút điều khiển
    keyboard = [
        [InlineKeyboardButton("⏯ Phát / Tạm dừng", callback_data="play_pause"),
         InlineKeyboardButton("⏪ Tua lại 10s", callback_data="rewind")],
        [InlineKeyboardButton("⏩ Tua tới 10s", callback_data="forward"),
         InlineKeyboardButton("🔄 Chuyển video", callback_data="change_video")],
        [InlineKeyboardButton("❌ Đóng toàn bộ", callback_data="close_all")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Chọn hành động:", reply_markup=reply_markup)


# Xử lý hành động từ nút
async def handle_brave_controls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global driver
    query = update.callback_query
    await query.answer()

    if query.data == "close_thorium_and_play":
        os.system("taskkill /F /IM thorium.exe")
        await query.edit_message_text("Đã đóng Thorium. Bạn có thể chạy lại lệnh /playvideo.")
    elif query.data == "cancel_playvideo":
        await query.edit_message_text("Lệnh /playvideo đã bị hủy.")

# Xử lý button điều khiển video
async def video_controls(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global driver
    query = update.callback_query
    await query.answer()

    action = query.data
    if action == "play_pause":
        video_element = driver.find_element(By.TAG_NAME, "video")
        driver.execute_script("arguments[0].paused ? arguments[0].play() : arguments[0].pause();", video_element)
        await query.edit_message_text("Đã chuyển trạng thái phát / tạm dừng.")

    elif action == "rewind":
        driver.execute_script("document.querySelector('video').currentTime -= 10;")
        await query.edit_message_text("Đã tua lại 10 giây.")

    elif action == "forward":
        driver.execute_script("document.querySelector('video').currentTime += 10;")
        await query.edit_message_text("Đã tua tới 10 giây.")

    elif action == "change_video":
        await query.edit_message_text("Gửi link YouTube mới kèm lệnh /playvideo [link] để phát.")

    elif action == "close_all":
        try:
            if driver:
                driver.quit()  # Đóng hoàn toàn driver Selenium
                driver = None  # Đặt lại biến `driver` về None

            # Tắt toàn bộ trình duyệt Thorium
            os.system("taskkill /F /IM thorium.exe")  # Dùng os.system để đảm bảo lệnh được thực thi
            await query.edit_message_text("Đã đóng toàn bộ trình duyệt Thorium.")
        except Exception as e:
            await query.edit_message_text(f"Có lỗi xảy ra khi tắt Thorium: {e}")

    # Lưu lại và giữ các nút điều khiển video luôn hoạt động (trừ khi đã đóng toàn bộ)
    if action != "close_all":
        keyboard = [
            [InlineKeyboardButton("⏯ Phát / Tạm dừng", callback_data="play_pause"),
             InlineKeyboardButton("⏪ Tua lại 10s", callback_data="rewind")],
            [InlineKeyboardButton("⏩ Tua tới 10s", callback_data="forward"),
             InlineKeyboardButton("🔄 Chuyển video", callback_data="change_video")],
            [InlineKeyboardButton("❌ Đóng trình duyệt", callback_data="close_all")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_reply_markup(reply_markup=reply_markup)
        
# Lệnh điều chỉnh âm lượng
async def custom_volume(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [
            InlineKeyboardButton("🔉 Giảm âm lượng", callback_data="decrease_volume"),
            InlineKeyboardButton("🔊 Tăng âm lượng", callback_data="increase_volume")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Chọn hành động để điều chỉnh âm lượng:", reply_markup=reply_markup)

# Xử lý các nút giảm/tăng âm lượng
async def handle_volume_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = query.data
    try:
        if action == "decrease_volume":
            os.system("<Enter the path to nircmdc.exe> changesysvolume -3277")  # Giảm âm lượng
            await query.edit_message_text("Đã giảm âm lượng.")
        elif action == "increase_volume":
            os.system("<Enter the path to nircmdc.exe> changesysvolume 3277")  # Tăng âm lượng
            await query.edit_message_text("Đã tăng âm lượng.")
    except Exception as e:
        await query.edit_message_text(f"Có lỗi xảy ra: {e}")

    # Giữ lại các nút điều khiển sau khi nhấn
    keyboard = [
        [
            InlineKeyboardButton("🔉 Giảm âm lượng", callback_data="decrease_volume"),
            InlineKeyboardButton("🔊 Tăng âm lượng", callback_data="increase_volume")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.edit_message_reply_markup(reply_markup=reply_markup)

# Tạo menu lệnh
async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Lệnh giới thiệu
    introduce_command = "🔻 /introduce ➡️ Giới thiệu về tôi."

    # Các nhóm lệnh khác
    system_commands = "\n".join([
        f"🔻 {command} ➡️ {desc}" for command, desc in COMMANDS.items() if command in [
            "/shutdown", "/hibernate", "/sleep", "/restart", "/cancel", "/screenshot"
        ]
    ])
    file_io_commands = "\n".join([
        f"🔻 {command} ➡️ {desc}" for command, desc in COMMANDS.items() if command in [
            "/uploadfile", "/downloadfile"
        ]
    ])
    system_info_commands = "\n".join([
        f"🔻 {command} ➡️ {desc}" for command, desc in COMMANDS.items() if command in [
            "/tasklist", "/systeminfo", "/ipconfig", "/release", "/renew",
            "/netuser", "/whoami", "/hostname", "/kill"
        ]
    ])
    utility_commands = "\n".join([
        f"🔻 {command} ➡️ {desc}" for command, desc in COMMANDS.items() if command in [
            "/menu", "/playvideo", "/spotify"
        ]
    ])

    # Nội dung đầy đủ menu
    menu_text = (
        f"DANH SÁCH CÁC LỆNH\n"
        f"📌 Author: LePhiAnhDev\n\n"
        f"📌 Edit contribute: harrytien107\n\n"
        f"{introduce_command}\n\n"
        f"⚡️ HỆ THỐNG LỆNH:\n"
        f"{system_commands}\n\n"
        f"⚡️ I/O FILE:\n"
        f"{file_io_commands}\n\n"
        f"⚡️ LỆNH HỆ THỐNG:\n"
        f"{system_info_commands}\n\n"
        f"⚡️ LỆNH TIỆN ÍCH:\n"
        f"{utility_commands}"
    )

    await update.message.reply_text(menu_text)

# Chạy lệnh terminal và trả về kết quả
async def run_command(update: Update, context: ContextTypes.DEFAULT_TYPE, command: str):
    try:
        result = os.popen(command).read()
        if not result.strip():  # Kiểm tra nếu kết quả rỗng
            result = "Không có dữ liệu để hiển thị hoặc lệnh không hợp lệ."
            await update.message.reply_text(result)
            return

        # Chia kết quả thành các phần nhỏ hơn (mỗi phần tối đa 4000 ký tự)
        MAX_LENGTH = 4000
        messages = []
        current_message = "```\n"  # Bắt đầu với markdown code block

        for line in result.split('\n'):
            if len(current_message) + len(line) + 4 > MAX_LENGTH:  # +4 cho ```\n ở đầu và cuối
                current_message += "\n```"
                messages.append(current_message)
                current_message = "```\n" + line
            else:
                current_message += line + "\n"

        if current_message != "```\n":
            current_message += "\n```"
            messages.append(current_message)

        # Gửi từng phần
        for i, message in enumerate(messages, 1):
            if len(messages) > 1:
                header = f"Phần {i}/{len(messages)}:\n"
                await update.message.reply_text(header + message, parse_mode="Markdown")
            else:
                await update.message.reply_text(message, parse_mode="Markdown")

    except Exception as e:
        await update.message.reply_text(f"Có lỗi xảy ra khi chạy lệnh: {str(e)}")

# Các lệnh mới
async def tasklist(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_command(update, context, "tasklist")

async def systeminfo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_command(update, context, "systeminfo")

async def ipconfig(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_command(update, context, "ipconfig")

async def release(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_command(update, context, "ipconfig /release")

async def renew(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_command(update, context, "ipconfig /renew")

async def netuser(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_command(update, context, "net user")

async def whoami(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_command(update, context, "whoami")

async def hostname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await run_command(update, context, "hostname")

# Tạo inline button để xác nhận
async def confirm_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    action = context.user_data.get("action")
    if action == "shutdown":
        os.system("shutdown /s /t 3")
        await query.edit_message_text("Máy sẽ tắt sau 3 giây.")
    elif action == "restart":
        os.system("shutdown /r /t 3")
        await query.edit_message_text("Máy sẽ khởi động lại sau 3 giây.")
    elif action == "hibernate":
        os.system("shutdown /h")
        await query.edit_message_text("Máy sẽ chuyển sang chế độ ngủ đông.")
    elif action == "sleep":
        os.system("rundll32.exe powrprof.dll,SetSuspendState 0,1,0")
        await query.edit_message_text("Máy sẽ chuyển sang chế độ ngủ.")
    elif action == "cancel":
        os.system("shutdown -a")
        await query.edit_message_text("Đã hủy toàn bộ lệnh.")
    else:
        await query.edit_message_text("Không có hành động được thực hiện.")

async def cancel_action(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Hành động đã bị hủy.")

# Hỏi xác nhận trước khi thực hiện lệnh
async def ask_confirmation(update: Update, context: ContextTypes.DEFAULT_TYPE, action):
    context.user_data["action"] = action
    keyboard = [
        [InlineKeyboardButton("✅ Xác nhận", callback_data="confirm"), InlineKeyboardButton("❎ Hủy", callback_data="cancel")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(f"Bạn có chắc chắn muốn {action} máy không?", reply_markup=reply_markup)

# Lệnh introduce
async def introduce(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👨‍💻 DEVELOPER | LÊ PHI ANH\n\n"
        "📩 Contact for Work:\n"
        "- Discord: LePhiAnhDev\n"
        "- Telegram: @lephianh386ht\n"
        "- GitHub: https://github.com/LePhiAnhDev\n"
        "👨‍💻 CONTRIBUTOR: harrytien107\n"
        "- Discord: harrytien107\n"
        "- Telegram: @harrytienthereal\n"
        "- GitHub: https://github.com/harrytien107"
    )

# Lệnh shutdown
async def shutdown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_confirmation(update, context, "shutdown")

# Lệnh restart
async def restart(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_confirmation(update, context, "restart")

# Lệnh cancel
async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_confirmation(update, context, "cancel")

# Lệnh hibernate
async def hibernate(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_confirmation(update, context, "hibernate")

# Lệnh sleep 
async def sleep(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await ask_confirmation(update, context, "sleep")

# Chụp ảnh màn hình
async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.effective_chat.id
    file_name = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
    screenshot_path = os.path.join(UPLOAD_FOLDER, file_name)

    try:
        # Lưu ảnh chụp màn hình vào thư mục
        screenshot = pyautogui.screenshot()
        screenshot.save(screenshot_path)

        # Gửi ảnh chụp màn hình đến Telegram
        with open(screenshot_path, 'rb') as photo:
            await context.bot.send_photo(chat_id=chat_id, photo=photo)

        os.remove(screenshot_path)  # Xóa file ảnh sau khi gửi
        await update.message.reply_text("Đã chụp ảnh màn hình và gửi thành công!")
    except Exception as e:
        await update.message.reply_text(f"Có lỗi xảy ra khi chụp ảnh màn hình: {e}")

# Xử lý lệnh /downloadfile
async def download_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text(
            "Hãy nhập đường dẫn file bạn muốn tải về. Ví dụ: D:/example.format"
        )
        return

    # Lấy và lưu đường dẫn file vào context.user_data
    file_path = " ".join(context.args).strip()
    context.user_data["file_path"] = file_path

    # Kiểm tra file có tồn tại hay không
    if os.path.isfile(file_path):
        await update.message.reply_text(f"Đường dẫn hợp lệ. Đang chuẩn bị gửi file: {file_path}")
        try:
            # Gửi file qua Telegram
            with open(file_path, 'rb') as file:
                await context.bot.send_document(chat_id=update.effective_chat.id, document=file)
            await update.message.reply_text(f"File đã được gửi thành công: {file_path}")
        except Exception as e:
            await update.message.reply_text(f"Có lỗi xảy ra khi gửi file: {e}")
    else:
        await update.message.reply_text(f"Không tìm thấy file tại đường dẫn: {file_path}")

# Yêu cầu gửi file
async def upload_request(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Hãy gửi file bạn muốn tải lên. File sẽ được lưu vào ổ D:/")

# Xử lý khi người dùng gửi file
async def upload_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message

    # Ưu tiên lấy file tài liệu, nếu không thì kiểm tra ảnh hoặc video
    file = message.document or (message.photo[-1] if message.photo else None) or message.video

    if file:
        # Lấy tên file, nếu không có, tạo tên file với đuôi mặc định
        file_name = file.file_name if hasattr(file, "file_name") else f"file_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
        file_path = os.path.join(UPLOAD_FOLDER, file_name)

        # Tải file về máy
        new_file = await file.get_file()
        await new_file.download_to_drive(file_path)

        await update.message.reply_text(f"File {file_name} đã được tải và lưu trong thư mục {UPLOAD_FOLDER}.")
    else:
        await update.message.reply_text("Không nhận được file hợp lệ. Vui lòng thử lại!")

# Thêm các hàm điều khiển Spotify
async def spotify_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Kiểm tra xem Spotify có đang chạy không
    spotify_running = False
    for proc in psutil.process_iter(['name']):
        if proc.info['name'] == 'Spotify.exe':
            spotify_running = True
            break
    
    if not spotify_running:
        try:
            # Mở Spotify
            spotify_path = "<Enter the path to spotify.exe>"
            subprocess.Popen([spotify_path])
            await update.message.reply_text("Đang mở Spotify...")
            
            # Đợi Spotify khởi động
            await asyncio.sleep(5)
            
            # Hiển thị bảng điều khiển
            keyboard = [
                [
                    InlineKeyboardButton("⏮ Bài trước", callback_data="spotify_previous"),
                    InlineKeyboardButton("⏯ Phát/Tạm dừng", callback_data="spotify_playpause"),
                    InlineKeyboardButton("⏭ Bài tiếp", callback_data="spotify_next")
                ],
                [
                    InlineKeyboardButton("🔉 Giảm âm lượng", callback_data="spotify_volume_down"),
                    InlineKeyboardButton("🔊 Tăng âm lượng", callback_data="spotify_volume_up")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await update.message.reply_text("Điều khiển Spotify:", reply_markup=reply_markup)
            return
        except Exception as e:
            await update.message.reply_text(f"Có lỗi khi mở Spotify: {str(e)}")
            return

    keyboard = [
        [
            InlineKeyboardButton("⏮ Bài trước", callback_data="spotify_previous"),
            InlineKeyboardButton("⏯ Phát/Tạm dừng", callback_data="spotify_playpause"),
            InlineKeyboardButton("⏭ Bài tiếp", callback_data="spotify_next")
        ],
        [
            InlineKeyboardButton("🔉 Giảm âm lượng", callback_data="spotify_volume_down"),
            InlineKeyboardButton("🔊 Tăng âm lượng", callback_data="spotify_volume_up")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Điều khiển Spotify:", reply_markup=reply_markup)

async def handle_spotify_control(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "open_spotify":
        await open_spotify(update, context)
        return
        
    try:
        # Sử dụng multimedia keys thay vì phím tắt Spotify
        if query.data == "spotify_previous":
            pyautogui.press('prevtrack')  # Phím Previous Track
            message = "⏮ Đã chuyển về bài trước"
        elif query.data == "spotify_playpause":
            pyautogui.press('playpause')  # Phím Play/Pause
            message = "⏯ Đã chuyển trạng thái phát/tạm dừng"
        elif query.data == "spotify_next":
            pyautogui.press('nexttrack')  # Phím Next Track
            message = "⏭ Đã chuyển sang bài tiếp theo"
        elif query.data == "spotify_volume_down":
            # Giảm âm lượng 10% (10 * 655 = 6550)
            os.system(f'"{NIRCMD_PATH}" changesysvolume -6550')
            message = "🔉 Đã giảm âm lượng 10%"
        elif query.data == "spotify_volume_up":
            # Tăng âm lượng 10% (10 * 655 = 6550)
            os.system(f'"{NIRCMD_PATH}" changesysvolume 6550')
            message = "🔊 Đã tăng âm lượng 10%"
            
        # Thêm timestamp vào tin nhắn để làm cho nó khác với tin nhắn cũ
        timestamp = datetime.now().strftime("%H:%M:%S")
        message = f"{message} ({timestamp})"
            
        # Cập nhật tin nhắn và giữ lại các nút
        keyboard = [
            [
                InlineKeyboardButton("⏮ Bài trước", callback_data="spotify_previous"),
                InlineKeyboardButton("⏯ Phát/Tạm dừng", callback_data="spotify_playpause"),
                InlineKeyboardButton("⏭ Bài tiếp", callback_data="spotify_next")
            ],
            [
                InlineKeyboardButton("🔉 Giảm âm lượng 10%", callback_data="spotify_volume_down"),
                InlineKeyboardButton("🔊 Tăng âm lượng 10%", callback_data="spotify_volume_up")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        try:
            await query.edit_message_text(text=message, reply_markup=reply_markup)
        except Exception as e:
            # Nếu không thể sửa tin nhắn, gửi tin nhắn mới
            await query.message.reply_text(text=message, reply_markup=reply_markup)
        
    except Exception as e:
        await query.message.reply_text(f"Có lỗi xảy ra: {str(e)}")

# Thêm hàm mở Spotify
async def open_spotify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Đường dẫn mặc định của Spotify
        spotify_path = "<Enter the path to spotify.exe>"
        
        # Kiểm tra xem Spotify đã chạy chưa
        spotify_running = False
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] == 'Spotify.exe':
                spotify_running = True
                break
        
        if spotify_running:
            await update.message.reply_text("Spotify đã được mở sẵn.")
            # Hiển thị bảng điều khiển Spotify
            await spotify_control(update, context)
            return
            
        # Mở Spotify
        subprocess.Popen([spotify_path])
        await update.message.reply_text("Đang mở Spotify...")
        
        # Đợi một chút để Spotify khởi động
        await asyncio.sleep(5)
        
        # Hiển thị bảng điều khiển Spotify
        await spotify_control(update, context)
        
    except Exception as e:
        await update.message.reply_text(f"Có lỗi khi mở Spotify: {str(e)}")

# Thêm hàm để lấy danh sách tiến trình
async def get_process_list():
    processes = []
    for proc in psutil.process_iter(['pid', 'name']):
        try:
            processes.append({
                'pid': proc.info['pid'],
                'name': proc.info['name']
            })
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return sorted(processes, key=lambda x: x['name'].lower())

# Thêm hàm xử lý lệnh kill
async def kill_process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        # Hiển thị danh sách các tiến trình
        processes = await get_process_list()
        
        # Tạo các nút cho từng tiến trình phổ biến
        common_processes = [
            "chrome.exe", "spotify.exe", "thorium.exe",
            "vlc.exe", "winword.exe", "excel.exe", "powerpnt.exe", "discord.exe"
        ]
        
        keyboard = []
        # Thêm nút tìm kiếm
        keyboard.append([InlineKeyboardButton("🔍 Tìm kiếm tiến trình", callback_data="search_process")])
        
        # Thêm các tiến trình phổ biến
        for proc_name in common_processes:
            matching_procs = [p for p in processes if p['name'].lower() == proc_name.lower()]
            if matching_procs:
                button = InlineKeyboardButton(
                    f"🔴 Tắt {proc_name}",
                    callback_data=f"kill_name_{proc_name}"
                )
                keyboard.append([button])
        
        # Thêm nút để xem tất cả tiến trình
        keyboard.append([InlineKeyboardButton("📋 Xem tất cả tiến trình", callback_data="show_all_processes")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "Chọn ứng dụng bạn muốn tắt hoặc tìm kiếm:",
            reply_markup=reply_markup
        )
        return

    # Nếu có args, xem như là tìm kiếm
    search_term = " ".join(context.args).lower()
    processes = await get_process_list()
    matching_processes = [
        p for p in processes 
        if search_term in p['name'].lower()
    ]

    if not matching_processes:
        await update.message.reply_text(f"Không tìm thấy tiến trình nào chứa từ khóa: {search_term}")
        return

    keyboard = []
    for proc in matching_processes:
        button = InlineKeyboardButton(
            f"🔴 {proc['name']} (PID: {proc['pid']})",
            callback_data=f"kill_name_{proc['name']}"
        )
        keyboard.append([button])

    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        f"Các tiến trình tìm thấy với từ khóa '{search_term}':",
        reply_markup=reply_markup
    )

# Thêm hàm xử lý callback cho lệnh kill
async def handle_kill_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "cancel_kill":
        await query.edit_message_text("Đã hủy lệnh kết thúc tiến trình.")
        return
        
    if query.data == "search_process":
        await query.edit_message_text(
            "Nhập lệnh /kill kèm theo tên tiến trình bạn muốn tìm.\n"
            "Ví dụ: /kill chrome để tìm các tiến trình chứa từ 'chrome'"
        )
        return
        
    if query.data == "show_all_processes":
        processes = await get_process_list()
        keyboard = []
        for proc in processes:
            button = InlineKeyboardButton(
                f"{proc['name']} (PID: {proc['pid']})",
                callback_data=f"kill_{proc['pid']}"
            )
            keyboard.append([button])
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("Chọn tiến trình bạn muốn kết thúc:", reply_markup=reply_markup)
        return

    if query.data.startswith("kill_name_"):
        # Xử lý xác nhận kill theo tên process
        process_name = query.data.split("kill_name_")[1]
        keyboard = [
            [
                InlineKeyboardButton("✅ Xác nhận", callback_data=f"confirm_kill_name_{process_name}"),
                InlineKeyboardButton("❌ Hủy", callback_data="cancel_kill")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            f"Bạn có chắc chắn muốn kết thúc tất cả tiến trình {process_name}?",
            reply_markup=reply_markup
        )
        return

    if query.data.startswith("confirm_kill_name_"):
        # Thực hiện kill theo tên process sau khi xác nhận
        process_name = query.data.split("confirm_kill_name_")[1]
        killed_count = 0
        for proc in psutil.process_iter(['pid', 'name']):
            if proc.info['name'].lower() == process_name.lower():
                try:
                    process = psutil.Process(proc.info['pid'])
                    process.terminate()
                    await asyncio.sleep(1)
                    if process.is_running():
                        process.kill()
                    killed_count += 1
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        
        if killed_count > 0:
            await query.edit_message_text(f"Đã kết thúc {killed_count} tiến trình {process_name}")
        else:
            await query.edit_message_text(f"Không tìm thấy tiến trình {process_name} đang chạy")
        return

    if query.data.startswith("kill_"):
        try:
            # Xử lý xác nhận kill theo PID
            pid = int(query.data.split('_')[1])
            process = psutil.Process(pid)
            process_name = process.name()
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Xác nhận", callback_data=f"confirm_kill_pid_{pid}"),
                    InlineKeyboardButton("❌ Hủy", callback_data="cancel_kill")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.edit_message_text(
                f"Bạn có chắc chắn muốn kết thúc tiến trình {process_name} (PID: {pid})?",
                reply_markup=reply_markup
            )
        except (psutil.NoSuchProcess, psutil.AccessDenied) as e:
            await query.edit_message_text(f"Lỗi: {str(e)}")
        return

    if query.data.startswith("confirm_kill_pid_"):
        try:
            # Thực hiện kill theo PID sau khi xác nhận
            pid = int(query.data.split('confirm_kill_pid_')[1])
            process = psutil.Process(pid)
            process_name = process.name()
            
            process.terminate()
            await asyncio.sleep(1)
            if process.is_running():
                process.kill()
                
            await query.edit_message_text(f"Đã kết thúc tiến trình {process_name} (PID: {pid})")
        except psutil.NoSuchProcess:
            await query.edit_message_text("Tiến trình không còn tồn tại.")
        except psutil.AccessDenied:
            await query.edit_message_text("Không có quyền kết thúc tiến trình này.")
        except Exception as e:
            await query.edit_message_text(f"Có lỗi xảy ra: {str(e)}")

# Khởi chạy bot Telegram
async def main():
    # Thay bằng token bot của bạn từ BotFather
    TOKEN = "<Enter your bot token>"

    app = ApplicationBuilder().token(TOKEN).build()

    # Gắn các lệnh vào bot
    app.add_handler(CommandHandler("introduce", introduce))
    app.add_handler(CommandHandler("shutdown", shutdown))
    app.add_handler(CommandHandler("restart", restart))
    app.add_handler(CommandHandler("screenshot", screenshot))
    app.add_handler(CommandHandler("uploadfile", upload_request))
    app.add_handler(CommandHandler("downloadfile", download_file))
    app.add_handler(CommandHandler("tasklist", tasklist))
    app.add_handler(CommandHandler("systeminfo", systeminfo))
    app.add_handler(CommandHandler("ipconfig", ipconfig))
    app.add_handler(CommandHandler("release", release))
    app.add_handler(CommandHandler("renew", renew))
    app.add_handler(CommandHandler("netuser", netuser))
    app.add_handler(CommandHandler("whoami", whoami))
    app.add_handler(CommandHandler("hostname", hostname))
    app.add_handler(CallbackQueryHandler(confirm_action, pattern="^confirm$"))
    app.add_handler(CallbackQueryHandler(cancel_action, pattern="^cancel$"))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("playvideo", play_video))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CallbackQueryHandler(video_controls, pattern="^(play_pause|rewind|forward|change_video|close_all)$"))
    app.add_handler(CommandHandler("customvolume", custom_volume))
    app.add_handler(CallbackQueryHandler(handle_volume_control, pattern="^(decrease_volume|increase_volume)$"))
    app.add_handler(CallbackQueryHandler(handle_brave_controls, pattern="^(close_thorium_and_play|cancel_playvideo)$"))
    app.add_handler(CommandHandler("hibernate", hibernate))
    app.add_handler(CommandHandler("sleep", sleep))
    app.add_handler(CommandHandler("spotify", spotify_control))
    app.add_handler(CallbackQueryHandler(handle_spotify_control, 
                                       pattern="^spotify_(previous|playpause|next|volume_down|volume_up)$"))
    app.add_handler(CommandHandler("openspotify", open_spotify))
    app.add_handler(CommandHandler("kill", kill_process))
    app.add_handler(CallbackQueryHandler(handle_kill_callback, 
        pattern="^(kill_name_.*|kill_[0-9]+|cancel_kill|show_all_processes|confirm_kill_name_.*|confirm_kill_pid_[0-9]+|search_process)$"))

    # Tạo bàn phím gợi ý cho người dùng
    user_keyboard = [
        ["/shutdown", "/restart", "/cancel"],
        ["/hibernate", "/sleep", "/screenshot"],
        ["/uploadfile", "/downloadfile", "/tasklist"],
        ["/systeminfo", "/ipconfig", "/release"],
        ["/renew", "/netuser", "/whoami"],
        ["/hostname", "/menu", "/playvideo", "/spotify"],
        ["/introduce", "/customvolume", "/kill"]
    ]

    reply_markup = ReplyKeyboardMarkup(user_keyboard, one_time_keyboard=False, resize_keyboard=True)

    # Set bot command suggestions
    async def set_command_suggestions(context):
        commands = [BotCommand(command, desc) for command, desc in COMMANDS.items()]
        await context.bot.set_my_commands(commands)

    app.post_init = set_command_suggestions

    # Lắng nghe file gửi từ người dùng
    app.add_handler(MessageHandler(filters.ATTACHMENT, upload_file))

    # Chạy bot
    app.run_polling()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
