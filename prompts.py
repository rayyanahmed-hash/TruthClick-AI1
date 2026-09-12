CLAIM_PROMPT='''Analyze a YouTube video's title and thumbnail to identify the specific promise made to a viewer. Do not decide whether the underlying story is true or false. Do not invent visual details. Return JSON only: {{"main_topic":"...","claim":"...","claim_type":"factual|opinion|prediction|entertainment|other","key_entities":["..."],"title_promise":"...","thumbnail_implication":"..."}}
TITLE:
{title}
The thumbnail is supplied separately to a vision-capable model.'''

CONTENT_PROMPT='''Evaluate whether the transcript supports this title/thumbnail promise. PROMISE: {promise_json} TRANSCRIPT: {transcript} Use semantic meaning, not keyword overlap. Mentioning the same person/topic is not sufficient. Return JSON only: {{"support_level":"strong_support|partial_support|weak_relevance|no_support|contradiction","evidence_found":true,"relevant_segments":[{{"start":0,"end":0,"topic":"...","evidence":"..."}}],"reason":"..."}}. Use only supplied transcript timestamps/evidence. Never invent them.'''

VERDICT_PROMPT='''Determine whether the title/thumbnail promise is meaningfully delivered by the available transcript evidence. PROMISE: {promise_json} CONTENT: {content_json} Return JSON only: {{"verdict":"CLICKBAIT|NON_CLICKBAIT|INCONCLUSIVE","confidence":0.0,"reason":"...","relevant_timestamps":[{{"start":0,"end":0}}]}}. Do not claim the underlying story is true or false. Use INCONCLUSIVE when evidence is insufficient.'''
