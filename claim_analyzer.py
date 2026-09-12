import os,json,base64,requests
from groq import Groq
from prompts import CLAIM_PROMPT
def _model():return os.getenv('GROQ_MODEL','meta-llama/llama-4-scout-17b-16e-instruct')
def _image_data(url):
    try:
        r=requests.get(url,timeout=15);r.raise_for_status();mime=r.headers.get('content-type','image/jpeg').split(';')[0]
        return f'data:{mime};base64,{base64.b64encode(r.content).decode()}'
    except Exception:return None
def _json(text):
    text=text.strip().replace('```json','').replace('```','').strip();a,b=text.find('{'),text.rfind('}')
    if a<0 or b<0:raise ValueError('Invalid JSON')
    return json.loads(text[a:b+1])
def analyze_promise(metadata,api_key):
    client=Groq(api_key=api_key);content=[{'type':'text','text':CLAIM_PROMPT.format(title=metadata.get('title',''))}]
    image=_image_data(metadata.get('thumbnail',''))
    if image:content.append({'type':'image_url','image_url':{'url':image}})
    else:content[0]['text']+='\nThumbnail unavailable; do not invent visual details.'
    try:
        r=client.chat.completions.create(model=_model(),messages=[{'role':'system','content':'Return valid JSON only.'},{'role':'user','content':content}],temperature=.1,response_format={'type':'json_object'})
        data=_json(r.choices[0].message.content or '')
    except Exception as exc:raise RuntimeError('Groq could not analyze the title/thumbnail. Check GROQ_MODEL and API access.') from exc
    required=['main_topic','claim','claim_type','key_entities','title_promise','thumbnail_implication'];missing=[x for x in required if x not in data]
    if missing:raise RuntimeError('AI response missing: '+', '.join(missing))
    return data
