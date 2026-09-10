import {
  characterProfileErrorPlain,
  emotionLead,
  filterCharacterCandidates,
  fleschEaseLabel,
  fleschGradeLabel,
  posCountsPlain,
  sentimentPlain,
  grammarIssueSentenceParts,
  splitGrammarIssues,
  stylePlain,
} from '../analysePresentation';

function Insight({ children }) {
  return <p className="result-insight">{children}</p>;
}

function Section({ title, children }) {
  return (
    <div className="result-section">
      <h2 className="result-section-title">{title}</h2>
      <div className="result-section-body">{children}</div>
    </div>
  );
}

function TechnicalDetails({ summary, children }) {
  return (
    <details className="result-technical">
      <summary>{summary}</summary>
      <div className="result-technical-body">{children}</div>
    </details>
  );
}

function moduleActive(module) {
  return module != null && module.enabled !== false;
}

function GrammarIssueList({ issues }) {
  if (!issues?.length) return null;
  return (
    <ul className="grammar-list">
      {issues.map((issue, i) => {
        const parts = grammarIssueSentenceParts(issue);
        return (
        <li key={`${issue.offset}-${issue.length}-${i}`} className="grammar-item">
          {parts && (
            <p className="grammar-context">
              <span className="grammar-context-label">In your text:</span>{' '}
              <q className="grammar-context-quote">
                {parts.before}
                {parts.highlight ? <mark className="grammar-highlight">{parts.highlight}</mark> : null}
                {parts.after}
              </q>
            </p>
          )}
          <p className="grammar-message">{issue.message}</p>
          {issue.suggestions?.length > 0 && (
            <p className="grammar-suggestions">
              Try:{' '}
              {issue.suggestions.map((s, j) => (
                <span key={j} className="suggestion">
                  {s}
                  {j < issue.suggestions.length - 1 ? ' · ' : ''}
                </span>
              ))}
            </p>
          )}
        </li>
        );
      })}
    </ul>
  );
}

export function AnalyseResults({
  message,
  fleschScore,
  fleschKincaidGrade,
  grammar,
  neuralGrammar,
  sentimentPolarity,
  emotionTone,
  paraphrase,
  linguistics,
  spacyNlp,
  styleConsistency,
  characters,
  dialogue,
  coreference,
  characterProfile,
}) {
  const nameCandidates = filterCharacterCandidates(characters?.candidates);
  const grammarSplit = grammar?.issues ? splitGrammarIssues(grammar.issues) : null;

  return (
    <section className="results" aria-live="polite">
      {(fleschScore != null || emotionTone || sentimentPolarity) && (
        <Section title="At a glance">
          <div className="result-grid result-grid--glance">
            {fleschScore != null && (
              <div className="result-card result-card--highlight">
                <h3 className="result-card-label">Reading ease</h3>
                <p className="score">{fleschScore}</p>
                <Insight>{fleschEaseLabel(fleschScore)}</Insight>
              </div>
            )}
            {fleschKincaidGrade != null && (
              <div className="result-card">
                <h3 className="result-card-label">School reading level</h3>
                <p className="score score--compact">{fleschKincaidGrade}</p>
                <Insight>{fleschGradeLabel(fleschKincaidGrade)}</Insight>
              </div>
            )}
            {moduleActive(emotionTone) && !emotionTone.unavailable && emotionTone.dominant_emotion && (
              <div className="result-card tone-card">
                <h3 className="result-card-label">Mood</h3>
                <p className="emotion-dominant">
                  <span className="emotion-label">{emotionTone.dominant_emotion}</span>
                </p>
                <Insight>{emotionLead(emotionTone)}</Insight>
                {emotionTone.summary && <p className="hint">{emotionTone.summary}</p>}
              </div>
            )}
            {moduleActive(sentimentPolarity) && !sentimentPolarity.unavailable && (
              <div className="result-card">
                <h3 className="result-card-label">Word tone</h3>
                <p className="grammar-summary">
                  <strong>{sentimentPolarity.label}</strong>
                  {sentimentPolarity.polarity_score != null && (
                    <> · score {sentimentPolarity.polarity_score}</>
                  )}
                </p>
                <Insight>{sentimentPlain(sentimentPolarity)}</Insight>
              </div>
            )}
          </div>
        </Section>
      )}

      <Section title="Story & characters">
        {nameCandidates.length > 0 && (
          <div className="result-card">
            <h3 className="result-card-label">Names that keep appearing</h3>
            <Insight>
              These capitalised words may be characters. Bloom cannot tell names from ordinary
              words perfectly — trust your own judgment.
            </Insight>
            <ul className="emotion-scores">
              {nameCandidates.map((c) => (
                <li key={c.name}>
                  {c.name} <span className="emotion-score-val">{c.mentions}×</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {moduleActive(dialogue) && (
          <div className="result-card">
            <h3 className="result-card-label">Dialogue</h3>
            <Insight>
              About{' '}
              <strong>
                {dialogue.dialogue_char_ratio != null
                  ? `${(dialogue.dialogue_char_ratio * 100).toFixed(0)}%`
                  : 'some'}
              </strong>{' '}
              of your text is inside quotation marks ({dialogue.quoted_segments ?? 0} spoken line
              {dialogue.quoted_segments === 1 ? '' : 's'}).
            </Insight>
            {dialogue.preview?.length > 0 && (
              <>
                <p className="neural-label">Opening lines of dialogue</p>
                <ol className="paraphrase-list">
                  {dialogue.preview.map((s, i) => (
                    <li key={i} className="paraphrase-item">
                      {s.length > 160 ? `${s.slice(0, 160)}…` : s}
                    </li>
                  ))}
                </ol>
              </>
            )}
          </div>
        )}

        {moduleActive(coreference) && coreference.links?.length > 0 && (
          <div className="result-card">
            <h3 className="result-card-label">Who is &ldquo;she&rdquo; or &ldquo;he&rdquo;?</h3>
            <Insight>
              Bloom&apos;s best guess for pronouns — especially useful when several characters share
              a scene.
            </Insight>
            <ul className="grammar-list coref-list">
              {coreference.links.slice(0, 10).map((link, i) => (
                <li key={i} className="grammar-item coref-item">
                  <span className="coref-pronoun">{link.pronoun}</span>
                  <span className="coref-arrow" aria-hidden>
                    →
                  </span>
                  <span className="coref-name">{link.antecedent_guess}</span>
                </li>
              ))}
            </ul>
          </div>
        )}

        {characterProfile?.enabled === false && characterProfile.note && (
          <div className="result-card character-profile-card">
            <h3 className="result-card-label">Character deep dive</h3>
            <p className="grammar-note">{characterProfile.note}</p>
          </div>
        )}

        {moduleActive(characterProfile) && characterProfile.unavailable && (
          <div className="result-card character-profile-card">
            <h3 className="result-card-label">Character deep dive</h3>
            <Insight>{characterProfileErrorPlain(characterProfile)}</Insight>
            <TechnicalDetails summary="Technical details">
              {characterProfile.error && <p className="mono grammar-unavailable">{characterProfile.error}</p>}
              {characterProfile.model && <p className="hint">Model: {characterProfile.model}</p>}
            </TechnicalDetails>
          </div>
        )}

        {moduleActive(characterProfile) && !characterProfile.unavailable && (
          <div className="result-card character-profile-card">
            <h3 className="result-card-label">Character deep dive</h3>
            <Insight>Inferred from this excerpt only — not a full-story analysis.</Insight>
            {characterProfile.characters?.length > 0 ? (
              <ul className="character-profile-list">
                {characterProfile.characters.map((ch, i) => (
                  <li key={i} className="character-profile-item">
                    <p className="character-profile-name">
                      <strong>{ch.name}</strong>
                      {ch.role_hint ? <span className="character-role"> · {ch.role_hint}</span> : null}
                    </p>
                    {ch.goals_or_motivation && (
                      <p className="character-profile-line">
                        <span className="cp-label">Wants</span> {ch.goals_or_motivation}
                      </p>
                    )}
                    {ch.conflict_or_stakes && (
                      <p className="character-profile-line">
                        <span className="cp-label">At stake</span> {ch.conflict_or_stakes}
                      </p>
                    )}
                    {ch.traits?.length > 0 && (
                      <p className="character-profile-line">
                        <span className="cp-label">Traits</span> {ch.traits.join(', ')}
                      </p>
                    )}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="grammar-summary">No characters extracted for this passage.</p>
            )}
            {characterProfile.relationships?.length > 0 && (
              <>
                <p className="neural-label">Relationships</p>
                <ul className="relationship-list">
                  {characterProfile.relationships.map((rel, i) => (
                    <li key={i} className="relationship-item">
                      <strong>{rel.from}</strong> → <strong>{rel.to}</strong>
                      {rel.relation ? <span className="rel-type"> ({rel.relation})</span> : null}
                      {rel.support && <p className="rel-support">{rel.support}</p>}
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>
        )}
      </Section>

      <Section title="Writing style">
        {moduleActive(styleConsistency) && !styleConsistency.unavailable && (
          <div className="result-card">
            <h3 className="result-card-label">Rhythm & variety</h3>
            <Insight>{stylePlain(styleConsistency)}</Insight>
            {styleConsistency.repeated_sentence_starters?.length > 0 && (
              <p className="hint">
                You often start sentences with:{' '}
                {styleConsistency.repeated_sentence_starters
                  .slice(0, 4)
                  .map((s) => s.replace(/\s*\(\d+×\)$/, ''))
                  .join(', ')}
                . Varying openings can make prose feel less repetitive.
              </p>
            )}
            <TechnicalDetails summary="Numbers behind this">
              <p className="hint">
                Consistency score: {styleConsistency.consistency_score} · Mean sentence length:{' '}
                {styleConsistency.sentence_length_mean} words · Vocabulary spread (TTR):{' '}
                {styleConsistency.lexical_diversity_ttr}
              </p>
            </TechnicalDetails>
          </div>
        )}

        {moduleActive(emotionTone) && !emotionTone.unavailable && emotionTone.emotion_scores && (
          <div className="result-card tone-card">
            <h3 className="result-card-label">Emotion mix</h3>
            <ul className="emotion-scores">
              {Object.entries(emotionTone.emotion_scores)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 5)
                .map(([label, score]) => (
                  <li key={label}>
                    {label} <span className="emotion-score-val">{(score * 100).toFixed(1)}%</span>
                  </li>
                ))}
            </ul>
          </div>
        )}

        {moduleActive(paraphrase) && !paraphrase.unavailable && paraphrase.suggestions?.length > 0 && (
          <div className="result-card paraphrase-card">
            <h3 className="result-card-label">Other ways to say the opening</h3>
            <Insight>Use as inspiration — keep your own voice.</Insight>
            <ol className="paraphrase-list">
              {paraphrase.suggestions.map((s, i) => (
                <li key={i} className="paraphrase-item">
                  {s}
                </li>
              ))}
            </ol>
          </div>
        )}
      </Section>

      <Section title="Grammar & suggestions">
        {grammar && (
          <div className="result-card grammar-card">
            <h3 className="result-card-label">LanguageTool checks</h3>
            {grammar.unavailable ? (
              <p className="grammar-unavailable">{grammar.error}</p>
            ) : (
              <>
                {grammarSplit && grammarSplit.substantive.length > 0 ? (
                  <>
                    <Insight>
                      {grammarSplit.substantive.length} wording or grammar suggestion
                      {grammarSplit.substantive.length === 1 ? '' : 's'} worth reviewing.
                    </Insight>
                    <GrammarIssueList issues={grammarSplit.substantive} />
                  </>
                ) : (
                  <Insight>No major grammar problems flagged. LanguageTool may still miss subtle issues.</Insight>
                )}
                {grammarSplit?.typography.length > 0 && (
                  <TechnicalDetails
                    summary={`${grammarSplit.typography.length} punctuation style note${grammarSplit.typography.length === 1 ? '' : 's'} (curly quotes)`}
                  >
                    <GrammarIssueList issues={grammarSplit.typography} />
                  </TechnicalDetails>
                )}
              </>
            )}
          </div>
        )}

        {moduleActive(neuralGrammar) && !neuralGrammar.unavailable && (
          <div className="result-card neural-card">
            <h3 className="result-card-label">AI rewrite suggestion</h3>
            <Insight>
              A machine-learned model&apos;s version of your opening — compare with LanguageTool above
              and keep what sounds like you.
            </Insight>
            {neuralGrammar.changed && neuralGrammar.corrected_text != null && (
              <div className="neural-output">
                <p className="neural-corrected">{neuralGrammar.corrected_text}</p>
              </div>
            )}
            {!neuralGrammar.changed && (
              <p className="grammar-summary">The model did not suggest changes to this text.</p>
            )}
            <TechnicalDetails summary="About this model">
              {neuralGrammar.model && <p className="hint">Model: {neuralGrammar.model}</p>}
              {neuralGrammar.limitations && <p className="grammar-note">{neuralGrammar.limitations}</p>}
            </TechnicalDetails>
          </div>
        )}
      </Section>

      {(moduleActive(linguistics) || moduleActive(spacyNlp)) && (
        <Section title="Technical details">
          {moduleActive(linguistics) && !linguistics.unavailable && (
            <div className="result-card">
              <h3 className="result-card-label">Text breakdown</h3>
              <p className="grammar-summary">
                {linguistics.sentence_count} sentences · {linguistics.token_count} words
              </p>
              {posCountsPlain(linguistics.pos_counts) && (
                <p className="hint">{posCountsPlain(linguistics.pos_counts)}</p>
              )}
            </div>
          )}
          {moduleActive(spacyNlp) && !spacyNlp.unavailable && spacyNlp.entities?.length > 0 && (
            <div className="result-card">
              <h3 className="result-card-label">SpaCy entities</h3>
              <p className="hint">
                {spacyNlp.entities.slice(0, 12).map((e) => (
                  <span key={`${e.start_char}-${e.text}`} className="spacy-ent">
                    {e.text} ({e.label}){' '}
                  </span>
                ))}
              </p>
            </div>
          )}
        </Section>
      )}

      {message && <p className="status">{message}</p>}
    </section>
  );
}
