from PIL import Image, ImageDraw, ImageFont, ImageEnhance, ImageFilter
import os
import logging
from typing import Tuple, Optional
import colorsys

def validate_text_input(text):
    """入力テキストのバリデーション"""
    if not text or not text.strip():
        raise ValueError("テキストが入力されていません")
    if len(text) > 100:
        raise ValueError("テキストは100文字以内で入力してください")
    return text.strip()

def validate_font_size(size):
    """フォントサイズのバリデーション"""
    try:
        size = int(size)
        if not (8 <= size <= 72):
            raise ValueError("フォントサイズは8px～72pxの範囲で指定してください")
        return size
    except (TypeError, ValueError):
        raise ValueError("不正なフォントサイズです")

def validate_color(color):
    """カラーコードのバリデーション"""
    if not isinstance(color, str) or not color.startswith('#') or len(color) != 7:
        raise ValueError("不正なカラーコードです")
    try:
        int(color[1:], 16)
        return color
    except ValueError:
        raise ValueError("不正なカラーコードです")

def hex_to_rgb(hex_color: str) -> Tuple[int, int, int]:
    """16進数カラーコードをRGBに変換"""
    hex_color = hex_color.lstrip('#')
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))

def validate_shadow(shadow_enabled: bool, shadow_blur: int, shadow_color: str) -> Tuple[bool, int, str]:
    """シャドウ設定のバリデーション"""
    if shadow_blur < 0 or shadow_blur > 20:
        shadow_blur = 5
    if not shadow_color.startswith('#') or len(shadow_color) != 7:
        shadow_color = '#000000'
    return shadow_enabled, shadow_blur, shadow_color

def validate_outline(outline_enabled: bool, outline_size: int, outline_color: str) -> Tuple[bool, int, str]:
    """輪郭線設定のバリデーション"""
    if outline_size < 0 or outline_size > 5:
        outline_size = 1
    if not outline_color.startswith('#') or len(outline_color) != 7:
        outline_color = '#000000'
    return outline_enabled, outline_size, outline_color

def validate_gradient(gradient_enabled: bool, gradient_color: str) -> Tuple[bool, str]:
    """グラデーション設定のバリデーション"""
    if not gradient_color.startswith('#') or len(gradient_color) != 7:
        gradient_color = '#000000'
    return gradient_enabled, gradient_color

def load_font(font_name, font_size):
    """フォントの読み込みと検証"""
    try:
        # カスタムフォントの場合
        if os.path.isfile(font_name):
            logging.info(f"Loading custom font: {font_name}")
            return ImageFont.truetype(font_name, font_size)

        # デフォルトのNoto Sans CJKフォントパス
        default_font_path = '/nix/store/a8h57nc89w8wqgg3rqkrw4cxc1x8z7c3-noto-fonts-cjk-2.004/share/fonts/opentype/noto-cjk/NotoSansCJK-Regular.ttc'

        if os.path.exists(default_font_path):
            logging.info(f"Using default Noto Sans CJK font: {default_font_path}")
            return ImageFont.truetype(default_font_path, font_size)

        # フォールバック：デフォルトフォント
        logging.warning("Default font not found, using fallback font")
        return ImageFont.load_default()

    except Exception as e:
        logging.error(f"Font loading error: {str(e)}")
        logging.warning("Using default font as fallback")
        return ImageFont.load_default()

def apply_shadow(img: Image.Image, text_mask: Image.Image, shadow_blur: int, shadow_color: str) -> Image.Image:
    """ドロップシャドウを適用"""
    shadow = Image.new('RGBA', img.size, (0, 0, 0, 0))
    shadow_rgb = hex_to_rgb(shadow_color)
    shadow.paste((shadow_rgb[0], shadow_rgb[1], shadow_rgb[2], 255), mask=text_mask)
    shadow = shadow.filter(ImageFilter.GaussianBlur(radius=shadow_blur))
    return Image.alpha_composite(img, shadow)

def apply_outline(draw: ImageDraw.ImageDraw, text: str, x: int, y: int, font: ImageFont.FreeTypeFont, 
                 outline_size: int, outline_color: str) -> None:
    """テキストの輪郭を描画"""
    for offset_x in range(-outline_size, outline_size + 1):
        for offset_y in range(-outline_size, outline_size + 1):
            if offset_x == 0 and offset_y == 0:
                continue
            draw.text((x + offset_x, y + offset_y), text, font=font, fill=outline_color)

def apply_gradient(img: Image.Image, text_mask: Image.Image, color: str, gradient_color: str) -> Image.Image:
    """グラデーションを適用"""
    start_rgb = hex_to_rgb(color)
    end_rgb = hex_to_rgb(gradient_color)

    gradient = Image.new('RGBA', img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(gradient)

    for y in range(img.size[1]):
        ratio = y / img.size[1]
        current_color = tuple(int(start_rgb[i] + (end_rgb[i] - start_rgb[i]) * ratio) for i in range(3))
        draw.line([(0, y), (img.size[0], y)], fill=current_color + (255,))

    gradient.putalpha(text_mask.split()[-1])
    return Image.alpha_composite(img, gradient)

def generate_transparent_text(text, output_path, font_size=16, color="#000000", font_name="Noto Sans JP", 
                            line_height=1.5, shadow_enabled=False, shadow_blur=5, shadow_color="#000000",
                            outline_enabled=False, outline_size=1, outline_color="#000000",
                            gradient_enabled=False, gradient_color="#000000"):
    """透過PNGテキスト画像を生成する"""
    temp_img = None
    img = None
    text_mask = None

    try:
        # 入力値の検証
        text = validate_text_input(text)
        font_size = validate_font_size(font_size)
        color = validate_color(color)
        shadow_enabled, shadow_blur, shadow_color = validate_shadow(shadow_enabled, shadow_blur, shadow_color)
        outline_enabled, outline_size, outline_color = validate_outline(outline_enabled, outline_size, outline_color)
        gradient_enabled, gradient_color = validate_gradient(gradient_enabled, gradient_color)

        # 行間の検証
        try:
            line_height = float(line_height)
            if not (1.0 <= line_height <= 2.5):
                raise ValueError
        except (TypeError, ValueError):
            line_height = 1.5
            logging.warning("Invalid line height, using default value 1.5")

        # フォントの読み込み
        font = load_font(font_name, font_size)

        # 高解像度設定 (4倍の解像度で作成)
        scale_factor = 4  
        scaled_font_size = font_size * scale_factor
        scaled_font = load_font(font_name, scaled_font_size)

        # テキストサイズの計算
        temp_img = Image.new('RGBA', (1, 1), (0, 0, 0, 0))
        temp_draw = ImageDraw.Draw(temp_img)

        lines = [line.strip() for line in text.split('\n')]
        line_sizes = []
        total_width = 0
        total_height = 0

        for line in lines:
            bbox = temp_draw.textbbox((0, 0), line, font=scaled_font)
            width = bbox[2] - bbox[0]
            height = bbox[3] - bbox[1]
            line_sizes.append((width, height))
            total_width = max(total_width, width)
            total_height += height * line_height

        # パディングとシャドウ用の余白を追加
        padding = 20 * scale_factor
        shadow_padding = shadow_enabled * (shadow_blur * 2 * scale_factor)
        outline_padding = outline_enabled * (outline_size * 2 * scale_factor)

        img_width = total_width + (padding * 2) + shadow_padding + outline_padding
        img_height = int(total_height + (padding * 2) + shadow_padding + outline_padding)

        # 最終的な画像の生成（高解像度）
        img = Image.new('RGBA', (img_width, img_height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        # テキストマスクの生成（シャドウとグラデーション用）
        text_mask = Image.new('L', img.size, 0)
        mask_draw = ImageDraw.Draw(text_mask)

        # テキストの描画
        y = padding + shadow_padding // 2 + outline_padding // 2
        for i, line in enumerate(lines):
            bbox = draw.textbbox((0, 0), line, font=scaled_font)
            width = bbox[2] - bbox[0]
            x = (img_width - width) // 2

            if shadow_enabled:
                mask_draw.text((x, y), line, font=scaled_font, fill=255)
                img = apply_shadow(img, text_mask, shadow_blur * scale_factor, shadow_color)
                text_mask = Image.new('L', img.size, 0)
                mask_draw = ImageDraw.Draw(text_mask)

            if outline_enabled:
                apply_outline(draw, line, x, y, scaled_font, outline_size * scale_factor, outline_color)

            if gradient_enabled:
                mask_draw.text((x, y), line, font=scaled_font, fill=255)
                img = apply_gradient(img, text_mask, color, gradient_color)
            else:
                draw.text((x, y), line, font=scaled_font, fill=color)

            y += int(line_sizes[i][1] * line_height)

        # 画像を元のサイズにリサイズ（高品質な縮小処理）
        final_width = img_width // scale_factor
        final_height = img_height // scale_factor
        img = img.resize((final_width, final_height), Image.LANCZOS)

        # 画像の保存（高品質設定）
        img.save(output_path, 'PNG', optimize=True, quality=95)
        logging.info(f"Generated image successfully: {output_path}")

    except Exception as e:
        logging.error(f"Error generating image: {str(e)}")
        raise
    finally:
        # リソースの解放
        if temp_img is not None:
            temp_img.close()
        if img is not None:
            img.close()
        if text_mask is not None:
            text_mask.close()