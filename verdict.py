import os,json
from groq import Groq
from prompts import VERDICT_PROMPT
def _model():return os.getenv('GROQ_MODEL','meta-llama/llama-4-scout-17b-16e-instruct')
def _json(text):
    text=text.strip().replace('```json','').replace('```','').strip();a,b=text.find('{'),text.rfind('}')
    if a<0 or b<0:raise ValueError('Invalid JSON')
    return json.loads(text[a:b+1])
def generate_verdict(promise,content,api_key):
    client=Groq(api_key=api_key);p=VERDICT_PROMPT.format(promise_json=json.dumps(promise,ensure_ascii=False),content_json=json.dumps(content,ensure_ascii=False))
    try:
        r=client.chat.completions.create(model=_model(),messages=[{'role':'system','content':'Return valid JSON only.'},{'role':'user','content':p}],temperature=0,response_format={'type':'json_object'});out=_json(r.choices[0].message.content or '')
    except Exception as exc:raise RuntimeError('Groq could not generate the final verdict.') from exc
    v=str(out.get('verdict','INCONCLUSIVE')).upper();v=v if v in {'CLICKBAIT','NON_CLICKBAIT','INCONCLUSIVE'} else 'INCONCLUSIVE'
    try:c=float(out.get('confidence',0))
    except:c=0
    return {'verdict':v,'confidence':max(0,min(1,c)),'reason':str(out.get('reason','Insufficient explanation.')),'relevant_timestamps':out.get('relevant_timestamps',[])}
