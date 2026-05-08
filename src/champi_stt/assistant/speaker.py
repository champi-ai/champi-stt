"""
Speaker identification using voice embeddings.

Uses Resemblyzer to create and compare voice embeddings for speaker recognition.
"""

# import logging - replaced with loguru
import pickle
from pathlib import Path

import numpy as np
from loguru import logger

try:
    from resemblyzer import VoiceEncoder, preprocess_wav

    RESEMBLYZER_AVAILABLE = True
except ImportError:
    RESEMBLYZER_AVAILABLE = False
    logger.warning("Resemblyzer not available - speaker identification disabled")


class SpeakerProfile:
    """A speaker's voice profile with embeddings"""

    def __init__(self, name: str, embeddings: list[np.ndarray]):
        self.name = name
        self.embeddings = embeddings  # List of embeddings from enrollment samples
        self.mean_embedding = np.mean(embeddings, axis=0)  # Average embedding

    def similarity(self, embedding: np.ndarray) -> float:
        """
        Calculate similarity score with given embedding.

        Args:
            embedding: Voice embedding to compare

        Returns:
            Similarity score (0-1, higher = more similar)
        """
        # Cosine similarity
        return np.dot(self.mean_embedding, embedding) / (
            np.linalg.norm(self.mean_embedding) * np.linalg.norm(embedding)
        )


class SpeakerIdentifier:
    """
    Speaker identification system using voice embeddings.

    Allows enrollment of speakers and identification from audio samples.
    """

    def __init__(self, profiles_dir: str | Path = "~/.config/champi-stt/speakers"):
        if not RESEMBLYZER_AVAILABLE:
            raise ImportError("Resemblyzer is required for speaker identification")

        self.profiles_dir = Path(profiles_dir).expanduser()
        self.profiles_dir.mkdir(parents=True, exist_ok=True)

        self.encoder = VoiceEncoder()
        self.profiles: dict[str, SpeakerProfile] = {}

        # Load existing profiles
        self._load_profiles()

        logger.info(
            f"Speaker identifier initialized with {len(self.profiles)} profiles"
        )

    def _load_profiles(self):
        """Load speaker profiles from disk"""
        for profile_file in self.profiles_dir.glob("*.pkl"):
            try:
                with open(profile_file, "rb") as f:
                    profile = pickle.load(f)  # nosec B301 — file written by this app only
                    self.profiles[profile.name] = profile
                    logger.debug(f"Loaded speaker profile: {profile.name}")
            except Exception as e:
                logger.error(f"Failed to load profile {profile_file}: {e}")

    def _save_profile(self, profile: SpeakerProfile):
        """Save speaker profile to disk"""
        profile_file = self.profiles_dir / f"{profile.name}.pkl"
        with open(profile_file, "wb") as f:
            pickle.dump(profile, f)
        logger.info(f"Saved speaker profile: {profile.name}")

    def enroll_speaker(
        self, name: str, audio_samples: list[np.ndarray]
    ) -> SpeakerProfile:
        """
        Enroll a new speaker with voice samples.

        Args:
            name: Speaker name
            audio_samples: List of audio samples (int16 numpy arrays @ 16kHz)

        Returns:
            Created speaker profile
        """
        if len(audio_samples) < 1:
            raise ValueError("At least 1 audio sample required for enrollment")

        # Preprocess and create embeddings
        embeddings = []
        for audio in audio_samples:
            # Convert int16 to float32 in range [-1, 1] for resemblyzer
            audio_float = audio.astype(np.float32) / 32768.0

            # Preprocess for resemblyzer (resampling if needed)
            preprocessed = preprocess_wav(audio_float, source_sr=16000)

            # Create embedding
            embedding = self.encoder.embed_utterance(preprocessed)
            embeddings.append(embedding)

        # Create profile
        profile = SpeakerProfile(name, embeddings)
        self.profiles[name] = profile
        self._save_profile(profile)

        logger.info(f"Enrolled speaker '{name}' with {len(audio_samples)} samples")
        return profile

    def identify_speaker(
        self, audio: np.ndarray, threshold: float = 0.75
    ) -> tuple[str | None, float]:
        """
        Identify speaker from audio sample.

        Args:
            audio: Audio data (int16 numpy array @ 16kHz)
            threshold: Minimum similarity threshold for identification

        Returns:
            Tuple of (speaker_name, confidence_score) or (None, 0.0) if unknown
        """
        if not self.profiles:
            logger.warning("No enrolled speakers - cannot identify")
            return None, 0.0

        # Convert int16 to float32 in range [-1, 1]
        audio_float = audio.astype(np.float32) / 32768.0

        # Preprocess
        preprocessed = preprocess_wav(audio_float, source_sr=16000)

        # Create embedding
        embedding = self.encoder.embed_utterance(preprocessed)

        # Find best match
        best_match = None
        best_score = 0.0

        for name, profile in self.profiles.items():
            score = profile.similarity(embedding)
            if score > best_score:
                best_score = score
                best_match = name

        # Check threshold
        if best_score >= threshold:
            logger.info(
                f"Identified speaker: {best_match} (confidence: {best_score:.2f})"
            )
            return best_match, best_score
        else:
            logger.info(
                f"Unknown speaker (best match: {best_match} @ {best_score:.2f}, threshold: {threshold})"
            )
            return None, best_score

    def remove_speaker(self, name: str):
        """Remove a speaker profile"""
        if name in self.profiles:
            del self.profiles[name]
            profile_file = self.profiles_dir / f"{name}.pkl"
            if profile_file.exists():
                profile_file.unlink()
            logger.info(f"Removed speaker profile: {name}")
        else:
            logger.warning(f"Speaker profile not found: {name}")

    def list_speakers(self) -> list[str]:
        """Get list of enrolled speaker names"""
        return list(self.profiles.keys())
