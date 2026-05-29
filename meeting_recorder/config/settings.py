import os
from pydantic_settings import BaseSettings, SettingsConfigDict, PydanticBaseSettingsSource
from meeting_recorder.data.audio import AudioConfig
from meeting_recorder.utils.paths import get_base_path
from typing import Tuple, Type

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=os.path.join(get_base_path(), ".env"), 
        extra="ignore"
    )
    
    audio: AudioConfig = AudioConfig()
    
    # Engine: "gemini" or "local"
    transcription_engine: str = "local"
    # local_model_id: str = "openai/whisper-base" 
    local_model_id: str = "openai/whisper-small" 
    gemini_model_id: str = "gemini-2.0-flash"
    
    gemini_api_key: str | None = None
    output_dir: str = os.path.join(get_base_path(), "recordings")
    
    # Transcription settings
    chunk_duration: float = 30.0
    
    # Silence detection: RMS threshold (0.0 to 1.0)
    silence_threshold: float = 0.01

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: Type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> Tuple[PydanticBaseSettingsSource, ...]:
        # Prioritize .env file over environment variables
        return init_settings, dotenv_settings, env_settings, file_secret_settings
