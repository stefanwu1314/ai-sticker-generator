import os
import io
import base64
import httpx
from PIL import Image, ImageDraw, ImageFont

# Provider abstraction for external AI services.
# Supported providers:
#   - volcano: Volcengine Ark (ByteDance) image generation API (OpenAI-compatible)
#   - mock: local Pillow fallback that overlays top/bottom text (for offline dev)

MODEL_API_URL = os.getenv('MODEL_API_URL')
MODEL_API_KEY = os.getenv('MODEL_API_KEY')
VOLCANO_API_URL = os.getenv('VOLCANO_API_URL')
VOLCANO_API_KEY = os.getenv('VOLCANO_API_KEY')
MODEL_PROVIDER = os.getenv('MODEL_PROVIDER', 'mock').lower()
VOLCANO_MODEL = os.getenv('VOLCANO_MODEL', 'doubao-seedream-4-0-250828')
VOLCANO_SIZE = os.getenv('VOLCANO_SIZE', '1024x1024')


async def generate_sticker_from_image_bytes_mock(image_bytes: bytes, top_text: str | None, bottom_text: str | None) -> bytes:
    with Image.open(io.BytesIO(image_bytes)).convert('RGBA') as base:
        w, h = base.size
        overlay = Image.new('RGBA', base.size, (255, 255, 255, 0))
        draw = ImageDraw.Draw(overlay)
        try:
            font = ImageFont.truetype('arial.ttf', max(20, w // 12))
        except Exception:
            font = ImageFont.load_default()

        def draw_text_with_outline(text, x, y):
            if not text:
                return
            for dx in (-2, -1, 0, 1, 2):
                for dy in (-2, -1, 0, 1, 2):
                    draw.text((x + dx, y + dy), text, font=font, fill='black')
            draw.text((x, y), text, font=font, fill='white')

        if top_text:
            draw_text_with_outline(top_text, 10, 10)
        if bottom_text:
            draw_text_with_outline(bottom_text, 10, h - (w // 10))
        result = Image.alpha_composite(base, overlay)
        out = io.BytesIO()
        result.convert('RGBA').save(out, format='PNG')
        return out.getvalue()


def _to_data_uri(image_bytes: bytes) -> str:
    # Ark image API requires the data URI prefix, e.g. data:image/png;base64,xxx
    return 'data:image/png;base64,' + base64.b64encode(image_bytes).decode('utf-8')


def _build_prompt(top_text: str | None, bottom_text: str | None, has_reference: bool) -> str:
    if top_text or bottom_text:
        text_line = ' / '.join(t for t in (top_text, bottom_text) if t)
        parts = [f'Pet meme sticker with the text "{text_line}" written on the image']
    else:
        parts = ['Cute pet meme sticker']
    parts.append("cartoon sticker style, keep the pet's face and pose recognizable, expressive, clean simple background, high detail")
    if has_reference:
        parts.append('follow the style of the second reference image')
    return ', '.join(parts)


async def _volcano_image_generation(prompt: str, input_image_bytes: bytes, reference_image_bytes: bytes | None = None) -> bytes:
    api_url = VOLCANO_API_URL or MODEL_API_URL
    api_key = VOLCANO_API_KEY or MODEL_API_KEY
    if not api_url:
        raise RuntimeError('VOLCANO_API_URL or MODEL_API_URL must be configured')
    if not api_key:
        raise RuntimeError('VOLCANO_API_KEY or MODEL_API_KEY must be configured')

    images = [_to_data_uri(input_image_bytes)]
    if reference_image_bytes:
        images.append(_to_data_uri(reference_image_bytes))

    payload = {
        'model': VOLCANO_MODEL,
        'prompt': prompt,
        'image': images if len(images) > 1 else images[0],
        'size': VOLCANO_SIZE,
        'response_format': 'b64_json',
        'watermark': False,
    }

    endpoint = api_url.rstrip('/') + '/api/v3/images/generations'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(endpoint, json=payload, headers=headers)
        if resp.status_code >= 400:
            raise RuntimeError(f'Volcano API error {resp.status_code}: {resp.text[:500]}')
        body = resp.json()
        data = body.get('data') if isinstance(body, dict) else None
        if data:
            item = data[0]
            if item.get('b64_json'):
                return base64.b64decode(item['b64_json'])
            if item.get('url'):
                img = await client.get(item['url'])
                img.raise_for_status()
                return img.content
        raise RuntimeError(f'Unsupported Volcano response format: {str(body)[:500]}')


async def generate_sticker_from_image_bytes(
    image_bytes: bytes,
    top_text: str | None,
    bottom_text: str | None,
    reference_image_bytes: bytes | None = None,
) -> bytes:
    provider = MODEL_PROVIDER

    if provider == 'volcano':
        prompt = _build_prompt(top_text, bottom_text, reference_image_bytes is not None)
        try:
            return await _volcano_image_generation(prompt, image_bytes, reference_image_bytes)
        except Exception as exc:
            print(f'Volcano image generation failed, falling back to mock: {exc}')
            return await generate_sticker_from_image_bytes_mock(image_bytes, top_text, bottom_text)

    return await generate_sticker_from_image_bytes_mock(image_bytes, top_text, bottom_text)
