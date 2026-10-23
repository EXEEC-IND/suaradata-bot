import os
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from telegram.request import HTTPXRequest
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ==========================================
# 1. KONFIGURASI & FUNGSI PEMBUAT GAMBAR
# ==========================================
CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1350
PHOTO_AREA_Y = 540
PHOTO_WIDTH = 1080
PHOTO_HEIGHT = CANVAS_HEIGHT - PHOTO_AREA_Y
TEXT_BOX_TOP = 150
TEXT_BOX_BOTTOM = 510
MARGIN_X = 85
MAX_TEXT_WIDTH = CANVAS_WIDTH - (MARGIN_X * 2)

def wrap_text_by_pixel(text, font, max_width, draw):
    words = text.split()
    lines = []
    current_line = []
    for word in words:
        test_line = ' '.join(current_line + [word])
        bbox = draw.textbbox((0, 0), test_line, font=font)
        width = bbox[2] - bbox[0]
        if width <= max_width:
            current_line.append(word)
        else:
            if current_line:
                lines.append(' '.join(current_line))
            current_line = [word]
    if current_line:
        lines.append(' '.join(current_line))
    return lines

def pasang_foto_dan_template(template_path, photo_path):
    base_canvas = Image.new("RGBA", (CANVAS_WIDTH, CANVAS_HEIGHT), (255, 255, 255, 255))
    photo = Image.open(photo_path).convert("RGBA")
    photo_cropped = ImageOps.fit(photo, (PHOTO_WIDTH, PHOTO_HEIGHT), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    base_canvas.paste(photo_cropped, (0, PHOTO_AREA_Y))
    template = Image.open(template_path).convert("RGBA")
    template = template.resize((CANVAS_WIDTH, CANVAS_HEIGHT), Image.Resampling.LANCZOS)
    return Image.alpha_composite(base_canvas, template)

def buat_slide_judul(template_path, photo_path, teks_judul, font_path, output_path):
    canvas = pasang_foto_dan_template(template_path, photo_path)
    txt_layer = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)
    font_size, line_spacing = 58, 14
    font = ImageFont.truetype(font_path, font_size)
    lines = wrap_text_by_pixel(teks_judul, font, MAX_TEXT_WIDTH, draw)
    line_height = font_size + line_spacing
    total_text_height = (len(lines) * line_height) - line_spacing
    current_y = TEXT_BOX_TOP + (((TEXT_BOX_BOTTOM - TEXT_BOX_TOP) - total_text_height) // 2)
    for line in lines:
        draw.text((MARGIN_X + 3, current_y + 3), line, font=font, fill=(0, 0, 0, 85))
        draw.text((MARGIN_X, current_y), line, font=font, fill=(15, 15, 15, 255))
        current_y += line_height
    Image.alpha_composite(canvas, txt_layer).convert("RGB").save(output_path, quality=95)

def buat_slide_narasi(template_path, photo_path, teks_narasi, font_path, output_path):
    canvas = pasang_foto_dan_template(template_path, photo_path)
    draw = ImageDraw.Draw(canvas)
    font_size, line_spacing = 38, 12
    font = ImageFont.truetype(font_path, font_size)
    lines = wrap_text_by_pixel(teks_narasi, font, MAX_TEXT_WIDTH, draw)
    line_height = font_size + line_spacing
    total_text_height = (len(lines) * line_height) - line_spacing
    current_y = TEXT_BOX_TOP + (((TEXT_BOX_BOTTOM - TEXT_BOX_TOP) - total_text_height) // 2)
    for i, line in enumerate(lines):
        words = line.split()
        if i == len(lines) - 1 or len(words) == 1:
            draw.text((MARGIN_X, current_y), line, font=font, fill=(20, 20, 20, 255))
        else:
            w_widths = [draw.textbbox((0, 0), w, font=font)[2] - draw.textbbox((0, 0), w, font=font)[0] for w in words]
            total_space_needed = MAX_TEXT_WIDTH - sum(w_widths)
            space_between_words = total_space_needed / (len(words) - 1)
            current_x = MARGIN_X
            for j, word in enumerate(words):
                draw.text((current_x, current_y), word, font=font, fill=(20, 20, 20, 255))
                current_x += w_widths[j] + space_between_words
        current_y += line_height
    canvas.convert("RGB").save(output_path, quality=95)


# ==========================================
# 2. ALUR 2 LANGKAH BOT TELEGRAM
# ==========================================
user_sessions = {}

async def handle_incoming_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if not message.photo or not message.caption:
        await message.reply_text("⚠️ Silakan kirim foto beserta caption teksnya ya!")
        return

    # Tahap ke-2: Menerima Foto & Narasi (Slide 2)
    if user_id in user_sessions and user_sessions[user_id]["step"] == "waiting_for_slide2":
        session = user_sessions.pop(user_id)
        judul = session["judul"]
        foto1_path = session["foto1_path"]
        narasi = message.caption

        await message.reply_text("⏳ Memproses Slide 1 & Slide 2...")

        base_dir = os.path.dirname(os.path.abspath(__file__))
        template_path = os.path.join(base_dir, "template_suaradata.png")
        font_bold = os.path.join(base_dir, "Montserrat-Bold.ttf")
        font_regular = os.path.join(base_dir, "OpenSans-Bold.ttf")

        foto2_path = os.path.join(base_dir, f"temp_foto2_{user_id}.jpg")
        photo_file = await message.photo[-1].get_file()
        await photo_file.download_to_drive(foto2_path)

        path_out1 = os.path.join(base_dir, f"hasil_slide1_{user_id}.jpg")
        path_out2 = os.path.join(base_dir, f"hasil_slide2_{user_id}.jpg")

        buat_slide_judul(template_path, foto1_path, judul, font_bold, path_out1)
        buat_slide_narasi(template_path, foto2_path, narasi, font_regular, path_out2)

        with open(path_out1, "rb") as f1:
            await context.bot.send_photo(chat_id=message.chat_id, photo=f1, caption="✅ Slide 1: Cover Judul")
        with open(path_out2, "rb") as f2:
            await context.bot.send_photo(chat_id=message.chat_id, photo=f2, caption="✅ Slide 2: Narasi Singkat")

        # Bersihkan file sementara agar penyimpanan server tidak penuh
        for p in [foto1_path, foto2_path, path_out1, path_out2]:
            if os.path.exists(p):
                os.remove(p)

    # Tahap ke-1: Menerima Foto & Judul (Slide 1)
    else:
        judul = message.caption
        base_dir = os.path.dirname(os.path.abspath(__file__))
        foto1_path = os.path.join(base_dir, f"temp_foto1_{user_id}.jpg")
        
        photo_file = await message.photo[-1].get_file()
        await photo_file.download_to_drive(foto1_path)

        user_sessions[user_id] = {
            "step": "waiting_for_slide2",
            "judul": judul,
            "foto1_path": foto1_path
        }

        await message.reply_text(
            "✅ Slide 1 (Judul) tersimpan!\n\n"
            "Sekarang kirim Foto ke-2 beserta caption narasi singkatnya untuk Slide 2."
        )


# ==========================================
# 3. WEB SERVER MINI & JALANKAN BOT
# ==========================================
class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Bot Suaradata Aktif 24 Jam!")

def run_web_server():
    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()

def main():
    # Mengambil token dari Environment Variable Render, atau pakai fallback token lokal
    TOKEN = os.getenv("TELEGRAM_TOKEN", "8871869260:AAGwquQqtmpnRo8NlTyeg80VoaNaQnc6UWc")
    
    # Nyalakan web server palsu di background supaya Render Web Service gratis bisa jalan
    t = threading.Thread(target=run_web_server)
    t.daemon = True
    t.start()

    # Nyalakan Bot Telegram
    custom_request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
    app = ApplicationBuilder().token(TOKEN).request(custom_request).build()
    app.add_handler(MessageHandler(filters.PHOTO & filters.CAPTION, handle_incoming_message))
    
    print("🤖 Bot Telegram Suaradata sedang berjalan...")
    app.run_polling()

if __name__ == "__main__":
    main()