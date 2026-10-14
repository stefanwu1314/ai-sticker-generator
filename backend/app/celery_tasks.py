import os, io, base64, json
import httpx
from PIL import Image, ImageDraw, ImageFont

MODEL_API_URL = os.getenv('MODEL_API_URL')
MODEL_API_KEY = os.getenv('MODEL_API_KEY')
VOLCANO_API_URL = os.getenv('VOLCANO_API_URL')
VOLCANO_API_KEY = os.getenv('VOLCANO_API_KEY')
MODEL_PROVIDER = os.getenv('MODEL_PROVIDER', 'mock').lower()
VOLCANO_MODEL = os.getenv('VOLCANO_MODEL', 'doubao-seed-1-6')

async def generate_sticker_from_image_bytes_mock(image_bytes: bytes, top_text: str | None, bottom_text: str | None) -> bytes:
    with Image.open(io.BytesIO(image_bytes)).convert('RGBA') as base:
        w, h = base.size
        overlay = Image.new('RGBA', base.size, (255,255,255,0))
        draw = ImageDraw.Draw(overlay)
        try:
            font = ImageFont.truetype('arial.ttf', max(20, w//12))
        except Exception:
            font = ImageFont.load_default()
        def draw_text_with_outline(text, x, y):
            if not text:
                return
            for dx in (-2,-1,0,1,2):
                for dy in (-2,-1,0,1,2):
                    draw.text((x+dx, y+dy), text, font=font, fill='black')
            draw.text((x, y), text, font=font, fill='white')
        if top_text:
            draw_text_with_outline(top_text, 10, 10)
        if bottom_text:
            draw_text_with_outline(bottom_text, 10, h - (w//10))
        result = Image.alpha_composite(base, overlay)
        out = io.BytesIO()
        result = result.convert('RGBA')
        result.save(out, format='PNG')
        return out.getvalue()

async def _volcano_image_generation(prompt: str, input_image_bytes: bytes, reference_image_bytes: bytes | None = None) -> bytes:
    api_url = VOLCANO_API_URL or MODEL_API_URL
    api_key = VOLCANO_API_KEY or MODEL_API_KEY
    if not api_url:
        raise RuntimeError('VOLCANO_API_URL or MODEL_API_URL must be configured')
    if not api_key:
        raise RuntimeError('VOLCANO_API_KEY or MODEL_API_KEY must be configured')

    payload = {
        'model': VOLCANO_MODEL,
        'prompt': prompt,
        'size': '1024x1024',
        'response_format': 'b64_json',
        'n': 1,
        'image': {
            'base64': base64.b64encode(input_image_bytes).decode('utf-8')
        }
    }
    if reference_image_bytes:
        payload['reference_image'] = {
            'base64': base64.b64encode(reference_image_bytes).decode('utf-8')
        }

    endpoint = api_url.rstrip('/') + '/api/v3/images/generations'
    headers = {'Content-Type': 'application/json', 'Authorization': f'Bearer {api_key}'}

    async with httpx.AsyncClient(timeout=120) as client:
        resp = await client.post(endpoint, json=payload, headers=headers)
        body = resp.json()
        if resp.status_code >= 400:
            raise RuntimeError(f'Volcano API error {resp.status_code}: {body}')

        # OpenAI-compatible response shape: { data: [{ b64_json: '...' }] }
        if isinstance(body, dict) and 'data' in body and body['data']:
            item = body['data'][0]
            if 'b64_json' in item:
                return base64.b64decode(item['b64_json'])
            if 'url' in item:
                img = await client.get(item['url'])
                img.raise_for_status()
                return img.content

        # Some vendors return a different shape: { output: [{ image: 'base64' }] }
        if isinstance(body, dict) and 'output' in body and body['output']:
            item = body['output'][0]
            if 'image' in item:
                return base64.b64decode(item['image'])
            if 'b64_json' in item:
                return base64.b64decode(item['b64_json'])

        raise RuntimeError(f'Unsupported Volcano response format: {body}')

async def generate_sticker_from_image_bytes(image_bytes: bytes, top_text: str | None, bottom_text: str | None, reference_image_bytes: bytes | None = None) -> bytes:
    provider = MODEL_PROVIDER
    prompt = ' '.join(filter(None, [top_text, bottom_text])).strip() or 'cute pet meme sticker, cartoon style, expressive face, transparent background, high detail'

    if provider == 'volcano':
        try:
            return await _volcano_image_generation(prompt, image_bytes, reference_image_bytes)
        except Exception as exc:
            print('Volcano image generation failed, falling back to mock:', exc)
            return await generate_sticker_from_image_bytes_mock(image_bytes, top_text, bottom_text)

    return await generate_sticker_from_image_bytes_mock(image_bytes, top_text, bottom_text)

async def call_remote_provider(prompt: str, image_url: str | None = None, reference_url: str | None = None) -> bytes:
    if not MODEL_API_URL and not VOLCANO_API_URL:
        raise RuntimeError('No AI API URL configured')
    if MODEL_PROVIDER == 'volcano':
        if not VOLCANO_API_KEY and not MODEL_API_KEY:
            raise RuntimeError('VOLCANO_API_KEY or MODEL_API_KEY missing')
        # best-effort helper if you want to call a model directly by URL reference later
        headers = {'Authorization': f'Bearer {VOLCANO_API_KEY or MODEL_API_KEY}', 'Content-Type': 'application/json'}
        payload = {'model': VOLCANO_MODEL, 'prompt': prompt, 'n': 1, 'size': '1024x1024'}
        if image_url:
            payload['image_url'] = image_url
        if reference_url:
            payload['reference_image_url'] = reference_url
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.post((VOLCANO_API_URL or MODEL_API_URL).rstrip('/') + '/api/v3/images/generations', json=payload, headers=headers)
            body = resp.json()
            if resp.status_code >= 400:
                raise RuntimeError(f'Volcano provider error {resp.status_code}: {body}')
            if 'data' in body and body['data'] and 'b64_json' in body['data'][0]:
                return base64.b64decode(body['data'][0]['b64_json'])
            raise RuntimeError(f'Unsupported provider response for remote provider: {body}')
    raise RuntimeError('No remote provider configured')
