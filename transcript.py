from youtube_transcript_api import YouTubeTranscriptApi
def get_transcript(video_id:str)->list[dict]:
    try:fetched=YouTubeTranscriptApi().fetch(video_id)
    except Exception as exc:raise RuntimeError('A usable transcript could not be retrieved. The video may not have captions or captions may be unavailable.') from exc
    result=[]
    for s in fetched:
        text=str(getattr(s,'text','')).strip()
        if text:
            start=float(getattr(s,'start',0));duration=float(getattr(s,'duration',0));result.append({'start':start,'end':start+duration,'text':text})
    if not result:raise RuntimeError('The transcript is empty.')
    return result
def build_chunks(segments:list[dict],max_chars:int=7000)->list[dict]:
    chunks=[];cur=[];count=0
    for s in segments:
        if cur and count+len(s['text'])>max_chars:
            chunks.append({'start':cur[0]['start'],'end':cur[-1]['end'],'text':' '.join(x['text'] for x in cur)});cur=[];count=0
        cur.append(s);count+=len(s['text'])
    if cur:chunks.append({'start':cur[0]['start'],'end':cur[-1]['end'],'text':' '.join(x['text'] for x in cur)})
    return chunks
