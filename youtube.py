import re
import yt_dlp
VIDEO_ID=re.compile(r'^[A-Za-z0-9_-]{11}$')
def extract_video_id(url:str)->str:
    if not isinstance(url,str):raise ValueError('YouTube URL must be text.')
    for p in [r'(?:youtube\.com/watch\?v=)([A-Za-z0-9_-]{11})',r'(?:youtu\.be/)([A-Za-z0-9_-]{11})',r'(?:youtube\.com/shorts/)([A-Za-z0-9_-]{11})',r'(?:youtube\.com/embed/)([A-Za-z0-9_-]{11})']:
        m=re.search(p,url.strip())
        if m and VIDEO_ID.match(m.group(1)):return m.group(1)
    raise ValueError('Invalid YouTube video URL.')
def validate_youtube_url(url:str)->bool:
    try:extract_video_id(url);return True
    except ValueError:return False
def get_video_metadata(url:str)->dict:
    vid=extract_video_id(url); canonical=f'https://www.youtube.com/watch?v={vid}'
    try:
        with yt_dlp.YoutubeDL({'quiet':True,'no_warnings':True,'skip_download':True}) as ydl:info=ydl.extract_info(canonical,download=False)
    except Exception as exc:raise RuntimeError('YouTube information could not be retrieved. The video may be private, restricted, unavailable, or temporarily inaccessible.') from exc
    return {'video_id':vid,'title':info.get('title') or 'Unknown title','thumbnail':info.get('thumbnail') or f'https://i.ytimg.com/vi/{vid}/hqdefault.jpg','channel':info.get('channel') or info.get('uploader') or 'Unknown channel','duration':info.get('duration'),'url':info.get('webpage_url') or canonical}
