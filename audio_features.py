"""
Extraction de features audio — DOIT rester strictement identique à la logique
utilisée dans train_autodiag.py, sinon le modèle reçoit des features
différentes de celles sur lesquelles il a été entraîné et ses prédictions
n'ont plus aucun sens.
"""

import numpy as np
from scipy.fftpack import dct
from scipy.io import wavfile

N_MFCC = 13
N_MELS = 26
N_FFT = 512
HOP_LENGTH = 256


def hz_to_mel(hz):
    return 2595.0 * np.log10(1.0 + hz / 700.0)


def mel_to_hz(mel):
    return 700.0 * (10.0 ** (mel / 2595.0) - 1.0)


def build_mel_filterbank(sample_rate, n_fft, n_mels, fmin=0, fmax=None):
    fmax = fmax or sample_rate / 2
    low_mel = hz_to_mel(fmin)
    high_mel = hz_to_mel(fmax)
    mel_points = np.linspace(low_mel, high_mel, n_mels + 2)
    hz_points = mel_to_hz(mel_points)
    bin_points = np.floor((n_fft + 1) * hz_points / sample_rate).astype(int)
    bin_points = np.clip(bin_points, 0, n_fft // 2)

    fbank = np.zeros((n_mels, n_fft // 2 + 1))
    for m in range(1, n_mels + 1):
        f_left, f_center, f_right = bin_points[m - 1], bin_points[m], bin_points[m + 1]
        if f_center == f_left:
            f_center += 1
        if f_right == f_center:
            f_right += 1
        for k in range(f_left, f_center):
            fbank[m - 1, k] = (k - f_left) / (f_center - f_left)
        for k in range(f_center, min(f_right, n_fft // 2 + 1)):
            fbank[m - 1, k] = (f_right - k) / (f_right - f_center)
    return fbank


def compute_mfcc(signal, sample_rate, n_mfcc=N_MFCC, n_fft=N_FFT,
                  hop_length=HOP_LENGTH, n_mels=N_MELS):
    if len(signal) < n_fft:
        signal = np.pad(signal, (0, n_fft - len(signal)))

    emphasized = np.append(signal[0], signal[1:] - 0.97 * signal[:-1])

    n_frames = 1 + (len(emphasized) - n_fft) // hop_length
    if n_frames < 1:
        n_frames = 1
        emphasized = np.pad(emphasized, (0, n_fft - len(emphasized)))

    frames = np.empty((n_frames, n_fft), dtype=np.float64)
    for i in range(n_frames):
        start = i * hop_length
        frames[i] = emphasized[start: start + n_fft]

    frames = frames * np.hamming(n_fft)

    mag_spec = np.abs(np.fft.rfft(frames, n=n_fft))
    power_spec = (mag_spec ** 2) / n_fft

    fbank = build_mel_filterbank(sample_rate, n_fft, n_mels)
    mel_energy = power_spec @ fbank.T
    mel_energy = np.where(mel_energy <= 0, np.finfo(float).eps, mel_energy)
    log_mel = np.log(mel_energy)

    mfcc = dct(log_mel, type=2, axis=1, norm="ortho")[:, :n_mfcc]
    return mfcc.T, power_spec


def extract_features_from_array(signal, sample_rate):
    """Extrait le vecteur de features à partir d'un signal audio déjà chargé en mémoire."""
    if signal.ndim > 1:
        signal = signal.mean(axis=1)

    signal = signal.astype(np.float32)
    max_val = np.max(np.abs(signal)) if np.max(np.abs(signal)) > 0 else 1.0
    signal = signal / max_val

    mfcc, power_spec = compute_mfcc(signal, sample_rate)

    mfcc_mean = mfcc.mean(axis=1)
    mfcc_std = mfcc.std(axis=1)

    zcr = np.mean(np.abs(np.diff(np.sign(signal)))) / 2.0
    rms = np.sqrt(np.mean(signal ** 2))

    freqs = np.linspace(0, sample_rate / 2, power_spec.shape[1])
    spectral_centroid = np.sum(freqs * power_spec, axis=1) / (
        np.sum(power_spec, axis=1) + 1e-10
    )
    spectral_centroid_mean = spectral_centroid.mean()

    return np.concatenate([
        mfcc_mean, mfcc_std,
        [zcr, rms, spectral_centroid_mean],
    ])


def extract_features(filepath):
    """Extrait le vecteur de features directement à partir d'un fichier WAV."""
    sample_rate, signal = wavfile.read(filepath)
    return extract_features_from_array(signal, sample_rate)
