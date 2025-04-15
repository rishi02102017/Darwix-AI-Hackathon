from dotenv import load_dotenv
from rest_framework.decorators import api_view
from rest_framework.response import Response
import tempfile
from faster_whisper import WhisperModel
from pydub import AudioSegment
from openai import OpenAI
import numpy as np
from resemblyzer import preprocess_wav, VoiceEncoder
from sklearn.cluster import AgglomerativeClustering
import os

# Load environment variables
load_dotenv()

# OpenRouter client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

# Load Whisper and Resemblyzer models
whisper_model = WhisperModel("base", compute_type="int8")
speaker_encoder = VoiceEncoder()

@api_view(['POST'])
def transcribe_audio(request):
    """
    Transcribe uploaded audio with speaker diarization.
    """
    audio_file = request.FILES.get('audio')
    if not audio_file:
        return Response({"error": "No audio file provided"}, status=400)

    # Save uploaded audio to temp WAV file
    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as temp:
        for chunk in audio_file.chunks():
            temp.write(chunk)
        temp_path = temp.name

    # Transcribe
    segments, _ = whisper_model.transcribe(temp_path)
    segments = list(segments)

    # Load audio for embedding
    wav = preprocess_wav(temp_path)
    segment_slices = [(int(seg.start * 16000), int(seg.end * 16000)) for seg in segments]
    embeddings = [
        speaker_encoder.embed_utterance(wav[start:end]) if end > start else np.zeros(256)
        for start, end in segment_slices
    ]

    # Cluster speakers
    if len(embeddings) > 1:
        num_speakers = min(2, len(embeddings))  # You can tune this
        labels = AgglomerativeClustering(n_clusters=num_speakers).fit_predict(embeddings)
    else:
        labels = [0] * len(embeddings)

    # Build response
    transcription = []
    for seg, label in zip(segments, labels):
        transcription.append({
            "start": seg.start,
            "end": seg.end,
            "speaker": f"speaker_{label + 1}",
            "text": seg.text
        })

    return Response({"transcription": transcription})


@api_view(['POST'])
def suggest_titles(request):
    """
    Suggest blog titles using OpenRouter LLM (Mistral).
    """
    content = request.data.get('content')
    if not content:
        return Response({"error": "No blog content provided"}, status=400)

    prompt = f"Suggest 3 catchy blog post titles for the following blog:\n\n{content}"

    try:
        response = client.chat.completions.create(
            model="mistralai/mistral-7b-instruct",
            messages=[{"role": "user", "content": prompt}]
        )
        titles = response.choices[0].message.content.strip().split('\n')
        return Response({"suggested_titles": titles})

    except Exception as e:
        return Response({"error": str(e)}, status=500)
