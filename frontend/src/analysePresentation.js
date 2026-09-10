const CHARACTER_STOP = new Set([
  'Also',
  'Are',
  'By',
  'Inside',
  'The',
  'She',
  'He',
  'They',
  'We',
  'It',
  'I',
  'You',
  'What',
  'When',
  'Then',
  'One',
  'Two',
  'My',
  'Her',
  'His',
  'Their',
]);

const POS_LABELS = {
  PROPN: 'names',
  NOUN: 'nouns',
  VERB: 'verbs',
  ADJ: 'adjectives',
  ADV: 'adverbs',
  PRON: 'pronouns',
  DET: 'determiners',
  ADP: 'prepositions',
  CCONJ: 'conjunctions',
  SCONJ: 'conjunctions',
  AUX: 'auxiliary verbs',
  PART: 'particles',
  NUM: 'numbers',
  INTJ: 'interjections',
  PUNCT: 'punctuation',
};

export function fleschEaseLabel(score) {
  if (score == null || Number.isNaN(score)) return null;
  if (score >= 90) return 'Very easy — comfortable for young readers.';
  if (score >= 80) return 'Fairly easy — similar to popular middle-grade fiction.';
  if (score >= 70) return 'Plain English — clear for most teen readers.';
  if (score >= 60) return 'Moderate — some sentences may need a second read.';
  if (score >= 50) return 'Fairly difficult — denser vocabulary or longer sentences.';
  if (score >= 30) return 'Difficult — academic or highly complex prose.';
  return 'Very difficult — may challenge even confident adult readers.';
}

export function fleschGradeLabel(grade) {
  if (grade == null || Number.isNaN(grade)) return null;
  const rounded = Math.round(grade);
  return `Roughly suitable for readers around school year ${rounded} (UK-style estimate).`;
}

export function sentimentPlain(sentiment) {
  if (!sentiment || sentiment.unavailable) return null;
  const label = (sentiment.label || 'neutral').toLowerCase();
  const score = sentiment.polarity_score;
  const pos = sentiment.positive_hits ?? 0;
  const neg = sentiment.negative_hits ?? 0;
  const strength =
    score != null && Math.abs(score) >= 0.15
      ? 'noticeably'
      : score != null && Math.abs(score) >= 0.05
        ? 'slightly'
        : 'mildly';
  const wordBalance =
    pos === 0 && neg === 0
      ? 'Few strongly positive or negative words were detected.'
      : `Bloom counted ${pos} positive word${pos === 1 ? '' : 's'} and ${neg} negative word${neg === 1 ? '' : 's'}.`;
  return `Overall word choice feels ${strength} ${label}. ${wordBalance}`;
}

export function emotionLead(emotion) {
  if (!emotion || emotion.unavailable || !emotion.dominant_emotion) return null;
  const key = emotion.dominant_emotion.toLowerCase();
  const leads = {
    fear: 'The passage feels tense or anxious.',
    joy: 'The passage feels upbeat or hopeful.',
    sadness: 'The passage feels sorrowful or subdued.',
    anger: 'The passage feels heated or frustrated.',
    disgust: 'The passage feels uneasy or distasteful in tone.',
    surprise: 'The passage feels startling or shifting in mood.',
    neutral: 'The passage feels emotionally steady or understated.',
  };
  return leads[key] || `Dominant mood: ${emotion.dominant_emotion}.`;
}

export function stylePlain(style) {
  if (!style || style.unavailable) return null;
  const score = style.consistency_score;
  let rhythm = 'Sentence rhythm looks fairly varied.';
  if (score != null) {
    if (score >= 70) rhythm = 'Sentence rhythm looks steady and consistent.';
    else if (score >= 45) rhythm = 'Sentence rhythm is mixed — some repetition, some variety.';
    else rhythm = 'Sentence rhythm varies a lot — you may be shifting pace on purpose, or mixing short and long lines unevenly.';
  }
  const mean = style.sentence_length_mean;
  const lengthNote =
    mean != null
      ? `Average sentence length is about ${mean} words.`
      : '';
  const passivePct =
    style.passive_like_sentence_ratio != null
      ? `${(style.passive_like_sentence_ratio * 100).toFixed(0)}% of sentences use a passive-like pattern (heuristic).`
      : null;
  return [rhythm, lengthNote, passivePct].filter(Boolean).join(' ');
}

export function filterCharacterCandidates(candidates) {
  if (!Array.isArray(candidates)) return [];
  return candidates.filter((c) => c?.name && !CHARACTER_STOP.has(c.name));
}

export function posCountsPlain(posCounts) {
  if (!posCounts) return null;
  return Object.entries(posCounts)
    .filter(([, v]) => v > 0)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 6)
    .map(([k, v]) => `${POS_LABELS[k] || k.toLowerCase()}: ${v}`)
    .join(' · ');
}

export function isTypographyIssue(message = '') {
  return /typographic|curly quote|opening quote|close quote/i.test(message);
}

export function grammarIssueSentenceParts(issue) {
  const sentence = issue?.sentence?.trim();
  if (!sentence) return null;
  const start = Number(issue.highlight_start);
  const len = Number(issue.highlight_length);
  if (
    Number.isFinite(start) &&
    Number.isFinite(len) &&
    len > 0 &&
    start >= 0 &&
    start + len <= sentence.length
  ) {
    return {
      before: sentence.slice(0, start),
      highlight: sentence.slice(start, start + len),
      after: sentence.slice(start + len),
    };
  }
  const matched = issue.matched_text?.trim();
  if (matched && sentence.includes(matched)) {
    const idx = sentence.indexOf(matched);
    return {
      before: sentence.slice(0, idx),
      highlight: matched,
      after: sentence.slice(idx + matched.length),
    };
  }
  return { before: '', highlight: '', after: sentence };
}

export function splitGrammarIssues(issues) {
  const list = Array.isArray(issues) ? issues : [];
  const typography = [];
  const substantive = [];
  for (const issue of list) {
    if (isTypographyIssue(issue.message)) typography.push(issue);
    else substantive.push(issue);
  }
  return { typography, substantive };
}

export function characterProfileErrorPlain(profile) {
  if (!profile?.error) return profile?.user_hint || null;
  const err = String(profile.error);
  if (err.includes('429') || err.includes('insufficient_quota') || err.includes('quota')) {
    return (
      'Your OpenAI account has run out of quota or billing credits. Add credits at platform.openai.com, ' +
      'or disable this feature with BLOOM_ENABLE_CHARACTER_PROFILE_LLM=false when starting the backend.'
    );
  }
  if (err.includes('401') || err.includes('invalid_api_key')) {
    return 'The API key was rejected. Check BLOOM_OPENAI_API_KEY in your backend environment.';
  }
  if (err.includes('403') || err.includes('1010')) {
    return (
      'The LLM provider blocked the request (Cloudflare 1010). If you use Groq, set ' +
      'BLOOM_OPENAI_BASE_URL to https://api.groq.com/openai/v1, use a gsk_ API key, restart the backend, ' +
      'and try BLOOM_OPENAI_JSON_OBJECT=false if it still fails.'
    );
  }
  return profile.user_hint || 'Character profiling could not run. See technical details below.';
}
