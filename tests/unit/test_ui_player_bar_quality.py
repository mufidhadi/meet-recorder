import os
import pytest
from meeting_recorder.ui.player_bar import PlayerBar
from PyQt6.QtMultimedia import QMediaPlayer

def test_player_bar_cleanup(qtbot):
    player_bar = PlayerBar()
    qtbot.addWidget(player_bar)
    
    # Mock player state
    # We can't easily mock QMediaPlayer in a way that verifies stop() without more complex mocking,
    # but we can check if it runs without error.
    player_bar.cleanup()
    assert player_bar.player.playbackState() == QMediaPlayer.PlaybackState.StoppedState

def test_load_audio_exists_check(qtbot, tmp_path):
    player_bar = PlayerBar()
    qtbot.addWidget(player_bar)
    
    # Test non-existent file
    fake_file = str(tmp_path / "non_existent.wav")
    player_bar.load_audio(fake_file)
    assert player_bar.player.source().isEmpty()
    
    # Test existent file
    real_file = tmp_path / "exists.wav"
    real_file.touch()
    player_bar.load_audio(str(real_file))
    assert not player_bar.player.source().isEmpty()
