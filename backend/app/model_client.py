import os, io
import httpx
from PIL import Image, ImageDraw, ImageFont

# This module is an abstraction layer for external AI providers.
# For the starter, we provide a simple 'mock' generator using Pillow that overlays top/bottom text on the input image.
# Replace generate_sticker implementation with calls to your chosen Chinese AI provider (ModelScope / 阿里 / 百度 etc.)

MODEL_API_URL = os.getenv('MODEL_API_URL')
MODEL_API_KEY = os.getenv('MODEL_API_KEY')

async def generate_sticker_from_image_bytes(image_bytes: bytes, top_text: str | None, bottom_text: str | None) -> bytes:
    # simple PIL overlay implementation for demo
    with Image.open(io.BytesIO(image_bytes)).convert('RGBA') as base:
        w, h = base.size
        # create overlay for text
        overlay = Image.new('RGBA', base.size, (255,255,255,0))
        draw = ImageDraw.Draw(overlay)
        # choose a font - Pillow default may not support emojis; this is just a placeholder
        try:
            font = ImageFont.truetype('arial.ttf', max(20, w//12))
        except Exception:
            font = ImageFont.load_default()
        # draw outline text function
        def draw_text_with_outline(text, x, y):
            if not text:
                return
            # outline
            for dx in (-2,-1,0,1,2):
                for dy in (-2,-1,0,1,2):
                    draw.text((x+dx,y+dy), text, font=font, fill='black')
            draw.text((x,y), text, font=font, fill='white')
        if top_text:
            draw_text_with_outline(top_text, 10, 10)
        if bottom_text:
            draw_text_with_outline(bottom_text, 10, h - (w//10))
        result = Image.alpha_composite(base, overlay)
        out = io.BytesIO()
        result = result.convert('RGBA')
        result.save(out, format='PNG')
        return out.getvalue()

# Example placeholder for calling a remote provider
async def call_remote_provider(prompt: str, image_url: str | None = None) -> bytes:
    # Example using httpx to call external API - adapt to provider's spec
    if not MODEL_API_URL:
        raise RuntimeError('MODEL_API_URL not configured')
    headers = {}
    if MODEL_API_KEY:
        headers['Authorization'] = f'Bearer {MODEL_API_KEY}'
    async with httpx.AsyncClient(timeout=60) as client:
        payload = {'prompt': prompt}
        if image_url:
            payload['image_url'] = image_url
        resp = await client.post(MODEL_API_URL, json=payload, headers=headers)
        resp.raise_for_status()
        # provider may return base64 image
        data = resp.json()
        import base64
        return base64.b64decode(data['image_base64'])
