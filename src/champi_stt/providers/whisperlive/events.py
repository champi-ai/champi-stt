"""Signals system for WhisperLive STT service using champi-signals."""
from blinker import Signal
from champi_signals import BaseSignalManager, EventProcessor, STTEventTypes

# from champi_signals import SignalType


class STTSignalManager(BaseSignalManager):
    """STT Signal Manager using champi-signals library with singleton pattern"""
    
    _instance = None
    
    def __new__(cls):
        """Singleton pattern implementation"""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        super().__init__()
        # Setup signals using STT event types
        self.setup_custom_signals({
            'lifecycle': STTEventTypes,
            'model': STTEventTypes,
            'processing': STTEventTypes,
            'telemetry': STTEventTypes,
        })
        self._initialized = True

    def get_signal_by_signal_type(self, signal_type: str) -> Signal:
        """Return signal object for given signal_type"""
        return self.signals[signal_type]
