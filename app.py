import os
import streamlit as st
from dotenv import load_dotenv
from youtube import validate_youtube_url, get_video_metadata
from transcript import get_transcript
from claim_analyzer import analyze_promise
from content_analyzer import analyze_content
from verdict import generate_verdict

load_dotenv()
st.set_page_config(page_title='TruthClick AI', page_icon='🔎', layout='wide')

st.markdown('''<style>
.stApp{background:#f5f7fb}.block-container{max-width:1180px;padding-top:2rem;padding-bottom:4rem}
.hero{background:linear-gradient(135deg,#0f172a,#1e3a8a);color:white;border-radius:22px;padding:38px 42px;margin-bottom:24px;box-shadow:0 12px 35px rgba(15,23,42,.12)}
.hero h1{margin:0 0 8px;font-size:3rem}.tagline{font-size:1.35rem;font-weight:700}.hero p{color:#dbeafe;max-width:800px}
.card{background:white;border:1px solid #e2e8f0;border-radius:16px;padding:22px;margin-bottom:16px;box-shadow:0 5px 20px rgba(15,23,42,.05)}
.section-title{font-size:1.45rem;font-weight:800;margin:26px 0 12px}.label{color:#64748b;font-size:.82rem;font-weight:700;text-transform:uppercase;letter-spacing:.04em}
.verdict{border-radius:18px;padding:28px;text-align:center;margin:15px 0 20px;background:white;border:1px solid #e2e8f0}.clickbait{background:#fff7f7;border-color:#fecaca}.non-clickbait{background:#f5fff8;border-color:#bbf7d0}.inconclusive{background:#fffcf0;border-color:#fde68a}.verdict-name{font-size:2rem;font-weight:900}
.evidence{border-left:4px solid #2563eb;background:#f8fafc;padding:15px 18px;border-radius:0 12px 12px 0;margin:10px 0}.disclaimer{background:#eef2ff;border:1px solid #c7d2fe;color:#3730a3;border-radius:12px;padding:14px 16px}.small{color:#64748b;font-size:.88rem}
div.stButton>button{width:100%;border-radius:10px;font-weight:800;min-height:46px}
</style>''', unsafe_allow_html=True)

def secret(name):
    value=os.getenv(name)
    if value:return value
    try:return st.secrets.get(name,'')
    except Exception:return ''

def ts(seconds):
    if seconds is None:return 'Unknown'
    s=max(0,int(seconds)); h,r=divmod(s,3600); m,s=divmod(r,60)
    return f'{h}:{m:02d}:{s:02d}' if h else f'{m}:{s:02d}'

def pct(v):
    try:return f'{float(v)*100:.0f}%'
    except:return 'N/A'

st.markdown('''<div class="hero"><h1>TruthClick AI</h1><div class="tagline">Does the video deliver what the title promises?</div><p>Analyze a YouTube video's title, thumbnail, and transcript to see whether the actual content supports the promise made to viewers.</p></div>''', unsafe_allow_html=True)
st.markdown('<div class="section-title">Analyze a YouTube Video</div>', unsafe_allow_html=True)
url=st.text_input('YouTube URL',placeholder='https://www.youtube.com/watch?v=...')
clicked=st.button('🔎 ANALYZE VIDEO',type='primary')
st.markdown('<p class="small">TruthClick AI compares the title/thumbnail promise with available transcript evidence.</p>',unsafe_allow_html=True)

if clicked:
    if not validate_youtube_url(url):st.error('Please enter a valid YouTube video URL.');st.stop()
    key=secret('GROQ_API_KEY')
    if not key:st.error('Groq API key is not configured. Add GROQ_API_KEY to .env or Streamlit Secrets.');st.stop()
    try:
        with st.status('Analyzing video...',expanded=True) as status:
            st.write('Fetching video information'); metadata=get_video_metadata(url)
            st.write('Retrieving transcript and timestamps'); transcript=get_transcript(metadata['video_id'])
            st.write('Understanding title and thumbnail'); promise=analyze_promise(metadata,key)
            st.write('Comparing promise with actual video content'); content=analyze_content(promise,transcript,key)
            st.write('Generating final verdict'); result=generate_verdict(promise,content,key)
            status.update(label='Analysis complete',state='complete',expanded=False)
        st.session_state['analysis']={'metadata':metadata,'promise':promise,'content':content,'result':result}
    except Exception as exc:
        st.error(f'Analysis could not be completed: {exc}');st.stop()

data=st.session_state.get('analysis')
if data:
    metadata,promise,content,result=data['metadata'],data['promise'],data['content'],data['result']
    st.markdown('<div class="section-title">Video</div>',unsafe_allow_html=True)
    a,b=st.columns([1,2])
    with a:
        if metadata.get('thumbnail'):st.image(metadata['thumbnail'],use_container_width=True)
    with b:
        st.markdown(f"### {metadata.get('title','Unknown title')}")
        st.write(f"**Channel:** {metadata.get('channel','Unknown')}")
        st.write(f"**Duration:** {ts(metadata.get('duration'))}")
        st.link_button('Open on YouTube',metadata.get('url',url),use_container_width=True)
    st.markdown('<div class="section-title">What Does This Video Promise?</div>',unsafe_allow_html=True)
    a,b=st.columns(2)
    with a:st.markdown(f'<div class="card"><div class="label">Title Claim</div><p>{promise.get("claim","Not determined")}</p></div>',unsafe_allow_html=True)
    with b:st.markdown(f'<div class="card"><div class="label">Thumbnail Implication</div><p>{promise.get("thumbnail_implication","No specific implication identified")}</p></div>',unsafe_allow_html=True)
    verdict=str(result.get('verdict','INCONCLUSIVE')).upper(); css={'CLICKBAIT':'clickbait','NON_CLICKBAIT':'non-clickbait'}.get(verdict,'inconclusive')
    st.markdown(f'<div class="verdict {css}"><div class="label">AI Verdict</div><div class="verdict-name">{verdict.replace("_"," ")}</div><div style="font-size:1.3rem;font-weight:800">{pct(result.get("confidence"))} Confidence</div></div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">Why?</div>',unsafe_allow_html=True)
    st.markdown(f'<div class="card">{result.get("reason","No explanation available.")}</div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">Evidence From The Video</div>',unsafe_allow_html=True)
    segments=content.get('relevant_segments',[])
    if segments:
        for item in segments:
            st.markdown(f'<div class="evidence"><strong>{ts(item.get("start"))} → {ts(item.get("end"))}</strong><br><span class="small">{item.get("topic","Relevant segment")}</span><br>{item.get("evidence","")}</div>',unsafe_allow_html=True)
    else:st.info('No strong supporting segment was found.')
    st.markdown(f'<div class="card"><div class="label">Evidence Strength</div><div style="font-size:1.4rem;font-weight:800">{content.get("support_level","unknown").replace("_"," ").title()}</div><p>{content.get("reason","")}</p></div>',unsafe_allow_html=True)
    st.markdown('<div class="section-title">How TruthClick AI Works</div>',unsafe_allow_html=True)
    for col,(n,t,d) in zip(st.columns(5),[('01','Analyze Video','Retrieve metadata, thumbnail and transcript.'),('02','Understand Promise','Extract what title and thumbnail lead viewers to expect.'),('03','Examine Content','Find meaningful evidence in the transcript.'),('04','Compare','Semantically compare promise with actual content.'),('05','Verdict','Return Clickbait, Non-Clickbait or Inconclusive.')]):
        with col:st.markdown(f'<div class="card"><div class="label">{n}</div><strong>{t}</strong><p class="small">{d}</p></div>',unsafe_allow_html=True)
    st.markdown('<div class="disclaimer"><strong>Responsible AI:</strong> TruthClick AI evaluates whether available video content supports the promise made by its title and thumbnail. It does not determine whether underlying information is objectively true or false. AI confidence is an estimate, not proof of accuracy.</div>',unsafe_allow_html=True)
