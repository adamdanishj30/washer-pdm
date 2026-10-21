// =========================================================================
// dsp_host_harness.cpp
// PC-side test driver for firmware/07_feature_streamer/pdm_dsp.h.
//
// Reads a binary file produced by test_dsp_parity.py:
//   int32 n_audio, int32 n_accel, int32[n_audio] raw I2S words,
//   float32[n_accel*3] acceleration samples (m/s^2)
// and feeds them through the SAME classes the ESP32 runs, using the same
// window rule as the firmware (157 audio blocks per window, accel samples
// interleaved at the 200 Hz / 16 kHz ratio). Prints one CSV line per window.
// =========================================================================
#include <cstdio>
#include <cstdlib>
#include <vector>
#include "../../firmware/07_feature_streamer/pdm_dsp.h"

int main(int argc, char** argv) {
    if (argc < 2) { std::fprintf(stderr, "usage: harness <input.bin>\n"); return 1; }
    FILE* f = std::fopen(argv[1], "rb");
    if (!f) { std::perror("open"); return 1; }
    int32_t na = 0, nv = 0;
    if (std::fread(&na, 4, 1, f) != 1 || std::fread(&nv, 4, 1, f) != 1) return 1;
    std::vector<int32_t> audio(na);
    std::vector<float> accel((size_t)nv * 3);
    if (std::fread(audio.data(), 4, na, f) != (size_t)na) return 1;
    if (std::fread(accel.data(), 4, (size_t)nv * 3, f) != (size_t)nv * 3) return 1;
    std::fclose(f);

    // Classes are large (FFT tables + buffers) -> heap, like a static global on the ESP32.
    pdm::AudioWindow* aw = new pdm::AudioWindow();
    pdm::VibWindow* vw = new pdm::VibWindow();
    aw->init(); vw->init();

    int blocks = 0, v_fed = 0;
    for (int start = 0; start + pdm::AUDIO_BLOCK <= na; start += pdm::AUDIO_BLOCK) {
        aw->processBlock(&audio[start], pdm::AUDIO_BLOCK);
        ++blocks;
        // accel samples that "arrived" during this audio block
        const long target = (long)(start + pdm::AUDIO_BLOCK) * pdm::VIB_FS / pdm::AUDIO_FS;
        while (v_fed < target && v_fed < nv) {
            vw->addSample(accel[3 * v_fed], accel[3 * v_fed + 1], accel[3 * v_fed + 2]);
            ++v_fed;
        }
        if (blocks % 157 == 0) {
            pdm::AudioFeatures a; pdm::VibFeatures v;
            aw->finish(a); vw->finish(v);
            std::printf("%u,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g,%.9g",
                        a.n, a.rms, a.peak, a.crest, a.kurtosis, a.hp_rms, a.hp_kurt,
                        a.blk_max, a.blk_p90, a.centroid_hz);
            for (int b = 0; b < pdm::AUDIO_N_BANDS; ++b) std::printf(",%.9g", a.band[b]);
            std::printf(",%u", v.n);
            for (int i = 0; i < 3; ++i) std::printf(",%.9g,%.9g,%.9g", v.mean[i], v.std[i], v.ptp[i]);
            std::printf(",%.9g,%.9g,%.9g", v.mag_std, v.dom_hz, v.dom_rms);
            for (int b = 0; b < pdm::VIB_N_BANDS; ++b) std::printf(",%.9g", v.band[b]);
            std::printf("\n");
        }
    }
    delete aw; delete vw;
    return 0;
}
