import os
from dotenv import load_dotenv
load_dotenv(".env")
print('API_KEY_OK', bool(os.getenv('GEMINI_API_KEY')))
print('MODEL', os.getenv('GEMINI_IMAGE_MODEL'))
try:
    from google import genai
    from google.genai import types
    client = genai.Client(api_key=os.getenv('GEMINI_API_KEY'))
    resp = client.models.generate_content(
        model=os.getenv('GEMINI_IMAGE_MODEL', 'gemini-2.5-flash-image'),
        contents='A simple red apple on a white background',
        config=types.GenerateContentConfig(response_modalities=['TEXT','IMAGE'])
    )
    print('RESPONSE_TYPE', type(resp).__name__)
    print('HAS_TEXT', bool(getattr(resp, 'text', None)))
    candidate = (getattr(resp, 'candidates', None) or [None])[0]
    content = getattr(candidate, 'content', None)
    parts = getattr(content, 'parts', None) or []
    print('PARTS', len(parts))
except Exception as e:
    import traceback
    traceback.print_exc()
    print('ERROR_CLASS', type(e).__name__)
    print('ERROR_MSG', str(e)[:500])
