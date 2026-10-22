import os
from PIL import Image, ImageDraw, ImageFont, ImageOps

# ==========================================
# KONFIGURASI UKURAN & KOORDINAT
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
    final_canvas = Image.alpha_composite(base_canvas, template)
    return final_canvas


def buat_slide_judul(template_path, photo_path, teks_judul, font_path, output_path):
    canvas = pasang_foto_dan_template(template_path, photo_path)
    txt_layer = Image.new("RGBA", canvas.size, (255, 255, 255, 0))
    draw = ImageDraw.Draw(txt_layer)
    
    font_size = 58
    line_spacing = 14
    font = ImageFont.truetype(font_path, font_size)
    lines = wrap_text_by_pixel(teks_judul, font, MAX_TEXT_WIDTH, draw)
    
    line_height = font_size + line_spacing
    total_text_height = (len(lines) * line_height) - line_spacing
    area_height = TEXT_BOX_BOTTOM - TEXT_BOX_TOP
    current_y = TEXT_BOX_TOP + ((area_height - total_text_height) // 2)
    
    for line in lines:
        draw.text((MARGIN_X + 3, current_y + 3), line, font=font, fill=(0, 0, 0, 85))
        draw.text((MARGIN_X, current_y), line, font=font, fill=(15, 15, 15, 255))
        current_y += line_height
        
    hasil = Image.alpha_composite(canvas, txt_layer).convert("RGB")
    hasil.save(output_path, quality=95)
    print(f"[SUKSES] Slide Judul tersimpan di: {output_path}")


def buat_slide_narasi(template_path, photo_path, teks_narasi, font_path, output_path):
    canvas = pasang_foto_dan_template(template_path, photo_path)
    draw = ImageDraw.Draw(canvas)
    
    font_size = 38
    line_spacing = 12
    font = ImageFont.truetype(font_path, font_size)
    lines = wrap_text_by_pixel(teks_narasi, font, MAX_TEXT_WIDTH, draw)
    
    line_height = font_size + line_spacing
    total_text_height = (len(lines) * line_height) - line_spacing
    area_height = TEXT_BOX_BOTTOM - TEXT_BOX_TOP
    current_y = TEXT_BOX_TOP + ((area_height - total_text_height) // 2)
    
    for i, line in enumerate(lines):
        words = line.split()
        if i == len(lines) - 1 or len(words) == 1:
            draw.text((MARGIN_X, current_y), line, font=font, fill=(20, 20, 20, 255))
        else:
            total_words_width = sum(draw.textbbox((0, 0), w, font=font)[2] - draw.textbbox((0, 0), w, font=font)[0] for w in words)
            total_space_needed = MAX_TEXT_WIDTH - total_words_width
            space_between_words = total_space_needed / (len(words) - 1)
            
            current_x = MARGIN_X
            for word in words:
                draw.text((current_x, current_y), word, font=font, fill=(20, 20, 20, 255))
                word_width = draw.textbbox((0, 0), word, font=font)[2] - draw.textbbox((0, 0), word, font=font)[0]
                current_x += word_width + space_between_words
                
        current_y += line_height
        
    hasil = canvas.convert("RGB")
    hasil.save(output_path, quality=95)
    print(f"[SUKSES] Slide Narasi tersimpan di: {output_path}")


# ==========================================
# EKSEKUSI PROGRAM
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

TEMPLATE_FILE = os.path.join(BASE_DIR, "template_suaradata.png")
FOTO_1 = os.path.join(BASE_DIR, "foto1.jpg")
FOTO_2 = os.path.join(BASE_DIR, "foto2.jpg")

FONT_BOLD = os.path.join(BASE_DIR, "Montserrat-Bold.ttf")
FONT_REGULAR = os.path.join(BASE_DIR, "OpenSans-Bold.ttf")

judul_berita = "Gerak Cepat Pemkab Bogor dan ALIMBO: Babak Akhir Produksi Miras PT Intitirta Sarimakmur."
narasi_berita = (
    "Jakarta. Komisi Pemberantasan Korupsi (KPK) resmi menetapkan dan "
    "menahan 5 orang sebagai tersangka dalam peristiwa tertangkap tangan "
    "terkait dugaan korupsi penggunaan Dana Siap Pakai (DSP) di Badan "
    "Nasional Penanggulangan Bencana (BNPB)."
)

print("Memulai proses pembuatan gambar...")

buat_slide_judul(
    template_path=TEMPLATE_FILE,
    photo_path=FOTO_1,
    teks_judul=judul_berita,
    font_path=FONT_BOLD,
    output_path=os.path.join(BASE_DIR, "hasil_slide1_judul.jpg")
)

buat_slide_narasi(
    template_path=TEMPLATE_FILE,
    photo_path=FOTO_2,
    teks_narasi=narasi_berita,
    font_path=FONT_REGULAR,
    output_path=os.path.join(BASE_DIR, "hasil_slide2_narasi.jpg")
)