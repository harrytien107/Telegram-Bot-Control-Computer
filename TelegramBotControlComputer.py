import os
import re
import time
import pyautogui
import nest_asyncio
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
    "/customvolume": "Điều chỉnh âm lượng."
}

# Selenium setup
# Selenium setup
CHROME_DRIVER_PATH = "<Enter the path to ChromeDriver (chromedriver.exe)>"
BRAVE_PATH = "<Enter the path to Brave Browser (brave.exe)>"

options = Options()
options.binary_location = BRAVE_PATH

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
    await update.message.reply_text("Đang phát video trên Brave.")

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

            # Tắt toàn bộ trình duyệt Brave
            os.system("taskkill /F /IM brave.exe")  # Dùng os.system để đảm bảo lệnh được thực thi
            await query.edit_message_text("Đã đóng toàn bộ trình duyệt Brave.")
        except Exception as e:
            await query.edit_message_text(f"Có lỗi xảy ra khi tắt Brave: {e}")

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
            "/shutdown", "/restart", "/cancel", "/screenshot"
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
            "/netuser", "/whoami", "/hostname"
        ]
    ])
    utility_commands = "\n".join([
        f"🔻 {command} ➡️ {desc}" for command, desc in COMMANDS.items() if command in [
            "/menu", "/playvideo"
        ]
    ])

    # Nội dung đầy đủ menu
    menu_text = (
        f"DANH SÁCH CÁC LỆNH\n"
        f"📌 Author: LePhiAnhDev\n\n"
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
        await update.message.reply_text(
            f"Kết quả:\n```\n{result}\n```",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"Có lỗi xảy ra khi chạy lệnh: {e}")

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
        "- GitHub: https://github.com/LePhiAnhDev"
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

# Khởi chạy bot Telegram
async def main():
    # Thay bằng token bot của bạn từ BotFather
    TOKEN = "<Enter the Telegram Bot token>"

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

    # Tạo bàn phím gợi ý cho người dùng
    user_keyboard = [
        ["/shutdown", "/restart", "/cancel"],
        ["/screenshot", "/uploadfile", "/downloadfile"],
        ["/tasklist", "/systeminfo", "/ipconfig"],
        ["/release", "/renew", "/netuser"],
        ["/whoami", "/hostname", "/menu"],
        ["/playvideo", "/introduce", "/customvolume"]
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