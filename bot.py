import os
from telegram import Update
from telegram.ext import ApplicationBuilder, ContextTypes, MessageHandler, filters
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ==========================================
# KONFIGURASI GAMBAR
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
# PENYIMPANAN SESI USER (MENGATUR ALUR 2 LANGKAH)
# ==========================================
user_sessions = {}

async def handle_incoming_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.message
    user_id = message.from_user.id
    
    if not message.photo or not message.caption:
        await message.reply_text("⚠️ Silakan kirim foto beserta *caption* teksnya ya!")
        return

    # Cek apakah user sedang berada di tahap menunggu Foto ke-2 (Narasi)
    if user_id in user_sessions and user_sessions[user_id]["step"] == "waiting_for_slide2":
        # Ini adalah proses untuk SLIDE KEDUA (Narasi)
        session = user_sessions.pop(user_id) # Hapus sesi setelah selesai
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

        # Generate kedua slide
        buat_slide_judul(template_path, foto1_path, judul, font_bold, path_out1)
        buat_slide_narasi(template_path, foto2_path, narasi, font_regular, path_out2)

        # Kirim hasil ke Telegram
        await context.bot.send_photo(chat_id=message.chat_id, photo=open(path_out1, "rb"), caption="✅ Slide 1: Cover Judul")
        await context.bot.send_photo(chat_id=message.chat_id, photo=open(path_out2, "rb"), caption="✅ Slide 2: Narasi Singkat")

        # Bersihkan file sementara foto pertama
        if os.path.exists(foto1_path):
            os.remove(foto1_path)

    else:
        # Ini adalah proses pertama: Menerima FOTO & JUDUL (Slide 1)
        judul = message.caption
        base_dir = os.path.dirname(os.path.abspath(__file__))
        foto1_path = os.path.join(base_dir, f"temp_foto1_{user_id}.jpg")
        
        photo_file = await message.photo[-1].get_file()
        await photo_file.download_to_drive(foto1_path)

        # Simpan data sementara ke sesi user, lalu minta foto kedua
        user_sessions[user_id] = {
            "step": "waiting_for_slide2",
            "judul": judul,
            "foto1_path": foto1_path
        }

        await message.reply_text(
            "✅ **Slide 1 (Judul) tersimpan!**\n\n"
            "Sekarang kirim **Foto ke-2** beserta **caption narasi singkatnya** untuk Slide 2."
        )

from telegram.ext import ApplicationBuilder
from telegram.request import HTTPXRequest # Tambahkan baris ini di atas jika belum ada
import os

def main():
    # Mengambil token secara aman dari sistem server Render
    TOKEN = os.getenv("TELEGRAM_TOKEN")
    
    if not TOKEN:
        print("ERROR: Token Telegram belum diset di Environment Variable!")
        return
    
    custom_request = HTTPXRequest(connect_timeout=30.0, read_timeout=30.0)
    app = ApplicationBuilder().token(TOKEN).request(custom_request).build()
    app.add_handler(MessageHandler(filters.PHOTO & filters.CAPTION, handle_incoming_message))
    
    print("🤖 Bot Telegram Suaradata sedang berjalan di Cloud...")
    app.run_polling()

if __name__ == "__main__":
    main()