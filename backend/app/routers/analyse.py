from fastapi import APIRouter, Depends

from app.dependencies import get_optional_user_id
from app.schemas.analyse import AnalyseRequest
from app.services.linguistics import analyse_linguistics
from app.services.sentiment import analyse_sentiment_polarity
from app.services.style_consistency import analyse_style_consistency
from app.services.grammar import check_grammar
from app.services.neural_grammar import neural_grammar_correct
from app.services.readability import flesch_kincaid_grade_level, flesch_reading_ease_score
from app.services.emotion_tone import analyse_emotion_tone
from app.services.paraphrase import paraphrase_suggestions
from app.services.analysis_history import append_analysis
from app.services.character_profile_llm import analyse_character_profile_llm
from app.services.spacy_pipeline import analyse_spacy
from app.services.story_craft import analyse_characters, analyse_coreference, analyse_dialogue

router = APIRouter(prefix="/api", tags=["analyse"])


@router.post("/analyse")
@router.post("/analyze", include_in_schema=False)
def run_analyse(
    request: AnalyseRequest,
    user_id: int | None = Depends(get_optional_user_id),
):
    text = request.text
    if not text.strip():
        return {
            "flesch_score": None,
            "flesch_kincaid_grade": None,
            "grammar": None,
            "neural_grammar": None,
            "sentiment_polarity": None,
            "emotion_tone": None,
            "paraphrase": None,
            "linguistics": None,
            "style_consistency": None,
            "characters": None,
            "dialogue": None,
            "coreference": None,
            "character_profile": None,
            "spacy_nlp": None,
            "error": "Text cannot be empty",
        }

    score = flesch_reading_ease_score(text)
    fk_grade = flesch_kincaid_grade_level(text)
    grammar = check_grammar(text)
    sentiment_polarity = analyse_sentiment_polarity(text)
    emotion_tone = analyse_emotion_tone(text)
    paraphrase = paraphrase_suggestions(text)
    neural_grammar = neural_grammar_correct(text)
    linguistics = analyse_linguistics(text)
    style_consistency = analyse_style_consistency(text)
    characters = analyse_characters(text)
    dialogue = analyse_dialogue(text)
    coreference = analyse_coreference(text)
    character_profile = analyse_character_profile_llm(text, character_signals=characters)
    spacy_nlp = analyse_spacy(text)

    out = {
        "flesch_score": round(score, 2),
        "flesch_kincaid_grade": round(fk_grade, 2),
        "grammar": grammar,
        "neural_grammar": neural_grammar,
        "sentiment_polarity": sentiment_polarity,
        "emotion_tone": emotion_tone,
        "paraphrase": paraphrase,
        "linguistics": linguistics,
        "style_consistency": style_consistency,
        "characters": characters,
        "dialogue": dialogue,
        "coreference": coreference,
        "character_profile": character_profile,
        "spacy_nlp": spacy_nlp,
    }
    if not append_analysis(text, out, user_id=user_id):
        out["history_warning"] = (
            "Analysis completed, but saving to your history failed. "
            "Start PostgreSQL from backend/ with: docker compose up -d"
        )
    return out
