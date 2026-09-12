import os,json
from groq import Groq
from prompts import CONTENT_PROMPT
from transcript import build_chunks
def _model():return os.getenv('GROQ_MODEL','meta-llama/llama-4-scout-17b-16e-instruct')
def _json(text):
    text=text.strip().replace('```json','').replace('```','').strip();a,b=text.find('{'),text.rfind('}')
    if a<0 or b<0:raise ValueError('Invalid JSON')
    return json.loads(text[a:b+1])
def _one(client,promise,chunk):
    p=CONTENT_PROMPT.format(promise_json=json.dumps(promise,ensure_ascii=False),transcript=json.dumps([chunk],ensure_ascii=False))
    r=client.chat.completions.create(model=_model(),messages=[{'role':'system','content':'Return valid JSON only.'},{'role':'user','content':p}],temperature=0,response_format={'type':'json_object'})
    return _json(r.choices[0].message.content or '')
def analyze_content(promise,transcript_segments,api_key):
    client=Groq(api_key=api_key);chunks=build_chunks(transcript_segments)[:int(os.getenv('MAX_TRANSCRIPT_CHUNKS','12'))];analyses=[]
    for c in chunks:
        try:
            x=_one(client,promise,c)
            if x.get('relevant_segments') or x.get('support_level') not in ('weak_relevance','no_support'):analyses.append(x)
        except Exception:continue
    if not analyses:return {'support_level':'no_support','evidence_found':False,'relevant_segments':[],'reason':'No meaningful supporting segment was identified in the analyzed transcript.'}
    p=f'''Consolidate these results for the promise below.\nPROMISE: {json.dumps(promise,ensure_ascii=False)}\nRESULTS: {json.dumps(analyses,ensure_ascii=False)}\nReturn JSON only: {{"support_level":"strong_support|partial_support|weak_relevance|no_support|contradiction","evidence_found":true,"relevant_segments":[{{"start":0,"end":0,"topic":"...","evidence":"..."}}],"reason":"..."}}\nUse only evidence/timestamps present in RESULTS. Return at most 5 strong segments.'''
    r=client.chat.completions.create(model=_model(),messages=[{'role':'system','content':'Return valid JSON only.'},{'role':'user','content':p}],temperature=0,response_format={'type':'json_object'})
    try:out=_json(r.choices[0].message.content or '')
    except Exception as exc:raise RuntimeError('Content-analysis response was not valid JSON.') from exc
    out.setdefault('relevant_segments',[]);out.setdefault('evidence_found',bool(out['relevant_segments']));out.setdefault('support_level','no_support');out.setdefault('reason','No explanation returned.');return out
