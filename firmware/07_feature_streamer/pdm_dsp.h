// =========================================================================
// pdm_dsp.h
// Portable on-device feature extraction for the Washer PdM rig (firmware 07)
//
// PURPOSE
//   Turns the raw sensor streams that the ESP32 already samples
//   (INMP441 audio @ 16 kHz, MPU-6050 acceleration @ 200 Hz) into one compact
//   feature vector per 5-second window. Only this vector leaves the device,
//   so the cloud sees *all* of the signal (summarised) instead of one
//   instantaneous snapshot every 5 s (what firmware 05/06 uploaded).
//
// DESIGN RULES
//   1. Pure C++11. No Arduino, FreeRTOS or ESP-IDF headers. This lets the
//      exact same code compile on a PC (g++) for unit tests against the
//      Python reference implementation in ml/dsp_features.py.
//   2. Signals are float, accumulators are double (avoids precision loss in
//      sums of x^4 over 80,000 samples).
//   3. No heap allocation after construction (fixed-size arrays only), so
//      the firmware cannot fragment memory during a 2-hour wash cycle.
//
// UNITS
//   Audio : "legacy units" = int24 sample value / 1000. This is the same
//           scale firmware 05/06 used for `audio_rms`, so old and new RMS
//           values are roughly comparable (old = 8 ms snapshot, new = full
//           5 s window, DC removed).
//   Vibration : m/s^2.
// =========================================================================

#pragma once

#include <math.h>
#include <stdint.h>
#include <string.h>
#include <algorithm>

namespace pdm {

// -------------------------------------------------------------------------
// SECTION 1: Global constants (must match ml/dsp_features.py exactly)
// -------------------------------------------------------------------------

static const int   AUDIO_FS          = 16000;   // INMP441 sample rate (Hz)
static const int   AUDIO_BLOCK       = 512;     // samples per I2S read / FFT block (32 ms)
static const int   AUDIO_MAX_BLOCKS  = 200;     // capacity for per-block RMS list (> 157 per window)
static const int   AUDIO_N_BANDS     = 6;       // number of audio band-RMS features
static const float AUDIO_DC_POLE     = 0.995f;  // DC-blocker pole -> ~12.7 Hz high-pass corner
static const float AUDIO_HP_HZ       = 2000.0f; // corner of the "impulsive band" high-pass filter
static const float AUDIO_LEGACY_DIV  = 1000.0f; // int24 -> legacy unit divisor

static const int   VIB_FS            = 200;     // MPU-6050 FIFO output rate (Hz)
static const int   VIB_FFT           = 512;     // vibration FFT length (2.56 s of history)
static const int   VIB_N_BANDS       = 4;       // number of vibration band-RMS features
static const float VIB_DOM_LO_HZ     = 0.5f;    // dominant-frequency search range, low edge
static const float VIB_DOM_HI_HZ     = 45.0f;   // ... high edge (DLPF corner is 44 Hz)

// Audio band edges in Hz: [0,250) [250,500) [500,1k) [1k,2k) [2k,4k) [4k,8k]
static const float AUDIO_BAND_EDGES[AUDIO_N_BANDS + 1] = {
    0.0f, 250.0f, 500.0f, 1000.0f, 2000.0f, 4000.0f, 8000.0f};

// Vibration band edges in Hz: [0.5,5) [5,15) [15,30) [30,60)
//   0.5-5 Hz  : cabinet rocking / suspension sway
//   5-15 Hz   : low-speed drum rotation orders (wash tumble, distribution)
//   15-30 Hz  : spin 1x order (900-1800 rpm = 15-30 Hz)
//   30-60 Hz  : spin 2x order; NOTE the MPU DLPF (44 Hz) attenuates the top
static const float VIB_BAND_EDGES[VIB_N_BANDS + 1] = {0.5f, 5.0f, 15.0f, 30.0f, 60.0f};

static const float PI_F = 3.14159265358979323846f;

// -------------------------------------------------------------------------
// SECTION 2: In-place radix-2 complex FFT (fixed length N, power of two)
// -------------------------------------------------------------------------
// Classic iterative Cooley-Tukey. Twiddle factors and the Hann window are
// pre-computed once in init() so the per-block cost is just the butterflies.
template <int N>
class FFT {
public:
    // Pre-compute cos/sin tables, the Hann window and its energy sum.
    void init() {
        for (int k = 0; k < N / 2; ++k) {
            cos_[k] = cosf(2.0f * PI_F * (float)k / (float)N);
            sin_[k] = -sinf(2.0f * PI_F * (float)k / (float)N);
        }
        double s2 = 0.0;
        for (int n = 0; n < N; ++n) {
            // Periodic Hann window (same definition as numpy hanning(N+1)[:-1]).
            hann_[n] = 0.5f - 0.5f * cosf(2.0f * PI_F * (float)n / (float)N);
            s2 += (double)hann_[n] * (double)hann_[n];
        }
        hann_s2_ = s2;
    }

    // Forward transform of (re, im) in place.
    void forward(float* re, float* im) const {
        // --- Step 1: bit-reversal permutation ---
        for (int i = 1, j = 0; i < N; ++i) {
            int bit = N >> 1;
            for (; j & bit; bit >>= 1) j ^= bit;
            j ^= bit;
            if (i < j) {
                float t = re[i]; re[i] = re[j]; re[j] = t;
                t = im[i]; im[i] = im[j]; im[j] = t;
            }
        }
        // --- Step 2: butterflies, stage length doubling each pass ---
        for (int len = 2; len <= N; len <<= 1) {
            const int half = len >> 1;
            const int step = N / len;          // twiddle stride for this stage
            for (int i = 0; i < N; i += len) {
                for (int k = 0; k < half; ++k) {
                    const float wr = cos_[k * step];
                    const float wi = sin_[k * step];
                    const int a = i + k;
                    const int b = a + half;
                    const float xr = re[b] * wr - im[b] * wi;
                    const float xi = re[b] * wi + im[b] * wr;
                    re[b] = re[a] - xr;  im[b] = im[a] - xi;
                    re[a] = re[a] + xr;  im[a] = im[a] + xi;
                }
            }
        }
    }

    float  hann(int n) const { return hann_[n]; }
    double hannEnergy() const { return hann_s2_; }   // sum of w[n]^2

private:
    float  cos_[N / 2];
    float  sin_[N / 2];
    float  hann_[N];
    double hann_s2_ = 1.0;
};

// -------------------------------------------------------------------------
// SECTION 3: Spectrum helpers (shared by audio and vibration)
// -------------------------------------------------------------------------

// RMS of the signal content inside [f_lo, f_hi) from a (mean) one-sided
// power spectrum P[k] = |X_k|^2 of a Hann-windowed N-point frame.
// Parseval with window correction:  sigma^2 ~= sum_k |X_k|^2 / (N * sum w^2)
// One-sided spectrum -> factor 2 for 0 < k < N/2.
inline float bandRms(const double* P, int N, float fs, double hannS2,
                     float f_lo, float f_hi, bool include_top) {
    const float df = fs / (float)N;
    double acc = 0.0;
    for (int k = 1; k < N / 2; ++k) {               // skip DC bin (k = 0)
        const float f = (float)k * df;
        const bool in_band = (f >= f_lo) && (f < f_hi || (include_top && f <= f_hi));
        if (in_band) acc += 2.0 * P[k];
    }
    return (float)sqrt(acc / ((double)N * hannS2));
}

// -------------------------------------------------------------------------
// SECTION 4: Audio window features
// -------------------------------------------------------------------------
// Feature meaning (all over the full ~5 s window, DC removed):
//   rms        overall loudness (legacy units)
//   peak       largest |sample|
//   crest      peak / rms  -> rises with sharp impacts (spall, knocking)
//   kurtosis   E[x^4]/E[x^2]^2 (3.0 for Gaussian noise) -> impulsiveness
//   hp_rms     RMS after a 2 kHz high-pass  (bearing / friction band)
//   hp_kurt    kurtosis of the high-passed signal -> classic early-spall cue
//   blk_max    max RMS of the 32 ms blocks inside the window (short bursts)
//   blk_p90    90th percentile of block RMS (robust "busy level")
//   centroid   spectral centroid in Hz (where the energy sits)
//   band[6]    RMS in each AUDIO_BAND_EDGES band (legacy units)
struct AudioFeatures {
    uint32_t n;        // samples that contributed
    float rms, peak, crest, kurtosis;
    float hp_rms, hp_kurt;
    float blk_max, blk_p90;
    float centroid_hz;
    float band[AUDIO_N_BANDS];
};

class AudioWindow {
public:
    // One-time setup: FFT tables + high-pass biquad coefficients.
    void init() {
        fft_.init();
        // RBJ cookbook 2nd-order Butterworth high-pass (Q = 1/sqrt(2)).
        const float w0 = 2.0f * PI_F * AUDIO_HP_HZ / (float)AUDIO_FS;
        const float alpha = sinf(w0) / (2.0f * 0.70710678f);
        const float c = cosf(w0);
        const float a0 = 1.0f + alpha;
        b0_ = ((1.0f + c) / 2.0f) / a0;
        b1_ = (-(1.0f + c)) / a0;
        b2_ = ((1.0f + c) / 2.0f) / a0;
        a1_ = (-2.0f * c) / a0;
        a2_ = (1.0f - alpha) / a0;
        // Filter states persist across windows (no start-up transient each
        // window); they are only zeroed here.
        dc_x1_ = dc_y1_ = 0.0f;
        hp_x1_ = hp_x2_ = hp_y1_ = hp_y2_ = 0.0f;
        reset();
    }

    // Clear the per-window accumulators (filter states are kept).
    void reset() {
        n_ = 0; s2_ = s4_ = 0.0; peak_ = 0.0f;
        hs2_ = hs4_ = 0.0; hpeak_ = 0.0f;
        n_blocks_ = 0;
        for (int k = 0; k <= AUDIO_BLOCK / 2; ++k) psd_[k] = 0.0;
    }

    // Process one block of raw 32-bit I2S words (INMP441: 24-bit data,
    // left-justified). `count` may be < AUDIO_BLOCK for a short DMA read;
    // short blocks still feed the time-domain statistics but skip the FFT.
    void processBlock(const int32_t* raw, int count) {
        double blk_s2 = 0.0;
        for (int i = 0; i < count; ++i) {
            // --- 4a: int32 -> int24 sample value (arithmetic shift keeps sign)
            const float x = (float)(raw[i] >> 8);
            // --- 4b: DC blocker  y[n] = x[n] - x[n-1] + R * y[n-1]
            const float y = x - dc_x1_ + AUDIO_DC_POLE * dc_y1_;
            dc_x1_ = x; dc_y1_ = y;
            // --- 4c: 2 kHz high-pass (direct form I)
            const float h = b0_ * y + b1_ * hp_x1_ + b2_ * hp_x2_ - a1_ * hp_y1_ - a2_ * hp_y2_;
            hp_x2_ = hp_x1_; hp_x1_ = y; hp_y2_ = hp_y1_; hp_y1_ = h;
            // --- 4d: moment accumulators
            const double y2 = (double)y * (double)y;
            const double h2 = (double)h * (double)h;
            s2_ += y2;  s4_ += y2 * y2;  blk_s2 += y2;
            hs2_ += h2; hs4_ += h2 * h2;
            const float ay = fabsf(y), ah = fabsf(h);
            if (ay > peak_) peak_ = ay;
            if (ah > hpeak_) hpeak_ = ah;
            // --- 4e: keep the DC-free sample for the FFT below
            if (i < AUDIO_BLOCK) frame_[i] = y;
        }
        n_ += (uint32_t)count;

        // --- 4f: per-block RMS list (used for blk_max / blk_p90)
        if (count > 0 && n_blocks_ < AUDIO_MAX_BLOCKS) {
            blk_rms_[n_blocks_] = (float)sqrt(blk_s2 / (double)count);
        }
        // --- 4g: Hann-windowed FFT of full blocks, accumulate power spectrum
        if (count == AUDIO_BLOCK) {
            for (int i = 0; i < AUDIO_BLOCK; ++i) {
                re_[i] = frame_[i] * fft_.hann(i);
                im_[i] = 0.0f;
            }
            fft_.forward(re_, im_);
            for (int k = 0; k <= AUDIO_BLOCK / 2; ++k) {
                psd_[k] += (double)re_[k] * re_[k] + (double)im_[k] * im_[k];
            }
            ++n_fft_in_window_;
        }
        if (count > 0 && n_blocks_ < AUDIO_MAX_BLOCKS) ++n_blocks_;
    }

    // Compute the window features and reset for the next window.
    void finish(AudioFeatures& out) {
        out.n = n_;
        const double n = (n_ > 0) ? (double)n_ : 1.0;
        // --- Time-domain statistics ---
        const double m2 = s2_ / n, m4 = s4_ / n;
        const double hm2 = hs2_ / n, hm4 = hs4_ / n;
        const float rms = (float)sqrt(m2);
        const float hrms = (float)sqrt(hm2);
        out.rms      = rms / AUDIO_LEGACY_DIV;
        out.peak     = peak_ / AUDIO_LEGACY_DIV;
        out.crest    = (rms > 0.0f) ? (peak_ / rms) : NAN;
        out.kurtosis = (m2 > 0.0) ? (float)(m4 / (m2 * m2)) : NAN;
        out.hp_rms   = hrms / AUDIO_LEGACY_DIV;
        out.hp_kurt  = (hm2 > 0.0) ? (float)(hm4 / (hm2 * hm2)) : NAN;

        // --- Block-RMS statistics (max and 90th percentile) ---
        if (n_blocks_ > 0) {
            float tmp[AUDIO_MAX_BLOCKS];
            memcpy(tmp, blk_rms_, sizeof(float) * n_blocks_);
            std::sort(tmp, tmp + n_blocks_);
            out.blk_max = tmp[n_blocks_ - 1] / AUDIO_LEGACY_DIV;
            // "lower" percentile index, identical to numpy method='lower'
            const int idx = (int)floor(0.9 * (double)(n_blocks_ - 1));
            out.blk_p90 = tmp[idx] / AUDIO_LEGACY_DIV;
        } else {
            out.blk_max = out.blk_p90 = NAN;
        }

        // --- Spectral features from the window-average power spectrum ---
        if (n_fft_in_window_ > 0) {
            double P[AUDIO_BLOCK / 2 + 1];
            for (int k = 0; k <= AUDIO_BLOCK / 2; ++k) P[k] = psd_[k] / (double)n_fft_in_window_;
            const float df = (float)AUDIO_FS / (float)AUDIO_BLOCK;
            double num = 0.0, den = 0.0;
            for (int k = 1; k < AUDIO_BLOCK / 2; ++k) {
                num += (double)k * df * P[k];
                den += P[k];
            }
            out.centroid_hz = (den > 0.0) ? (float)(num / den) : NAN;
            for (int b = 0; b < AUDIO_N_BANDS; ++b) {
                out.band[b] = bandRms(P, AUDIO_BLOCK, (float)AUDIO_FS, fft_.hannEnergy(),
                                      AUDIO_BAND_EDGES[b], AUDIO_BAND_EDGES[b + 1],
                                      b == AUDIO_N_BANDS - 1) / AUDIO_LEGACY_DIV;
            }
        } else {
            out.centroid_hz = NAN;
            for (int b = 0; b < AUDIO_N_BANDS; ++b) out.band[b] = NAN;
        }
        n_fft_in_window_ = 0;
        reset();
    }

private:
    FFT<AUDIO_BLOCK> fft_;
    // biquad coefficients and states
    float b0_ = 0, b1_ = 0, b2_ = 0, a1_ = 0, a2_ = 0;
    float dc_x1_ = 0, dc_y1_ = 0;
    float hp_x1_ = 0, hp_x2_ = 0, hp_y1_ = 0, hp_y2_ = 0;
    // per-window accumulators
    uint32_t n_ = 0;
    double s2_ = 0, s4_ = 0, hs2_ = 0, hs4_ = 0;
    float peak_ = 0, hpeak_ = 0;
    float blk_rms_[AUDIO_MAX_BLOCKS];
    int n_blocks_ = 0;
    int n_fft_in_window_ = 0;
    double psd_[AUDIO_BLOCK / 2 + 1];
    // scratch buffers
    float frame_[AUDIO_BLOCK];
    float re_[AUDIO_BLOCK];
    float im_[AUDIO_BLOCK];
};

// -------------------------------------------------------------------------
// SECTION 5: Vibration window features
// -------------------------------------------------------------------------
// Feature meaning:
//   mean[3]  per-axis mean (gravity vector -> sensor tilt / mounting)
//   std[3]   per-axis standard deviation (dynamic vibration level)
//   ptp[3]   per-axis peak-to-peak inside the window
//   mag_std  std of |a| (orientation-independent vibration level)
//   dom_hz   dominant frequency 0.5-45 Hz of the last 2.56 s (~drum speed)
//   dom_rms  RMS of the dominant peak (+/- 2 bins), all axes combined
//   band[4]  RMS in each VIB_BAND_EDGES band, all axes combined
// Spectral features use a 512-sample ring that spans window boundaries;
// they are NaN until 512 samples have ever been collected.
struct VibFeatures {
    uint32_t n;
    float mean[3], std[3], ptp[3];
    float mag_std;
    float dom_hz, dom_rms;
    float band[VIB_N_BANDS];
};

class VibWindow {
public:
    void init() {
        fft_.init();
        ring_pos_ = 0; ring_count_ = 0;
        reset();
    }

    void reset() {
        n_ = 0;
        for (int a = 0; a < 3; ++a) {
            sum_[a] = sumsq_[a] = 0.0;
            min_[a] = 1e30f; max_[a] = -1e30f;
        }
        msum_ = msumsq_ = 0.0;
    }

    // Add one acceleration sample (m/s^2).
    void addSample(float ax, float ay, float az) {
        const float v[3] = {ax, ay, az};
        for (int a = 0; a < 3; ++a) {
            sum_[a] += v[a];
            sumsq_[a] += (double)v[a] * v[a];
            if (v[a] < min_[a]) min_[a] = v[a];
            if (v[a] > max_[a]) max_[a] = v[a];
            ring_[a][ring_pos_] = v[a];
        }
        const double m = sqrt((double)ax * ax + (double)ay * ay + (double)az * az);
        msum_ += m; msumsq_ += m * m;
        ring_pos_ = (ring_pos_ + 1) % VIB_FFT;
        if (ring_count_ < VIB_FFT) ++ring_count_;
        ++n_;
    }

    // Copy the ring (oldest -> newest) for diagnostics (/accel.csv).
    int snapshot(float out[][3], int max_n) const {
        const int n = std::min(ring_count_, max_n);
        const int start = (ring_pos_ - n + VIB_FFT) % VIB_FFT;
        for (int i = 0; i < n; ++i) {
            const int j = (start + i) % VIB_FFT;
            out[i][0] = ring_[0][j]; out[i][1] = ring_[1][j]; out[i][2] = ring_[2][j];
        }
        return n;
    }

    void finish(VibFeatures& out) {
        out.n = n_;
        const double n = (n_ > 0) ? (double)n_ : 1.0;
        // --- Time-domain statistics (population std, ddof = 0) ---
        for (int a = 0; a < 3; ++a) {
            const double mu = sum_[a] / n;
            const double var = std::max(0.0, sumsq_[a] / n - mu * mu);
            out.mean[a] = (n_ > 0) ? (float)mu : NAN;
            out.std[a]  = (n_ > 0) ? (float)sqrt(var) : NAN;
            out.ptp[a]  = (n_ > 0) ? (max_[a] - min_[a]) : NAN;
        }
        {
            const double mu = msum_ / n;
            out.mag_std = (n_ > 0) ? (float)sqrt(std::max(0.0, msumsq_ / n - mu * mu)) : NAN;
        }

        // --- Spectral statistics over the last VIB_FFT samples ---
        if (ring_count_ == VIB_FFT) {
            double P[VIB_FFT / 2 + 1];
            for (int k = 0; k <= VIB_FFT / 2; ++k) P[k] = 0.0;
            for (int a = 0; a < 3; ++a) {
                // chronological copy + mean removal (detrend constant)
                double mu = 0.0;
                for (int i = 0; i < VIB_FFT; ++i) mu += ring_[a][i];
                mu /= (double)VIB_FFT;
                for (int i = 0; i < VIB_FFT; ++i) {
                    const int j = (ring_pos_ + i) % VIB_FFT;   // oldest first
                    re_[i] = (float)(ring_[a][j] - mu) * fft_.hann(i);
                    im_[i] = 0.0f;
                }
                fft_.forward(re_, im_);
                for (int k = 0; k <= VIB_FFT / 2; ++k) {
                    P[k] += (double)re_[k] * re_[k] + (double)im_[k] * im_[k];
                }
            }
            const float df = (float)VIB_FS / (float)VIB_FFT;
            // dominant peak search
            int kbest = -1; double pbest = -1.0;
            for (int k = 1; k < VIB_FFT / 2; ++k) {
                const float f = (float)k * df;
                if (f < VIB_DOM_LO_HZ || f > VIB_DOM_HI_HZ) continue;
                if (P[k] > pbest) { pbest = P[k]; kbest = k; }
            }
            if (kbest > 1 && kbest < VIB_FFT / 2 - 1) {
                // parabolic interpolation of the peak position
                const double pl = P[kbest - 1], pc = P[kbest], pr = P[kbest + 1];
                const double den = pl - 2.0 * pc + pr;
                const double delta = (den != 0.0) ? 0.5 * (pl - pr) / den : 0.0;
                out.dom_hz = (float)(((double)kbest + delta) * df);
                double acc = 0.0;
                for (int k = kbest - 2; k <= kbest + 2; ++k) {
                    if (k >= 1 && k < VIB_FFT / 2) acc += 2.0 * P[k];
                }
                out.dom_rms = (float)sqrt(acc / ((double)VIB_FFT * fft_.hannEnergy()));
            } else {
                out.dom_hz = out.dom_rms = NAN;
            }
            for (int b = 0; b < VIB_N_BANDS; ++b) {
                out.band[b] = bandRms(P, VIB_FFT, (float)VIB_FS, fft_.hannEnergy(),
                                      VIB_BAND_EDGES[b], VIB_BAND_EDGES[b + 1], false);
            }
        } else {
            out.dom_hz = out.dom_rms = NAN;
            for (int b = 0; b < VIB_N_BANDS; ++b) out.band[b] = NAN;
        }
        reset();
    }

private:
    FFT<VIB_FFT> fft_;
    uint32_t n_ = 0;
    double sum_[3], sumsq_[3];
    float min_[3], max_[3];
    double msum_ = 0, msumsq_ = 0;
    float ring_[3][VIB_FFT];
    int ring_pos_ = 0, ring_count_ = 0;
    float re_[VIB_FFT], im_[VIB_FFT];
};

}  // namespace pdm
